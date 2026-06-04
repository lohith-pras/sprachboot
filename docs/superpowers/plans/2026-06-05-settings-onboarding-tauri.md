# Settings, Onboarding & Tauri Desktop Build — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add secure in-app API key management (OS keychain), user-selectable OpenRouter models, a first-run onboarding wizard (name + keys + models), and package the app as cross-platform `.dmg` (macOS) / `.exe` (Windows) via Tauri v2.

**Architecture:** A `user_preferences` table (single row) holds name + model choices + onboarding flag. API keys live ONLY in the OS keychain via the `keyring` lib. A new `settings` FastAPI router exposes preferences + key management + OpenRouter model listing. The frontend gains an `/onboard` wizard (gated in root layout) and a `/settings` page. For packaging, the Next.js proxy routes are deleted (frontend calls FastAPI directly), Next is statically exported and served by FastAPI, FastAPI is bundled as a PyInstaller sidecar, and Tauri wraps it. GitHub Actions builds installers on macOS + Windows runners.

**Tech Stack:** FastAPI, SQLAlchemy (async), `keyring`, `httpx`, Next.js 16 (App Router), Tauri v2 (Rust), PyInstaller, GitHub Actions. Backend tests via `pytest` + `pytest-asyncio`. Endpoint/UI verification via `curl` and manual checks (no JS test runner in repo).

**Spec:** `docs/superpowers/specs/2026-06-05-settings-onboarding-tauri-design.md`

---

## File Structure

**Backend (create):**
- `backend/services/keychain.py` — keyring wrapper (set/get/status/test)
- `backend/routers/settings.py` — settings + key + models endpoints
- `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_keychain.py`, `backend/tests/test_preferences.py`, `backend/tests/test_settings_api.py`

**Backend (modify):**
- `backend/models/db.py` — add `UserPreferences` model + `get_or_create_preferences`
- `backend/models/schemas.py` — add settings Pydantic schemas
- `backend/services/openrouter_client.py` — key from keychain; model resolver
- `backend/services/conversation.py` — use resolved conv model
- `backend/services/error_analysis.py` — use resolved analysis model
- `backend/routers/session.py` — pass resolved model into conversation
- `backend/main.py` — register settings router; widen CORS
- `backend/pyproject.toml` — add `keyring`; dev-deps `pytest`, `pytest-asyncio`

**Frontend (create):**
- `frontend/lib/settings.ts` — typed client for settings endpoints
- `frontend/app/onboard/page.tsx` — 3-step wizard
- `frontend/app/onboard/onboard.module.css` — wizard styles
- `frontend/app/settings/page.tsx` — settings page
- `frontend/components/OnboardingGate.tsx` — client redirect gate

**Frontend (modify):**
- `frontend/app/layout.tsx` — mount `OnboardingGate`
- `frontend/app/page.tsx` — greeting uses `user_name`
- `frontend/components/Nav.tsx` — add Settings link

**Packaging (create — Phase 3):**
- `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `src-tauri/src/main.rs`, `src-tauri/build.rs`
- `backend/sprachboot-server.spec` — PyInstaller spec
- `.github/workflows/release.yml` — CI matrix

**Packaging (modify — Phase 3):**
- delete `frontend/app/api/` (whole dir)
- `frontend/lib/api.ts` (new) — base URL helper; repoint all fetches
- `frontend/next.config.ts` — `output: 'export'`
- `backend/main.py` — mount StaticFiles for exported frontend

---

# PHASE 1 — Backend: preferences, keychain, model selection

### Task 1: Test harness + `UserPreferences` model

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Modify: `backend/models/db.py`
- Create: `backend/tests/test_preferences.py`

- [ ] **Step 1: Add test + keyring deps**

In `backend/pyproject.toml`, add to `dependencies`:
```toml
    "keyring>=25.0.0",
```
Append a dev-dependency group at end of file:
```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```
Run: `cd backend && uv sync --all-groups`
Expected: resolves and installs `keyring`, `pytest`, `pytest-asyncio`.

- [ ] **Step 2: Add pytest config**

Append to `backend/pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create test package + shared in-memory DB fixture**

Create `backend/tests/__init__.py` (empty).

Create `backend/tests/conftest.py`:
```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models.db import Base


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()
```

- [ ] **Step 4: Write failing test for `get_or_create_preferences`**

Create `backend/tests/test_preferences.py`:
```python
from models.db import get_or_create_preferences


async def test_creates_default_row_on_first_access(db):
    prefs = await get_or_create_preferences(db)
    assert prefs.id == 1
    assert prefs.user_name == "User"
    assert prefs.conv_model == "meta-llama/llama-3.3-70b-instruct"
    assert prefs.analysis_model == "deepseek/deepseek-v4-flash"
    assert prefs.onboarding_complete is False


async def test_returns_same_row_on_second_access(db):
    first = await get_or_create_preferences(db)
    first.user_name = "Lo"
    await db.commit()
    second = await get_or_create_preferences(db)
    assert second.id == 1
    assert second.user_name == "Lo"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_preferences.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_or_create_preferences'`.

- [ ] **Step 6: Add model + helper**

