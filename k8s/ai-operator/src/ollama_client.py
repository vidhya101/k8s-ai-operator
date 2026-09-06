"""Thin async client for a local Ollama server: chat + embeddings, with retry, model fallback,
and a concurrency gate (big models are RAM-bound on a laptop, so we don't hammer it)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

log = logging.getLogger("ai-operator.ollama")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


class OllamaError(RuntimeError):
    """Ollama returned an error or was unreachable after retries."""


class OllamaClient:
    def __init__(
        self,
        host: str = OLLAMA_HOST,
        timeout: float = 180.0,
        max_concurrent: int = 2,
        retries: int = 3,
        backoff_seconds: float = 5.0,
    ) -> None:
        self._host = host
        self._timeout = timeout
        self._retries = retries
        self._backoff = backoff_seconds
        self._sem = asyncio.Semaphore(max_concurrent)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self._host}/api/tags")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[str]:
        r = await self._client.get(f"{self._host}/api/tags")
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                async with self._sem:
                    r = await self._client.post(f"{self._host}{path}", json=payload)
                r.raise_for_status()
                return r.json()
            except (httpx.HTTPError, json.JSONDecodeError) as exc:  # named, not bare
                last = exc
                wait = self._backoff * attempt
                log.warning("ollama %s attempt %d/%d failed: %s (retry in %.0fs)",
                            path, attempt, self._retries, exc, wait)
                await asyncio.sleep(wait)
        raise OllamaError(f"ollama {path} failed after {self._retries} attempts: {last}")

    async def chat(
        self,
        model: str,
        system: str,
        user: str,
        *,
        fallback_model: str | None = None,
        temperature: float = 0.1,
        num_ctx: int = 8192,
        max_tokens: int = 2048,
        json_mode: bool = True,
    ) -> str:
        """Return the assistant message content. Falls back to `fallback_model` once on failure."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            data = await self._post("/api/chat", payload)
        except OllamaError:
            if not fallback_model or fallback_model == model:
                raise
            log.warning("falling back from %s to %s", model, fallback_model)
            payload["model"] = fallback_model
            data = await self._post("/api/chat", payload)
        return data.get("message", {}).get("content", "").strip()

    async def embed(self, model: str, text: str) -> list[float]:
        data = await self._post("/api/embeddings", {"model": model, "prompt": text[:8000]})
        vec = data.get("embedding")
        if not vec:
            raise OllamaError(f"empty embedding from {model}")
        return vec


def extract_json(raw: str) -> Any:
    """Ollama in format=json still occasionally wraps output. Pull the first JSON value out."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("\n") + 1:] if "\n" in raw else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # find the outermost {...} or [...]
    for open_c, close_c in (("[", "]"), ("{", "}")):
        i, j = raw.find(open_c), raw.rfind(close_c)
        if 0 <= i < j:
            try:
                return json.loads(raw[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise OllamaError(f"model did not return parseable JSON: {raw[:300]!r}")
