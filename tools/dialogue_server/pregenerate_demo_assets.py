"""
Один раз пред-генерирует 8 demo LSes для dialogue server'а.

Использует существующие WAV файлы в audio_test_wav/demo_lines/ (созданные
generate_demo_lines.py), вызывает firefly_face_pipeline.run_pipeline в
открытом UE Editor через Python Remote Execution. По 2 line_id на каждого
speaker'а — Mal/Zoe/Wash/Inara.

Pre-requisites:
  1. UE Editor открыт, L_SerenityCabin загружен (любой), PIE OFF
  2. Project Settings → Plugins → Python → Enable Remote Execution = True
  3. WAV файлы существуют в audio_test_wav/demo_lines/<Speaker>_<line_id>.wav

Run:
    cd tools/dialogue_server
    .venv\\Scripts\\python.exe pregenerate_demo_assets.py
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from ue_pipeline_client import run_pipeline_in_ue, UEPipelineError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


# (character, line_id) — должны соответствовать _DEMO_LINE_ID_POOL в server.py.
DEMO_LINES: list[tuple[str, str]] = [
    ("Mal",   "intro_atmo"),
    ("Mal",   "orders"),
    ("Zoe",   "status"),
    ("Zoe",   "cargo"),
    ("Wash",  "vote"),
    ("Wash",  "dramatic"),
    ("Inara", "sinclair"),
    ("Inara", "surprise"),
]


def main() -> int:
    wav_dir = Path("audio_test_wav/demo_lines").resolve()
    if not wav_dir.is_dir():
        log.error("WAV dir not found: %s — run generate_demo_lines.py first", wav_dir)
        return 1

    log.info("Pre-generating %d demo LSes...", len(DEMO_LINES))
    log.info("WAV source: %s", wav_dir)

    failures: list[tuple[str, str, str]] = []

    for i, (character, line_id) in enumerate(DEMO_LINES, 1):
        wav_path = wav_dir / f"{character}_{line_id}.wav"
        if not wav_path.is_file():
            log.error("[%d/%d] WAV missing: %s", i, len(DEMO_LINES), wav_path)
            failures.append((character, line_id, "WAV missing"))
            continue

        log.info("[%d/%d] %s/%s ← %s", i, len(DEMO_LINES), character, line_id, wav_path.name)
        try:
            paths = run_pipeline_in_ue(
                wav_path=str(wav_path),
                character=character,
                line_id=line_id,
                overwrite=True,
                exec_timeout_seconds=180,
            )
            log.info("    LS: %s", paths.get("level_sequence"))
        except UEPipelineError as e:
            log.error("    FAILED: %s", e)
            failures.append((character, line_id, str(e)))
        except Exception as e:
            log.exception("    UNEXPECTED ERROR: %s", e)
            failures.append((character, line_id, f"unexpected: {e}"))

        # Pause между pipeline calls — UE state нужно время чтобы settle.
        # Без задержки только 1-я реплика проходит, остальные fail на
        # export_animation_sequence None (Performance Process race).
        if i < len(DEMO_LINES):
            log.info("    sleeping 3s before next line...")
            time.sleep(3.0)

    log.info("=== Done. %d/%d successful ===",
             len(DEMO_LINES) - len(failures), len(DEMO_LINES))
    if failures:
        log.error("Failures:")
        for ch, lid, err in failures:
            log.error("  %s/%s: %s", ch, lid, err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
