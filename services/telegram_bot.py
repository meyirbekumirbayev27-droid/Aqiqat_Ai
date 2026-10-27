"""AQIQAT AI Telegram боты. Сайттың анализаторларын қолданады, webhook арқылы жұмыс істейді.

Баптау: TELEGRAM_BOT_TOKEN айнымалысын қойыңыз — webhook сайт ашылғанда өзі тіркеледі."""
import base64
import hashlib
import json
import os
import re
from html import escape

import requests

from . import db as dbm
from . import factcheck, manipulation, media, privacy, quiz, scam, source
from .web import FetchError

API = "https://api.telegram.org/bot{token}/{method}"
FILE_API = "https://api.telegram.org/file/bot{token}/{path}"
MAX_LEN = 4000

BUTTONS = {
    "🔎 Ақпаратты тексеру": "check",
    "🌐 Дереккөз": "source",
    "🚨 Алаяқтық": "scam",
    "🧠 Манипуляция": "manip",
    "🔐 Жеке деректер": "privacy",
    "🖼 Сурет тексеру": "media",
    "🎮 Ойын": "quiz",
    "ℹ️ Көмек": "help",
}
COMMANDS = {"/check": "check", "/source": "source", "/scam": "scam", "/manip": "manip", "/privacy": "privacy",
            "/media": "media", "/quiz": "quiz", "/help": "help", "/start": "start"}
KEYBOARD = {
    "keyboard": [["🔎 Ақпаратты тексеру", "🌐 Дереккөз"], ["🚨 Алаяқтық", "🧠 Манипуляция"],
                 ["🔐 Жеке деректер", "🖼 Сурет тексеру"], ["🎮 Ойын", "ℹ️ Көмек"]],
    "resize_keyboard": True, "is_persistent": True,
    "input_field_placeholder": "Мәтін, сілтеме немесе сурет жіберіңіз",
}
PROMPTS = {
    "check": "🔎 Тексергіңіз келетін мәлімдемені немесе жаңалықты жіберіңіз.",
    "source": "🌐 Сайттың немесе мақаланың сілтемесін (URL) жіберіңіз.",
    "scam": "🚨 Күмәнді SMS, хат немесе хабарлама мәтінін жіберіңіз.",
    "manip": "🧠 Талданатын мәтінді (пост, мақала, үндеу) жіберіңіз.",
    "privacy": "🔐 Жарияламақ мәтініңізді жіберіңіз — жеке деректерді тауып, тазартып беремін.\n"
               "<i>Мәтін сақталмайды.</i>",
    "media": "🖼 Суретті <b>файл ретінде</b> жіберіңіз (📎 → Файл). Сурет ретінде жіберсеңіз, Telegram "
             "метадеректерді өшіріп тастайды.",
}
HELP = (
    "<b>AQIQAT AI</b> — жалған ақпаратты анықтауға көмектесетін бот.\n\n"
    "Төмендегі батырмалардың бірін басып, мәтін, сілтеме немесе сурет жіберіңіз:\n"
    "🔎 <b>Ақпаратты тексеру</b> — мәлімдемені AI мен Wikipedia бойынша тексеру\n"
    "🌐 <b>Дереккөз</b> — сайттың сенімділік белгілері\n"
    "🚨 <b>Алаяқтық</b> — SMS пен хаттағы алаяқтық белгілері\n"
    "🧠 <b>Манипуляция</b> — эмоциялық қысым мен бейтарап нұсқа\n"
    "🔐 <b>Жеке деректер</b> — телефон, ЖСН, карта, құпиясөзді бүркемелеу\n"
    "🖼 <b>Сурет тексеру</b> — метадеректер және өңдеу іздері\n"
    "🎮 <b>Ойын</b> — «Шындықты анықта!»\n\n"
    "Батырма баспай жіберсеңіз, мәтін түрін өзім анықтаймын.\n"
    "<i>Нәтижелер — кеңес, түпкілікті үкім емес.</i>"
)
VERDICT_ICON = {"likely_true": "✅", "likely_false": "❌", "insufficient": "⚠️"}
LEVEL_ICON = {"low": "🟢", "good": "🟢", "medium": "🟡", "high": "🔴", "bad": "🔴"}
URL_ONLY = re.compile(r"^\s*(https?://\S+|www\.\S+|[\w-]+(\.[\w-]+)+(/\S*)?)\s*$", re.I)


# ---------- Telegram API ----------

def token():
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def enabled():
    return bool(token())


