from services import openrouter_client, keychain


def test_resolve_key_prefers_keychain(monkeypatch):
    monkeypatch.setattr(keychain, "get_key", lambda n: "sk-from-keychain")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env")
    assert openrouter_client.resolve_api_key() == "sk-from-keychain"


def test_resolve_key_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(keychain, "get_key", lambda n: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env")
    assert openrouter_client.resolve_api_key() == "sk-from-env"
