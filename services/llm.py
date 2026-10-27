"""AI модельге қосылу: Anthropic API (ANTHROPIC_API_KEY) немесе жергілікті Ollama.
Кілттер тек серверде сақталады. Модель қолжетімсіз болса None қайтарылады."""
import json
import os
import re
import time

import requests

_status_cache = {"t": 0.0, "value": None}


def _provider_pref():
    return os.environ.get("AI_PROVIDER", "auto").lower()


def _ollama_url():
    return os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")


def _ollama_model():
    return os.environ.get("OLLAMA_MODEL", "llama3.2:3b")


def status():
    """{'provider': 'anthropic'|'ollama'|None, 'model': str, 'local': bool}"""
    now = time.time()
    if now - _status_cache["t"] < 60 and _status_cache["value"] is not None:
        return _status_cache["value"]
    pref = _provider_pref()
    value = {"provider": None, "model": None, "local": False}
    if pref in ("auto", "anthropic") and os.environ.get("ANTHROPIC_API_KEY"):
        value = {"provider": "anthropic", "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "local": False}
    # Serverless ортада жергілікті Ollama жоқ: оны тек анық сұралса ғана іздейміз
    elif pref == "ollama" or (pref == "auto" and not os.environ.get("VERCEL")):
        try:
            r = requests.get(_ollama_url() + "/api/tags", timeout=2)
            names = [m.get("name") for m in r.json().get("models", [])]
            model = _ollama_model()
            if model in names or (names and not os.environ.get("OLLAMA_MODEL")):
                value = {"provider": "ollama", "model": model if model in names else names[0], "local": True}
        except Exception:
            pass
    _status_cache.update(t=now, value=value)
    return value


def _extract_json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def ask_json(system: str, user: str, max_tokens: int = 700, timeout: int = 60):
    """Модельден JSON жауап алады. Сәтсіз болса None."""
    st = status()
    try:
        if st["provider"] == "anthropic":
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": st["model"],
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=timeout,
            )
            r.raise_for_status()
            text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
            return _extract_json(text)
        if st["provider"] == "ollama":
            r = requests.post(
                _ollama_url() + "/api/chat",
                json={
                    "model": st["model"],
                    "stream": False,
                    "format": "json",
                    "keep_alive": "30m",
                    "options": {"temperature": 0.1, "num_predict": min(max_tokens, 160), "num_ctx": 2048},
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                },
                timeout=timeout,
            )
            r.raise_for_status()
            return _extract_json(r.json().get("message", {}).get("content", ""))
    except Exception:
        return None
    return None