def secret():
    """Webhook сұрауының шын Telegram-нан келгенін тексеруге арналған құпия (токеннен туындатылады)."""
    return hashlib.sha256(("aqiqat-tg:" + token()).encode()).hexdigest()[:48]


def call(method, files=None, **params):
    url = API.format(token=token(), method=method)
    try:
        if files:
            data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()}
            r = requests.post(url, data=data, files=files, timeout=30)
        else:
            r = requests.post(url, json=params, timeout=30)
        return r.json()
    except Exception:
        return {"ok": False}


_info = {"username": None, "webhook_checked": False}


def username():
    if not enabled():
        return None
    if _info["username"] is None:
        res = call("getMe")
        _info["username"] = (res.get("result") or {}).get("username") or ""
    return _info["username"] or None


def ensure_webhook(base_url):
    """Webhook-ты бір рет тексеріп, қажет болса тіркейді (әр сервер данасында бір рет)."""
    if not enabled() or _info["webhook_checked"] or not base_url.startswith("https://"):
        return
    _info["webhook_checked"] = True
    want = base_url.rstrip("/") + "/telegram/webhook"
    current = (call("getWebhookInfo").get("result") or {}).get("url")
    if current != want:
        call("setWebhook", url=want, secret_token=secret(), allowed_updates=["message", "callback_query"])
        call("setMyCommands", commands=[
            {"command": "check", "description": "Ақпаратты тексеру"},
            {"command": "source", "description": "Дереккөзді тексеру"},
            {"command": "scam", "description": "Алаяқтықты анықтау"},
            {"command": "manip", "description": "Манипуляцияны анықтау"},
            {"command": "privacy", "description": "Жеке деректерді тексеру"},
            {"command": "media", "description": "Суретті тексеру"},
            {"command": "quiz", "description": "Шындықты анықта! ойыны"},
            {"command": "help", "description": "Көмек"},
        ])


def send(chat_id, text, keyboard=None, **extra):
    chunks = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)] or [""]
    for i, chunk in enumerate(chunks):
        params = {"chat_id": chat_id, "text": chunk, "parse_mode": "HTML", "link_preview_options": {"is_disabled": True}}
        if keyboard is not None and i == len(chunks) - 1:
            params["reply_markup"] = keyboard
        params.update(extra)
        res = call("sendMessage", **params)
        if not res.get("ok"):
            # HTML қате болса, қарапайым мәтінмен қайталаймыз
            params.pop("parse_mode", None)
            params["text"] = re.sub(r"<[^>]+>", "", chunk)
            call("sendMessage", **params)


def typing(chat_id, action="typing"):
    call("sendChatAction", chat_id=chat_id, action=action)


# ---------- Чат күйі (таңдалған режим, ойын) ----------

def get_state(chat_id):
    row = dbm.get_db().execute("SELECT mode, quiz_json FROM tg_chats WHERE chat_id = ?", (str(chat_id),)).fetchone()
    if not row:
        return {"mode": None, "quiz": None}
    return {"mode": row["mode"], "quiz": json.loads(row["quiz_json"]) if row["quiz_json"] else None}


def set_state(chat_id, mode=..., quiz_state=...):
    cur = get_state(chat_id)
    mode = cur["mode"] if mode is ... else mode
    quiz_state = cur["quiz"] if quiz_state is ... else quiz_state
    db = dbm.get_db()
    db.execute(
        "INSERT INTO tg_chats (chat_id, mode, quiz_json, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (chat_id) DO UPDATE SET mode = excluded.mode, quiz_json = excluded.quiz_json, "
        "updated_at = excluded.updated_at",
        (str(chat_id), mode, json.dumps(quiz_state) if quiz_state else None, dbm.now_str()),
    )
    db.commit()


# ---------- Нәтижелерді форматтау ----------

def e(text):
    return escape(str(text or ""), quote=False)


def fmt_factcheck(r):
    lines = [f"{VERDICT_ICON[r['verdict']]} <b>{e(r['verdict_label'])}</b>"
             + (f" · сенімділік {r['confidence']}%" if r["verdict"] != "insufficient" else ""),
             e(r["summary"]), ""]
    signs = [f"• {e(f['text'])}" for f in r["flags"]]
    signs.append("• Дереккөзге сілтеме бар." if r["attributed"] else "• Мәтінде дереккөз көрсетілмеген.")
    signs.append(f"• Манипуляциялық тіл: {e(r['manipulation']['label'])}.")
    lines += ["<b>Белгілер:</b>", *signs, ""]
    ai = r.get("ai")
    if ai and ai.get("explanation"):
        lines += ["🤖 <b>AI түсіндірмесі</b> <i>(тексерілмеген пікір)</i>:", e(ai["explanation"]), ""]
    elif r["ai_status"].get("provider"):
        lines += ["🤖 <i>AI қазір жауап бермеді (тегін шектеу). Жарты минуттан кейін қайталаңыз.</i>", ""]
    if r["evidence"]:
        lines.append("📚 <b>Табылған материалдар:</b>")
        lines += [f"• <a href=\"{e(x['url'])}\">{e(x['title'])}</a> — {e(x['source'])}" for x in r["evidence"][:4]]
        lines.append("")
    lines.append("<b>Әрі қарай:</b>")
    lines += [f"• {e(t)}" for t in r["tips"][:3]]
    return "\n".join(lines)


