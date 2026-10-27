"""Сыртқы желіге қауіпсіз сұраныстар: URL жүктеу, Wikipedia іздеу, RDAP домен деректері."""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests

UA = "Mozilla/5.0 (compatible; AqiqatAI/1.0; educational fact-checking project)"
HEADERS = {"User-Agent": UA, "Accept-Language": "kk,ru;q=0.8,en;q=0.6"}

# Екі деңгейлі домен аймақтары (eTLD+1 табу үшін)
SECOND_LEVEL = {
    "gov.kz", "edu.kz", "com.kz", "org.kz", "net.kz", "mil.kz", "co.uk", "org.uk", "ac.uk",
    "gov.uk", "com.ru", "org.ru", "net.ru", "msk.ru", "spb.ru", "com.ua", "co.jp", "com.au",
    "com.tr", "gov.tr", "com.cn", "co.kr", "com.br",
}


class FetchError(Exception):
    pass


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise FetchError("URL енгізілмеді.")
    if len(raw) > 2000:
        raise FetchError("URL тым ұзын.")
    if not re.match(r"^https?://", raw, re.I):
        if "://" in raw:
            raise FetchError("Тек http немесе https сілтемелерін тексеруге болады.")
        raw = "https://" + raw
    p = urlparse(raw)
    if p.scheme.lower() not in ("http", "https") or not p.hostname or "." not in p.hostname:
        raise FetchError("URL форматы дұрыс емес.")
    return raw


def registered_domain(host: str) -> str:
    host = (host or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _check_public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise FetchError("Домен табылмады: DNS жауап бермеді.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise FetchError("Ішкі желі мекенжайларын тексеруге рұқсат жоқ.")


def safe_get(url: str, max_bytes: int = 2_000_000, timeout: int = 8):
    """Ішкі желіге (SSRF) жол бермей бетті жүктейді. (response, bytes, final_url) қайтарады."""
    for _ in range(5):
        host = urlparse(url).hostname
        _check_public_host(host)
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=False, stream=True)
        except requests.exceptions.SSLError:
            raise FetchError("Сайттың SSL сертификаты жарамсыз немесе қате.")
        except requests.exceptions.Timeout:
            raise FetchError("Сайт уақытында жауап бермеді.")
        except requests.exceptions.RequestException:
            raise FetchError("Сайтқа қосылу мүмкін болмады.")
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location")
            r.close()
            if not loc:
                break
            url = urljoin(url, loc)
            if urlparse(url).scheme not in ("http", "https"):
                raise FetchError("Сайт рұқсат етілмеген мекенжайға бағыттады.")
            continue
        content = b""
        for chunk in r.iter_content(65536):
            content += chunk
            if len(content) > max_bytes:
                break
        r.close()
        return r, content, url
    raise FetchError("Бағыттау (redirect) тым көп.")


def wiki_search(query: str, lang: str = "kk", limit: int = 3):
    """Wikipedia-дан нақты табылған мақалалар. Қате болса бос тізім."""
    if not query.strip():
        return []
    params = {
        "action": "query", "generator": "search", "gsrsearch": query, "gsrlimit": limit,
        "prop": "extracts|info", "exintro": 1, "explaintext": 1, "exsentences": 3,
        "exlimit": limit, "inprop": "url", "format": "json", "formatversion": 2,
    }
    try:
        r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", params=params,
                         headers=HEADERS, timeout=7)
        pages = r.json().get("query", {}).get("pages", [])
    except Exception:
        return []
    pages.sort(key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        extract = re.sub(r"\s+", " ", p.get("extract") or "").strip()
        if not extract:
            continue
        out.append({
            "title": p.get("title", ""),
            "url": p.get("fullurl", ""),
            "snippet": extract[:420] + ("…" if len(extract) > 420 else ""),
            "source": f"Wikipedia ({lang})",
        })
    return out


def rdap_domain(domain: str):
    """Домен тіркеу деректері (RDAP). Қолжетімсіз болса None."""
    try:
        r = requests.get(f"https://rdap.org/domain/{domain}", headers=HEADERS, timeout=7)
        if r.status_code != 200:
            return None
        j = r.json()
    except Exception:
        return None
    events = {e.get("eventAction"): e.get("eventDate") for e in j.get("events", []) if isinstance(e, dict)}
    registrar = None
    for ent in j.get("entities", []) or []:
        if "registrar" in (ent.get("roles") or []):
            try:
                for item in ent["vcardArray"][1]:
                    if item[0] == "fn":
                        registrar = item[3]
            except (KeyError, IndexError, TypeError):
                pass
    return {
        "registered": events.get("registration"),
        "expires": events.get("expiration"),
        "updated": events.get("last changed"),
        "registrar": registrar,
        "rdap_url": r.url,
    }
