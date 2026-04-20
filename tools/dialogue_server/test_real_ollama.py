"""
Real-LLM smoke: вызывает Ollama (qwen3.5:9b) один раз на /start и один раз
на /turn, печатает что модель реально возвращает. Проверяет что speakers
попадают в ACTIVE_CHARACTER_KEYS.

Требует: запущенный Ollama (http://localhost:11434) с моделью qwen3.5:9b.
"""

from __future__ import annotations

import json
import sys

from backends import OllamaBackend
from characters import ACTIVE_CHARACTER_KEYS
from prompts import (
    opener_instruction,
    opener_schema,
    system_prompt,
    turn_instruction,
    turn_schema,
)


def section(title: str) -> None:
    print(f"\n\033[1;33m=== {title} ===\033[0m")


def check_speakers(lines: list[dict]) -> bool:
    bad = [ln["speaker"] for ln in lines if ln["speaker"] not in ACTIVE_CHARACTER_KEYS]
    if bad:
        print(f"\033[31mFAIL\033[0m non-active speakers: {bad}")
        return False
    print(f"\033[32mOK\033[0m all speakers active: {[ln['speaker'] for ln in lines]}")
    return True


def main() -> int:
    backend = OllamaBackend(model="qwen3.5:9b")
    sp = system_prompt()

    section("Opener (/start equivalent)")
    opener_user = (
        f"CURRENT CONTEXT\nphase=cruise\norbit_progress=0.00\n\n"
        f"HISTORY\n(none)\n\nPLAYER'S LATEST LINE (just selected)\n(none)\n\n"
        f"TASK\n{opener_instruction()}"
    )
    print("Calling Ollama for opener...")
    data = backend.generate_turn(sp, opener_user, opener_schema())
    print(json.dumps(data, indent=2, ensure_ascii=False))
    if not check_speakers(data["lines"]):
        return 1

    section("Turn 1 (with player choice)")
    history_str = f"1. Mal: {data['lines'][0]['line']}\n2. player: How's the cargo?"
    turn_user = (
        f"CURRENT CONTEXT\nphase=cruise\norbit_progress=0.12\n\n"
        f"HISTORY\n{history_str}\n\nPLAYER'S LATEST LINE (just selected)\n"
        f"How's the cargo?\n\nTASK\n{turn_instruction()}"
    )
    print("Calling Ollama for turn...")
    data2 = backend.generate_turn(sp, turn_user, turn_schema())
    print(json.dumps(data2, indent=2, ensure_ascii=False))
    if not check_speakers(data2["lines"]):
        return 1

    print("\n\033[32mReal LLM smoke OK — qwen3.5:9b respects 4-speaker constraint.\033[0m")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
