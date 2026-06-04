import pytest
from services import keychain


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    store = {}
    monkeypatch.setattr(
        keychain.keyring, "set_password",
        lambda svc, name, val: store.__setitem__((svc, name), val),
    )
    monkeypatch.setattr(
        keychain.keyring, "get_password",
        lambda svc, name: store.get((svc, name)),
    )
    monkeypatch.setattr(
        keychain.keyring, "delete_password",
        lambda svc, name: store.pop((svc, name), None),
    )
    return store


def test_set_and_get_key():
    keychain.set_key("openrouter", "sk-or-123")
    assert keychain.get_key("openrouter") == "sk-or-123"


def test_get_missing_key_returns_none():
    assert keychain.get_key("deepl") is None


def test_status_reports_presence():
    keychain.set_key("openrouter", "sk-or-123")
    status = keychain.key_status()
    assert status == {"openrouter": True, "openai": False, "deepl": False}


def test_rejects_unknown_service():
    with pytest.raises(ValueError):
        keychain.set_key("bogus", "x")