In `backend/models/db.py`, add after the `TestResult` class:
```python
class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    user_name: Mapped[str] = mapped_column(String(100), default="User")
    conv_model: Mapped[str] = mapped_column(
        String(200), default="meta-llama/llama-3.3-70b-instruct"
    )
    analysis_model: Mapped[str] = mapped_column(
        String(200), default="deepseek/deepseek-v4-flash"
    )
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
```
Add this function after `get_db` at the end of the file:
```python
async def get_or_create_preferences(session: AsyncSession) -> "UserPreferences":
    from sqlalchemy import select
    result = await session.execute(
        select(UserPreferences).where(UserPreferences.id == 1)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = UserPreferences(id=1)
        session.add(prefs)
        await session.commit()
        await session.refresh(prefs)
    return prefs
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_preferences.py -v`
Expected: PASS (2 passed).

- [ ] **Step 8: Commit**
```bash
git add backend/pyproject.toml backend/uv.lock backend/tests/ backend/models/db.py
git commit -m "feat(backend): add user_preferences model + pytest harness"
```

---

### Task 2: Keychain wrapper

**Files:**
- Create: `backend/services/keychain.py`
- Create: `backend/tests/test_keychain.py`

- [ ] **Step 1: Write failing test (keyring mocked, no real OS calls)**

Create `backend/tests/test_keychain.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_keychain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.keychain'`.

- [ ] **Step 3: Implement keychain wrapper**

Create `backend/services/keychain.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_keychain.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**
```bash
git add backend/services/keychain.py backend/tests/test_keychain.py
git commit -m "feat(backend): add OS keychain wrapper for API keys"
```

---

### Task 3: Settings schemas + router

**Files:**
- Modify: `backend/models/schemas.py`
- Create: `backend/routers/settings.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_settings_api.py`

- [ ] **Step 1: Add schemas**

Append to `backend/models/schemas.py`:
```python
# ── Settings ──────────────────────────────────────────────────────────────────

class PreferencesResponse(BaseModel):
    user_name: str
    conv_model: str
    analysis_model: str
    onboarding_complete: bool


class PreferencesUpdate(BaseModel):
    user_name: Optional[str] = None
    conv_model: Optional[str] = None
    analysis_model: Optional[str] = None
    onboarding_complete: Optional[bool] = None


class ApiKeySet(BaseModel):
    service: str  # 'openrouter' | 'openai' | 'deepl'
    key: str


class ApiKeyStatus(BaseModel):
    openrouter: bool
    openai: bool
    deepl: bool


class ApiKeyTestRequest(BaseModel):
    service: str


class ApiKeyTestResult(BaseModel):
    ok: bool
    detail: Optional[str] = None


class ModelOption(BaseModel):
    id: str
    name: str


class ModelsResponse(BaseModel):
    models: List[ModelOption]
```

- [ ] **Step 2: Write failing API test**

Create `backend/tests/test_settings_api.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_settings_api.py -v`
Expected: FAIL — 404s (router not registered).

- [ ] **Step 4: Implement settings router**

Create `backend/routers/settings.py`:
```python
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import get_db, get_or_create_preferences
from models.schemas import (
    PreferencesResponse, PreferencesUpdate, ApiKeySet, ApiKeyStatus,
    ApiKeyTestRequest, ApiKeyTestResult, ModelOption, ModelsResponse,
)
from services import keychain

router = APIRouter()

_models_cache: dict = {"ts": 0.0, "data": None}
_CACHE_TTL = 3600


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    p = await get_or_create_preferences(db)
    return PreferencesResponse(
        user_name=p.user_name,
        conv_model=p.conv_model,
        analysis_model=p.analysis_model,
        onboarding_complete=p.onboarding_complete,
    )


@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(body: PreferencesUpdate, db: AsyncSession = Depends(get_db)):
    p = await get_or_create_preferences(db)
    for field in ("user_name", "conv_model", "analysis_model", "onboarding_complete"):
        val = getattr(body, field)
        if val is not None:
            setattr(p, field, val)
    await db.commit()
    await db.refresh(p)
    return PreferencesResponse(
        user_name=p.user_name,
        conv_model=p.conv_model,
        analysis_model=p.analysis_model,
        onboarding_complete=p.onboarding_complete,
    )


