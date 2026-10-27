"""Басты беттегі ақпаратты тексеру: мәтін белгілері + Wikipedia дәлелдері + AI түсіндірмесі."""
import re
from concurrent.futures import ThreadPoolExecutor

from . import llm, manipulation, web

VERDICTS = {
    "likely_true": "Шынайы болуы мүмкін",
    "likely_false": "Жалған болуы мүмкін",
    "insufficient": "Тексеруге дәлел жеткіліксіз",
}

STOP = set("""және мен бен пен да де та те ол бұл осы сол бір үшін туралы деп деген болды болып еді екен ғой
қазір енді тек барлық әр өте ең жоқ бар немесе бірақ сондай оның олар біз сіз мына сияқты кейін бойынша
дейін арқылы жылы жыл және что это как но по из за для или так все уже его она они был была были будет
есть который также только можно нужно the a an is are was were of to in on and or for with that this it be by as at from
""".split())

RED_FLAGS = [
    ("share", r"бөлісіңіз|таратыңыз|барлығына жіберіңіз|репост\w*|поделитесь|перешлите|share this|forward this",
     "Таратуға шақыру — жалған хабарламаларға тән."),
    ("hidden", r"жасырады|жасырып отыр|үндемейді|шындықты айтпайды|скрывают|молчат|не расскажут|they hide",
     "«Шындықты жасырады» деген қастандық риторикасы."),
    ("anon", r"белгісіз дереккөз|инсайдер\w*|танысым айтты|досым айтты|бір дәрігер айтты|анонимн\w* источник|знакомый врач|друг рассказал",
     "Тексерілмейтін, анонимді дереккөзге сілтеме."),
    ("miracle", r"толық емдейді|бір күнде жазады|100\s*%|кепілдік береді|лечит все|чудо[\s\-]?средств\w*|излечивает|cures? (?:all|everything)",
     "Ғажайып нәтиже не 100% кепілдік уәдесі."),
    ("shock", r"сенсация\w*|шок\w*|сұмдық|шокирующ\w*|breaking|срочная новость",
     "Сенсациялық, эмоциялық тақырып."),
]
ATTRIBUTION = r"мәлімдеді|хабарлады|мәліметінше|дерегінше|мәліметі бойынша|сәйкес|жариялады|деп хабарлайды|" \
              r"сообщил\w*|по данным|заявил\w*|according to|reported|https?://|www\."


HYPE = ("шұғыл", "сұмдық", "шок", "сенсац", "барлығ", "тарат", "бөліс", "жасыр", "үндеме", "толық", "кепіл",
        "дереу", "срочн", "поделит", "скрыва", "перешл", "внимани", "назар", "жаңалық", "хабар", "деген", "айтты",
        "емдейді", "аптада", "күні", "ертең", "бүгін", "кеше")


def _stem(word: str) -> str:
    return word.lower()[:5]


def keywords(text: str, n: int = 6):
    words = re.findall(r"[^\W\d_][\w\-]{2,}", text)
    seen, low = [], set()
    for w in words:
        lw = w.lower()
        if lw in STOP or lw in low or len(lw) < 4 or lw.startswith(HYPE) or (w.isupper() and len(w) > 4):
            continue
        low.add(lw)
        seen.append(w)
    caps = [w for w in seen if w[0].isupper()]
    rest = [w for w in seen if w not in caps]
    return (caps + rest)[:n]


def text_signals(text: str):
    flags = []
    for key, pat, label in RED_FLAGS:
        m = re.search(pat, text, re.I)
        if m:
            flags.append({"key": key, "text": label, "match": m.group(0)})
    caps = re.findall(r"\b[A-ZА-ЯӘҒҚҢӨҰҮҺІ]{5,}\b", text)
    if len(caps) >= 2:
        flags.append({"key": "caps", "text": "Бас әріптермен жазылған айқай сөздер.", "match": caps[0]})
    if re.search(r"!{2,}", text):
        flags.append({"key": "excl", "text": "Көп леп белгілері — эмоциялық қысым.", "match": "!!"})
    attributed = bool(re.search(ATTRIBUTION, text, re.I))
    return flags, attributed


SYSTEM = """You are a careful fact-checking assistant for a Kazakh-language website.
You receive a CLAIM and EVIDENCE snippets retrieved from Wikipedia (they may be irrelevant).
Judge the claim ONLY with the evidence and well-established general knowledge. Never invent sources.
If the evidence does not clearly address the claim, answer "insufficient".
Return strict JSON only:
{"verdict": "likely_true" | "likely_false" | "insufficient",
 "confidence": integer 0-100,
 "supporting_evidence": [indexes of evidence items that support or refute the claim],
 "explanation_kk": "2-4 sentences in Kazakh (Cyrillic) explaining the reasoning",
 "check_next_kk": ["1-3 short practical suggestions in Kazakh on how to verify further"]}"""

# Жергілікті шағын модельге қысқа сұрау: тек тұжырым, түсіндірмені жүйе өзі құрады
SYSTEM_LOCAL = """You check a CLAIM against EVIDENCE snippets. Use only the evidence and well-known facts.
If the evidence does not clearly address the claim, use "insufficient". Never guess.
Reply with JSON only: {"verdict": "likely_true" | "likely_false" | "insufficient", "confidence": 0-100, "supporting_evidence": [indexes]}"""


