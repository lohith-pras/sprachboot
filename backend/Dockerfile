# SprachBoot backend — FastAPI + uv. ffmpeg bundled for audio transcode
# (speech-to-text is routed through OpenRouter; no local Whisper model).
FROM python:3.13-slim

# ffmpeg: transcode browser WebM → WAV before sending to OpenRouter STT.
# build-essential: some chromadb deps may compile from source.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependency layer first for caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Pre-download ChromaDB's embedding model (all-MiniLM-L6-v2, ~79MB) into the
# image so the first real RAG query is instant. Without this, every fresh
# container downloads it on the user's first message (~20s of lag).
RUN uv run python -c "import chromadb; c=chromadb.PersistentClient(path='/tmp/warm'); col=c.get_or_create_collection('warm'); col.add(documents=['warmup'], ids=['1']); col.query(query_texts=['warmup'], n_results=1)" \
    && rm -rf /tmp/warm

# App code.
COPY . .

EXPOSE 8000

# Data (sqlite db, chroma, api_keys.json) is redirected to /data via env in
# docker-compose so it persists in a named volume, separate from the image.
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
