"""Алаяқтық хабарламалардың белгілерін анықтау."""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from . import web

SIGNALS = {
    "credentials": {
        "label": "Құпия деректерді сұрау", "weight": 30,
        "why": "Банктер мен мемлекеттік органдар SMS-код, PIN, CVV немесе құпиясөзді ешқашан сұрамайды.",
        "advice": "Кодты, құпиясөзді немесе карта деректерін ешкімге айтпаңыз.",
    },
    "urgency": {
        "label": "Шұғыл әрекетке мәжбүрлеу", "weight": 15,
        "why": "Алаяқтар ойлануға уақыт бермеу үшін уақыт шектеуін ойлап табады.",
        "advice": "Асықпаңыз: ресми нөмір арқылы ұйымға өзіңіз хабарласып, ақпаратты тексеріңіз.",
    },
    "payment": {
        "label": "Күмәнді төлем талабы", "weight": 25,
        "why": "Алдын ала төлем, «комиссия» немесе бейтаныс адамға аударым сұрау — алаяқтықтың жиі белгісі.",
        "advice": "Бейтаныс адамға немесе түсініксіз «комиссия» үшін ақша аудармаңыз.",
    },
    "prize": {
        "label": "Жалған сыйлық не ұтыс", "weight": 20,
        "why": "Қатыспаған ұтысты «ұтып алу» немесе тым тиімді ұсыныс — классикалық алдау тәсілі.",
        "advice": "Сыйлық алу үшін ақша төлеуді не деректерді беруді талап етсе — бұл алаяқтық.",
    },
    "threat": {
        "label": "Қорқыту немесе билік атын жамылу", "weight": 20,
        "why": "«Картаңыз бұғатталды», «полиция», «банк қауіпсіздік қызметі» деп қорқыту арқылы сенім жасалады.",
        "advice": "Қоңырауды тоқтатып, банктің не органның ресми нөміріне өзіңіз қоңырау шалыңыз.",
    },
    "investment": {
        "label": "Кепілдендірілген табыс уәдесі", "weight": 20,
        "why": "Тәуекелсіз жоғары табыс уәде ету — қаржылық пирамида мен алаяқтық инвестицияның белгісі.",
        "advice": "Лицензиясы бар-жоғын ҚНРДА (АРРФР) сайтынан тексеріңіз.",
    },
    "contact_switch": {
        "label": "Басқа арнаға көшуге шақыру", "weight": 10,
        "why": "Алаяқтар бақылауы әлсіз мессенджерге немесе бейтаныс нөмірге көшуді сұрайды.",
        "advice": "Ресми емес арналар арқылы келіссөз жүргізбеңіз.",
    },
    "link": {
        "label": "Күмәнді сілтеме", "weight": 0,
        "why": "Сілтеменің домені мен құрылымында қауіпті белгілер бар.",
        "advice": "Сілтемені ашпаңыз; ұйымның сайтына адресті өзіңіз теріп кіріңіз.",
    },
}

PHRASES = {
    "credentials": [
        r"sms[\s\-]?код\w*", r"смс[\s\-]?код\w*", r"код\w* (?:айтыңыз|жіберіңіз|хабарлаңыз)", r"кодты\b",
        r"\bpin\b", r"\bпин[\s\-]?код\w*", r"\bcvv\w*", r"\bcvc\b", r"құпия\s?сөз\w*", r"\bпарол\w*",
        r"карта\w* (?:нөмір|деректер)\w*", r"номер\w* карт\w*", r"код из смс", r"сообщите код", r"\bлогин\w*",
        r"\bpassword\b", r"verification code", r"(?:ЖСН|ИИН)\w*",
    ],
    "urgency": [
        r"\bшұғыл\w*", r"\bдереу\b", r"тез арада", r"\d+\s*(?:сағат|минут)\s*(?:ішінде|қалды)", r"бүгін ғана",
        r"соңғы мүмкіндік", r"\bсрочно\b", r"немедленно", r"в течение \d+\s*(?:час|минут)\w*", r"последний шанс",
        r"\burgent\w*", r"\bimmediately\b", r"within \d+ (?:hours|minutes)",
    ],
    "payment": [
        r"аударыңыз", r"аудару керек", r"төлеңіз", r"\bкомиссия\w*", r"алдын ала төлем", r"кепіл\w* төлем",
        r"переведите", r"оплатите", r"предоплат\w*", r"\bперевод\w*", r"kaspi\w* (?:аудар|gold)\w*",
        r"транзакция\w*", r"\btransfer\b", r"\bpay (?:now|a fee)\b", r"gift ?card",
    ],
    "prize": [
        r"ұтып алдыңыз", r"\bұтыс\w*", r"\bсыйлық\w*", r"жеңімпаз\w*", r"тегін\b", r"\bбонус\w*",
        r"выиграли", r"\bприз\w*", r"\bподар\w*", r"\bбесплатн\w*", r"\bwinner\b", r"you(?:'ve| have) won",
        r"\bfree\b",
    ],
    "threat": [
        r"бұғат\w*", r"бұғаттал\w*", r"\bполиция\w*", r"қауіпсіздік қызмет\w*", r"банк қызметкер\w*",
        r"заблокир\w*", r"служба безопасности", r"сотрудник банка", r"уголовн\w*", r"\bштраф\w*", r"айыппұл\w*",
        r"\bsuspended\b", r"account (?:locked|blocked)",
    ],
    "investment": [
        r"пассивті табыс", r"кепілдендірілген табыс", r"\d+\s*%\s*(?:пайда|табыс)", r"\bинвестиц\w*",
        r"\bкрипто\w*", r"гарантированн\w* доход", r"доход от \d+", r"пассивн\w* доход", r"guaranteed (?:profit|return)",
    ],
    "contact_switch": [
        r"whats\s?app\w*", r"telegram\w*", r"телеграм\w*", r"\bватсап\w*", r"мына нөмірге", r"на этот номер",
        r"жеке хат\w*", r"напишите в личк\w*",
    ],
}