def fmt_source(r):
    sig_icon = {"good": "✅", "bad": "❗", "info": "ℹ️"}
    rd = r.get("rdap") or {}
    rows = [("Тақырыбы", r["title"]), ("Сайт", r["site_name"]), ("Автор", r["author"] or "көрсетілмеген"),
            ("Жарияланған", r["published"] or "табылмады"),
            ("Домен тіркелген", (rd.get("registered") or "")[:10] or "белгісіз"), ("Тіркеуші", rd.get("registrar"))]
    lines = [f"{LEVEL_ICON.get(r['level'], '•')} <b>{e(r['label'])}</b> · {r['score']}/100",
             f"<code>{e(r['host'])}</code> · HTTP {r['http_status']}", ""]
    lines += [f"<b>{k}:</b> {e(v)}" for k, v in rows if v]
    lines += ["", "<b>Сенімділік белгілері:</b>"]
    lines += [f"{sig_icon.get(s['type'], '•')} {e(s['text'])}" for s in r["signals"]]
    if r["related"]:
        lines += ["", "📚 <b>Байланысты материалдар:</b>"]
        lines += [f"• <a href=\"{e(x['url'])}\">{e(x['title'])}</a>" for x in r["related"][:3]]
    lines += ["", f"<i>{e(r['note'])}</i>"]
    return "\n".join(lines)


def fmt_scam(r):
    lines = [f"{LEVEL_ICON[r['level']]} Тәуекел деңгейі: <b>{e(r['label'])}</b> · {r['score']}/100", e(r["summary"]), ""]
    for s in r["signals"]:
        lines += [f"❗ <b>{e(s['label'])}</b>", f"{e(s['why'])}", f"→ <i>{e(s['advice'])}</i>", ""]
    for u in r["urls"]:
        if u["flags"]:
            lines.append(f"🔗 <code>{e(u['host'] or u['url'])}</code>")
            lines += [f"  • {e(f)}" for f in u["flags"]]
            lines.append("")
    lines.append("<b>Кеңес:</b>")
    lines += [f"• {e(a)}" for a in r["advice"]]
    return "\n".join(lines)


def fmt_manip(r):
    lines = [f"{LEVEL_ICON[r['level']]} <b>{e(r['label'])}</b> · қарқын {r['intensity']}/100", ""]
    by_cat = {}
    for f in r["flags"]:
        by_cat.setdefault(f["category"], []).append(f["text"])
    for c in r["categories"]:
        found = ", ".join(f"«{e(t)}»" for t in by_cat.get(c["key"], [])[:5])
        lines += [f"• <b>{e(c['label'])}</b> ({c['count']}): {found}", f"  <i>{e(c['why'])}</i>"]
    if r["flags"]:
        lines += ["", "✍️ <b>Бейтарап нұсқа:</b>", f"<blockquote>{e(r['neutral'])}</blockquote>"]
    lines += ["", f"<i>{e(r['note'])}</i>"]
    return "\n".join(lines)


def fmt_privacy(r):
    lines = [f"{LEVEL_ICON[r['level']]} <b>{e(r['label'])}</b>"]
    if r["groups"]:
        lines.append("")
        for gr in r["groups"]:
            masked = ", ".join(e(i["masked"]) for i in r["items"] if i["type"] == gr["type"])[:200]
            lines += [f"• <b>{e(gr['label'])}</b> ({gr['count']}): <code>{masked}</code>", f"  <i>{e(gr['why'])}</i>"]
        lines += ["", "🧹 <b>Жариялауға қауіпсіз нұсқа:</b>", f"<pre>{e(r['redacted'])}</pre>"]
    else:
        lines.append("Мәтінде жеке немесе құпия деректер үлгілері табылмады.")
    lines += ["", "<i>Мәтін сақталмайды.</i>"]
    return "\n".join(lines)


