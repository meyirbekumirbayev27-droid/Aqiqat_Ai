"""«Шындықты анықта!» ойынының тексерілген сұрақтары."""
import random

ANSWERS = {"true": "Шынайы", "false": "Жалған", "unknown": "Дәлел жеткіліксіз"}

QUESTIONS = [
    {"id": 1, "claim": "Қазақстан — теңізге шығатын жолы жоқ мемлекеттердің ішіндегі ең үлкені.",
     "answer": "true", "category": "География",
     "explain": "Қазақстанның аумағы шамамен 2,7 млн км². Ол Дүниежүзілік мұхитқа шығатын жолы жоқ елдердің ішіндегі ең ірісі. Каспий — тұйық су айдыны.",
     "sources": [{"title": "Wikipedia: Landlocked country", "url": "https://en.wikipedia.org/wiki/Landlocked_country"}]},
    {"id": 2, "claim": "Ұлы Қытай қорғанын ғарыштан жай көзбен оңай көруге болады.",
     "answer": "false", "category": "Мифтер",
     "explain": "Қорған өте ұзын болғанымен, тар әрі түсі айналасындағы жерге ұқсас. Ғарышкерлердің айтуынша, оны орбитадан жай көзбен ажырату өте қиын.",
     "sources": [{"title": "Wikipedia: Great Wall of China", "url": "https://en.wikipedia.org/wiki/Great_Wall_of_China"}]},
    {"id": 3, "claim": "Адам өз миының тек 10 пайызын ғана пайдаланады.",
     "answer": "false", "category": "Ғылым",
     "explain": "Бұл — кең тараған миф. Нейровизуализация зерттеулері мидың барлық бөлігі белсенді екенін көрсетеді.",
     "sources": [{"title": "Wikipedia: Ten percent of the brain myth", "url": "https://en.wikipedia.org/wiki/Ten_percent_of_the_brain_myth"}]},
    {"id": 4, "claim": "Балқаш көлінің батыс бөлігі тұщы, ал шығыс бөлігі тұзды.",
     "answer": "true", "category": "География",
     "explain": "Батыс бөлігіне Іле өзені құяды, сондықтан суы тұщы дерлік. Тар бұғаз арқылы бөлінген шығыс бөлігі әлдеқайда тұзды.",
     "sources": [{"title": "Wikipedia: Lake Balkhash", "url": "https://en.wikipedia.org/wiki/Lake_Balkhash"}]},
    {"id": 5, "claim": "Найзағай бір жерге ешқашан екі рет түспейді.",
     "answer": "false", "category": "Мифтер",
     "explain": "Найзағай бір жерге бірнеше рет түсе береді, әсіресе биік ғимараттарға. Мысалы, Эмпайр-Стейт-Билдингке жылына ондаған рет түседі.",
     "sources": [{"title": "NOAA / National Weather Service: Lightning myths", "url": "https://www.weather.gov/safety/lightning-myths"}]},
    {"id": 6, "claim": "Байқоңыр ғарыш айлағы Қазақстан аумағында орналасқан.",
     "answer": "true", "category": "Тарих",
     "explain": "Байқоңыр Қызылорда облысында орналасқан. Ол қазір Ресейге жалға берілген. 1961 жылы Юрий Гагарин осы жерден ұшқан.",
     "sources": [{"title": "Wikipedia: Baikonur Cosmodrome", "url": "https://en.wikipedia.org/wiki/Baikonur_Cosmodrome"}]},
    {"id": 7, "claim": "Абай Құнанбайұлы 1845 жылы дүниеге келген.",
     "answer": "true", "category": "Тарих",
     "explain": "Ұлы ақын Абай 1845 жылы 10 тамызда (жаңа стиль) Шыңғыстау өңірінде туған.",
     "sources": [{"title": "Wikipedia: Abai Qunanbaiuly", "url": "https://en.wikipedia.org/wiki/Abai_Qunanbaiuly"}]},
    {"id": 8, "claim": "Қызылшаға қарсы (MMR) вакцина аутизм тудырады.",
     "answer": "false", "category": "Денсаулық",
     "explain": "Бұл байланысты «дәлелдеген» 1998 жылғы мақала алаяқтық деп танылып, кері қайтарылды. Миллиондаған баланы қамтыған зерттеулер ешқандай байланыс таппады.",
     "sources": [{"title": "Wikipedia: MMR vaccine and autism", "url": "https://en.wikipedia.org/wiki/MMR_vaccine_and_autism"}]},
    {"id": 9, "claim": "Хан Тәңірі шыңы — Қазақстандағы ең биік нүкте.",
     "answer": "true", "category": "География",
     "explain": "Қазақстан мен Қырғызстан шекарасындағы Хан Тәңірі шыңы (мұзымен бірге шамамен 7010 м) — Қазақстанның ең биік нүктесі.",
     "sources": [{"title": "Wikipedia: Khan Tengri", "url": "https://en.wikipedia.org/wiki/Khan_Tengri"}]},
    {"id": 10, "claim": "Анонимді Telegram-арнада «ертең елдегі барлық банктер жабылады» деп жазылды. Демек, бұл — рас.",
     "answer": "unknown", "category": "Медиа сауаттылық",
     "explain": "Анонимді арнадағы жазба — дәлел емес. Мұндай ақпаратты тек Ұлттық Банк немесе ресми органдар растай алады. Тексерілмеген хабарды таратпаңыз.",
     "sources": [{"title": "ҚР Ұлттық Банкі (ресми сайт)", "url": "https://nationalbank.kz/"}]},
    {"id": 11, "claim": "Түйеқұстар қорыққанда басын құмға тығады.",
     "answer": "false", "category": "Мифтер",
     "explain": "Түйеқұстар басын құмға тықпайды. Олар қауіп кезінде жерге жата қалады немесе қашады. Ұя салғанда жұмыртқасын аударатындықтан, басы құмға кіргендей көрінеді.",
     "sources": [{"title": "Wikipedia: Common ostrich", "url": "https://en.wikipedia.org/wiki/Common_ostrich"}]},
    {"id": 12, "claim": "Қазақстан Республикасы тәуелсіздігін 1991 жылғы 16 желтоқсанда жариялады.",
     "answer": "true", "category": "Тарих",
     "explain": "1991 жылғы 16 желтоқсанда «Қазақстан Республикасының мемлекеттік тәуелсіздігі туралы» Конституциялық заң қабылданды.",
     "sources": [{"title": "Wikipedia: Kazakhstan", "url": "https://en.wikipedia.org/wiki/Kazakhstan"}]},
    {"id": 13, "claim": "Ай өз осінен айналмайды, сондықтан біз оның бір жағын ғана көреміз.",
     "answer": "false", "category": "Ғылым",
     "explain": "Ай өз осінен айналады. Бірақ бір айналымы Жерді бір айналып шығу уақытымен тең (синхронды айналу), сондықтан бізге әрдайым бір жағымен қарап тұрады.",
     "sources": [{"title": "Wikipedia: Tidal locking", "url": "https://en.wikipedia.org/wiki/Tidal_locking"}]},
    {"id": 14, "claim": "Әлеуметтік желіде танымал адамның «жаңа» фотосы тарады, бірақ оның авторы мен түсірілген уақыты белгісіз.",
     "answer": "unknown", "category": "Медиа сауаттылық",
     "explain": "Авторы мен уақыты белгісіз фото ештеңені дәлелдемейді. Кері сурет іздеу (Google Lens, TinEye) арқылы оның бұрын жарияланған-жарияланбағанын тексеріңіз.",
     "sources": [{"title": "TinEye — кері сурет іздеу", "url": "https://tineye.com/"}]},
    {"id": 15, "claim": "Қазақ тілі түркі тілдері тобына жатады.",
     "answer": "true", "category": "Тіл",
     "explain": "Қазақ тілі түркі тілдерінің қыпшақ тобына жатады. Оған ноғай, қарақалпақ, қырғыз тілдері жақын.",
     "sources": [{"title": "Wikipedia: Kazakh language", "url": "https://en.wikipedia.org/wiki/Kazakh_language"}]},
    {"id": 16, "claim": "Каспий теңізі — әлемдегі ең үлкен тұйық су айдыны.",
     "answer": "true", "category": "География",
     "explain": "Каспийдің ауданы шамамен 371 мың км². Ол мұхитпен байланыспайтын ең үлкен су айдыны.",
     "sources": [{"title": "Wikipedia: Caspian Sea", "url": "https://en.wikipedia.org/wiki/Caspian_Sea"}]},
    {"id": 17, "claim": "«Дәрігерлер жасырып жүр: лимонды сода бір аптада қатерлі ісікті толық емдейді!» — деген хабарлама тарады.",
     "answer": "false", "category": "Денсаулық",
     "explain": "Қатерлі ісікті лимон мен сода емдейтіні туралы ғылыми дәлел жоқ. «Дәрігерлер жасырады», «толық емдейді» деген тіркестер — жалған медициналық ақпаратқа тән белгілер.",
     "sources": [{"title": "Wikipedia: List of unproven and disproven cancer treatments", "url": "https://en.wikipedia.org/wiki/List_of_unproven_and_disproven_cancer_treatments"}]},
    {"id": 18, "claim": "Тері — адам денесіндегі ең үлкен мүше.",
     "answer": "true", "category": "Ғылым",
     "explain": "Ересек адамның терісінің ауданы шамамен 1,5–2 м². Сондықтан ол дененің ең үлкен мүшесі саналады.",
     "sources": [{"title": "Wikipedia: Skin", "url": "https://en.wikipedia.org/wiki/Skin"}]},
    {"id": 19, "claim": "Көршіңіз «қаладағы су ертең уланады» деп естігенін айтты, бірақ ресми хабарландыру жоқ.",
     "answer": "unknown", "category": "Медиа сауаттылық",
     "explain": "Біреудің «естігені» — дәлел емес. Мұндай ақпаратты тек жергілікті әкімдік немесе төтенше жағдайлар қызметінің ресми хабарламасы растай алады.",
     "sources": [{"title": "ҚР Төтенше жағдайлар министрлігі", "url": "https://www.gov.kz/memleket/entities/emer"}]},
    {"id": 20, "claim": "Алтын балықтың есте сақтау қабілеті небәрі 3 секундқа жетеді.",
     "answer": "false", "category": "Мифтер",
     "explain": "Тәжірибелер алтын балықтардың кем дегенде бірнеше ай бойы есте сақтай алатынын көрсетті.",
     "sources": [{"title": "Wikipedia: Goldfish", "url": "https://en.wikipedia.org/wiki/Goldfish"}]},
    {"id": 21, "claim": "Жер Күнді шамамен 365 күнде бір рет айналып шығады.",
     "answer": "true", "category": "Ғылым",
     "explain": "Жердің Күнді айналу кезеңі шамамен 365,25 тәулік. Сондықтан төрт жылда бір рет кібісе жыл қосылады.",
     "sources": [{"title": "Wikipedia: Year", "url": "https://en.wikipedia.org/wiki/Year"}]},
    {"id": 22, "claim": "Алматы 1997 жылға дейін Қазақстанның астанасы болған.",
     "answer": "true", "category": "Тарих",
     "explain": "Астана 1997 жылы Алматыдан Ақмолаға (кейін Астана) көшірілді.",
     "sources": [{"title": "Wikipedia: Astana", "url": "https://en.wikipedia.org/wiki/Astana"}]},
    {"id": 23, "claim": "Белгісіз сайт «ғалымдар Жердің 2030 жылы тоқтайтынын анықтады» деп жазды, бірақ зерттеудің атауы мен авторлары көрсетілмеген.",
     "answer": "false", "category": "Медиа сауаттылық",
     "explain": "Жердің айналуы күрт тоқтайды деген ғылыми болжам жоқ. Зерттеу атауы мен авторлары көрсетілмеген «ғалымдар анықтады» деген тіркес — жалған жаңалықтың жиі белгісі.",
     "sources": [{"title": "Wikipedia: Earth's rotation", "url": "https://en.wikipedia.org/wiki/Earth%27s_rotation"}]},
    {"id": 24, "claim": "Қаладағы жаңа кафеге кеше 1000 адам келді — деп кафе иесі өз парақшасында жазды.",
     "answer": "unknown", "category": "Медиа сауаттылық",
     "explain": "Мүдделі тараптың өз парақшасындағы сан — тәуелсіз дәлел емес. Растайтын да, жоққа шығаратын да мәлімет жоқ.",
     "sources": []},
]

