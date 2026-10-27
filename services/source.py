"""Ақпарат дереккөзін (сайт, мақала) тексеру. Тек нақты жүктелген деректер көрсетіледі."""
import json
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote_plus, urlparse

from . import web

KNOWN = {
    # Ресми мемлекеттік және халықаралық ұйымдар
    "gov.kz": "Қазақстанның мемлекеттік порталы", "egov.kz": "Электрондық үкімет порталы",
    "akorda.kz": "ҚР Президентінің ресми сайты", "primeminister.kz": "ҚР Премьер-Министрінің ресми сайты",
    "parlam.kz": "ҚР Парламентінің ресми сайты", "nationalbank.kz": "ҚР Ұлттық Банкі", "stat.gov.kz": "Ұлттық статистика бюросы",
    "who.int": "Дүниежүзілік денсаулық сақтау ұйымы", "un.org": "Біріккен Ұлттар Ұйымы",
    # Ақпарат агенттіктері мен БАҚ
    "kazinform.kz": "«Kazinform» ақпарат агенттігі", "inform.kz": "«Kazinform» ақпарат агенттігі",
    "tengrinews.kz": "Tengrinews.kz", "zakon.kz": "Zakon.kz", "kursiv.media": "Kursiv Media",
    "khabar.kz": "«Хабар» агенттігі", "24.kz": "«Хабар 24»", "azattyq.org": "Азаттық радиосы",
    "egemen.kz": "«Егемен Қазақстан»", "kaztag.kz": "КазТАГ", "vlast.kz": "Vlast.kz", "forbes.kz": "Forbes Kazakhstan",
    "bbc.com": "BBC", "bbc.co.uk": "BBC", "reuters.com": "Reuters", "apnews.com": "Associated Press",
    "theguardian.com": "The Guardian", "nytimes.com": "The New York Times", "dw.com": "Deutsche Welle",
    "wikipedia.org": "Wikipedia (ашық энциклопедия)", "factcheck.kz": "Factcheck.kz",
}


def _meta(html: str, *names):
    for n in names:
        for pat in (
            rf'<meta[^>]+(?:property|name|itemprop)=["\']{re.escape(n)}["\'][^>]*content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name|itemprop)=["\']{re.escape(n)}["\']',
        ):
            m = re.search(pat, html, re.I)
            if m:
                return unescape(m.group(1)).strip()
    return None


