# SprachBoot 🚤

An AI-powered German conversational fluency trainer. Practice speaking German daily through realistic conversations — the app corrects your grammar, explains errors in context, and adapts to your level. Runs entirely on your machine; no accounts or cloud required.

Powered by Llama and DeepSeek via OpenRouter.

## Features

- Conversational German practice with real-time AI feedback
- Grammar error detection and in-context explanations
- Optional tap-to-translate via DeepL
- Local-first — your conversations never leave your machine
- FastAPI backend + React frontend, launched with one command

## Stack

| Layer | Tech |
|---|---|
| Frontend | React, TypeScript |
| Backend | Python, FastAPI |
| AI models | Llama + DeepSeek via OpenRouter |
| Vector store | ChromaDB |
| Package manager | uv |

## Quick start (Docker — recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) and an [OpenRouter](https://openrouter.ai/) API key. Nothing else — no Node, Python, or uv on your machine.

```bash
git clone https://github.com/lohith-pras/sprachboot.git
cd sprachboot
docker compose up --build
```

Open <http://localhost:3000>, enter **your own** OpenRouter API key in onboarding, and start talking. Voice (speech-to-text) is routed through OpenRouter with that same key — no local speech model.

Your conversations, progress, and key persist in a Docker volume across restarts. Stop with `Ctrl+C`; `docker compose down` keeps your data, `docker compose down -v` wipes it.

DeepL translation is optional — leave that field blank to skip it.

## Share with friends (no repo, no build)

Friends don't clone anything. Publish prebuilt images once, then they run two commands.

**You (once per update):** `./publish.sh` — builds multi-arch images and pushes them to GHCR. See the script header for one-time login + making the packages public.

**Your friend:**
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. Save [`compose.friend.yml`](compose.friend.yml) as `docker-compose.yml` in any empty folder.
3. In that folder: `docker compose up`
4. Open <http://localhost:3000>, paste their **own** OpenRouter key.

No clone, no build — Docker pulls the images and runs. Each friend's data and key stay on their own machine.

## Quick start (native dev)

**Prerequisites:** Node.js, Python 3.13+, `uv` (`pip install uv`), an OpenRouter API key.

```bash
git clone https://github.com/lohith-pras/sprachboot.git
cd sprachboot
python start.py
```
