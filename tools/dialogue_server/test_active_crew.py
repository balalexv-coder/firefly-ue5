"""
Smoke-test: dialogue server сужен с 9 до 4 активных.

Подменяет LLM-backend моком, проходит /start + /turn через FastAPI TestClient,
проверяет:
  1. opener.speaker == "Mal"
  2. speaker во всех repliках — только из ACTIVE_CHARACTER_KEYS
  3. system_prompt содержит именно 4 персоны
  4. /turn отвергает history с не-активным спикером (403 → мы ставим 400)
  5. turn_schema enum у speaker ограничен 4-мя ключами

Запуск из tools/dialogue_server/:
    python test_active_crew.py

Не требует Ollama / ANTHROPIC_API_KEY — backend подменяется до инстансирования server.
"""

from __future__ import annotations

import json
import sys
from typing import Any

# ------- Подменяем make_backend ДО импорта server -------

from characters import ACTIVE_CHARACTER_KEYS
import backends as _backends


class MockBackend:
    name = "mock"
    calls = 0

    def generate_turn(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        MockBackend.calls += 1

        # Отработаем два сценария: opener (minItems=1) и turn (minItems=2)
        is_opener = schema["properties"]["lines"].get("minItems", 0) == 1
        if is_opener:
            return {
                "lines": [
                    {"speaker": "Mal", "line": "Two hours to atmo.", "emotion": "calm"},
                ],
                "next_player_options": [
                    "How's the cargo?",
                    "Any chance this one doesn't go sideways?",
                    "Inara, you been quiet.",
                ],
                "phase": "cruise",
                "continue": True,
            }
        return {
            "lines": [
                {"speaker": "Zoe",   "line": "Two klicks out, sir.",    "emotion": "deadpan"},
                {"speaker": "Wash",  "line": "I vote for 'don't explode' again.", "emotion": "amused"},
            ],
            "next_player_options": [
                "Inara, your thoughts?",
                "Let's keep it simple.",
                "Wash, fly the ship.",
            ],
            "phase": "cruise",
            "continue": True,
        }


def _patched_make_backend() -> MockBackend:
    return MockBackend()


_backends.make_backend = _patched_make_backend  # type: ignore[assignment]

# Теперь импортируем server — он подхватит подменённый make_backend
import server  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(server.app)


# ------- Утилиты -------

def ok(msg: str) -> None:
    print(f"  \033[32mOK\033[0m   {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31mFAIL\033[0m {msg}")
    sys.exit(1)


# ------- Тесты -------

def test_active_keys_resolved() -> None:
    print("\n[1] ACTIVE_CHARACTER_KEYS resolves correctly")
    assert ACTIVE_CHARACTER_KEYS == ["Mal", "Zoe", "Wash", "Inara"], (
        f"Expected [Mal, Zoe, Wash, Inara], got {ACTIVE_CHARACTER_KEYS}"
    )
    ok(f"ACTIVE_CHARACTER_KEYS = {ACTIVE_CHARACTER_KEYS}")


def test_schema_enum_scoped() -> None:
    print("\n[2] turn_schema speaker enum limited to 4")
    from prompts import turn_schema
    schema = turn_schema()
    enum = schema["properties"]["lines"]["items"]["properties"]["speaker"]["enum"]
    assert enum == ACTIVE_CHARACTER_KEYS, f"Schema enum drift: {enum}"
    ok(f"speaker enum = {enum}")


def test_system_prompt_contains_only_active() -> None:
    print("\n[3] system_prompt lists only 4 personas, excludes others")
    from prompts import system_prompt
    sp = system_prompt()
    for k in ACTIVE_CHARACTER_KEYS:
        assert f"({k})" in sp, f"Active key {k} missing from system prompt"
    for excluded in ["Jayne", "Kaylee", "Simon", "River", "Book"]:
        # Allow the name as a word (e.g. in "Inara" containing "ara") — check exact key format
        assert f"({excluded})" not in sp, (
            f"Excluded key {excluded} leaked into system prompt"
        )
    ok("4 active personas present, 5 excluded not present")


def test_health() -> None:
    print("\n[4] GET /health")
    r = client.get("/health")
    assert r.status_code == 200, r.text
    ok(f"health = {r.json()}")


def test_start() -> None:
    print("\n[5] POST /start returns Mal opener + 3 player options")
    r = client.post("/start", json={})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["opener"]["speaker"] == "Mal", data
    assert len(data["next_player_options"]) == 3
    ok(f"opener = Mal: {data['opener']['line']!r}")


def test_turn_with_active_speakers() -> None:
    print("\n[6] POST /turn with history of active speakers — OK, speakers all active")
    r = client.post("/start", json={})
    session_id = r.json()["session_id"]

    history = [
        {"speaker": "Mal", "line": "Two hours to atmo."},
        {"speaker": "player", "line": "How's the cargo?"},
    ]
    r = client.post("/turn", json={
        "session_id": session_id,
        "history": history,
        "player_choice": "How's the cargo?",
        "orbit_progress": 0.1,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    speakers = [ln["speaker"] for ln in data["lines"]]
    assert all(s in ACTIVE_CHARACTER_KEYS for s in speakers), (
        f"Non-active speaker leaked: {speakers}"
    )
    ok(f"speakers in response = {speakers} (all active)")


def test_turn_rejects_inactive_history() -> None:
    print("\n[7] POST /turn with history containing 'Jayne' — rejected 400")
    r = client.post("/start", json={})
    session_id = r.json()["session_id"]

    history = [
        {"speaker": "Mal",   "line": "Two hours to atmo."},
        {"speaker": "Jayne", "line": "I'm hungry."},  # Jayne not active
    ]
    r = client.post("/turn", json={
        "session_id": session_id,
        "history": history,
        "player_choice": "How's the cargo?",
        "orbit_progress": 0.1,
    })
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "Jayne" in r.text, r.text
    ok(f"correctly rejected inactive speaker (400)")


def test_turn_accepts_player() -> None:
    print("\n[8] POST /turn accepts 'player' as valid speaker in history")
    r = client.post("/start", json={})
    session_id = r.json()["session_id"]

    history = [
        {"speaker": "Mal", "line": "Two hours to atmo."},
        {"speaker": "player", "line": "Noted."},
    ]
    r = client.post("/turn", json={
        "session_id": session_id,
        "history": history,
        "player_choice": "Noted.",
        "orbit_progress": 0.1,
    })
    assert r.status_code == 200, r.text
    ok("'player' accepted in history")


# ------- Runner -------

def main() -> int:
    print("Firefly Dialogue Server — active-crew smoke test")
    print("=" * 50)

    tests = [
        test_active_keys_resolved,
        test_schema_enum_scoped,
        test_system_prompt_contains_only_active,
        test_health,
        test_start,
        test_turn_with_active_speakers,
        test_turn_rejects_inactive_history,
        test_turn_accepts_player,
    ]
    for t in tests:
        t()

    print("\n" + "=" * 50)
    print(f"\033[32mALL PASS\033[0m — {len(tests)} tests, {MockBackend.calls} mock LLM calls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