BY_ID = {q["id"]: q for q in QUESTIONS}
ROUND_SIZE = 10

ACHIEVEMENTS = {
    "first": {"title": "Алғашқы қадам", "desc": "Алғашқы дұрыс жауап", "icon": "✦"},
    "streak3": {"title": "Үштік серия", "desc": "Қатарынан 3 дұрыс жауап", "icon": "⚡"},
    "streak5": {"title": "Шындық іздеуші", "desc": "Қатарынан 5 дұрыс жауап", "icon": "🔥"},
    "careful": {"title": "Сақ тексеруші", "desc": "«Дәлел жеткіліксіз» жағдайын дұрыс таныды", "icon": "🔍"},
    "perfect": {"title": "Мінсіз раунд", "desc": "Барлық сұраққа дұрыс жауап", "icon": "🏆"},
}


def new_round():
    ids = random.sample([q["id"] for q in QUESTIONS], ROUND_SIZE)
    return {"ids": ids, "idx": 0, "score": 0, "correct": 0, "streak": 0, "best_streak": 0,
            "achievements": [], "answered": False}


def public_question(state):
    q = BY_ID[state["ids"][state["idx"]]]
    return {"id": q["id"], "claim": q["claim"], "category": q["category"],
            "number": state["idx"] + 1, "total": len(state["ids"]),
            "level": 1 + state["idx"] * 3 // len(state["ids"])}


def level_name(level):
    return {1: "Бастаушы", 2: "Зерттеуші", 3: "Сарапшы"}.get(level, "Сарапшы")
