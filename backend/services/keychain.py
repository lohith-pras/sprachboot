"""Local API-key store. Keys live in a JSON file beside the app, never the OS
keychain (avoids macOS login-keychain password prompts) and never the database."""
import json
import os
from pathlib import Path

SERVICE = "SprachBoot"
KNOWN_KEYS = ("openrouter", "openai", "deepl")

# Where the plaintext key file lives (backend/api_keys.json). Override with
# SPRACHBOOT_KEYS_FILE for tests.
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "api_keys.json"

# Fallback environment variables, used when a key isn't in the file.
_ENV_FALLBACK = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepl": "DEEPL_API_KEY",
}


def _check(name: str) -> None:
    if name not in KNOWN_KEYS:
        raise ValueError(f"Unknown key service: {name!r}")


def _path() -> Path:
    return Path(os.getenv("SPRACHBOOT_KEYS_FILE", str(_DEFAULT_PATH)))


def _load() -> dict[str, str]:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, str]) -> None:
    p = _path()
    p.write_text(json.dumps(data, indent=2))
    os.chmod(p, 0o600)


def set_key(name: str, value: str) -> None:
    _check(name)
    data = _load()
    data[name] = value
    _save(data)


def get_key(name: str) -> str | None:
    _check(name)
    val = _load().get(name)
    if val:
        return val
    return os.getenv(_ENV_FALLBACK[name]) or None


def delete_key(name: str) -> None:
    _check(name)
    data = _load()
    data.pop(name, None)
    _save(data)


def key_status() -> dict[str, bool]:
    return {name: get_key(name) is not None for name in KNOWN_KEYS}
