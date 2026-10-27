"""AQIQAT AI — жалған ақпаратты анықтауға көмектесетін веб-қосымша."""
import json
import os
import re
import secrets
import time
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from services import db as dbm
from services import factcheck, llm, manipulation, media, privacy, quiz, scam, source
from services.web import FetchError

BASE_DIR = Path(__file__).resolve().parent


def load_env():
    env = BASE_DIR / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


load_env()
# Vercel сияқты serverless ортада жоба папкасы тек оқуға арналған — жазуға тек /tmp рұқсат етілген
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
DATA_DIR = Path(os.environ.get("DATA_DIR") or ("/tmp/aqiqat" if IS_SERVERLESS else BASE_DIR / "instance"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    path = DATA_DIR / "secret_key"
    if not path.exists():
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


app = Flask(__name__)
app.config.update(
    SECRET_KEY=secret_key(),
    DATABASE=os.environ.get("DATABASE_PATH") or str(DATA_DIR / "aqiqat.db"),
    MAX_CONTENT_LENGTH=61 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
)
app.json.sort_keys = False
dbm.init_db(app.config["DATABASE"])
app.teardown_appcontext(dbm.close_db)

TOOLS = {
    "factcheck": {"title": "Ақпаратты тексеру", "endpoint": "index", "icon": "spark"},
    "source": {"title": "Дереккөзді тексеру", "endpoint": "source_checker", "icon": "globe"},
    "media": {"title": "Сурет пен видеоны тексеру", "endpoint": "media_checker", "icon": "image"},
    "scam": {"title": "Алаяқтықты анықтау", "endpoint": "scam_detector", "icon": "alert"},
    "manipulation": {"title": "Манипуляцияны анықтау", "endpoint": "manipulation_detector", "icon": "brain"},
    "privacy": {"title": "Жеке деректер қауіпсіздігі", "endpoint": "privacy_checker", "icon": "lock"},
    "quiz": {"title": "Шындықты анықтау ойыны", "endpoint": "fact_challenge", "icon": "game"},
}
FEATURES = [
    {"key": "source", "endpoint": "source_checker", "title": "Дереккөзді тексеру", "emoji": "🌐",
     "text": "Сайттың домені, авторы, жарияланған күні және сенімділік белгілері.", "accent": "cyan"},
    {"key": "media", "endpoint": "media_checker", "title": "Сурет пен видеоны тексеру", "emoji": "🖼️",
     "text": "Метадеректер, өңдеу іздері, ELA картасы және AI генерация белгілері.", "accent": "blue"},
    {"key": "scam", "endpoint": "scam_detector", "title": "Алаяқтықты анықтау", "emoji": "🚨",
     "text": "SMS, хат және сілтемелердегі алаяқтық белгілері мен тәуекел деңгейі.", "accent": "red"},
    {"key": "manipulation", "endpoint": "manipulation_detector", "title": "Манипуляцияны анықтау", "emoji": "🧠",
     "text": "Эмоциялық қысым, қорқыту, жалпылау және бейтарап балама тұжырым.", "accent": "violet"},
    {"key": "privacy", "endpoint": "privacy_checker", "title": "Жеке деректер қауіпсіздігі", "emoji": "🔐",
     "text": "Телефон, ЖСН, карта, құпиясөз, API кілттерін тауып, бүркемелеу.", "accent": "magenta"},
    {"key": "quiz", "endpoint": "fact_challenge", "title": "Шындықты анықта!", "emoji": "🎮",
     "text": "Сыни ойлауды ойын арқылы дамыт: ұпай, деңгей, жетістіктер.", "accent": "green"},
]


# ---------- Көмекші функциялар ----------

@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        row = dbm.get_db().execute("SELECT id, username, display_name, created_at FROM users WHERE id = ?", (uid,)).fetchone()
        if row:
            g.user = row
        else:
            session.clear()
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)


@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not token or not secrets.compare_digest(token, session.get("csrf", "")):
            if request.path.startswith("/api/"):
                return jsonify(error="Қауіпсіздік белгісі ескірген. Бетті жаңартып, қайталап көріңіз."), 400
            flash("Қауіпсіздік белгісі ескірген. Қайталап көріңіз.", "error")
            return redirect(request.url)


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return resp


@app.context_processor
def inject_globals():
    return {"csrf_token": session.get("csrf", ""), "user": g.get("user"), "TOOLS": TOOLS, "FEATURES": FEATURES}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Жүйеге кіру қажет."), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def json_text(field, min_len=1, max_len=8000):
    data = request.get_json(silent=True) or {}
    text = str(data.get(field, "")).strip()
    if len(text) < min_len:
        abort(_bad(f"Кемінде {min_len} таңба енгізіңіз."))
    if len(text) > max_len:
        abort(_bad(f"Мәтін тым ұзын: ең көбі {max_len} таңба."))
    return text, data


def _bad(msg, code=400):
    resp = jsonify(error=msg)
    resp.status_code = code
    return resp


def short(text, n=90):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------- Беттер ----------

@app.route("/")
def index():
    return render_template("index.html", ai=llm.status())


@app.route("/source-checker")
@login_required
def source_checker():
    return render_template("source_checker.html", tool="source")


@app.route("/media-checker")
@login_required
def media_checker():
    return render_template("media_checker.html", tool="media")


@app.route("/scam-detector")
@login_required
def scam_detector():
    return render_template("scam_detector.html", tool="scam")


@app.route("/manipulation-detector")
@login_required
def manipulation_detector():
    return render_template("manipulation_detector.html", tool="manipulation")


@app.route("/privacy-checker")
@login_required
def privacy_checker():
    return render_template("privacy_checker.html", tool="privacy")


@app.route("/fact-challenge")
@login_required
def fact_challenge():
    best = dbm.get_db().execute(
        "SELECT MAX(score) AS best, COUNT(*) AS games FROM quiz_results WHERE user_id = ?", (g.user["id"],)).fetchone()
    return render_template("fact_challenge.html", tool="quiz", best=best, achievements=quiz.ACHIEVEMENTS)


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="images/favicon.svg"), 301)


