"""Shared OpenRouter API client. All model calls go through here."""
import os
import base64
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
# Conversation default: a fast non-reasoning instruct model. Reasoning models
# (e.g. DeepSeek V4) are wrong for live chat — they burn the token budget
# thinking and return empty content. Keep this a plain instruct model.
CONV_MODEL = "google/gemma-4-31b-it:free"
DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"
_HTTP_REFERER = "https://sprachboot.vercel.app"


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


async def call_openrouter(
    model: str,
    messages: list[dict],
    max_tokens: int = 200,
    temperature: float = 0.7,
    response_format: dict | None = None,
) -> str:
    """Call OpenRouter and return the response content string. Raises on HTTP error."""
    async def _post(mt: int):
        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": mt,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=_headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json(), resp

    data, resp = await _post(max_tokens)

    # OpenRouter can return a 200 with an error envelope and no choices.
    if not data.get("choices"):
        raise httpx.HTTPStatusError(
            f"OpenRouter returned no choices: {str(data)[:300]}",
            request=resp.request, response=resp,
        )

    choice = data["choices"][0]
    content = (choice.get("message") or {}).get("content")

    # Reasoning models (e.g. DeepSeek V4) can spend the whole token budget on
    # hidden reasoning and return empty content with finish_reason 'length'.
    # Give it one retry with much more room before giving up.
    if not content and choice.get("finish_reason") == "length":
        data, resp = await _post(max_tokens * 5)
        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content")

    if not content:
        # Surface the real reason in the logs instead of swallowing it.
        print(
            f"[openrouter] empty content from {model}: "
            f"finish_reason={choice.get('finish_reason')} "
            f"message_keys={list((choice.get('message') or {}).keys())} "
            f"raw={str(data)[:500]}"
        )
        raise httpx.HTTPStatusError(
            f"Empty content from {model} (finish_reason={choice.get('finish_reason')})",
            request=resp.request, response=resp,
        )
    return content


WHISPER_MODEL = "openai/whisper-1"


async def transcribe(
    audio_bytes: bytes,
    fmt: str = "wav",
    language: str = "de",
    model: str = WHISPER_MODEL,
) -> str:
    """Transcribe audio to text via OpenRouter's STT endpoint (same key as chat).

    Routes speech-to-text through OpenRouter so no local Whisper model is needed.
    Returns the transcript text. Raises on HTTP error.
    """
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    payload = {
        "model": model,
        "input_audio": {"data": b64, "format": fmt},
        "language": language,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE}/audio/transcriptions",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return (resp.json().get("text") or "").strip()
