import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from services import keychain, translation


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch, tmp_path):
    monkeypatch.setenv("SPRACHBOOT_KEYS_FILE", str(tmp_path / "keys.json"))
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "DEEPL_API_KEY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def clear_cache():
    translation._cache.clear()
    yield
    translation._cache.clear()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_word_no_key_returns_503(client):
    async with client as c:
        r = await c.post("/translate/word", json={"word": "Haus"})
    assert r.status_code == 503


async def test_word_with_key(client, fake_keyring, monkeypatch):
    keychain.set_key("deepl", "fake-key")

    async def fake_translate(text):
        return "house"
    monkeypatch.setattr(translation, "_translate", fake_translate)

    async with client as c:
        r = await c.post("/translate/word", json={"word": "Haus"})
    assert r.status_code == 200
    assert r.json()["translation"] == "house"


async def test_sentence_with_key(client, fake_keyring, monkeypatch):
    keychain.set_key("deepl", "fake-key")

    async def fake_translate(text):
        return "I am going hiking."
    monkeypatch.setattr(translation, "_translate", fake_translate)

    async with client as c:
        r = await c.post("/translate/sentence", json={"text": "Ich gehe wandern."})
    assert r.status_code == 200
    assert r.json()["translation"] == "I am going hiking."


async def test_cache_hit_skips_http(monkeypatch):
    keychain.set_key("deepl", "fake-key")
    calls = {"n": 0}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"translations": [{"text": "house"}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, *a, **k):
            calls["n"] += 1
            return FakeResp()

    monkeypatch.setattr(translation.httpx, "AsyncClient", FakeClient)

    assert await translation.translate_word("Haus") == "house"
    assert await translation.translate_word("Haus") == "house"
    assert calls["n"] == 1  # second call served from cache