def _jsonld(html: str):
    out = {}
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.I | re.S):
        try:
            data = json.loads(block.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if not isinstance(it, dict):
                continue
            out.setdefault("datePublished", it.get("datePublished"))
            out.setdefault("dateModified", it.get("dateModified"))
            a = it.get("author")
            if a and "author" not in out:
                if isinstance(a, list):
                    a = a[0] if a else None
                if isinstance(a, dict):
                    a = a.get("name")
                if isinstance(a, str):
                    out["author"] = a
            pub = it.get("publisher")
            if isinstance(pub, dict) and pub.get("name"):
                out.setdefault("publisher", pub.get("name"))
    return {k: v for k, v in out.items() if v}


def _fmt_date(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d.strftime("%d.%m.%Y")
    except ValueError:
        return str(value)[:25]


def _text_of(html: str):
    html = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def analyze(url_raw: str, article_text: str = ""):
    url = web.normalize_url(url_raw)
    resp, content, final_url = web.safe_get(url)
    ctype = resp.headers.get("Content-Type", "")
    parsed = urlparse(final_url)
    host = (parsed.hostname or "").lower()
    domain = web.registered_domain(host)

    html = ""
    if "html" in ctype.lower() or content[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
        enc = resp.encoding if resp.encoding and resp.encoding.lower() != "iso-8859-1" else "utf-8"
        html = content.decode(enc, errors="replace")

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = _meta(html, "og:title", "twitter:title") or (unescape(title_m.group(1)).strip() if title_m else None)
    ld = _jsonld(html)
    site_name = _meta(html, "og:site_name", "application-name") or ld.get("publisher")
    author = _meta(html, "author", "article:author", "twitter:creator", "sailthru.author") or ld.get("author")
    published = (_meta(html, "article:published_time", "datePublished", "pubdate", "publish-date", "date", "dc.date")
                 or ld.get("datePublished"))
    if not published:
        tm = re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', html, re.I)
        published = tm.group(1) if tm else None
    modified = _meta(html, "article:modified_time", "dateModified") or ld.get("dateModified")
    description = _meta(html, "og:description", "description", "twitter:description")
    body_text = _text_of(html)
    word_count = len(body_text.split())
    links = re.findall(r'<a[^>]+href=["\'](https?://[^"\']+)["\']', html, re.I)
    external = {web.registered_domain(urlparse(h).hostname or "") for h in links} - {domain, ""}
    has_about = bool(re.search(r'href=["\'][^"\']*(about|contacts?|kontakt|redakci|байланыс|біз-туралы|o-nas|o-proekte)',
                               html, re.I))

    rdap = web.rdap_domain(domain) if not web.is_ip(host) else None
    age_days = None
    if rdap and rdap.get("registered"):
        try:
            age_days = (datetime.now(timezone.utc) -
                        datetime.fromisoformat(rdap["registered"].replace("Z", "+00:00"))).days
        except ValueError:
            pass

    signals = []

    def sig(kind, text):
        signals.append({"type": kind, "text": text})

    known = KNOWN.get(domain) or (KNOWN.get(".".join(domain.split(".")[-2:])) if domain.endswith(".gov.kz") else None)
    if host.endswith(".gov.kz") or domain == "gov.kz":
        sig("good", "Мемлекеттік .gov.kz домені — ресми органның сайты.")
    elif known:
        sig("good", f"Белгілі дереккөздер тізімінде: {known}.")
    else:
        sig("info", "Домен белгілі дереккөздер тізімінде жоқ — бұл жаман дегенді білдірмейді, бірақ қосымша тексеру қажет.")
    if parsed.scheme == "https":
        sig("good", "HTTPS қорғалған байланыс қолданылады.")
    else:
        sig("bad", "Сайт қорғалмаған HTTP байланысымен жұмыс істейді.")
    if age_days is not None:
        years = age_days / 365.25
        if age_days < 180:
            sig("bad", f"Домен жақында тіркелген ({age_days} күн бұрын). Жаңа сайттарды мұқият тексеру керек.")
        elif years >= 3:
            sig("good", f"Домен {years:.0f} жылдан астам бұрын тіркелген.")
        else:
            sig("info", f"Домен шамамен {years:.1f} жыл бұрын тіркелген.")
    else:
        sig("info", "Домен тіркеу күні қолжетімсіз (бұл аймақ үшін ашық RDAP деректері жоқ болуы мүмкін).")
    if author:
        sig("good", "Автор көрсетілген.")
    elif html:
        sig("bad", "Бетте автор туралы мәлімет табылмады.")
    if published:
        sig("good", "Жарияланған күні көрсетілген.")
    elif html:
        sig("info", "Жарияланған күні метадеректерде табылмады.")
    if has_about:
        sig("good", "«Біз туралы» немесе байланыс беті сілтемесі бар.")
    elif html:
        sig("info", "«Біз туралы» / байланыс беті сілтемесі табылмады.")
    if len(external) >= 3:
        sig("good", f"Мәтінде басқа {len(external)} доменге сілтеме бар (дереккөздерге сілтеу белгісі).")
    if resp.status_code >= 400:
        sig("bad", f"Сайт қате кодын қайтарды: HTTP {resp.status_code}.")

    good = sum(1 for s in signals if s["type"] == "good")
    bad = sum(1 for s in signals if s["type"] == "bad")
    score = max(5, min(95, 50 + good * 8 - bad * 12))
    if score >= 70:
        level, label = "good", "Сенімділік белгілері басым"
    elif score >= 45:
        level, label = "medium", "Аралас белгілер — қосымша тексеру қажет"
    else:
        level, label = "bad", "Күмәнді белгілер басым"

    query = title or (article_text[:120] if article_text else domain)
    related = []
    if query:
        q = " ".join(re.findall(r"\w+", query)[:8])
        related = web.wiki_search(q, "kk", 2) + web.wiki_search(q, "ru", 2)

    return {
        "level": level, "label": label, "score": score,
        "url": final_url, "requested_url": url, "host": host, "domain": domain,
        "http_status": resp.status_code, "content_type": ctype.split(";")[0],
        "title": title, "site_name": site_name, "author": author,
        "published": _fmt_date(published), "modified": _fmt_date(modified),
        "description": description, "word_count": word_count if html else None,
        "external_domains": sorted(external)[:12],
        "rdap": rdap, "age_days": age_days, "known": known,
        "signals": signals, "related": related,
        "search_links": [
            {"label": "Google News-тен іздеу", "url": "https://news.google.com/search?q=" + quote_plus(query or domain)},
            {"label": "Factcheck.kz-тен іздеу", "url": "https://factcheck.kz/?s=" + quote_plus(query or domain)},
        ],
        "note": "Бағалау тек табылған белгілерге сүйенеді. Бұл белгілер мақаланың мазмұны шын не жалған екенін дәлелдемейді.",
    }
