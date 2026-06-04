"""Shared OpenRouter API client. All model calls go through here."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
LLAMA_MODEL = "meta-llama/llama-3.3-70b-instruct"
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
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"].get("content")
        if not content:
            raise httpx.HTTPStatusError(
                "Empty content from model", request=resp.request, response=resp
            )
        return content
