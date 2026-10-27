"""Мәтіндегі манипуляциялық тілдік тәсілдерді анықтау (қазақ, орыс, ағылшын)."""
import re

CATEGORIES = {
    "emotional": {
        "label": "Эмоциялық қысым",
        "why": "Оқырманның сезіміне әсер етіп, ақылмен ойлануды әлсірететін сөздер.",
    },
    "fear": {
        "label": "Қорқыту",
        "why": "Қауіпті әсірелеп, үрей тудыру арқылы шешім қабылдауға итермелейді.",
    },
    "generalization": {
        "label": "Негізсіз жалпылау",
        "why": "Дәлелсіз «барлығы», «ешкім», «әрқашан» сияқты кең тұжырымдар жасалады.",
    },
    "urgency": {
        "label": "Асықтыру",
        "why": "Тексеруге уақыт бермей, дереу әрекет етуге мәжбүрлейді.",
    },
    "one_sided": {
        "label": "Біржақты баяндау",
        "why": "Тек бір көзқарас «жалғыз шындық» ретінде беріледі, басқа пікірлер жоққа шығарылады.",
    },
    "loaded": {
        "label": "Бояуы күшті сөздер",
        "why": "Бағалаушы, жапсырма тағатын немесе қатты эмоциялы сөздер бейтарап сипаттаманы ығыстырады.",
    },
    "style": {
        "label": "Айқай стилі",
        "why": "Бас әріптер мен көп леп белгілері мәтінге жасанды шұғылдық пен эмоция береді.",
    },
}

# (санат, регулярлы өрнек, бейтарап балама немесе None)
RULES = [
    # Эмоциялық қысым
    ("emotional", r"\bсұмдық\w*", "назар аударарлық"),
    ("emotional", r"\bшок\w*", "күтпеген"),
    ("emotional", r"\bсенсаци\w*", "жаңа ақпарат"),
    ("emotional", r"\bжүрег\w* ауыр\w*", "алаңдатады"),
    ("emotional", r"\bкөз жас\w*", None),
    ("emotional", r"\bмасқара\w*", "сынға ұшыраған"),
    ("emotional", r"\bжан түршіг\w*", "алаңдатарлық"),
    ("emotional", r"\bнамыс\w*", None),
    ("emotional", r"\bшокир\w*", None),
    ("emotional", r"\bужас\w*", None),
    ("emotional", r"\bshocking\b", "unexpected"),
    ("emotional", r"\bheartbreaking\b", "sad"),
    # Қорқыту
    ("fear", r"\bқауіп төн\w*", "тәуекел бар"),
    ("fear", r"\bапат\w*", "қиын жағдай"),
    ("fear", r"\bжойыл\w*", "өзгеруі мүмкін"),
    ("fear", r"\bөліп кет\w*", "денсаулыққа зиян келуі мүмкін"),
    ("fear", r"\bқырыл\w*", "зардап шегуі мүмкін"),
    ("fear", r"\bқорқынышты\w*", "алаңдатарлық"),
    ("fear", r"\bкатастроф\w*", "серьёзная проблема"),
    ("fear", r"\bпогибн\w*", "могут пострадать"),
    ("fear", r"\bсмертельн\w*", "опасный"),
    ("fear", r"\bdeadly\b", "dangerous"),
    ("fear", r"\bdisaster\b", "problem"),
    # Негізсіз жалпылау
    ("generalization", r"\bбарлығы\b", "көпшілігі"),
    ("generalization", r"\bбәрі біледі\b", "кейбір адамдар айтады"),
    ("generalization", r"\bешкім\b", "аз адам"),
    ("generalization", r"\bәрқашан\b", "жиі"),
    ("generalization", r"\bешқашан\b", "сирек"),
    ("generalization", r"\bбарлық (?:адам|ғалым|дәрігер|сарапшы)\w*", "кейбір мамандар"),
    ("generalization", r"\bвсе знают\b", "некоторые считают"),
    ("generalization", r"\bвсем известно\b", "по некоторым данным"),
    ("generalization", r"\bникто не\b", "мало кто"),
    ("generalization", r"\bвсегда\b", "часто"),
    ("generalization", r"\beveryone knows\b", "some people say"),
    ("generalization", r"\bnobody\b", "few people"),
    # Асықтыру
    ("urgency", r"\bдереу\b", None),
    ("urgency", r"\bшұғыл\w*", None),
    ("urgency", r"\bтез арада\b", None),
    ("urgency", r"\bкешікпей\b", None),
    ("urgency", r"\bөшіріп тастамай тұрғанда\b", None),
    ("urgency", r"\bуақыт аз\b", None),
    ("urgency", r"\bсрочно\b", None),
    ("urgency", r"\bуспейте\b", None),
    ("urgency", r"\bпока не удалили\b", None),
    ("urgency", r"\bact now\b", None),
    ("urgency", r"\burgent\w*", None),
    # Біржақты баяндау
    ("one_sided", r"\bжалғыз шындық\w*", "бір көзқарас"),
    ("one_sided", r"\bешқандай күмән жоқ\b", "дәлелдер көрсетеді"),
    ("one_sided", r"\bсізден жасыр\w*(?: (?:отыр|жүр|тұр)\w*)?", "кеңінен жарияланбаған"),
    ("one_sided", r"\bшындықты жасыр\w*(?: (?:отыр|жүр|тұр)\w*)?", "толық ақпарат бермейді"),
    ("one_sided", r"\b(?:БАҚ|ақпарат құралдары) үндемейді\b", "БАҚ-та әлі жазылмаған"),
    ("one_sided", r"\bбіз және олар\b", None),
    ("one_sided", r"\bединственн\w* правд\w*", "одна из точек зрения"),
    ("one_sided", r"\bбез (?:всякого )?сомнени\w*", "по имеющимся данным"),
    ("one_sided", r"\bСМИ молчат\b", "в СМИ пока нет информации"),
    ("one_sided", r"\bот вас скрыва\w*", "широко не обсуждается"),
    ("one_sided", r"\bthey don'?t want you to know\b", "is not widely reported"),
    # Бояуы күшті сөздер
    ("loaded", r"\bсатқын\w*", "сынға ұшыраған тұлға"),
    ("loaded", r"\bақымақ\w*", "қате шешім"),
    ("loaded", r"\bжексұрын\w*", "қабылданбайтын"),
    ("loaded", r"\bғажайып\w*", "назар аударарлық"),
    ("loaded", r"\bкеремет\w*", "жақсы"),
    ("loaded", r"\bмасқарапаз\w*", "сынға ұшыраған"),
    ("loaded", r"\bнағыз жау\w*", "қарсылас"),
    ("loaded", r"\bпредател\w*", "критикуемый человек"),
    ("loaded", r"\bпозор\w*", None),
    ("loaded", r"\bчудо\w*", None),
    ("loaded", r"\bidiot\w*", "mistaken"),
    ("loaded", r"\btraitor\w*", "critic"),
]