@router.post("/apikey")
async def set_apikey(body: ApiKeySet):
    try:
        keychain.set_key(body.service, body.key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/apikey/status", response_model=ApiKeyStatus)
async def apikey_status():
    return ApiKeyStatus(**keychain.key_status())


@router.post("/apikey/test", response_model=ApiKeyTestResult)
async def apikey_test(body: ApiKeyTestRequest):
    key = keychain.get_key(body.service)
    if not key:
        return ApiKeyTestResult(ok=False, detail="No key stored")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if body.service == "openrouter":
                r = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
            elif body.service == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
            else:  # deepl
                r = await client.get(
                    "https://api-free.deepl.com/v2/usage",
                    headers={"Authorization": f"DeepL-Auth-Key {key}"},
                )
        return ApiKeyTestResult(ok=r.status_code == 200,
                                detail=None if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as e:
        return ApiKeyTestResult(ok=False, detail=str(e))


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    now = time.time()
    if _models_cache["data"] and now - _models_cache["ts"] < _CACHE_TTL:
        return ModelsResponse(models=_models_cache["data"])

    key = keychain.get_key("openrouter")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
            r.raise_for_status()
            raw = r.json().get("data", [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch models: {e}")

    models = [
        ModelOption(id=m["id"], name=m.get("name", m["id"]))
        for m in raw
        if m.get("id")
    ]
    _models_cache["data"] = models
    _models_cache["ts"] = now
    return ModelsResponse(models=models)
```

- [ ] **Step 5: Register router**

In `backend/main.py`, change the import line:
```python
from routers import session, profile, review, test, analytics, settings
```
Add after the `analytics` include line:
```python
app.include_router(settings.router, prefix="/settings", tags=["settings"])
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_settings_api.py -v`
Expected: PASS (3 passed).

- [ ] **Step 7: Commit**
```bash
git add backend/routers/settings.py backend/models/schemas.py backend/main.py backend/tests/test_settings_api.py
git commit -m "feat(backend): settings router (preferences, api keys, models)"
```

---

### Task 4: Resolve key + models at call time

**Files:**
- Modify: `backend/services/openrouter_client.py`
- Modify: `backend/services/conversation.py`
- Modify: `backend/services/error_analysis.py`
- Modify: `backend/routers/session.py`
- Create: `backend/tests/test_model_resolution.py`

- [ ] **Step 1: Write failing test for key resolution preferring keychain**

Create `backend/tests/test_model_resolution.py`:
```python
from services import openrouter_client, keychain


def test_resolve_key_prefers_keychain(monkeypatch):
    monkeypatch.setattr(keychain, "get_key", lambda n: "sk-from-keychain")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env")
    assert openrouter_client.resolve_api_key() == "sk-from-keychain"


def test_resolve_key_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(keychain, "get_key", lambda n: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env")
    assert openrouter_client.resolve_api_key() == "sk-from-env"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_model_resolution.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'resolve_api_key'`.

- [ ] **Step 3: Update `openrouter_client.py`**

Replace the `_headers` function in `backend/services/openrouter_client.py` with:
```python
def resolve_api_key() -> str:
    from services import keychain
    return keychain.get_key("openrouter") or os.getenv("OPENROUTER_API_KEY", "")


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {resolve_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": _HTTP_REFERER,
        "X-Title": "SprachBoot",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_model_resolution.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Thread preferred models through conversation**

In `backend/services/conversation.py`, change the `build_conversation_response` signature to accept models, and the API-key guard to use the resolver. Replace the signature + guard block:
```python
async def build_conversation_response(
    user_input: str,
    mode: str,
    topic: str,
    weak_patterns: List[Dict],
    low_conf_words: List[str],
    current_level: str = "A1",
    chroma_context: str = "",
    conv_model: str = LLAMA_MODEL,
    fallback_model: str = DEEPSEEK_MODEL,
) -> Tuple[str, bool]:
    """Returns (ai_response_text, english_switch_flag). Falls back on 429."""
    from services.openrouter_client import resolve_api_key
    if not resolve_api_key():
        return (
            "Entschuldigung, der API-Schlüssel fehlt. Bitte konfiguriere OPENROUTER_API_KEY.",
            False,
        )
```
And replace the `try/except` call block at the end with:
```python
    try:
        text = await call_openrouter(conv_model, messages, max_tokens=200, temperature=0.7)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            text = await call_openrouter(fallback_model, messages, max_tokens=200, temperature=0.7)
        else:
            raise

    return text, _detect_english_switch(text)
```

- [ ] **Step 6: Pass preferences into the call from session router**

In `backend/routers/session.py`, add import near the top:
```python
from models.db import get_or_create_preferences
```
Then in `session_turn`, immediately before the `# Call AI for response` block, add:
```python
    prefs = await get_or_create_preferences(db)
```
And change the `build_conversation_response(...)` call to pass models:
```python
    ai_response, english_switch = await build_conversation_response(
        user_input=req.user_input,
        mode=req.mode,
        topic=req.topic,
        weak_patterns=weak_patterns,
        low_conf_words=low_conf_words,
        chroma_context=chroma_context,
        conv_model=prefs.conv_model,
        fallback_model=prefs.analysis_model,
    )
```

- [ ] **Step 7: Use preferred analysis model in error analysis**

In `backend/services/error_analysis.py`, the call currently passes `DEEPSEEK_MODEL`. Replace the analysis-model resolution at the top of `analyze_errors_background` (after the existing `if not os.getenv(...)` guard) — change the guard and model. Replace:
```python
    import os
    if not os.getenv("OPENROUTER_API_KEY"):
        return
```
with:
```python
    from services.openrouter_client import resolve_api_key
    from models.db import AsyncSessionLocal as _ASL, get_or_create_preferences
    if not resolve_api_key():
        return
    async with _ASL() as _pdb:
        _prefs = await get_or_create_preferences(_pdb)
        analysis_model = _prefs.analysis_model
```
Then change the `call_openrouter(DEEPSEEK_MODEL, ...)` line to `call_openrouter(analysis_model, ...)`.

- [ ] **Step 8: Run full backend test suite**

Run: `cd backend && uv run pytest -v`
Expected: PASS (all tests green).

- [ ] **Step 9: Commit**
```bash
git add backend/services/openrouter_client.py backend/services/conversation.py backend/services/error_analysis.py backend/routers/session.py backend/tests/test_model_resolution.py
git commit -m "feat(backend): resolve api key from keychain + use preferred models"
```

---

### Task 5: Widen CORS for desktop webview

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Update CORS origins**

In `backend/main.py`, replace `allow_origins=["http://localhost:3000"]` with:
```python
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
```

- [ ] **Step 2: Verify server boots**

Run: `cd backend && uv run python -c "import main; print('ok')"`
Expected: prints `ok` with no import errors.

- [ ] **Step 3: Commit**
```bash
git add backend/main.py
git commit -m "feat(backend): allow tauri webview origins in CORS"
```

---

# PHASE 2 — Frontend: onboarding wizard + settings page

### Task 6: Typed settings client

**Files:**
- Create: `frontend/lib/settings.ts`

- [ ] **Step 1: Create the client**

Create `frontend/lib/settings.ts`:
```typescript
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Preferences {
  user_name: string
  conv_model: string
  analysis_model: string
  onboarding_complete: boolean
}

export interface KeyStatus {
  openrouter: boolean
  openai: boolean
  deepl: boolean
}

export interface ModelOption {
  id: string
  name: string
}

export async function getPreferences(): Promise<Preferences> {
  const r = await fetch(`${API}/settings/preferences`, { cache: 'no-store' })
  if (!r.ok) throw new Error('Failed to load preferences')
  return r.json()
}

export async function updatePreferences(p: Partial<Preferences>): Promise<Preferences> {
  const r = await fetch(`${API}/settings/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p),
  })
  if (!r.ok) throw new Error('Failed to save preferences')
  return r.json()
}

export async function setApiKey(service: string, key: string): Promise<void> {
  const r = await fetch(`${API}/settings/apikey`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, key }),
  })
  if (!r.ok) throw new Error('Failed to save key')
}

