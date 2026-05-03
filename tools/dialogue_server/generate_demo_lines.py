"""
Сгенерировать 8 demo WAV-ов для первого Firefly playable demo.

Реплики и привязка к character'у фиксированные. Складывает результаты в
audio_test_wav/demo_lines/<character>_<line_id>.wav.

Запуск:
    cd tools/dialogue_server
    python generate_demo_lines.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from tts import EdgeTTSBackend


# (character, line_id, text) — порядок важен для звучания demo loop'a.
DEMO_LINES: list[tuple[str, str, str]] = [
    ("Mal",   "intro_atmo",     "Two hours to atmo, folks. Grab your cups before we get dusty."),
    ("Zoe",   "status",         "Two klicks out, sir. No patrol activity on the scanner."),
    ("Wash",  "vote",           "I vote for 'don't explode' again. Always polls well."),
    ("Inara", "sinclair",       "Malcolm. About tomorrow. You didn't mention the Sinclair family."),
    ("Mal",   "orders",         "Wash, hold us steady on approach. Zoe, run the cargo manifest one more time."),
    ("Zoe",   "cargo",          "Cargo's all secure below. Wouldn't want to start the day apologizing again."),
    ("Wash",  "dramatic",       "If anyone needs me, I'll be dramatically not crashing the ship."),
    ("Inara", "surprise",       "Try to act surprised when this goes sideways. It's a small kindness."),
]


def main() -> None:
    out_dir = Path("./audio_test_wav/demo_lines").resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    backend = EdgeTTSBackend(output_format="wav")
    print(f"voice_male={backend.voice_male}  voice_female={backend.voice_female}")
    print(f"output_dir={out_dir}")
    print()

    for i, (char, line_id, text) in enumerate(DEMO_LINES, 1):
        stem = f"{char}_{line_id}"
        path = backend.synthesize(
            text=text,
            character_key=char,
            output_dir=out_dir,
            stem=stem,
        )
        size = path.stat().st_size
        print(f"  [{i}/{len(DEMO_LINES)}] {char:<5} {line_id:<14} {size:>7,} bytes  {path.name}")

    print()
    print(f"Done. {len(DEMO_LINES)} WAVs in {out_dir}")


if __name__ == "__main__":
    main()
