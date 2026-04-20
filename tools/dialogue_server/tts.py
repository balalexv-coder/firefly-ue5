"""
TTS backends для озвучки реплик экипажа.

По аналогии с backends.py (LLM): pluggable, один protocol, несколько реализаций.

Текущий дефолт — EdgeTTSBackend (Microsoft Edge neural voices, free, internet required).
На будущее — PiperTTSBackend (fully offline, open-source neural).

Интерфейс:
    backend = make_tts_backend()
    mp3_path = backend.synthesize(text, character_key, output_dir)
    # → Path к MP3 файлу на диске

Пока что — заглушка на 2 голоса:
    - Male характеры (Mal, Wash) → en-US-GuyNeural
    - Female характеры (Zoe, Inara) → en-US-JennyNeural

Когда захочется per-character voice profiles — расширим CHARACTER_VOICES map
и добавим DIALOGUE_TTS_VOICES=per_character env var.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Protocol

log = logging.getLogger("dialogue_server.tts")


# ---------- Gender map (placeholder — 2 голоса на всех) ----------

GENDER_BY_CHARACTER: dict[str, str] = {
    "Mal":    "male",
    "Wash":   "male",
    "Jayne":  "male",
    "Simon":  "male",
    "Book":   "male",
    "Zoe":    "female",
    "Inara":  "female",
    "Kaylee": "female",
    "River":  "female",
}

# Default Edge TTS voices for male/female.
# Other candidates worth trying:
#   male:   en-US-DavisNeural, en-US-TonyNeural, en-GB-RyanNeural
#   female: en-US-AriaNeural, en-US-MichelleNeural, en-GB-SoniaNeural
DEFAULT_VOICE_MALE   = "en-US-GuyNeural"
DEFAULT_VOICE_FEMALE = "en-US-JennyNeural"


def voice_for_character(character_key: str) -> str:
    """Вернуть name Edge TTS голоса для персонажа (по gender map)."""
    gender = GENDER_BY_CHARACTER.get(character_key, "male")
    if gender == "female":
        return os.getenv("TTS_VOICE_FEMALE", DEFAULT_VOICE_FEMALE)
    return os.getenv("TTS_VOICE_MALE", DEFAULT_VOICE_MALE)


# ---------- Utilities ----------

def _safe_name(s: str) -> str:
    """Превратить строку в filesystem-safe токен."""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_") or "x"


# ---------- Protocol ----------

class TTSBackend(Protocol):
    name: str

    def synthesize(
        self,
        text: str,
        character_key: str,
        output_dir: Path,
        *,
        stem: str | None = None,
    ) -> Path:
        """
        Синтезировать `text` голосом персонажа, сохранить в output_dir,
        вернуть Path к созданному файлу.
        """
        ...


# ---------- Edge TTS ----------

class EdgeTTSBackend:
    """
    Microsoft Edge's public neural TTS (через python `edge-tts` пакет).

    Pros: бесплатно, без API key, качество high-neural.
    Cons: интернет обязателен, rate-limits от MS есть но щедрые.
    """

    name = "edge-tts"

    def __init__(
        self,
        voice_male: str | None = None,
        voice_female: str | None = None,
        rate: str = "+0%",   # "+10%" ускоряет, "-10%" замедляет
        volume: str = "+0%",
    ):
        self.voice_male = voice_male or os.getenv("TTS_VOICE_MALE", DEFAULT_VOICE_MALE)
        self.voice_female = voice_female or os.getenv("TTS_VOICE_FEMALE", DEFAULT_VOICE_FEMALE)
        self.rate = rate
        self.volume = volume

    def _voice(self, character_key: str) -> str:
        gender = GENDER_BY_CHARACTER.get(character_key, "male")
        return self.voice_female if gender == "female" else self.voice_male

    def synthesize(
        self,
        text: str,
        character_key: str,
        output_dir: Path,
        *,
        stem: str | None = None,
    ) -> Path:
        import edge_tts  # local import — тяжёлый

        output_dir.mkdir(parents=True, exist_ok=True)
        voice = self._voice(character_key)
        stem = stem or f"{_safe_name(character_key)}_{uuid.uuid4().hex[:8]}"
        out_path = output_dir / f"{stem}.mp3"

        log.debug("edge-tts synth voice=%s chars=%d → %s", voice, len(text), out_path)

        async def _run() -> None:
            comm = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=self.rate,
                volume=self.volume,
            )
            await comm.save(str(out_path))

        asyncio.run(_run())
        return out_path


# ---------- Factory ----------

def make_tts_backend() -> TTSBackend:
    """
    Выбор TTS-бекенда по env. Пока только edge-tts реализован.

        TTS_BACKEND=edge         # default
        TTS_BACKEND=none         # отключить TTS (сервер всё равно запустится)
    """
    name = os.getenv("TTS_BACKEND", "edge").lower()

    if name in ("edge", "edge-tts"):
        return EdgeTTSBackend()

    if name in ("none", "off", "disabled"):
        return _NullTTSBackend()

    raise RuntimeError(
        f"Unknown TTS_BACKEND={name!r}. Expected one of: edge, none."
    )


class _NullTTSBackend:
    """Заглушка для случая когда TTS выключен."""
    name = "null"

    def synthesize(
        self,
        text: str,
        character_key: str,
        output_dir: Path,
        *,
        stem: str | None = None,
    ) -> Path:
        raise RuntimeError("TTS is disabled (TTS_BACKEND=none). Set TTS_BACKEND=edge to enable.")