COMPILED = {k: [re.compile(p, re.I | re.U) for p in v] for k, v in PHRASES.items()}
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+|\b[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.(?:kz|ru|com|net|org|xyz|top|click|icu|online|site|live|buzz|info|link|shop|io|me|tk|ml|ga|cf|gq|cc|pw|biz)\b(?:/[^\s<>\"')]*)?", re.I)

SHORTENERS = {"bit.ly", "tinyurl.com", "clck.ru", "goo.gl", "t.ly", "cutt.ly", "is.gd", "ow.ly", "rb.gy",
              "shorturl.at", "tiny.cc", "u.to", "vk.cc", "s.id", "t.co"}
BAD_TLDS = {"xyz", "top", "click", "icu", "online", "site", "live", "buzz", "tk", "ml", "ga", "cf", "gq", "pw",
            "info", "link", "shop", "rest", "monster", "cc"}
BRANDS = {
    "kaspi": ["kaspi.kz"], "halyk": ["halykbank.kz", "homebank.kz"], "homebank": ["homebank.kz"],
    "egov": ["egov.kz"], "jusan": ["jusan.kz"], "forte": ["forte.kz"], "bcc": ["bcc.kz"],
    "freedom": ["ffin.kz", "freedombank.kz", "freedomholding.kz"], "kazpost": ["post.kz", "kazpost.kz"],
    "olx": ["olx.kz"], "wildberries": ["wildberries.ru", "wildberries.kz", "wb.ru"], "google": ["google.com", "google.kz"],
    "apple": ["apple.com", "icloud.com"], "paypal": ["paypal.com"], "telegram": ["telegram.org", "t.me"],
    "whatsapp": ["whatsapp.com", "wa.me"], "instagram": ["instagram.com"], "facebook": ["facebook.com"],
    "gov": [], "nationalbank": ["nationalbank.kz"],
}


def analyze_url(raw: str, check_age: bool = True):
    url = raw if re.match(r"^https?://", raw, re.I) else "http://" + raw
    p = urlparse(url)
    host = (p.hostname or "").lower()
    reg = web.registered_domain(host)
    flags = []
    score = 0

    def add(text, pts):
        nonlocal score
        flags.append(text)
        score += pts

    if not host:
        return {"url": raw, "host": "", "flags": ["Сілтеме форматы дұрыс емес."], "score": 10}
    if web.is_ip(host):
        add("Домен орнына IP-мекенжай қолданылған.", 25)
    if host.startswith("xn--") or ".xn--" in host:
        add("Punycode домен — танымал атауға ұқсатылған әріптер болуы мүмкін.", 25)
    if reg in SHORTENERS:
        add("Қысқартылған сілтеме — нақты бағыты жасырылған.", 15)
    tld = host.rsplit(".", 1)[-1]
    if tld in BAD_TLDS:
        add(f"«.{tld}» домен аймағы алаяқтық сайттарда жиі қолданылады.", 15)
    if host.count("-") >= 2:
        add("Доменде көп дефис бар — жалған сайттарға тән құрылым.", 10)
    if host.count(".") >= 4:
        add("Тым көп субдомен — нақты доменді жасыру тәсілі болуы мүмкін.", 10)
    if "@" in p.netloc:
        add("Сілтемеде «@» таңбасы бар — нақты адрес жасырылуы мүмкін.", 20)
    if p.scheme == "http" and raw.lower().startswith("http://"):
        add("Қорғалмаған HTTP байланысы (HTTPS емес).", 5)
    for brand, official in BRANDS.items():
        if brand in host and official and reg not in official:
            add(f"Доменде «{brand}» атауы бар, бірақ ол ресми доменге ({', '.join(official)}) жатпайды.", 35)
            break
    if re.search(r"(login|verify|secure|account|update|bonus|prize|gift|confirm)", host + p.path, re.I):
        add("Сілтемеде «login / verify / bonus» сияқты фишингке тән сөздер бар.", 10)
    age_days = None
    if check_age and not web.is_ip(host) and reg not in SHORTENERS:
        info = web.rdap_domain(reg)
        if info and info.get("registered"):
            try:
                reg_date = datetime.fromisoformat(info["registered"].replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - reg_date).days
                if age_days < 90:
                    add(f"Домен жақында тіркелген: {age_days} күн бұрын (RDAP деректері).", 25)
            except ValueError:
                pass
    return {"url": raw, "host": host, "domain": reg, "flags": flags, "score": min(score, 60), "age_days": age_days}


def analyze(message: str, extra_url: str = ""):
    hits = []
    taken = []
    found = {}
    # Алдымен сілтемелер: олардың ішіндегі сөздер жеке белгі ретінде саналмайды
    urls = []
    for m in URL_RE.finditer(message):
        u = m.group(0).rstrip(".,;:!?")
        if "@" in u and not u.lower().startswith("http"):
            continue  # электрондық пошта
        if u not in urls:
            urls.append(u)
        taken.append((m.start(), m.start() + len(u)))
        hits.append({"start": m.start(), "end": m.start() + len(u), "text": u, "category": "link",
                     "label": SIGNALS["link"]["label"]})
    for cat, rxs in COMPILED.items():
        for rx in rxs:
            for m in rx.finditer(message):
                s, e = m.span()
                if any(s < te and e > ts for ts, te in taken):
                    continue
                taken.append((s, e))
                hits.append({"start": s, "end": e, "text": m.group(0), "category": cat,
                             "label": SIGNALS[cat]["label"]})
                found[cat] = found.get(cat, 0) + 1
    hits.sort(key=lambda h: h["start"])
    if extra_url.strip() and extra_url.strip() not in urls:
        urls.insert(0, extra_url.strip())
    url_reports = [analyze_url(u, check_age=i < 3) for i, u in enumerate(urls[:6])]

    score = sum(SIGNALS[c]["weight"] + min(n - 1, 2) * 4 for c, n in found.items())
    score += max((r["score"] for r in url_reports), default=0)
    if len(found) >= 3:
        score += 10
    score = min(100, score)
    if score >= 55:
        level, label = "high", "Жоғары"
    elif score >= 25:
        level, label = "medium", "Орташа"
    else:
        level, label = "low", "Төмен"

    signals = [
        {"key": c, "label": SIGNALS[c]["label"], "count": n, "why": SIGNALS[c]["why"], "advice": SIGNALS[c]["advice"]}
        for c, n in sorted(found.items(), key=lambda kv: -SIGNALS[kv[0]]["weight"])
    ]
    if any(r["flags"] for r in url_reports):
        signals.append({"key": "link", "label": SIGNALS["link"]["label"], "count": sum(1 for r in url_reports if r["flags"]),
                        "why": SIGNALS["link"]["why"], "advice": SIGNALS["link"]["advice"]})

    advice = [
        "Күмәнді болса, ұйымның ресми нөміріне немесе қосымшасына өзіңіз хабарласыңыз.",
        "Алаяқтық туралы 102 нөміріне немесе банкіңізге хабарлаңыз.",
    ]
    if level == "low":
        summary = "Хабарламадан айқын алаяқтық белгілері табылмады. Дегенмен жіберушіні тексеру артық емес."
    elif level == "medium":
        summary = "Хабарламада бірнеше күмәнді белгі бар. Ешқандай әрекет жасамас бұрын жіберушіні тексеріңіз."
    else:
        summary = "Хабарлама алаяқтыққа тән бірнеше белгіні қамтиды. Сілтемені ашпаңыз, ақша аудармаңыз, кодты айтпаңыз."
    return {
        "level": level, "label": label, "score": score, "summary": summary,
        "hits": hits, "signals": signals, "urls": url_reports, "advice": advice,
        "note": "Бағалау мәтіндегі белгілерге негізделген ережелер жүйесімен жасалды; ол 100% кепілдік бермейді.",
    }
