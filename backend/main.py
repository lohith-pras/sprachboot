import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from models.db import init_db
from routers import session, profile, review, test, analytics, settings, translate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="SprachBoot API",
    description="AI-powered German conversational fluency trainer",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(test.router, prefix="/test", tags=["test"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(translate.router, prefix="/translate", tags=["translate"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SprachBoot API"}


# Serve the statically-exported Next.js frontend (desktop build). Mounted last
# so API routes take precedence. Only active when the export exists.
_frontend_out = Path(__file__).parent.parent / "frontend" / "out"
if _frontend_out.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_out), html=True), name="frontend")