export async function getKeyStatus(): Promise<KeyStatus> {
  const r = await fetch(`${API}/settings/apikey/status`, { cache: 'no-store' })
  if (!r.ok) throw new Error('Failed to load key status')
  return r.json()
}

export async function testApiKey(service: string): Promise<{ ok: boolean; detail?: string }> {
  const r = await fetch(`${API}/settings/apikey/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service }),
  })
  return r.json()
}

export async function getModels(): Promise<ModelOption[]> {
  const r = await fetch(`${API}/settings/models`, { cache: 'no-store' })
  if (!r.ok) return []
  return (await r.json()).models
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**
```bash
git add frontend/lib/settings.ts
git commit -m "feat(frontend): typed settings API client"
```

---

### Task 7: Onboarding wizard

**Files:**
- Create: `frontend/app/onboard/page.tsx`
- Create: `frontend/app/onboard/onboard.module.css`

- [ ] **Step 1: Create wizard component**

Create `frontend/app/onboard/page.tsx`:
```typescript
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  updatePreferences, setApiKey, testApiKey, getModels, ModelOption,
} from '@/lib/settings'
import styles from './onboard.module.css'

export default function OnboardPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [keys, setKeys] = useState({ openrouter: '', openai: '', deepl: '' })
  const [testResult, setTestResult] = useState<Record<string, string>>({})
  const [models, setModels] = useState<ModelOption[]>([])
  const [convModel, setConvModel] = useState('meta-llama/llama-3.3-70b-instruct')
  const [analysisModel, setAnalysisModel] = useState('deepseek/deepseek-v4-flash')
  const [filter, setFilter] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (step === 3) getModels().then(setModels).catch(() => setModels([]))
  }, [step])

  const saveKey = async (service: 'openrouter' | 'openai' | 'deepl') => {
    if (!keys[service]) return
    await setApiKey(service, keys[service])
    const res = await testApiKey(service)
    setTestResult((t) => ({ ...t, [service]: res.ok ? '✓ Connected' : `✗ ${res.detail ?? 'failed'}` }))
  }

  const finish = async () => {
    setSaving(true)
    await updatePreferences({
      user_name: name || 'User',
      conv_model: convModel,
      analysis_model: analysisModel,
      onboarding_complete: true,
    })
    router.push('/')
  }

  const filtered = models.filter(
    (m) => m.id.toLowerCase().includes(filter.toLowerCase()) ||
           m.name.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <main className={styles.wrap}>
      <div className={styles.card}>
        <div className={styles.steps}>Step {step} of 3</div>

        {step === 1 && (
          <>
            <h1>Welcome to SprachBoot ⛵</h1>
            <p>What should I call you?</p>
            <input
              className={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              autoFocus
            />
            <button className={styles.btn} disabled={!name} onClick={() => setStep(2)}>
              Next
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <h1>API Keys</h1>
            <p>Stored securely in your OS keychain — never in a file.</p>
            {(['openrouter', 'openai', 'deepl'] as const).map((svc) => (
              <div key={svc} className={styles.keyRow}>
                <label>{svc}{svc === 'deepl' ? ' (optional)' : ''}</label>
                <div className={styles.keyInput}>
                  <input
                    className={styles.input}
                    type="password"
                    value={keys[svc]}
                    onChange={(e) => setKeys((k) => ({ ...k, [svc]: e.target.value }))}
                    placeholder={`${svc} key`}
                  />
                  <button className={styles.btnGhost} onClick={() => saveKey(svc)}>
                    Test
                  </button>
                </div>
                {testResult[svc] && <span className={styles.test}>{testResult[svc]}</span>}
              </div>
            ))}
            <div className={styles.row}>
              <button className={styles.btnGhost} onClick={() => setStep(1)}>Back</button>
              <button
                className={styles.btn}
                disabled={!keys.openrouter || !keys.openai}
                onClick={() => setStep(3)}
              >
                Next
              </button>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h1>Choose your models</h1>
            <p>Defaults are recommended. Search to pick others.</p>
            <input
              className={styles.input}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter models…"
            />
            <label>Conversation model</label>
            <select className={styles.input} value={convModel} onChange={(e) => setConvModel(e.target.value)}>
              <option value={convModel}>{convModel}</option>
              {filtered.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <label>Analysis model</label>
            <select className={styles.input} value={analysisModel} onChange={(e) => setAnalysisModel(e.target.value)}>
              <option value={analysisModel}>{analysisModel}</option>
              {filtered.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <div className={styles.row}>
              <button className={styles.btnGhost} onClick={() => setStep(2)}>Back</button>
              <button className={styles.btn} disabled={saving} onClick={finish}>
                {saving ? 'Saving…' : 'Finish'}
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Create styles**

Create `frontend/app/onboard/onboard.module.css`:
```css
.wrap { min-height: 80vh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
.card { width: 100%; max-width: 480px; background: var(--color-paper, #1a1a1a); border: 1px solid var(--color-rule, #333); border-radius: 16px; padding: 2rem; }
.steps { font-size: 0.75rem; opacity: 0.6; margin-bottom: 1rem; letter-spacing: 0.05em; text-transform: uppercase; }
.input { width: 100%; padding: 0.75rem; margin: 0.5rem 0 1rem; border-radius: 8px; border: 1px solid var(--color-rule, #333); background: transparent; color: inherit; font-size: 1rem; }
.btn { width: 100%; padding: 0.75rem; border-radius: 8px; border: none; background: var(--color-accent, #7c9); color: #000; font-weight: 600; cursor: pointer; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btnGhost { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--color-rule, #333); background: transparent; color: inherit; cursor: pointer; }
.row { display: flex; gap: 0.75rem; justify-content: space-between; margin-top: 1rem; }
.keyRow { margin-bottom: 1rem; }
.keyInput { display: flex; gap: 0.5rem; align-items: center; }
.keyInput .input { margin: 0.25rem 0; }
.test { font-size: 0.8rem; opacity: 0.8; }
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Manual verification**

Start backend (`cd backend && uv run fastapi dev main.py`) and frontend (`cd frontend && npm run dev`). Visit `http://localhost:3000/onboard`. Verify: 3 steps navigate, name required for step 1, OpenRouter+OpenAI required for step 2, Test buttons show ✓/✗, Finish redirects to `/`.

- [ ] **Step 5: Commit**
```bash
git add frontend/app/onboard/
git commit -m "feat(frontend): onboarding wizard (name, keys, models)"
```

---

### Task 8: Onboarding redirect gate

**Files:**
- Create: `frontend/components/OnboardingGate.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create the gate**

Create `frontend/components/OnboardingGate.tsx`:
```typescript
'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { getPreferences } from '@/lib/settings'

export default function OnboardingGate() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (pathname === '/onboard') return
    getPreferences()
      .then((p) => { if (!p.onboarding_complete) router.replace('/onboard') })
      .catch(() => { /* backend down — let app render */ })
  }, [pathname, router])

  return null
}
```

- [ ] **Step 2: Mount in layout**

In `frontend/app/layout.tsx`, add import:
```typescript
import OnboardingGate from '@/components/OnboardingGate'
```
And add `<OnboardingGate />` as the first child inside `<body>`, before `<Nav />`.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Manual verification**

With a fresh DB (`onboarding_complete=false`), visit `http://localhost:3000/` → should redirect to `/onboard`. Complete onboarding → future visits to `/` should NOT redirect.

- [ ] **Step 5: Commit**
```bash
git add frontend/components/OnboardingGate.tsx frontend/app/layout.tsx
git commit -m "feat(frontend): redirect to onboarding until complete"
```

---

### Task 9: Settings page

**Files:**
- Create: `frontend/app/settings/page.tsx`

- [ ] **Step 1: Create settings page**

Create `frontend/app/settings/page.tsx`:
```typescript
'use client'

import { useEffect, useState } from 'react'
import {
  getPreferences, updatePreferences, getKeyStatus, setApiKey, testApiKey,
  getModels, ModelOption, KeyStatus,
} from '@/lib/settings'
import styles from '../onboard/onboard.module.css'

export default function SettingsPage() {
  const [name, setName] = useState('')
  const [convModel, setConvModel] = useState('')
  const [analysisModel, setAnalysisModel] = useState('')
  const [models, setModels] = useState<ModelOption[]>([])
  const [status, setStatus] = useState<KeyStatus>({ openrouter: false, openai: false, deepl: false })
  const [keys, setKeys] = useState({ openrouter: '', openai: '', deepl: '' })
  const [testResult, setTestResult] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getPreferences().then((p) => {
      setName(p.user_name)
      setConvModel(p.conv_model)
      setAnalysisModel(p.analysis_model)
    })
    getKeyStatus().then(setStatus)
    getModels().then(setModels).catch(() => setModels([]))
  }, [])

  const saveAccount = async () => {
    await updatePreferences({ user_name: name, conv_model: convModel, analysis_model: analysisModel })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const saveKey = async (svc: 'openrouter' | 'openai' | 'deepl') => {
    if (!keys[svc]) return
    await setApiKey(svc, keys[svc])
    const res = await testApiKey(svc)
    setTestResult((t) => ({ ...t, [svc]: res.ok ? '✓ Connected' : `✗ ${res.detail ?? 'failed'}` }))
    setStatus(await getKeyStatus())
    setKeys((k) => ({ ...k, [svc]: '' }))
  }

  return (
    <main className={styles.wrap}>
      <div className={styles.card}>
        <h1>Settings</h1>

        <h2>Account</h2>
        <label>Name</label>
        <input className={styles.input} value={name} onChange={(e) => setName(e.target.value)} />

        <h2>AI Configuration</h2>
        <label>Conversation model</label>
        <select className={styles.input} value={convModel} onChange={(e) => setConvModel(e.target.value)}>
          <option value={convModel}>{convModel}</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <label>Analysis model</label>
        <select className={styles.input} value={analysisModel} onChange={(e) => setAnalysisModel(e.target.value)}>
          <option value={analysisModel}>{analysisModel}</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <button className={styles.btn} onClick={saveAccount}>{saved ? 'Saved ✓' : 'Save'}</button>

        <h2>API Keys</h2>
        {(['openrouter', 'openai', 'deepl'] as const).map((svc) => (
          <div key={svc} className={styles.keyRow}>
            <label>{svc} {status[svc] ? '✓' : '✗'}</label>
            <div className={styles.keyInput}>
              <input
                className={styles.input}
                type="password"
                value={keys[svc]}
                onChange={(e) => setKeys((k) => ({ ...k, [svc]: e.target.value }))}
                placeholder={status[svc] ? 'Replace key…' : `${svc} key`}
              />
              <button className={styles.btnGhost} onClick={() => saveKey(svc)}>Save</button>
            </div>
            {testResult[svc] && <span className={styles.test}>{testResult[svc]}</span>}
          </div>
        ))}
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Manual verification**

Visit `http://localhost:3000/settings`. Verify: name + models prefill, key status shows ✓/✗, saving a key updates status, Save shows confirmation.

- [ ] **Step 4: Commit**
```bash
git add frontend/app/settings/
git commit -m "feat(frontend): settings page"
```

---

### Task 10: Personalized greeting + Settings nav link

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/components/Nav.tsx`

- [ ] **Step 1: Use the user name in the greeting**

In `frontend/app/page.tsx`, the profile fetch currently only loads `/profile/summary`. Add a preferences fetch and use it. After the existing `profile` fetch block, add:
```typescript
  let userName = 'there';
  try {
    const pr = await fetch(`${API_URL}/settings/preferences`, { cache: 'no-store' });
    if (pr.ok) userName = (await pr.json()).user_name || 'there';
  } catch (e) {
    console.error('Failed to fetch preferences', e);
  }
```
Then replace the greeting line `<h1>Guten Tag, Lo. 👋</h1>` with:
```tsx
          <h1>Guten Tag, {userName}. 👋</h1>
```

- [ ] **Step 2: Add Settings link to Nav**

In `frontend/components/Nav.tsx`, add after the Analytics `<Link>`:
```tsx
          <Link
            className={`nav__link${pathname === '/settings' ? ' active' : ''}`}
            href="/settings"
          >
            Settings
          </Link>
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Manual verification**

Set name to "Lo" in settings, reload `/` → greeting reads "Guten Tag, Lo. 👋". Nav shows a Settings link that highlights on `/settings`.

- [ ] **Step 5: Commit**
```bash
git add frontend/app/page.tsx frontend/components/Nav.tsx
git commit -m "feat(frontend): personalized greeting + settings nav link"
```

---

# PHASE 3 — Desktop packaging (Tauri)

> **High-risk phase.** Do Task 13 (PyInstaller validation) BEFORE investing in Tauri config. If the sidecar can't bundle faster-whisper/ChromaDB, stop and revisit the spec's risk section.

### Task 11: Remove proxy layer, call FastAPI directly

**Files:**
- Create: `frontend/lib/api.ts`
- Delete: `frontend/app/api/` (entire directory)
- Modify: all fetch callers (`frontend/app/speak/page.tsx`, `frontend/hooks/useErrorPoll.ts`, `frontend/hooks/useVoiceRecorder.ts`, `frontend/app/test/page.tsx`, `frontend/app/analytics/page.tsx`, `frontend/app/review/page.tsx`)

- [ ] **Step 1: Create base-URL helper**

Create `frontend/lib/api.ts`:
```typescript
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** Build an absolute backend URL from a backend path like '/session/turn'. */
export function api(path: string): string {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}
```

- [ ] **Step 2: Inventory every `/api/...` fetch**

Run: `cd frontend && rtk grep "fetch('/api" app hooks`
Expected: a list of all call sites. For EACH match, replace the relative `/api/...` Next path with the direct backend path via `api(...)`. The proxy routes mapped 1:1, dropping the `/api` prefix:
- `/api/session/turn` → `api('/session/turn')`
- `/api/session/end` → `api('/session/end')`
- `/api/session/transcribe` → `api('/session/transcribe')`
- `/api/session/${turnId}` → `api('/session/turn/' + turnId)`
- `/api/profile/summary` → `api('/profile/summary')`
- `/api/review/...` → `api('/review/...')`

Add `import { api } from '@/lib/api'` to each modified file.

- [ ] **Step 3: Delete the proxy directory**

Run: `rm -rf frontend/app/api`

- [ ] **Step 4: Verify no stragglers remain**

Run: `cd frontend && rtk grep "fetch('/api" app hooks components`
Expected: zero matches.

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Manual verification (dev mode still works direct-to-backend)**

With both servers running, exercise `/speak` (send a message), `/test`, `/analytics`. All must work hitting FastAPI directly (port 8000). Watch the browser console for CORS errors — there should be none (Task 5 widened CORS).

- [ ] **Step 7: Commit**
```bash
git add frontend/lib/api.ts frontend/app frontend/hooks frontend/components
git commit -m "refactor(frontend): call FastAPI directly, remove Next proxy routes"
```

---

### Task 12: Static export + FastAPI serves the UI

**Files:**
- Modify: `frontend/next.config.ts`
- Modify: `backend/main.py`

- [ ] **Step 1: Enable static export**

Replace `frontend/next.config.ts` contents with:
```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'export',
  images: { unoptimized: true },
}

export default nextConfig
```

- [ ] **Step 2: Build the static frontend**

Run: `cd frontend && npm run build`
Expected: produces `frontend/out/` with static HTML/JS. If a route errors on export (dynamic server feature), note it — all data fetching is client-side or `cache: 'no-store'` against an external API, so export should succeed.

- [ ] **Step 3: Mount static files in FastAPI (only if present)**

In `backend/main.py`, add near the top:
```python
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
```
At the END of the file (after all routers), add:
```python
_frontend_out = Path(__file__).parent.parent / "frontend" / "out"
if _frontend_out.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_out), html=True), name="frontend")
```

- [ ] **Step 4: Verify single-process serving**

Run: `cd backend && uv run uvicorn main:app --port 8000` then open `http://localhost:8000/`.
Expected: dashboard renders from FastAPI-served static files; API calls (same origin) work.

- [ ] **Step 5: Commit**
```bash
git add frontend/next.config.ts backend/main.py
git commit -m "feat: static-export frontend served by FastAPI for desktop build"
```

---

### Task 13: PyInstaller sidecar (VALIDATE FIRST)

**Files:**
- Create: `backend/sprachboot-server.spec`
- Modify: `backend/pyproject.toml` (add `pyinstaller` dev dep)

- [ ] **Step 1: Add PyInstaller**

Add `"pyinstaller>=6.0.0"` to the `dev` dependency group in `backend/pyproject.toml`.
Run: `cd backend && uv sync --all-groups`
Expected: installs pyinstaller.

- [ ] **Step 2: Create an entrypoint runner**

Create `backend/run_server.py`:
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")
```

- [ ] **Step 3: Create the PyInstaller spec**

Create `backend/sprachboot-server.spec`:
```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("faster_whisper", "chromadb", "onnxruntime", "tokenizers"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(
    ["run_server.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["aiosqlite", "uvicorn.logging", "uvicorn.protocols"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name="sprachboot-server", console=True)
```

- [ ] **Step 4: Build the sidecar binary**

Run: `cd backend && uv run pyinstaller sprachboot-server.spec --noconfirm`
Expected: produces `backend/dist/sprachboot-server` (macOS/Linux) or `.exe` (Windows).

- [ ] **Step 5: VALIDATE the bundled server actually runs**

Run: `cd backend && ./dist/sprachboot-server` (or `dist\sprachboot-server.exe` on Windows), then in another shell: `rtk curl http://127.0.0.1:8000/health`
Expected: `{"status":"ok",...}`. Then exercise `/settings/preferences`. **If faster-whisper or chromadb import fails at runtime, STOP** — add the missing module via `collect_all`/`hiddenimports` and rebuild before continuing.

- [ ] **Step 6: Commit**
```bash
git add backend/run_server.py backend/sprachboot-server.spec backend/pyproject.toml backend/uv.lock
echo "dist/" >> backend/.gitignore && echo "build/" >> backend/.gitignore
git add backend/.gitignore
git commit -m "build(backend): PyInstaller sidecar spec for desktop bundle"
```

---

### Task 14: Tauri scaffold + sidecar wiring

**Files:**
- Create: `src-tauri/Cargo.toml`, `src-tauri/build.rs`, `src-tauri/tauri.conf.json`, `src-tauri/src/main.rs`

- [ ] **Step 1: Install Tauri CLI prerequisites**

Ensure Rust is installed (`rustc --version`). Install Tauri CLI: `cargo install tauri-cli --version "^2"`.
Expected: `cargo tauri --version` prints a 2.x version.

- [ ] **Step 2: Create `src-tauri/Cargo.toml`**

```toml
[package]
name = "sprachboot"
version = "0.1.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"

[features]
custom-protocol = ["tauri/custom-protocol"]
```

- [ ] **Step 3: Create `src-tauri/build.rs`**

```rust
fn main() {
    tauri_build::build()
}
```

- [ ] **Step 4: Create `src-tauri/tauri.conf.json`**

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "SprachBoot",
  "version": "0.1.0",
  "identifier": "com.sprachboot.app",
  "build": {
    "frontendDist": "../frontend/out"
  },
  "app": {
    "windows": [
      { "title": "SprachBoot", "width": 1200, "height": 800, "resizable": true }
    ],
    "security": { "csp": null }
  },
  "bundle": {
    "active": true,
    "targets": ["dmg", "nsis"],
    "icon": ["icons/icon.icns", "icons/icon.ico"],
    "externalBin": ["binaries/sprachboot-server"]
  }
}
```

- [ ] **Step 5: Create `src-tauri/src/main.rs` (spawn + kill sidecar)**

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use std::sync::Mutex;

struct Sidecar(Mutex<Option<CommandChild>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Sidecar(Mutex::new(None)))
        .setup(|app| {
            let sidecar = app.shell().sidecar("sprachboot-server")?;
            let (_rx, child) = sidecar.spawn()?;
            *app.state::<Sidecar>().0.lock().unwrap() = Some(child);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(child) = window.state::<Sidecar>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running SprachBoot");
}
```

- [ ] **Step 6: Stage the sidecar binary with Tauri's target-triple naming**

Tauri expects `binaries/sprachboot-server-<target-triple>`. Create the dir and copy:
```bash
mkdir -p src-tauri/binaries
TRIPLE=$(rustc -Vv | grep host | cut -d' ' -f2)
cp backend/dist/sprachboot-server "src-tauri/binaries/sprachboot-server-$TRIPLE"
```
(On Windows, copy `sprachboot-server.exe` to `sprachboot-server-<triple>.exe`.)

- [ ] **Step 7: Add placeholder icons**

Run: `cargo tauri icon` against any 1024×1024 PNG (e.g. reuse `frontend/public` logo if present) to generate `src-tauri/icons/`. If no source image, create a simple 1024px PNG first.

- [ ] **Step 8: Build the desktop app**

Run: `cargo tauri build`
Expected: produces a `.dmg` (macOS) under `src-tauri/target/release/bundle/dmg/` or `.exe` (Windows) under `bundle/nsis/`.

- [ ] **Step 9: VALIDATE the installer**

Install/run the produced app. Verify: window opens, sidecar boots (dashboard loads), onboarding works, a conversation turn round-trips. Check the sidecar process is killed when the window closes.

- [ ] **Step 10: Commit**
```bash
echo "src-tauri/target/" >> .gitignore
echo "src-tauri/binaries/" >> .gitignore
git add src-tauri/ .gitignore
git commit -m "feat: Tauri v2 desktop shell with FastAPI sidecar"
```

---

### Task 15: GitHub Actions CI (macOS + Windows installers)

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/release.yml`:
```yaml
name: Release

on:
  push:
    tags: ["v*"]
  workflow_dispatch:

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-latest
            triple: aarch64-apple-darwin
          - os: windows-latest
            triple: x86_64-pc-windows-msvc
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with: { node-version: "20" }

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - uses: dtolnay/rust-toolchain@stable
        with: { targets: ${{ matrix.triple }} }

      - name: Build frontend (static export)
        working-directory: frontend
        run: |
          npm ci
          npm run build

      - name: Build backend sidecar
        working-directory: backend
        run: |
          uv sync --all-groups
          uv run pyinstaller sprachboot-server.spec --noconfirm

      - name: Stage sidecar with target triple
        shell: bash
        run: |
          mkdir -p src-tauri/binaries
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            cp backend/dist/sprachboot-server.exe "src-tauri/binaries/sprachboot-server-${{ matrix.triple }}.exe"
          else
            cp backend/dist/sprachboot-server "src-tauri/binaries/sprachboot-server-${{ matrix.triple }}"
          fi

      - name: Build Tauri app
        uses: tauri-apps/tauri-action@v0
        with:
          projectPath: .

      - name: Upload installers
        uses: actions/upload-artifact@v4
        with:
          name: sprachboot-${{ matrix.os }}
          path: |
            src-tauri/target/release/bundle/dmg/*.dmg
            src-tauri/target/release/bundle/nsis/*.exe
```

- [ ] **Step 2: Validate workflow syntax**

Run: `rtk gh workflow view release.yml` (after pushing) or lint locally with `actionlint .github/workflows/release.yml` if available.
Expected: no syntax errors.

- [ ] **Step 3: Commit + push to trigger**
```bash
git add .github/workflows/release.yml
git commit -m "ci: build macOS .dmg and Windows .exe via Tauri matrix"
git push
```

- [ ] **Step 4: VALIDATE CI run**

Run: `rtk gh run list --limit 1` then `rtk gh run watch`. Confirm both matrix jobs produce installer artifacts. Download and smoke-test each.

---

## Self-Review

**Spec coverage:**
- §2 user_preferences table → Task 1 ✓
- §3 settings router (preferences/apikey/status/test/models) → Tasks 1–3 ✓
- §3 keyring + openrouter_client key resolution → Tasks 2, 4 ✓
- §3 model resolution from preferences → Task 4 ✓
- §4 onboarding wizard (name/keys/models) → Task 7 ✓
- §4 layout redirect gate → Task 8 ✓
- §5 settings page + dashboard name swap → Tasks 9, 10 ✓
- §6a delete /app/api, repoint fetches, CORS → Tasks 5, 11 ✓
- §6b static export + StaticFiles → Task 12 ✓
- §6c Tauri scaffold → Task 14 ✓
- §6d PyInstaller sidecar → Task 13 ✓
- §6e CI matrix (macOS+Windows) → Task 15 ✓
- "ask for user_name in setup" small change → Task 7 step 1 + Task 10 ✓

**Placeholder scan:** No TBD/TODO; all code steps contain full code. UI tasks use manual verification (no JS test runner in repo — intentional, noted in Tech Stack).

**Type consistency:** `get_or_create_preferences` (db.py) used identically in settings router, session router, error_analysis. `resolve_api_key()` defined Task 4 step 3, used in conversation.py + error_analysis.py. `api()` helper defined Task 11, used across frontend. Pydantic schema names match router usage. Tauri sidecar binary name `sprachboot-server` consistent across spec, main.rs, CI.

**Scope note:** Phases 1–2 deliver working in-app settings/onboarding independently. Phase 3 (packaging) is environment-heavy and gated on Task 13 validation.
