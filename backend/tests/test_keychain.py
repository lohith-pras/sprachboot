import pytest
from services import keychain


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch, tmp_path):
    monkeypatch.setenv("SPRACHBOOT_KEYS_FILE", str(tmp_path / "keys.json"))
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "DEEPL_API_KEY"):
        monkeypatch.delenv(var, raising=False)


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
