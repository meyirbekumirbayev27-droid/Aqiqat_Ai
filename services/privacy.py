"""Мәтіндегі жеке және құпия деректерді анықтау, бүркемелеу.
Нәтижеде толық құпия мәндер қайтарылмайды: тек орны, түрі және бүркемеленген нұсқасы."""
import re

TYPES = {
    "email": {"label": "Электрондық пошта", "risk": "medium", "tag": "[EMAIL]",
              "why": "Спам, фишинг хаттары және аккаунтты бұзу әрекеттері үшін пайдаланылуы мүмкін."},
    "phone": {"label": "Телефон нөмірі", "risk": "medium", "tag": "[ТЕЛЕФОН]",
              "why": "Алаяқтық қоңыраулар, SMS-фишинг және мессенджер арқылы шабуыл жасауға мүмкіндік береді."},
    "iin": {"label": "ЖСН (ИИН)", "risk": "high", "tag": "[ЖСН]",
            "why": "Жеке сәйкестендіру нөмірі туған күнді ашады және жеке басын ұрлау үшін пайдаланылуы мүмкін."},
    "card": {"label": "Банк картасының нөмірі", "risk": "high", "tag": "[КАРТА]",
             "why": "Карта нөмірі жария болса, ақша ұрлау және алаяқтық төлемдер қаупі туындайды."},
    "iban": {"label": "Банк шоты (IBAN)", "risk": "high", "tag": "[IBAN]",
             "why": "Шот нөмірі жалған төлем талаптары мен әлеуметтік инженерияға пайдаланылуы мүмкін."},
    "password": {"label": "Құпиясөз", "risk": "high", "tag": "[ҚҰПИЯСӨЗ]",
                 "why": "Құпиясөз ешқашан жарияланбауы керек — аккаунтқа тікелей кіруге жол ашады."},
    "api_key": {"label": "API кілті / токен", "risk": "high", "tag": "[API КІЛТІ]",
                "why": "Кілт арқылы бөгде адам сіздің атыңыздан қызметтерді пайдаланып, шығын келтіруі мүмкін."},
    "address": {"label": "Мекенжай", "risk": "medium", "tag": "[МЕКЕНЖАЙ]",
                "why": "Тұрғылықты мекенжай жеке қауіпсіздікке қатер төндіруі мүмкін."},
    "doc": {"label": "Құжат нөмірі", "risk": "high", "tag": "[ҚҰЖАТ]",
            "why": "Жеке куәлік немесе төлқұжат нөмірі жеке басын ұрлау үшін пайдаланылуы мүмкін."},
}

