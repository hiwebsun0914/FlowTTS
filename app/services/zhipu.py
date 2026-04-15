from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

from app.config import Settings


class ZhipuAPIError(RuntimeError):
    """Raised when the Zhipu API returns an error."""


@dataclass(slots=True)
class StreamChunk:
    delta: str = ""
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None


async def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = await response.aread()
        data = json.loads(payload.decode("utf-8"))
    except Exception:
        return f"Zhipu API request failed with status {response.status_code}."

    error = data.get("error") or {}
    message = error.get("message") or data.get("message")
    code = error.get("code")

    if message and code:
        return f"Zhipu API error {code}: {message}"
    if message:
        return message
    return f"Zhipu API request failed with status {response.status_code}."


async def stream_chat_completion(
    *,
    client: httpx.AsyncClient,
    settings: Settings,
    messages: list[dict[str, str]],
) -> AsyncIterator[StreamChunk]:
    payload = {
        "model": settings.zhipu_model,
        "stream": True,
        "thinking": {"type": "disabled"},
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {settings.zhipu_api_key}",
        "Content-Type": "application/json",
    }

    async with client.stream(
        "POST",
        settings.chat_completions_url,
        headers=headers,
        json=payload,
    ) as response:
        if response.status_code >= 400:
            raise ZhipuAPIError(await _extract_error_message(response))

        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue

            payload_text = line[5:].strip()
            if not payload_text or payload_text == "[DONE]":
                continue

            try:
                data = json.loads(payload_text)
            except json.JSONDecodeError:
                continue

            choices = data.get("choices") or []
            if not choices:
                continue

            choice = choices[0]
            delta = (choice.get("delta") or {}).get("content") or ""
            finish_reason = choice.get("finish_reason")
            yield StreamChunk(delta=delta, finish_reason=finish_reason, raw=data)