def analyze(text: str):
    flags, attributed = text_signals(text)
    manip = manipulation.analyze(text)
    kw = keywords(text)
    query = " ".join(kw)
    evidence = []
    if query:
        # Іздеулерді қатар жүргіземіз: жауап уақыты ең баяу сұраумен шектеледі
        jobs = [(" ".join(kw[:3]), "kk", 3), (" ".join(kw[:2]), "kk", 2), (query, "kk", 2), (" ".join(kw[:3]), "ru", 2)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda j: web.wiki_search(*j), jobs))
        evidence = [e for res in results for e in res]
    # Қайталанатын және мәлімдемеге қатысы жоқ нәтижелерді алып тастау
    stems = {_stem(w) for w in kw}
    need = min(2, len(stems))
    uniq, seen = [], set()
    for e in evidence:
        if e["url"] in seen:
            continue
        hay = (e["title"] + " " + e["snippet"]).lower()
        hits = sum(1 for s in stems if s in hay)
        in_title = any(s in e["title"].lower() for s in stems)
        if hits >= need or (in_title and hits >= 1 and len(stems) <= 3):
            seen.add(e["url"])
            uniq.append(e)
    evidence = uniq[:5]

    ai = None
    st = llm.status()
    if st["provider"]:
        limit = 260 if st["local"] else 420
        ev_text = "\n".join(f"[{i}] {e['title']}: {e['snippet'][:limit]}" for i, e in enumerate(evidence)) or "(no evidence found)"
        raw = llm.ask_json(SYSTEM_LOCAL if st["local"] else SYSTEM, f"CLAIM: {text[:1500]}\n\nEVIDENCE:\n{ev_text}")
        if isinstance(raw, dict) and raw.get("verdict") in VERDICTS:
            try:
                conf = max(0, min(100, int(raw.get("confidence", 50))))
            except (TypeError, ValueError):
                conf = 50
            used = [i for i in raw.get("supporting_evidence", []) if isinstance(i, int) and 0 <= i < len(evidence)]
            ai = {
                "verdict": raw["verdict"], "confidence": conf, "used": used,
                "explanation": str(raw.get("explanation_kk", ""))[:1200] if not st["local"] else "",
                "check_next": [str(x)[:200] for x in raw.get("check_next_kk", [])][:3] if not st["local"] else [],
                "model": st["model"], "local": st["local"],
            }

    red = len(flags)
    strong_red = sum(1 for f in flags if f["key"] in ("share", "hidden", "anon", "miracle"))
    verdict, confidence, basis = "insufficient", 0, []
    # Шағын жергілікті модель тексерісте жиі қателеседі, сондықтан оның пікірі тек кеңес ретінде көрсетіледі.
    # Қорытынды тұжырымға тек қуатты модель (Anthropic) әсер етеді.
    if ai and not ai["local"] and ai["confidence"] >= 55 and ai["verdict"] != "insufficient":
        verdict, confidence = ai["verdict"], ai["confidence"]
        basis.append("AI моделі табылған дереккөз үзінділерін салыстырды.")
        if verdict == "likely_true" and strong_red >= 2:
            verdict, confidence = "insufficient", 40
            basis.append("Бірақ мәтінде дезинформацияға тән бірнеше белгі бар, сондықтан нақты тұжырым жасалмады.")
    elif strong_red >= 2 or red >= 3:
        verdict, confidence = "likely_false", min(80, 45 + red * 8)
        basis.append("Мәтінде жалған хабарламаларға тән бірнеше стильдік белгі бар.")
    else:
        basis.append("Тұжырым жасау үшін нақты дәлел жеткіліксіз.")
    if ai and ai["local"]:
        basis.append("Жергілікті шағын AI моделінің пікірі тек кеңес ретінде көрсетілді — ол қорытындыға әсер етпейді.")

    if verdict == "likely_true":
        summary = "Табылған дереккөздер мәлімдемені қолдайтын сияқты. Дегенмен түпнұсқа дереккөзді өзіңіз тексеріңіз."
    elif verdict == "likely_false":
        summary = "Мәлімдеме жалған немесе бұрмаланған болуы мүмкін. Оны таратпас бұрын ресми дереккөздерден тексеріңіз."
    else:
        summary = "Мәлімдемені растайтын не жоққа шығаратын жеткілікті дәлел табылмады. Ресми дереккөзді күтіңіз немесе өзіңіз тексеріңіз."

    tips = [
        "Ақпараттың алғашқы дереккөзін табыңыз: кім, қашан және қай жерде жариялады?",
        "Ресми сайттардан (.gov.kz) немесе бірнеше тәуелсіз БАҚ-тан салыстырыңыз.",
        "Factcheck.kz сияқты фактчекинг ресурстарында бұл тақырыптың тексерілгенін қараңыз.",
    ]
    return {
        "verdict": verdict, "verdict_label": VERDICTS[verdict], "confidence": confidence,
        "summary": summary, "basis": basis,
        "flags": flags, "attributed": attributed,
        "manipulation": {"level": manip["level"], "label": manip["label"], "count": len(manip["flags"])},
        "keywords": kw, "evidence": evidence,
        "ai": ai, "ai_status": {"provider": st["provider"], "model": st["model"]},
        "tips": (ai["check_next"] if ai and ai["check_next"] else tips),
        "note": "Жүйе дереккөз ойлап таппайды. Төмендегі сілтемелер нақты табылған материалдар; олар мәлімдемемен "
                "тікелей байланысты болмауы мүмкін.",
    }
