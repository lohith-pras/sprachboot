"""OS keychain wrapper for API keys. Keys never touch the database."""
import keyring

SERVICE = "SprachBoot"
KNOWN_KEYS = ("openrouter", "openai", "deepl")


def _check(name: str) -> None:
    if name not in KNOWN_KEYS:
        raise ValueError(f"Unknown key service: {name!r}")


def set_key(name: str, value: str) -> None:
    _check(name)
    keyring.set_password(SERVICE, name, value)


def get_key(name: str) -> str | None:
    _check(name)
    return keyring.get_password(SERVICE, name)


def delete_key(name: str) -> None:
    _check(name)
    keyring.delete_password(SERVICE, name)


def key_status() -> dict[str, bool]:
    return {name: get_key(name) is not None for name in KNOWN_KEYS}
