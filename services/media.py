"""Сурет пен видеоны тексеру: формат, метадеректер, өңдеу іздері, ELA талдауы."""
import base64
import hashlib
import io
import re
import struct
from datetime import datetime, timedelta

from PIL import ExifTags, Image, ImageChops, ImageOps

Image.MAX_IMAGE_PIXELS = 60_000_000

IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_EXT = {"mp4", "mov", "webm", "m4v"}
IMAGE_MAX = 15 * 1024 * 1024
VIDEO_MAX = 60 * 1024 * 1024

EDITORS = ["photoshop", "gimp", "lightroom", "snapseed", "canva", "picsart", "pixlr", "affinity", "capture one",
           "facetune", "meitu", "vsco", "paint.net", "illustrator", "inshot", "capcut", "premiere", "after effects",
           "davinci", "final cut", "imovie", "kinemaster"]
AI_MARKERS = ["midjourney", "stable diffusion", "dall-e", "dall·e", "openai", "firefly", "imagen", "leonardo",
              "novelai", "comfyui", "automatic1111", "sdxl", "flux", "gemini", "grok"]


class MediaError(Exception):
    pass


def detect_kind(data: bytes):
    if data[:3] == b"\xff\xd8\xff":
        return "image", "JPEG"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image", "PNG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", "WEBP"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image", "GIF"
    if data[4:8] == b"ftyp":
        brand = data[8:12].decode("latin-1", "replace").strip()
        return "video", "MOV (QuickTime)" if brand == "qt" else f"MP4 ({brand})"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "video", "WebM / Matroska"
    return None, None


def _fmt_size(n):
    return f"{n / 1024 / 1024:.2f} МБ" if n >= 1024 * 1024 else f"{n / 1024:.0f} КБ"


def _gps_to_deg(v):
    try:
        d, m, s = (float(x) for x in v)
        return d + m / 60 + s / 3600
    except (TypeError, ValueError):
        return None


def _ela(img: Image.Image):
    """Error Level Analysis: суретті қайта сығып, айырмашылықты күшейтеді."""
    rgb = img.convert("RGB")
    rgb.thumbnail((900, 900))
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=90)
    buf.seek(0)
    resaved = Image.open(buf)
    diff = ImageChops.difference(rgb, resaved)
    extrema = diff.getextrema()
    max_diff = max(e[1] for e in extrema) or 1
    gray = diff.convert("L")
    hist = gray.histogram()
    total = sum(hist) or 1
    mean = sum(i * c for i, c in enumerate(hist)) / total
    bright = sum(hist[40:]) / total  # айқын айырмашылығы бар пиксельдер үлесі
    scale = 255.0 / max_diff
    enhanced = diff.point(lambda p: min(255, int(p * scale)))
    out = io.BytesIO()
    enhanced.save(out, "PNG", optimize=True)
    return {
        "image": "data:image/png;base64," + base64.b64encode(out.getvalue()).decode(),
        "max_diff": max_diff, "mean": round(mean, 2), "bright_ratio": round(bright * 100, 2),
    }


