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

## Quick start

**Prerequisites:** Node.js, Python 3.11+, `uv` (`pip install uv`), an [OpenRouter](https://openrouter.ai/) API key.

```bash
git clone https://github.com/lohith-pras/sprachboot.git
cd sprachboot
python start.py
```

Open the app in your browser, enter your OpenRouter API key, and start speaking.

DeepL translation is optional — leave that field blank to skip it.
