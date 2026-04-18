"""
Backends для LLM-генерации реплик. Два варианта:

    OllamaBackend    — локальный, дефолт. Для разработки. Модель qwen3.5:9b.
    AnthropicBackend — Claude API. Для финального демо / когда нужно pro-качество.

Оба реализуют один метод: generate_turn(system, user, schema) -> dict.
Возврат — уже распарсенный JSON по schema.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol

import requests

log = logging.getLogger("dialogue_server.backends")


class DialogueBackend(Protocol):
    name: str

    def generate_turn(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Возвращает структурированный ответ, строго соответствующий schema."""
        ...


# ---------- Ollama ----------

class OllamaBackend:
    """
    Ollama с `format: <JSON Schema>` — структурированный выход.
    Для Qwen3.5 отключаем thinking через `think: false` (иначе уходит в размышления).
    """

    name = "ollama"

    def __init__(
        self,
        model: str = "qwen3.5:9b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.85,
        num_predict: int = 700,
        request_timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.num_predict = num_predict
        self.request_timeout = request_timeout

    def generate_turn(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "format": schema,
            "think": False,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
                "top_p": 0.9,
            },
        }

        log.debug("ollama request model=%s", self.model)
        r = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.request_timeout,
        )
        r.raise_for_status()
        data = r.json()

        content = (data.get("message") or {}).get("content", "")
        if not content:
            raise RuntimeError(f"Ollama returned empty content: {data}")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Ollama returned invalid JSON despite format schema: {content!r}"
            ) from e

        return parsed


# ---------- Anthropic ----------

class AnthropicBackend:
    """
    Claude с tool-use для структурированного выхода.
    Включается `DIALOGUE_BACKEND=anthropic` в .env. Требует ANTHROPIC_API_KEY.
    Используем, когда локальное качество Ollama недостаточно (финальное демо).
    """

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-opus-4-7",
        max_tokens: int = 800,
        api_key: str | None = None,
    ):
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "anthropic SDK is not installed. "
                "`pip install anthropic` or switch DIALOGUE_BACKEND=ollama."
            ) from e

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Fill .env or switch DIALOGUE_BACKEND=ollama."
            )

        self.client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.max_tokens = max_tokens

    def generate_turn(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        tool = {
            "name": "emit_turn",
            "description": "Emit the next round of crew dialogue and player options.",
            "input_schema": schema,
        }
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit_turn"},
            messages=[{"role": "user", "content": user}],
        )

        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "emit_turn":
                return block.input  # type: ignore[return-value]

        raise RuntimeError(
            f"Claude did not call emit_turn. Stop reason: {resp.stop_reason}. "
            f"Content types: {[getattr(b, 'type', '?') for b in resp.content]}"
        )


# ---------- Factory ----------

def make_backend() -> DialogueBackend:
    """Выбор бекенда по DIALOGUE_BACKEND env. По умолчанию — ollama."""
    name = os.getenv("DIALOGUE_BACKEND", "ollama").lower()

    if name == "ollama":
        return OllamaBackend(
            model=os.getenv("DIALOGUE_MODEL", "qwen3.5:9b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=float(os.getenv("DIALOGUE_TEMPERATURE", "0.85")),
            num_predict=int(os.getenv("DIALOGUE_NUM_PREDICT", "700")),
        )

    if name == "anthropic":
        return AnthropicBackend(
            model=os.getenv("DIALOGUE_MODEL", "claude-opus-4-7"),
            max_tokens=int(os.getenv("DIALOGUE_MAX_TOKENS", "800")),
        )

    raise RuntimeError(
        f"Unknown DIALOGUE_BACKEND={name!r}. Expected one of: ollama, anthropic."
    )
