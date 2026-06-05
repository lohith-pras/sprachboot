# SprachBoot 🚤

An AI-powered German conversational fluency trainer designed to help learners reach conversational fluency through daily speaking practice, powered by Llama and DeepSeek.

## 🚀 Quick Start for Friends & Contributors

The easiest way to run the entire application (frontend + backend) is to use our bundled start script!

It runs entirely on your own machine — a browser frontend talking to a local
FastAPI backend. No accounts, no hosting, no desktop install.

### Prerequisites
Before you start, make sure you have the following installed on your computer:
1. **[Node.js](https://nodejs.org/) & npm** (for the frontend)
2. **Python 3.11+** (for the backend)
3. **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - A fast Python package installer (`pip install uv`)

You'll also need **one [OpenRouter](https://openrouter.ai/) API key** (powers
conversation + error analysis). A DeepL key is optional and only adds
tap-to-translate. You enter these *in the app*, not in any file.

### How to Run

1. **Clone the repository** and navigate to the folder:
   ```bash
   git clone https://github.com/your-username/sprachboot.git
   cd sprachboot
   ```

2. **Run the start script:**
   ```bash
   python start.py
   ```
   It creates a `.env` for you, installs backend (`uv`) and frontend (`npm`)
   dependencies, starts both servers, and opens `http://localhost:3000`.

3. **Finish onboarding in the browser:**
   On first launch you'll land on the welcome page → **Start practicing** →
   a short onboarding wizard. Paste your OpenRouter key there and pick your
   models. Keys are stored locally in `backend/api_keys.json`, never uploaded.

> **First voice use** downloads a local Whisper speech model (~460 MB) once —
> give it a moment the first time you hold the mic. Speech and all AI run from
> your machine; only the chat/analysis calls go out to OpenRouter.

### Shutting Down
To stop both the frontend and backend servers, simply press `Ctrl+C` in your terminal. The script will gracefully shut down both processes.

---

## Technical Stack
* **Frontend:** Next.js (App Router)
* **Backend:** FastAPI (Python)
* **Speech-to-Text:** local `faster-whisper` (runs on your machine)
* **AI Models (via OpenRouter):** Llama 3.3 70B (Conversation), DeepSeek (Error Analysis)

*For more in-depth technical details, check out our [CLAUDE.md](./CLAUDE.md).*