@app.route("/learn")
def learn():
    return render_template("learn.html")


@app.route("/about")
def about():
    return render_template("about.html", ai=llm.status())


@app.route("/history")
@login_required
def history():
    tool = request.args.get("tool", "")
    db = dbm.get_db()
    params = [g.user["id"]]
    sql = "SELECT id, tool, title, verdict, level, created_at FROM analyses WHERE user_id = ?"
    if tool in TOOLS:
        sql += " AND tool = ?"
        params.append(tool)
    rows = db.execute(sql + " ORDER BY id DESC LIMIT 200", params).fetchall()
    stats = {r["tool"]: r["n"] for r in db.execute(
        "SELECT tool, COUNT(*) AS n FROM analyses WHERE user_id = ? GROUP BY tool", (g.user["id"],))}
    games = db.execute("SELECT score, correct, total, best_streak, created_at FROM quiz_results WHERE user_id = ? "
                       "ORDER BY id DESC LIMIT 10", (g.user["id"],)).fetchall()
    return render_template("history.html", rows=rows, stats=stats, games=games, active_tool=tool,
                           total=sum(stats.values()))


@app.route("/history/<int:item_id>")
@login_required
def history_item(item_id):
    row = dbm.get_db().execute("SELECT * FROM analyses WHERE id = ? AND user_id = ?", (item_id, g.user["id"])).fetchone()
    if row is None:
        abort(404)
    return render_template("history_item.html", item=row, result=json.loads(row["result_json"]))


@app.route("/history/<int:item_id>/delete", methods=["POST"])
@login_required
def history_delete(item_id):
    db = dbm.get_db()
    db.execute("DELETE FROM analyses WHERE id = ? AND user_id = ?", (item_id, g.user["id"]))
    db.commit()
    flash("Жазба тарихтан өшірілді.", "success")
    return redirect(url_for("history"))


@app.route("/history/clear", methods=["POST"])
@login_required
def history_clear():
    db = dbm.get_db()
    db.execute("DELETE FROM analyses WHERE user_id = ?", (g.user["id"],))
    db.commit()
    flash("Бүкіл тарих тазартылды.", "success")
    return redirect(url_for("history"))


# ---------- Аутентификация ----------

_failed = {}


def _throttled(key):
    fails, ts = _failed.get(key, (0, 0))
    return fails >= 5 and time.time() - ts < 300


