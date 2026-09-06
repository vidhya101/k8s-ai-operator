"""Agent registry + LLM orchestration. Each agent = a system prompt + a model (resolved from the
live ConfigMap so you retune without a rebuild) + memory injection."""
from __future__ import annotations

import logging
import os
import pathlib
from dataclasses import dataclass
from typing import Any

import yaml

from ollama_client import OllamaClient, extract_json
from memory import Memory, Recall

log = logging.getLogger("ai-operator.agents")

# The operator pod clones this repo to /code; prompts + agents.yaml live inside it. Override with
# PROMPT_DIR / AGENTS_FILE if you mount them elsewhere.
_CFG = pathlib.Path(os.environ.get("CONFIG_DIR", "/code/k8s/ai-operator/config"))
PROMPT_DIR = pathlib.Path(os.environ.get("PROMPT_DIR", str(_CFG / "prompts")))
AGENTS_FILE = pathlib.Path(os.environ.get("AGENTS_FILE", str(_CFG / "agents.yaml")))


@dataclass
class Agent:
    name: str
    role: str
    model_key: str
    model_fallback_key: str | None
    prompt: str
    temperature: float
    scan: dict[str, Any]


class AgentRegistry:
    def __init__(self, ollama: OllamaClient, memory: Memory, cfg: "ConfigView") -> None:
        self._ollama = ollama
        self._memory = memory
        self._cfg = cfg
        self._agents: dict[str, Agent] = {}
        self._defaults: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        spec = yaml.safe_load(AGENTS_FILE.read_text())
        self._defaults = spec.get("defaults", {})
        for a in spec.get("agents", []):
            pf = PROMPT_DIR / a["promptFile"]
            self._agents[a["name"]] = Agent(
                name=a["name"],
                role=a.get("role", ""),
                model_key=a["model"],
                model_fallback_key=a.get("modelFallback"),
                prompt=pf.read_text() if pf.exists() else a.get("role", ""),
                temperature=float(a.get("temperature", 0.1)),
                scan=a.get("scan", {}),
            )

    def get(self, name: str) -> Agent:
        return self._agents[name]

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    # ------------------------------------------------------------------------------------------
    async def embed(self, text: str) -> list[float] | None:
        model = self._cfg.get("model.embedding", "nomic-embed-text")
        try:
            return await self._ollama.embed(model, text)
        except Exception as exc:  # embedding is best-effort; recall degrades to recency
            log.warning("embed failed (%s) — similarity recall disabled for this item", exc)
            return None

    async def run(
        self,
        agent_name: str,
        user_payload: str,
        *,
        recall_query: str | None = None,
        recall_k: int = 4,
    ) -> Any:
        agent = self._agents[agent_name]
        model = self._cfg.get(agent.model_key, "llama3:8b")
        fallback = self._cfg.get(agent.model_fallback_key) if agent.model_fallback_key else None

        memory_block = ""
        if recall_query:
            emb = await self.embed(recall_query)
            hits: list[Recall] = self._memory.recall(emb, k=recall_k)
            if hits:
                memory_block = "\n\nPAST SIMILAR CASES (most similar first):\n" + "\n".join(
                    f"- [{h.outcome or 'n/a'}] {h.scope}: {h.text[:400]}" for h in hits
                )

        raw = await self._ollama.chat(
            model=model,
            system=agent.prompt,
            user=user_payload + memory_block,
            fallback_model=fallback,
            temperature=agent.temperature,
            num_ctx=int(self._defaults.get("numCtx", 8192)),
            max_tokens=int(self._defaults.get("maxTokens", 2048)),
            json_mode=True,
        )
        return extract_json(raw)


class ConfigView:
    """Reads keys from the ai-operator-config ConfigMap, refreshed on demand by the operator."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def update(self, data: dict[str, str]) -> None:
        self._data = dict(data or {})

    def get(self, key: str | None, default: Any = None) -> Any:
        if key is None:
            return default
        return self._data.get(key, default)

    def bool(self, key: str, default: bool = False) -> bool:
        return str(self.get(key, str(default))).lower() in ("1", "true", "yes", "on")

    def int(self, key: str, default: int) -> int:
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            return default

    def csv(self, key: str) -> list[str]:
        return [x.strip() for x in str(self.get(key, "")).split(",") if x.strip()]
