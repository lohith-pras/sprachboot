import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from models.db import get_db
from services import keychain


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    store = {}
    monkeypatch.setattr(keychain.keyring, "set_password",
                        lambda s, n, v: store.__setitem__((s, n), v))
    monkeypatch.setattr(keychain.keyring, "get_password",
                        lambda s, n: store.get((s, n)))
    return store


@pytest.fixture
def client(db):
    async def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


async def test_get_default_preferences(client):
    async with client as c:
        r = await c.get("/settings/preferences")
    assert r.status_code == 200
    body = r.json()
    assert body["user_name"] == "User"
    assert body["onboarding_complete"] is False


async def test_update_preferences(client):
    async with client as c:
        r = await c.put("/settings/preferences",
                        json={"user_name": "Lo", "onboarding_complete": True})
        assert r.status_code == 200
        r2 = await c.get("/settings/preferences")
    assert r2.json()["user_name"] == "Lo"
    assert r2.json()["onboarding_complete"] is True


async def test_set_apikey_and_status(client):
    async with client as c:
        r = await c.post("/settings/apikey",
                         json={"service": "openrouter", "key": "sk-or-xyz"})
        assert r.status_code == 200
        s = await c.get("/settings/apikey/status")
    assert s.json() == {"openrouter": True, "openai": False, "deepl": False}