def analyze_image(data: bytes, fmt: str):
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise MediaError("Суретті оқу мүмкін болмады — файл бүлінген немесе қолдау көрсетілмейді.")

    info = {"Формат": fmt, "Өлшемі": f"{img.width} × {img.height} px", "Түс режимі": img.mode}
    findings, metadata = [], {}
    exif = img.getexif()
    tags = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
    try:
        tags.update({ExifTags.TAGS.get(k, str(k)): v for k, v in exif.get_ifd(0x8769).items()})
    except Exception:
        pass
    gps = {}
    try:
        gps = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in exif.get_ifd(0x8825).items()}
    except Exception:
        pass

    labels = {
        "Make": "Құрылғы өндірушісі", "Model": "Құрылғы моделі", "Software": "Бағдарлама",
        "DateTimeOriginal": "Түсірілген уақыты", "DateTime": "Өзгертілген уақыты", "LensModel": "Объектив",
        "Artist": "Автор", "Copyright": "Авторлық құқық", "ExposureTime": "Экспозиция", "FNumber": "Диафрагма",
        "ISOSpeedRatings": "ISO", "FocalLength": "Фокус қашықтығы",
    }
    for k, lbl in labels.items():
        v = tags.get(k)
        if v not in (None, "", b""):
            metadata[lbl] = str(v).strip("\x00 ")[:120]

    software = str(tags.get("Software", "")).lower()
    text_blob = " ".join(str(v) for v in img.info.values() if isinstance(v, (str, bytes)))[:20000].lower()
    xmp = ""
    if b"<x:xmpmeta" in data:
        start = data.find(b"<x:xmpmeta")
        xmp = data[start:start + 20000].decode("utf-8", "ignore").lower()
        tool = re.search(r'creatortool[=">]+([^"<]+)', xmp)
        if tool:
            metadata["XMP CreatorTool"] = tool.group(1)[:120]
    haystack = " ".join([software, text_blob, xmp, metadata.get("XMP CreatorTool", "").lower()])

    if not tags and not xmp:
        findings.append({"type": "info", "text": "EXIF метадеректері жоқ. Әлеуметтік желілер мен мессенджерлер "
                                                 "метадеректерді жиі өшіреді — бұл өздігінен күдік белгісі емес."})
    if any(e in haystack for e in EDITORS):
        name = next(e for e in EDITORS if e in haystack)
        findings.append({"type": "warn", "text": f"Өңдеу бағдарламасының ізі табылды: «{name}». Сурет өңделген не "
                                                 f"экспортталған болуы мүмкін."})
    ai_hit = next((m for m in AI_MARKERS if m in haystack), None)
    if ai_hit or "parameters" in img.info or "prompt" in img.info:
        findings.append({"type": "bad", "text": "Метадеректерде генеративті AI құралының ізі бар"
                                                + (f" («{ai_hit}»)" if ai_hit else " (генерация параметрлері)") + "."})
    if b"c2pa" in data or b"jumb" in data:
        findings.append({"type": "info", "text": "C2PA / Content Credentials белгісі бар — шығу тегі туралы "
                                                 "қолтаңбалы мәлімет қамтылуы мүмкін (contentcredentials.org арқылы тексеріңіз)."})
    dto, dtm = tags.get("DateTimeOriginal"), tags.get("DateTime")
    if dto and dtm and str(dto) != str(dtm):
        try:
            a = datetime.strptime(str(dto)[:19], "%Y:%m:%d %H:%M:%S")
            b = datetime.strptime(str(dtm)[:19], "%Y:%m:%d %H:%M:%S")
            if abs(b - a) > timedelta(minutes=2):
                findings.append({"type": "warn", "text": "Түсірілген және өзгертілген уақыттары сәйкес келмейді — "
                                                         "файл кейін сақталған немесе өңделген болуы мүмкін."})
        except ValueError:
            pass
    if gps:
        lat = _gps_to_deg(gps.get("GPSLatitude"))
        findings.append({"type": "warn", "text": "Суретте GPS координаттары бар. Жарияламас бұрын оларды өшіру "
                                                 "ұсынылады — орналасқан жеріңізді ашуы мүмкін."})
        metadata["GPS"] = "бар (дәлдік үшін көрсетілмейді)" if lat is not None else "бар"

    ela = None
    if fmt in ("JPEG", "WEBP", "PNG"):
        try:
            ela = _ela(ImageOps.exif_transpose(img))
            if fmt == "JPEG" and ela["bright_ratio"] > 6:
                findings.append({"type": "warn", "text": "ELA картасында қысу деңгейі біркелкі емес аймақтар бар. "
                                                         "Бұл өңдеуді көрсетуі мүмкін, бірақ мәтін, жиектер мен қайта "
                                                         "сақтау да осындай әсер береді."})
        except Exception:
            ela = None
    if not findings:
        findings.append({"type": "good", "text": "Метадеректерде өңдеу немесе генерация іздері табылмады."})
    return info, metadata, findings, ela


def _mp4_boxes(data: bytes, start: int, end: int):
    i = start
    while i + 8 <= end:
        size, typ = struct.unpack(">I4s", data[i:i + 8])
        header = 8
        if size == 1 and i + 16 <= end:
            size = struct.unpack(">Q", data[i + 8:i + 16])[0]
            header = 16
        elif size == 0:
            size = end - i
        if size < header:
            break
        yield typ.decode("latin-1"), i + header, min(i + size, end)
        i += size