def fmt_media(r):
    icon = {"good": "✅", "bad": "❗", "warn": "⚠️", "info": "ℹ️"}
    lines = [f"{LEVEL_ICON[r['level']]} <b>{e(r['label'])}</b>", ""]
    lines += [f"<b>{e(k)}:</b> {e(v)}" for k, v in r["info"].items()]
    if r["metadata"]:
        lines += ["", "<b>Метадеректер:</b>"] + [f"• {e(k)}: {e(v)}" for k, v in r["metadata"].items()]
    lines += ["", "<b>Белгілер:</b>"] + [f"{icon.get(f['type'], '•')} {e(f['text'])}" for f in r["findings"]]
    lines += ["", "Түпнұсқаны іздеу: <a href=\"https://lens.google.com/\">Google Lens</a> · "
                  "<a href=\"https://tineye.com/\">TinEye</a>", "", f"<i>{e(r['note'])}</i>"]
    return "\n".join(lines)


# ---------- Ойын ----------

def quiz_question(chat_id, state):
    q = quiz.BY_ID[state["ids"][state["idx"]]]
    kb = {"inline_keyboard": [[{"text": "✓ Шынайы", "callback_data": f"q:{q['id']}:true"},
                               {"text": "✕ Жалған", "callback_data": f"q:{q['id']}:false"}],
                              [{"text": "? Дәлел жеткіліксіз", "callback_data": f"q:{q['id']}:unknown"}]]}
    send(chat_id, f"🎮 <b>Сұрақ {state['idx'] + 1}/{len(state['ids'])}</b> · {e(q['category'])}\n"
                  f"Ұпай: {state['score']}\n\n<b>{e(q['claim'])}</b>", kb)


def quiz_start(chat_id):
    state = quiz.new_round()
    set_state(chat_id, quiz_state=state)
    send(chat_id, "🎯 <b>Шындықты анықта!</b>\n10 сұрақ. Дұрыс жауап — 10 ұпай, қатарынан дұрыс жауапқа бонус.")
    quiz_question(chat_id, state)


def quiz_answer(chat_id, message_id, qid, answer):
    state = get_state(chat_id)["quiz"]
    if not state or state["idx"] >= len(state["ids"]) or state["ids"][state["idx"]] != qid:
        return "Бұл сұрақ ескірген. /quiz арқылы жаңа ойын бастаңыз."
    q = quiz.BY_ID[qid]
    correct = answer == q["answer"]
    gained = 0
    if correct:
        state["correct"] += 1
        state["streak"] += 1
        state["best_streak"] = max(state["best_streak"], state["streak"])
        gained = 10 + min(state["streak"] - 1, 4) * 2
        state["score"] += gained
    else:
        state["streak"] = 0
    state["idx"] += 1
    finished = state["idx"] >= len(state["ids"])
    src = "\n".join(f"📎 <a href=\"{e(s['url'])}\">{e(s['title'])}</a>" for s in q["sources"])
    head = f"✅ <b>Дұрыс! +{gained} ұпай</b>" if correct else f"❌ <b>Қате.</b> Дұрыс жауап: «{quiz.ANSWERS[q['answer']]}»"
    text = f"<b>{e(q['claim'])}</b>\n\n{head}\n{e(q['explain'])}" + (f"\n{src}" if src else "")
    kb = {"inline_keyboard": [[{"text": "Нәтижені көру 🏁" if finished else "Келесі сұрақ →", "callback_data": "q:next"}]]}
    call("editMessageText", chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML",
         reply_markup=kb, link_preview_options={"is_disabled": True})
    set_state(chat_id, quiz_state=state)
    return "Дұрыс! ✅" if correct else "Қате ❌"


def quiz_next(chat_id):
    state = get_state(chat_id)["quiz"]
    if not state:
        return quiz_start(chat_id)
    if state["idx"] < len(state["ids"]):
        return quiz_question(chat_id, state)
    pct = round(state["correct"] / len(state["ids"]) * 100)
    medal = "🏆" if pct >= 80 else "⭐" if pct >= 50 else "📚"
    send(chat_id, f"{medal} <b>Ойын аяқталды!</b>\nҰпай: <b>{state['score']}</b>\n"
                  f"Дұрыс жауап: {state['correct']}/{len(state['ids'])}\nЕң ұзын серия: {state['best_streak']}",
         {"inline_keyboard": [[{"text": "↻ Қайта ойнау", "callback_data": "q:restart"}]]})
    set_state(chat_id, quiz_state=None)


# ---------- Негізгі өңдеу ----------

