"""
Firefly UE5 — Dialogue Server.

FastAPI-обёртка над Anthropic Claude, генерирует реплики экипажа через tool-use
(структурированный выход). Поддерживает prompt caching для system prompt.

Запуск:
    uvicorn server:app --reload --port 8765
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from characters import CHARACTER_KEYS
from prompts import opener_prompt, system_prompt, tool_schema


load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("dialogue_server")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("DIALOGUE_MODEL", "claude-opus-4-7")
MAX_TOKENS = int(os.getenv("DIALOGUE_MAX_TOKENS", "800"))
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(exist_ok=True)

if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
    )

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ---------- Models ----------

class HistoryTurn(BaseModel):
    speaker: str
    line: str


class StartRequest(BaseModel):
    seed: str | None = None


class TurnRequest(BaseModel):
    session_id: str
    history: list[HistoryTurn] = Field(default_factory=list)
    player_choice: str
    orbit_progress: float = 0.0


class ReplyLine(BaseModel):
    speaker: str
    line: str
    emotion: str
    audio_url: str | None = None
    duration_ms: int = 0


class TurnResponse(BaseModel):
    lines: list[ReplyLine]
    next_player_options: list[str]
    phase: str
    continue_: bool = Field(alias="continue")


class StartResponse(BaseModel):
    session_id: str
    opener: ReplyLine
    next_player_options: list[str]
    phase: str
    orbit_progress: float


# ---------- Helpers ----------

def _estimate_duration_ms(text: str) -> int:
    """Грубая оценка длительности реплики по количеству слов."""
    words = max(1, len(text.split()))
    return int(words * 350 + 400)  # 350 мс на слово + 400 мс фикс


def _build_system() -> list[dict[str, Any]]:
    """System prompt с cache control — кешируется на стороне Anthropic."""
    return [
        {
            "type": "text",
            "text": system_prompt(),
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _history_to_messages(history: list[HistoryTurn], player_choice: str | None,
                         orbit_progress: float, extra_instruction: str | None = None) -> list[dict[str, Any]]:
    """Готовим список messages для Anthropic."""
    convo_text_parts: list[str] = []
    for turn in history:
        if turn.speaker == "player":
            convo_text_parts.append(f"PLAYER: {turn.line}")
        else:
            convo_text_parts.append(f"{turn.speaker}: {turn.line}")

    if player_choice and (not history or history[-1].line != player_choice):
        convo_text_parts.append(f"PLAYER: {player_choice}")

    history_block = "\n".join(convo_text_parts) if convo_text_parts else "(conversation not yet started)"

    user_text = (
        f"orbit_progress: {orbit_progress:.2f}\n\n"
        f"RECENT HISTORY\n{history_block}\n\n"
    )
    if extra_instruction:
        user_text += f"INSTRUCTION\n{extra_instruction}\n"
    else:
        user_text += (
            "INSTRUCTION\n"
            "Produce the next turn. Call emit_turn with 2-3 crew lines reacting to the "
            "most recent PLAYER line, and 3 next player options."
        )

    return [{"role": "user", "content": user_text}]


def _call_llm(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Вызов Claude с tool-use. Возвращает распарсенный input тула emit_turn."""
    resp = claude.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_build_system(),
        tools=[tool_schema()],
        tool_choice={"type": "tool", "name": "emit_turn"},
        messages=messages,
    )

    # Забираем tool_use блок
    for block in resp.content:
        if block.type == "tool_use" and block.name == "emit_turn":
            return block.input  # уже dict

    raise RuntimeError(
        f"LLM did not call emit_turn tool. Stop reason: {resp.stop_reason}. "
        f"Content types: {[b.type for b in resp.content]}"
    )


def _log_turn(session_id: str, kind: str, payload: dict[str, Any]) -> None:
    """Пишем лог каждого оборота в JSON-файл."""
    path = LOG_DIR / f"{session_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False) + "\n")


def _normalize_output(raw: dict[str, Any]) -> dict[str, Any]:
    """Санитайзер ответа модели — добавляем audio_url=None и duration."""
    lines = []
    for item in raw.get("lines", []):
        lines.append(
            {
                "speaker": item["speaker"],
                "line": item["line"].strip(),
                "emotion": item.get("emotion", "calm"),
                "audio_url": None,
                "duration_ms": _estimate_duration_ms(item["line"]),
            }
        )

    return {
        "lines": lines,
        "next_player_options": [opt.strip() for opt in raw.get("next_player_options", [])],
        "phase": raw.get("phase", "cruise"),
        "continue": bool(raw.get("continue", True)),
    }


# ---------- API ----------

app = FastAPI(title="Firefly Dialogue Server", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL}


@app.post("/start", response_model=StartResponse)
def start(_: StartRequest) -> StartResponse:
    session_id = "sess_" + secrets.token_hex(6)
    log.info("start session=%s", session_id)

    messages = _history_to_messages(history=[], player_choice=None, orbit_progress=0.0,
                                    extra_instruction=opener_prompt())
    try:
        raw = _call_llm(messages)
    except anthropic.APIError as e:
        log.exception("Anthropic API error on /start")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e

    data = _normalize_output(raw)
    if not data["lines"]:
        raise HTTPException(status_code=500, detail="LLM returned no opener line.")

    # Берём первую строку как opener (по контракту /start там только 1 строка от Mal).
    opener_line = data["lines"][0]
    _log_turn(session_id, "start", {"raw": raw, "normalized": data})

    return StartResponse(
        session_id=session_id,
        opener=ReplyLine(**opener_line),
        next_player_options=data["next_player_options"],
        phase=data["phase"],
        orbit_progress=0.0,
    )


@app.post("/turn")
def turn(req: TurnRequest) -> dict[str, Any]:
    # Валидация: история должна содержать только валидных speakers
    valid_speakers = set(CHARACTER_KEYS) | {"player"}
    for t in req.history:
        if t.speaker not in valid_speakers:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown speaker '{t.speaker}' in history. Valid: {sorted(valid_speakers)}",
            )

    log.info("turn session=%s history=%d progress=%.2f choice=%r",
             req.session_id, len(req.history), req.orbit_progress, req.player_choice)

    messages = _history_to_messages(req.history, req.player_choice, req.orbit_progress)
    try:
        raw = _call_llm(messages)
    except anthropic.APIError as e:
        log.exception("Anthropic API error on /turn")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e

    data = _normalize_output(raw)
    _log_turn(req.session_id, "turn", {
        "request": req.model_dump(),
        "raw": raw,
        "normalized": data,
    })

    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