PATTERNS = [
    ("api_key", re.compile(r"\b(?:sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}"
                           r"|AIza[0-9A-Za-z_\-]{35}|xox[abprs]-[A-Za-z0-9\-]{10,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})")),
    ("api_key", re.compile(r"(?i)\b(?:api[_\- ]?key|apikey|secret|token|access[_\- ]?key)\s*[:=]\s*[\"']?([A-Za-z0-9_\-\.]{12,})")),
    ("password", re.compile(r"(?i)(?:пароль|құпия\s?сөз|құпиясөз|password|passwd|pwd|pass)\s*[:=\-–—]\s*[\"']?([^\s\"',;]{3,})")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("iban", re.compile(r"\bKZ\d{2}\s?(?:[A-Z0-9]{4}\s?){3}[A-Z0-9]{4}\b", re.I)),
    ("card", re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)")),
    ("iin", re.compile(r"(?<!\d)\d{12}(?!\d)")),
    ("phone", re.compile(r"(?<![\w+])(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)")),
    ("phone", re.compile(r"(?<![\w+])\+(?!7)\d{1,3}[\s\-]?\(?\d{2,4}\)?(?:[\s\-]?\d{2,4}){2,3}(?!\d)")),
    ("doc", re.compile(r"(?i)(?:жеке куәлік|удостоверени\w*|паспорт\w*|төлқұжат\w*)\s*(?:№|N|нөмірі)?\s*[:\-]?\s*([A-Z]?\d{8,9})")),
    ("address", re.compile(r"[А-ЯӘҒҚҢӨҰҮҺІA-Z][\w\-]+\s+(?:көшесі|даңғылы|ықшамауданы|шағын ауданы)(?:[,\s]*(?:үй|пәтер|п\.)?\s*\d+[\w/]*(?:\s*(?:үй|пәтер|п\.)(?!\w))?){0,3}")),
    ("address", re.compile(r"(?i)\b(?:ул\.|улица|пр\.|просп\.|проспект|мкр\.?|микрорайон)\s*[\w\-]+(?:[,\s]+(?:д\.|дом)?\s*\d+[\w/]*)?(?:[,\s]+(?:кв\.|квартира)\s*\d+)?")),
]


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def iin_ok(iin: str) -> bool:
    """Қазақстандық ЖСН бақылау санын тексеру."""
    if len(iin) != 12 or not iin.isdigit():
        return False
    month, day = int(iin[2:4]), int(iin[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    d = [int(c) for c in iin]
    s = sum(d[i] * (i + 1) for i in range(11)) % 11
    if s == 10:
        w = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]
        s = sum(d[i] * w[i] for i in range(11)) % 11
        if s == 10:
            return False
    return s == d[11]


def mask_value(kind: str, value: str) -> str:
    v = value.strip()
    if kind == "email":
        name, _, domain = v.partition("@")
        dom, _, tld = domain.rpartition(".")
        return f"{name[:1]}***@{dom[:1]}***.{tld}"
    if kind == "password":
        return "•" * 8
    digits = re.sub(r"\D", "", v)
    if kind in ("phone", "card", "iin", "iban", "doc") and digits:
        keep = 2 if kind in ("phone", "iin") else 4
        return "•" * max(4, len(digits) - keep) + digits[-keep:]
    if len(v) <= 4:
        return "•" * len(v)
    return v[:2] + "•" * min(12, len(v) - 3) + v[-1:]


def find_items(text: str):
    items, taken = [], []

    def free(s, e):
        return not any(s < te and e > ts for ts, te in taken)

    for kind, rx in PATTERNS:
        for m in rx.finditer(text):
            # Мән тобы болса (құпиясөз, кілт) — тек мәнін белгілейміз
            if m.lastindex:
                s, e = m.span(1)
            else:
                s, e = m.span()
            value = text[s:e]
            stripped = value.rstrip(".!?)")
            if kind in ("password", "api_key", "address") and stripped != value:
                e -= len(value) - len(stripped)
                value = stripped
            digits = re.sub(r"\D", "", value)
            if kind == "card":
                if not (13 <= len(digits) <= 19) or not luhn_ok(digits):
                    continue
            if kind == "iin" and not iin_ok(digits):
                continue
            if kind == "address" and len(value.strip()) < 8:
                continue
            if not free(s, e):
                continue
            taken.append((s, e))
            items.append({"start": s, "end": e, "type": kind, "masked": mask_value(kind, value)})
    items.sort(key=lambda i: i["start"])
    return items


def redact(text: str, items, mode: str = "tag") -> str:
    out, pos = [], 0
    for it in items:
        out.append(text[pos:it["start"]])
        out.append(TYPES[it["type"]]["tag"] if mode == "tag" else it["masked"])
        pos = it["end"]
    out.append(text[pos:])
    return "".join(out)


def analyze(text: str):
    items = find_items(text)
    counts = {}
    for it in items:
        counts[it["type"]] = counts.get(it["type"], 0) + 1
        it["label"] = TYPES[it["type"]]["label"]
        it["risk"] = TYPES[it["type"]]["risk"]
    high = sum(v for k, v in counts.items() if TYPES[k]["risk"] == "high")
    if not items:
        level, label = "low", "Жеке деректер табылмады"
    elif high:
        level, label = "high", "Жоғары тәуекел"
    else:
        level, label = "medium", "Орташа тәуекел"
    groups = [
        {"type": k, "label": TYPES[k]["label"], "count": v, "risk": TYPES[k]["risk"], "why": TYPES[k]["why"]}
        for k, v in sorted(counts.items(), key=lambda kv: (TYPES[kv[0]]["risk"] != "high", -kv[1]))
    ]
    return {
        "level": level,
        "label": label,
        "items": items,
        "groups": groups,
        "total": len(items),
        "redacted": redact(text, items, "tag"),
        "masked": redact(text, items, "mask"),
        "note": "Мәтін серверде сақталмайды. Тарихқа тек табылған дерек түрлерінің саны жазылады.",
    }
