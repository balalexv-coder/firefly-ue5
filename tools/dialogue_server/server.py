"""
Firefly UE5 — Dialogue Server.

FastAPI поверх pluggable LLM-backend'ов (Ollama | Anthropic).
Генерирует реплики экипажа структурированным JSON'ом.

По умолчанию — Ollama с qwen3.5:9b (локально, бесплатно). Переключается
переменной DIALOGUE_BACKEND=anthropic для pro-качества.

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

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backends import make_backend
from characters import CHARACTER_KEYS
from prompts import (
    opener_instruction,
    opener_schema,
    system_prompt,
    turn_instruction,
    turn_schema,
)


load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("dialogue_server")

LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(exist_ok=True)

backend = make_backend()
log.info("dialogue backend=%s", backend.name)


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


class StartResponse(BaseModel):
    session_id: str
    opener: ReplyLine
    next_player_options: list[str]
    phase: str
    orbit_progress: float


# ---------- Helpers ----------

def _estimate_duration_ms(text: str) -> int:
    words = max(1, len(text.split()))
    return int(words * 350 + 400)


def _history_to_user(history: list[HistoryTurn], player_choice: str | None,
                     orbit_progress: float, instruction: str) -> str:
    parts: list[str] = []
    for t in history:
        if t.speaker == "player":
            parts.append(f"PLAYER: {t.line}")
        else:
            parts.append(f"{t.speaker}: {t.line}")

    if player_choice and (not history or history[-1].line != player_choice):
        parts.append(f"PLAYER: {player_choice}")

    history_block = "\n".join(parts) if parts else "(conversation not yet started)"
    return (
        f"orbit_progress: {orbit_progress:.2f}\n\n"
        f"RECENT HISTORY\n{history_block}\n\n"
        f"INSTRUCTION\n{instruction}\n"
    )


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    lines = []
    for item in raw.get("lines", []):
        text = (item.get("line") or "").strip()
        if not text:
            continue
        lines.append({
            "speaker": item.get("speaker", "Mal"),
            "line":    text,
            "emotion": item.get("emotion", "calm"),
            "audio_url": None,
            "duration_ms": _estimate_duration_ms(text),
        })
    return {
        "lines": lines,
        "next_player_options": [opt.strip() for opt in raw.get("next_player_options", [])],
        "phase": raw.get("phase", "cruise"),
        "continue": bool(raw.get("continue", True)),
    }


def _log_turn(session_id: str, kind: str, payload: dict[str, Any]) -> None:
    path = LOG_DIR / f"{session_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False) + "\n")


# ---------- API ----------

app = FastAPI(title="Firefly Dialogue Server", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "backend": backend.name}


@app.post("/start", response_model=StartResponse)
def start(_: StartRequest) -> StartResponse:
    session_id = "sess_" + secrets.token_hex(6)
    log.info("start session=%s", session_id)

    user = _history_to_user(history=[], player_choice=None, orbit_progress=0.0,
                            instruction=opener_instruction())
    try:
        raw = backend.generate_turn(system_prompt(), user, opener_schema())
    except Exception as e:
        log.exception("Backend error on /start")
        raise HTTPException(status_code=502, detail=f"Backend error: {e}") from e

    data = _normalize(raw)
    if not data["lines"]:
        raise HTTPException(status_code=500, detail="Backend returned no opener line.")

    _log_turn(session_id, "start", {"raw": raw, "normalized": data})

    return StartResponse(
        session_id=session_id,
        opener=ReplyLine(**data["lines"][0]),
        next_player_options=data["next_player_options"],
        phase=data["phase"],
        orbit_progress=0.0,
    )


@app.post("/turn")
def turn(req: TurnRequest) -> dict[str, Any]:
    valid_speakers = set(CHARACTER_KEYS) | {"player"}
    for t in req.history:
        if t.speaker not in valid_speakers:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown speaker '{t.speaker}'. Valid: {sorted(valid_speakers)}",
            )

    log.info("turn session=%s history=%d progress=%.2f choice=%r",
             req.session_id, len(req.history), req.orbit_progress, req.player_choice)

    user = _history_to_user(req.history, req.player_choice, req.orbit_progress,
                            turn_instruction())
    try:
        raw = backend.generate_turn(system_prompt(), user, turn_schema())
    except Exception as e:
        log.exception("Backend error on /turn")
        raise HTTPException(status_code=502, detail=f"Backend error: {e}") from e

    data = _normalize(raw)
    _log_turn(req.session_id, "turn", {
        "request": req.model_dump(),
        "raw": raw,
        "normalized": data,
    })

    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
