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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backends import make_backend
from characters import ACTIVE_CHARACTER_KEYS
from prompts import (
    opener_instruction,
    opener_schema,
    system_prompt,
    turn_instruction,
    turn_schema,
)
from tts import make_tts_backend
from ue_pipeline_client import run_pipeline_in_ue, UEPipelineError


load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("dialogue_server")

LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_DIR.mkdir(exist_ok=True)

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./audio"))
AUDIO_DIR.mkdir(exist_ok=True)

backend = make_backend()
log.info("dialogue backend=%s", backend.name)

tts_backend = make_tts_backend()
log.info("tts backend=%s", tts_backend.name)


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
    line_id: str = ""  # стабильный ID для маршрутизации к LS asset'у в UE
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


# Demo pool: 8 предзаписанных LSes (по 2 на speaker'a), сгенеренных через
# pregenerate_demo_assets.py при подготовке демо. Server cycle'ит per-session.
# После исчерпания пула line_id остаётся пустым → C++ HUD-only fallback.
_DEMO_LINE_ID_POOL: dict[str, list[str]] = {
    "Mal":   ["intro_atmo", "orders"],
    "Zoe":   ["status", "cargo"],
    "Wash":  ["vote", "dramatic"],
    "Inara": ["sinclair", "surprise"],
}

# Per-session счётчики использования пула.
_DEMO_LINE_ID_USAGE: dict[str, dict[str, int]] = {}


def _assign_demo_line_ids(lines: list[dict[str, Any]], session_id: str) -> None:
    """Назначить line_id из demo-пула для реплик у которых он не установлен."""
    usage = _DEMO_LINE_ID_USAGE.setdefault(session_id, {})
    for line in lines:
        if line.get("line_id"):
            continue
        speaker = line.get("speaker", "")
        pool = _DEMO_LINE_ID_POOL.get(speaker)
        if not pool:
            continue
        idx = usage.get(speaker, 0)
        if idx < len(pool):
            line["line_id"] = pool[idx]
            usage[speaker] = idx + 1


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
            "line_id": item.get("line_id", ""),  # backend может проставить
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


def _synthesize_audio(lines: list[dict[str, Any]], session_id: str, turn_tag: str) -> None:
    """
    Для каждой реплики синтезирует TTS аудио (edge-tts → MP3/WAV), проставляет
    audio_url. line_id назначается отдельно через _assign_demo_line_ids из
    pre-generated pool (см. pregenerate_demo_assets.py).
    """
    if tts_backend.name == "null":
        return

    session_dir = AUDIO_DIR / session_id
    for idx, line in enumerate(lines):
        try:
            stem = f"{turn_tag}_{idx:02d}_{line['speaker']}"
            audio_path = tts_backend.synthesize(
                text=line["line"],
                character_key=line["speaker"],
                output_dir=session_dir,
                stem=stem,
            )
            rel = audio_path.relative_to(AUDIO_DIR)
            line["audio_url"] = f"/audio/{rel.as_posix()}"
        except Exception as e:
            log.warning("TTS failed for line %d (%s): %s", idx, line["speaker"], e)


def _start_audio_dir(session_id: str) -> None:
    """Подготовить поддиректорию для аудио сессии (создаётся автоматом при synth,
    но оставляем явный helper если захотим preflight)."""
    (AUDIO_DIR / session_id).mkdir(parents=True, exist_ok=True)


# ---------- API ----------

app = FastAPI(title="Firefly Dialogue Server", version="0.3.0")

# Serve synthesized audio (MP3 or WAV) as static files under /audio/<session>/<file>.<ext>
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "backend": backend.name, "tts": tts_backend.name}


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

    _assign_demo_line_ids(data["lines"], session_id=session_id)
    _synthesize_audio(data["lines"], session_id=session_id, turn_tag="start")

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
    valid_speakers = set(ACTIVE_CHARACTER_KEYS) | {"player"}
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

    _assign_demo_line_ids(data["lines"], session_id=req.session_id)

    turn_tag = f"turn_{len(req.history):03d}"
    _synthesize_audio(data["lines"], session_id=req.session_id, turn_tag=turn_tag)

    _log_turn(req.session_id, "turn", {
        "request": req.model_dump(),
        "raw": raw,
        "normalized": data,
    })

    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8765, reload=False)