def analyze_video(data: bytes, fmt: str):
    info = {"Формат": fmt}
    metadata, findings = {}, []
    if fmt.startswith(("MP4", "MOV")):
        for typ, s, e in _mp4_boxes(data, 0, len(data)):
            if typ == "moov":
                for t2, s2, e2 in _mp4_boxes(data, s, e):
                    if t2 == "mvhd":
                        ver = data[s2]
                        if ver == 1:
                            ctime, _, scale, dur = struct.unpack(">QQIQ", data[s2 + 4:s2 + 32])
                        else:
                            ctime, _, scale, dur = struct.unpack(">IIII", data[s2 + 4:s2 + 20])
                        if scale:
                            info["Ұзақтығы"] = f"{dur / scale:.1f} сек"
                        if ctime:
                            created = datetime(1904, 1, 1) + timedelta(seconds=ctime)
                            metadata["Жасалған уақыты (mvhd)"] = created.strftime("%d.%m.%Y %H:%M") + " UTC"
        low = data[:4_000_000].lower()
        m = re.search(rb"(lavf[\d.]+|handbrake[^\x00]{0,20}|capcut|inshot|premiere|davinci|final cut|imovie)", low)
        if m:
            tool = m.group(1).decode("latin-1", "ignore")
            metadata["Кодтау құралы"] = tool[:60]
            findings.append({"type": "warn", "text": f"Видео «{tool[:30]}» құралымен қайта кодталған немесе өңделген "
                                                     f"болуы мүмкін. Бұл жиі кездеседі және жалғандықты білдірмейді."})
        if b"\xa9xyz" in data[:4_000_000]:
            findings.append({"type": "warn", "text": "Видеода геолокация тегі (©xyz) бар."})
    if not findings:
        findings.append({"type": "info", "text": "Видео метадеректерінде айқын өңдеу іздері табылмады. Видеоны кадр "
                                                 "бойынша тексеру үшін кілт кадрларды кері іздеу қызметтерімен салыстырыңыз."})
    return info, metadata, findings


def analyze(data: bytes, filename: str):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    kind, fmt = detect_kind(data)
    if kind is None or (ext and ext not in IMAGE_EXT | VIDEO_EXT):
        raise MediaError("Бұл формат қолдау көрсетілмейді. Рұқсат етілген: JPG, PNG, WEBP, GIF, MP4, MOV, WEBM.")
    if kind == "image" and len(data) > IMAGE_MAX:
        raise MediaError("Сурет 15 МБ-тан аспауы керек.")
    if kind == "video" and len(data) > VIDEO_MAX:
        raise MediaError("Видео 60 МБ-тан аспауы керек.")

    if kind == "image":
        info, metadata, findings, ela = analyze_image(data, fmt)
    else:
        (info, metadata, findings), ela = analyze_video(data, fmt), None
    info["Файл көлемі"] = _fmt_size(len(data))
    sha = hashlib.sha256(data).hexdigest()
    bad = sum(1 for f in findings if f["type"] == "bad")
    warn = sum(1 for f in findings if f["type"] == "warn")
    if bad:
        level, label = "high", "Генерация немесе күшті өңдеу іздері бар"
    elif warn:
        level, label = "medium", "Өңдеу белгілері болуы мүмкін"
    else:
        level, label = "low", "Айқын өңдеу іздері табылмады"
    return {
        "kind": kind, "level": level, "label": label, "filename": filename[:120],
        "info": info, "metadata": metadata, "findings": findings, "ela": ela, "sha256": sha,
        "reverse_search": [
            {"label": "Google Lens", "url": "https://lens.google.com/"},
            {"label": "Yandex Суреттер", "url": "https://yandex.kz/images/"},
            {"label": "TinEye", "url": "https://tineye.com/"},
        ],
        "note": "Метадеректер медианың түпнұсқа екенін дәлелдемейді: оларды өшіруге де, жалғандауға да болады. "
                "Түпнұсқаны табу үшін кері іздеу қызметтерін қолданыңыз (автоматты іздеу қызметі қосылмаған).",
    }
