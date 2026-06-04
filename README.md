# SprachBoot 🚤

An AI-powered German conversational fluency trainer designed to help learners reach conversational fluency through daily speaking practice, powered by Llama and DeepSeek.

## 🚀 Quick Start for Friends & Contributors

The easiest way to run the entire application (frontend + backend) is to use our bundled start script!

### Prerequisites
Before you start, make sure you have the following installed on your computer:
1. **[Node.js](https://nodejs.org/) & npm** (for the frontend)
2. **Python 3.11+** (for the backend)
3. **[uv](https://docs.astral.sh/uv/getting-started/installation/)** - A fast Python package installer (`pip install uv`)

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

3. **Add your API Keys:**
   On the very first run, the script will automatically generate a `.env` file for you and stop.
   Open the `.env` file in the root folder, add your `OPENROUTER_API_KEY` and `OPENAI_API_KEY`, and save the file.

4. **Run the script again:**
   ```bash
   python start.py
   ```
   
   The script will now automatically:
   - Install and sync backend Python dependencies using `uv`
   - Install frontend Node.js dependencies
   - Start the FastAPI backend
   - Start the Next.js frontend
   - Open your default web browser to `http://localhost:3000`

### Shutting Down
To stop both the frontend and backend servers, simply press `Ctrl+C` in your terminal. The script will gracefully shut down both processes.

---

## Technical Stack
* **Frontend:** Next.js 14 (App Router) + Tailwind CSS
* **Backend:** FastAPI (Python)
* **AI Models:** Llama 3.3 70B (Conversation), DeepSeek V4 (Error Analysis), Whisper (Speech-to-Text)

*For more in-depth technical details, check out our [CLAUDE.md](./CLAUDE.md).*