def run_tool(chat_id, mode, text):
    if mode == "check":
        if len(text) < 15:
            return send(chat_id, "Мәлімдемені толығырақ жазыңыз (кемінде 15 таңба).")
        typing(chat_id)
        return send(chat_id, fmt_factcheck(factcheck.analyze(text[:5000])))
    if mode == "source":
        typing(chat_id)
        try:
            return send(chat_id, fmt_source(source.analyze(text.split()[0])))
        except FetchError as ex:
            return send(chat_id, f"⚠️ {e(ex)}")
    if mode == "scam":
        return send(chat_id, fmt_scam(scam.analyze(text[:6000])))
    if mode == "manip":
        if len(text) < 20:
            return send(chat_id, "Талдау үшін кемінде 20 таңба жіберіңіз.")
        return send(chat_id, fmt_manip(manipulation.analyze(text[:8000])))
    if mode == "privacy":
        return send(chat_id, fmt_privacy(privacy.analyze(text[:8000])))
    if mode == "media":
        return send(chat_id, PROMPTS["media"])


def auto_mode(text):
    if URL_ONLY.match(text):
        return "source"
    if privacy.find_items(text):
        return "privacy"
    if scam.analyze(text)["score"] >= 25:
        return "scam"
    return "check"


def handle_file(chat_id, file_id, filename):
    info = call("getFile", file_id=file_id).get("result") or {}
    if not info.get("file_path"):
        return send(chat_id, "⚠️ Файлды жүктеу мүмкін болмады (Telegram боттарға 20 МБ-қа дейін рұқсат етеді).")
    typing(chat_id, "upload_photo")
    try:
        data = requests.get(FILE_API.format(token=token(), path=info["file_path"]), timeout=40).content
        r = media.analyze(data, filename)
    except media.MediaError as ex:
        return send(chat_id, f"⚠️ {e(ex)}")
    except Exception:
        return send(chat_id, "⚠️ Файлды талдау кезінде қате шықты.")
    send(chat_id, fmt_media(r))
    if r.get("ela") and r["ela"].get("image"):
        png = base64.b64decode(r["ela"]["image"].split(",", 1)[1])
        call("sendPhoto", files={"photo": ("ela.png", png, "image/png")}, chat_id=chat_id,
             caption="ELA картасы: ашық аймақтар қайта сығуға басқаша жауап береді. "
                     "Біркелкі жарық жиектер мен мәтін — қалыпты құбылыс.")


def handle_update(update):
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        note = None
        if data.startswith("q:") and data.count(":") == 2:
            _, qid, ans = data.split(":")
            note = quiz_answer(chat_id, cq["message"]["message_id"], int(qid), ans) if qid.isdigit() else None
        elif data == "q:next":
            quiz_next(chat_id)
        elif data == "q:restart":
            quiz_start(chat_id)
        call("answerCallbackQuery", callback_query_id=cq["id"], **({"text": note} if note else {}))
        return

    msg = update.get("message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    if msg.get("document"):
        doc = msg["document"]
        return handle_file(chat_id, doc["file_id"], doc.get("file_name") or "file.jpg")
    if msg.get("photo"):
        send(chat_id, "ℹ️ Сурет қысылған түрде келді — Telegram метадеректерді өшіреді. "
                      "Толық тексеру үшін суретті <b>файл ретінде</b> жіберіңіз.")
        return handle_file(chat_id, msg["photo"][-1]["file_id"], "photo.jpg")

    text = (msg.get("text") or msg.get("caption") or "").strip()
    if not text:
        return send(chat_id, "Мәтін, сілтеме немесе сурет жіберіңіз.", KEYBOARD)

    first = text.split(maxsplit=1)
    cmd = first[0].split("@")[0].lower()
    mode = BUTTONS.get(text) or COMMANDS.get(cmd)
    if mode:
        rest = first[1].strip() if cmd in COMMANDS and len(first) > 1 else ""
        if mode == "start":
            set_state(chat_id, mode=None)
            name = e(msg.get("from", {}).get("first_name", ""))
            return send(chat_id, f"Сәлем, {name}! 👋\n\n" + HELP, KEYBOARD)
        if mode == "help":
            return send(chat_id, HELP, KEYBOARD)
        if mode == "quiz":
            return quiz_start(chat_id)
        set_state(chat_id, mode=mode)
        if rest:
            return run_tool(chat_id, mode, rest)
        return send(chat_id, PROMPTS[mode], KEYBOARD)

    mode = get_state(chat_id)["mode"] or auto_mode(text)
    run_tool(chat_id, mode, text)
