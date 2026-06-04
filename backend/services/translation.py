"""DeepL translation (German → English). Key read from OS keychain.

Used for inline word lookup and per-message "show in English" in the chat UI.
Returns None when no key is configured so the frontend can hide the translate UI
gracefully. Words repeat heavily, so results are memoised in a bounded LRU cache.
"""
from collections import OrderedDict

import httpx

from services import keychain

# DeepL free-tier endpoint. Pro keys (no ':fx' suffix) use api.deepl.com, but the
# free endpoint is what the settings key-test targets, so keep them consistent.
_DEEPL_URL = "https://api-free.deepl.com/v2/translate"
_CACHE_MAX = 1000
_cache: "OrderedDict[str, str]" = OrderedDict()


def _cache_get(text: str) -> str | None:
    val = _cache.get(text)
    if val is not None:
        _cache.move_to_end(text)
    return val


def _cache_put(text: str, translation: str) -> None:
    _cache[text] = translation
    _cache.move_to_end(text)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


async def _translate(text: str) -> str | None:
    text = text.strip()
    if not text:
        return ""
    cached = _cache_get(text)
    if cached is not None:
        return cached

    key = keychain.get_key("deepl")
    if not key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                _DEEPL_URL,
                headers={"Authorization": f"DeepL-Auth-Key {key}"},
                data={"text": text, "source_lang": "DE", "target_lang": "EN"},
            )
            r.raise_for_status()
            translations = r.json().get("translations", [])
    except Exception:
        return None

    if not translations:
        return None
    translation = translations[0].get("text", "")
    _cache_put(text, translation)
    return translation


async def translate_word(word: str) -> str | None:
    return await _translate(word)


async def translate_sentence(text: str) -> str | None:
    return await _translate(text)