COMPILED = [(c, re.compile(p, re.I | re.U), rep) for c, p, rep in RULES]
CAPS_RE = re.compile(r"\b[A-ZА-ЯӘҒҚҢӨҰҮҺІЁ]{4,}\b")
EXCL_RE = re.compile(r"[!?]{2,}")

# Бейтарап нұсқада тұтас ауыстыруға жарайтын сөз формалары (сөз түбірі сақталмайтын жағдай)
def _neutral(match_text, replacement):
    if replacement is None:
        return ""
    if match_text[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def find_flags(text: str):
    flags = []
    taken = []

    def overlaps(s, e):
        return any(s < te and e > ts for ts, te in taken)

    for cat, rx, rep in COMPILED:
        for m in rx.finditer(text):
            s, e = m.span()
            if overlaps(s, e):
                continue
            taken.append((s, e))
            flags.append({"start": s, "end": e, "text": m.group(0), "category": cat, "replacement": rep})
    for m in CAPS_RE.finditer(text):
        word = m.group(0)
        # аббревиатураларды (БАҚ, ҚР, NASA) елемеу үшін тек ұзын сөздер
        if len(word) >= 6 and not overlaps(*m.span()):
            taken.append(m.span())
            flags.append({"start": m.start(), "end": m.end(), "text": word, "category": "style",
                          "replacement": word.capitalize() if word.isalpha() else word})
    for m in EXCL_RE.finditer(text):
        if not overlaps(*m.span()):
            taken.append(m.span())
            flags.append({"start": m.start(), "end": m.end(), "text": m.group(0), "category": "style",
                          "replacement": m.group(0)[0] if m.group(0)[0] == "?" else "."})
    flags.sort(key=lambda f: f["start"])
    return flags


def neutral_version(text: str, flags):
    out, pos = [], 0
    for f in flags:
        out.append(text[pos:f["start"]])
        out.append(_neutral(f["text"], f["replacement"]))
        pos = f["end"]
    out.append(text[pos:])
    result = "".join(out)
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r"\s+([,.!?;:])", r"\1", result)
    result = re.sub(r"([,.])\1+", r"\1", result)
    result = re.sub(r"^[\s,.;:—–-]+", "", result)
    # Сөз алынып тасталса, сөйлем басын бас әріппен жазу
    result = re.sub(r"(^|[.!?]\s+)(\w)", lambda mm: mm.group(1) + mm.group(2).upper(), result)
    return result.strip()


def analyze(text: str):
    flags = find_flags(text)
    words = max(1, len(re.findall(r"\w+", text)))
    counts = {}
    for f in flags:
        counts[f["category"]] = counts.get(f["category"], 0) + 1
    density = len(flags) / words * 100
    intensity = min(100, round(density * 9 + len(counts) * 6))
    if not flags:
        level, label = "low", "Манипуляция белгілері табылмады"
    elif intensity < 35:
        level, label = "low", "Әлсіз белгілер"
    elif intensity < 65:
        level, label = "medium", "Орташа деңгей"
    else:
        level, label = "high", "Күшті манипуляциялық тіл"
    categories = [
        {"key": k, "label": CATEGORIES[k]["label"], "why": CATEGORIES[k]["why"], "count": v}
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    for f in flags:
        f["label"] = CATEGORIES[f["category"]]["label"]
    return {
        "level": level,
        "label": label,
        "intensity": intensity,
        "flags": flags,
        "categories": categories,
        "neutral": neutral_version(text, flags) if flags else text,
        "word_count": words,
        "note": "Манипуляциялық тілдің болуы ақпараттың жалған екенін өздігінен білдірмейді — "
                "ол тек мәтінге сыни көзқараспен қарау керектігін көрсетеді.",
    }