def _safe_next(target):
    if target and target.startswith("/") and not target.startswith(("//", "/\\")) and "\\" not in target:
        return target
    return url_for("index")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        key = (request.remote_addr, username.lower())
        if _throttled(key):
            flash("Тым көп сәтсіз әрекет. 5 минуттан кейін қайталап көріңіз.", "error")
            return render_template("login.html", username=username), 429
        row = dbm.get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            _failed.pop(key, None)
            csrf = session.get("csrf")
            session.clear()
            session["uid"] = row["id"]
            session["csrf"] = csrf or secrets.token_urlsafe(32)
            session.permanent = bool(request.form.get("remember"))
            flash(f"Қош келдіңіз, {row['display_name']}!", "success")
            return redirect(_safe_next(request.form.get("next")))
        fails, _ = _failed.get(key, (0, 0))
        _failed[key] = (fails + 1, time.time())
        flash("Логин немесе құпиясөз қате.", "error")
        return render_template("login.html", username=username), 401
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display = request.form.get("display_name", "").strip() or username
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        errors = []
        if not re.fullmatch(r"[A-Za-z0-9_.\-]{3,32}", username):
            errors.append("Логин 3–32 таңбадан тұруы керек: латын әріптері, сандар, _ . -")
        if len(display) > 40:
            errors.append("Аты-жөні 40 таңбадан аспауы керек.")
        if len(password) < 8 or not re.search(r"[^\W\d_]", password) or not re.search(r"\d", password):
            errors.append("Құпиясөз кемінде 8 таңба, оның ішінде әріп пен сан болуы керек.")
        if password != confirm:
            errors.append("Құпиясөздер сәйкес келмейді.")
        db = dbm.get_db()
        if not errors and db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            errors.append("Бұл логин бос емес. Басқасын таңдаңыз.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", username=username, display_name=display), 400
        cur = db.execute("INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
                         (username, display, generate_password_hash(password)))
        db.commit()
        csrf = session.get("csrf")
        session.clear()
        session["uid"] = cur.lastrowid
        session["csrf"] = csrf or secrets.token_urlsafe(32)
        flash("Тіркелу сәтті өтті! AQIQAT AI-ға қош келдіңіз.", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Жүйеден шықтыңыз.", "success")
    return redirect(url_for("index"))


# ---------- API ----------

@app.post("/api/factcheck")
@login_required
def api_factcheck():
    text, _ = json_text("text", 15, 5000)
    result = factcheck.analyze(text)
    result["input"] = short(text, 400)
    result["history_id"] = dbm.save_analysis(g.user["id"], "factcheck", short(text), result["verdict_label"],
                                             result["verdict"], result)
    return jsonify(result)


@app.post("/api/source")
@login_required
def api_source():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    text = str(data.get("text", "")).strip()[:5000]
    try:
        result = source.analyze(url, text)
    except FetchError as e:
        return _bad(str(e), 422)
    result["history_id"] = dbm.save_analysis(g.user["id"], "source", result["title"] or result["host"],
                                             result["label"], result["level"], result)
    return jsonify(result)


@app.post("/api/media")
@login_required
def api_media():
    f = request.files.get("file")
    if not f or not f.filename:
        return _bad("Файл таңдалмады.")
    data = f.read()
    if not data:
        return _bad("Файл бос.")
    try:
        result = media.analyze(data, f.filename)
    except media.MediaError as e:
        return _bad(str(e), 422)
    stored = dict(result)
    if stored.get("ela"):
        stored["ela"] = {k: v for k, v in stored["ela"].items() if k != "image"}
    result["history_id"] = dbm.save_analysis(g.user["id"], "media", result["filename"], result["label"],
                                             result["level"], stored)
    return jsonify(result)


@app.post("/api/scam")
@login_required
def api_scam():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    url = str(data.get("url", "")).strip()[:2000]
    if len(text) < 5 and not url:
        return _bad("Хабарлама мәтінін немесе сілтемені енгізіңіз.")
    if len(text) > 6000:
        return _bad("Мәтін тым ұзын: ең көбі 6000 таңба.")
    result = scam.analyze(text, url)
    result["input"] = text
    result["history_id"] = dbm.save_analysis(g.user["id"], "scam", short(text or url), f"Тәуекел: {result['label']}",
                                             result["level"], result)
    return jsonify(result)


@app.post("/api/manipulation")
@login_required
def api_manipulation():
    text, _ = json_text("text", 20, 8000)
    result = manipulation.analyze(text)
    result["input"] = text
    result["history_id"] = dbm.save_analysis(g.user["id"], "manipulation", short(text), result["label"],
                                             result["level"], result)
    return jsonify(result)


@app.post("/api/privacy")
@login_required
def api_privacy():
    text, _ = json_text("text", 5, 8000)
    result = privacy.analyze(text)
    # Тарихқа тек жиынтық сақталады — құпия мәтін емес
    stored = {"level": result["level"], "label": result["label"], "groups": result["groups"],
              "total": result["total"], "note": result["note"]}
    result["history_id"] = dbm.save_analysis(g.user["id"], "privacy",
                                             f"Мәтін тексерілді ({len(text)} таңба)", result["label"],
                                             result["level"], stored)
    return jsonify(result)


@app.post("/api/quiz/start")
@login_required
def api_quiz_start():
    state = quiz.new_round()
    session["quiz"] = state
    return jsonify(question=quiz.public_question(state), score=0, streak=0, level_name=quiz.level_name(1))


@app.post("/api/quiz/answer")
@login_required
def api_quiz_answer():
    state = session.get("quiz")
    data = request.get_json(silent=True) or {}
    answer = data.get("answer")
    if not state or state["idx"] >= len(state["ids"]):
        return _bad("Ойын басталмаған. «Ойынды бастау» батырмасын басыңыз.", 409)
    if answer not in quiz.ANSWERS:
        return _bad("Жауап нұсқасы дұрыс емес.")
    q = quiz.BY_ID[state["ids"][state["idx"]]]
    if data.get("id") != q["id"]:
        return _bad("Сұрақ ескірген. Бетті жаңартыңыз.", 409)
    correct = answer == q["answer"]
    new_ach = []

    def unlock(key):
        if key not in state["achievements"]:
            state["achievements"].append(key)
            new_ach.append(dict(quiz.ACHIEVEMENTS[key], key=key))

    gained = 0
    if correct:
        state["correct"] += 1
        state["streak"] += 1
        state["best_streak"] = max(state["best_streak"], state["streak"])
        gained = 10 + min(state["streak"] - 1, 4) * 2
        state["score"] += gained
        unlock("first")
        if state["streak"] >= 3:
            unlock("streak3")
        if state["streak"] >= 5:
            unlock("streak5")
        if q["answer"] == "unknown":
            unlock("careful")
    else:
        state["streak"] = 0
    state["idx"] += 1
    finished = state["idx"] >= len(state["ids"])
    payload = {
        "correct": correct, "gained": gained, "right_answer": q["answer"], "right_label": quiz.ANSWERS[q["answer"]],
        "explain": q["explain"], "sources": q["sources"], "score": state["score"], "streak": state["streak"],
        "correct_count": state["correct"], "answered": state["idx"], "new_achievements": new_ach,
        "finished": finished,
    }
    if finished:
        if state["correct"] == len(state["ids"]):
            unlock("perfect")
            payload["new_achievements"] = new_ach
        db = dbm.get_db()
        db.execute("INSERT INTO quiz_results (user_id, score, correct, total, best_streak, achievements) "
                   "VALUES (?, ?, ?, ?, ?, ?)",
                   (g.user["id"], state["score"], state["correct"], len(state["ids"]), state["best_streak"],
                    json.dumps(state["achievements"])))
        db.commit()
        payload["summary"] = {"score": state["score"], "correct": state["correct"], "total": len(state["ids"]),
                              "best_streak": state["best_streak"],
                              "achievements": [dict(quiz.ACHIEVEMENTS[k], key=k) for k in state["achievements"]]}
        session.pop("quiz", None)
    else:
        payload["next"] = quiz.public_question(state)
        payload["level_name"] = quiz.level_name(payload["next"]["level"])
        session["quiz"] = state
    session.modified = True
    return jsonify(payload)


@app.get("/api/quiz/leaderboard")
@login_required
def api_leaderboard():
    rows = dbm.get_db().execute(
        "SELECT u.display_name AS name, MAX(q.score) AS score FROM quiz_results q JOIN users u ON u.id = q.user_id "
        "GROUP BY q.user_id ORDER BY score DESC LIMIT 10").fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- Қателер ----------

@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return _bad("Табылмады.", 404)
    return render_template("error.html", code=404, message="Бет табылмады."), 404


@app.errorhandler(413)
def too_large(_e):
    return _bad("Файл тым үлкен: ең көбі 60 МБ.", 413)


@app.errorhandler(500)
def server_error(_e):
    if request.path.startswith("/api/"):
        return _bad("Серверде күтпеген қате орын алды. Қайталап көріңіз.", 500)
    return render_template("error.html", code=500, message="Серверде күтпеген қате орын алды."), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
