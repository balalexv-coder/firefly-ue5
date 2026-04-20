"""
Smoke-test TTS integration. Два уровня:

1. Direct EdgeTTSBackend — синтезирует 2 реплики (1 мужская, 1 женская),
   проверяет что MP3 файлы созданы и ненулевого размера.

2. End-to-end через FastAPI TestClient с mock-LLM — убеждаемся что
   /start и /turn возвращают audio_url и файлы реально на диске.

Требует интернет (edge-tts обращается к Microsoft endpoint).

Запуск:
    python test_tts.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any


def ok(msg: str) -> None:
    print(f"  \033[32mOK\033[0m   {msg}")


def fail(msg: str) -> None:
    print(f"  \033[31mFAIL\033[0m {msg}")
    sys.exit(1)


def section(title: str) -> None:
    print(f"\n\033[1;33m=== {title} ===\033[0m")


# ---------------- Test 1: direct EdgeTTSBackend ----------------

def test_direct_edge_tts() -> Path:
    from tts import EdgeTTSBackend, GENDER_BY_CHARACTER

    section("Direct EdgeTTSBackend")
    backend = EdgeTTSBackend()
    print(f"voice_male={backend.voice_male}  voice_female={backend.voice_female}")

    out_dir = Path("./audio_test_direct").resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)

    # Male line
    mp3_male = backend.synthesize(
        text="Two hours to atmo, folks. Grab your cups before we get dusty.",
        character_key="Mal",
        output_dir=out_dir,
        stem="test_mal",
    )
    size_male = mp3_male.stat().st_size
    if size_male < 1000:
        fail(f"Male MP3 too small: {size_male} bytes")
    ok(f"Male MP3 written: {mp3_male.name} ({size_male:,} bytes)")

    # Female line
    mp3_female = backend.synthesize(
        text="Malcolm. About tomorrow. You didn't mention the Sinclair family.",
        character_key="Inara",
        output_dir=out_dir,
        stem="test_inara",
    )
    size_female = mp3_female.stat().st_size
    if size_female < 1000:
        fail(f"Female MP3 too small: {size_female} bytes")
    ok(f"Female MP3 written: {mp3_female.name} ({size_female:,} bytes)")

    # Verify gender mapping works
    assert GENDER_BY_CHARACTER.get("Mal") == "male", "Gender map: Mal should be male"
    assert GENDER_BY_CHARACTER.get("Inara") == "female", "Gender map: Inara should be female"
    ok("gender map correct (Mal=male, Inara=female)")

    return out_dir


# ---------------- Test 2: end-to-end via FastAPI TestClient ----------------

def test_endpoint_returns_audio_urls() -> None:
    section("End-to-end: /start + /turn return audio_url and files exist")

    # Подменяем LLM backend моком перед импортом server
    import backends as _backends

    class MockBackend:
        name = "mock"

        def generate_turn(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
            is_opener = schema["properties"]["lines"].get("minItems", 0) == 1
            if is_opener:
                return {
                    "lines": [{"speaker": "Mal", "line": "Two hours to atmo.", "emotion": "calm"}],
                    "next_player_options": ["How's the cargo?", "Inara, you been quiet.", "Fly safe, Wash."],
                    "phase": "cruise",
                    "continue": True,
                }
            return {
                "lines": [
                    {"speaker": "Zoe",   "line": "Two klicks out, sir.", "emotion": "deadpan"},
                    {"speaker": "Inara", "line": "Malcolm, please reconsider.", "emotion": "calm"},
                ],
                "next_player_options": ["Noted.", "What did Inara mean?", "Let's do this."],
                "phase": "cruise",
                "continue": True,
            }

    _backends.make_backend = lambda: MockBackend()  # type: ignore[assignment]

    # TTS оставляем включённым (edge-tts)
    os.environ.pop("TTS_BACKEND", None)

    # Use a dedicated audio dir so we can clean up and verify
    audio_root = Path("./audio_test_e2e").resolve()
    if audio_root.exists():
        shutil.rmtree(audio_root)
    os.environ["AUDIO_DIR"] = str(audio_root)

    # Чистый импорт server с новыми env переменными
    for mod in list(sys.modules):
        if mod in ("server", "tts", "backends", "prompts"):
            del sys.modules[mod]

    import server  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402

    client = TestClient(server.app)

    # /start
    r = client.post("/start", json={})
    assert r.status_code == 200, r.text
    data = r.json()
    session_id = data["session_id"]
    opener = data["opener"]
    assert opener["speaker"] == "Mal"
    assert opener["audio_url"], f"opener missing audio_url: {opener}"
    ok(f"/start opener.audio_url = {opener['audio_url']}")

    # Check file exists on disk
    rel = opener["audio_url"].removeprefix("/audio/")
    mp3 = audio_root / rel
    if not mp3.exists():
        fail(f"opener MP3 missing on disk: {mp3}")
    if mp3.stat().st_size < 1000:
        fail(f"opener MP3 too small: {mp3.stat().st_size} bytes")
    ok(f"opener MP3 on disk: {mp3} ({mp3.stat().st_size:,} bytes)")

    # /turn
    r = client.post("/turn", json={
        "session_id": session_id,
        "history": [
            {"speaker": "Mal", "line": "Two hours to atmo."},
            {"speaker": "player", "line": "How's the cargo?"},
        ],
        "player_choice": "How's the cargo?",
        "orbit_progress": 0.1,
    })
    assert r.status_code == 200, r.text
    turn_data = r.json()
    n_lines = len(turn_data["lines"])
    assert 1 <= n_lines <= 3, f"expected 1-3 lines, got {n_lines}"
    for line in turn_data["lines"]:
        assert line["audio_url"], f"turn line missing audio_url: {line}"
        rel = line["audio_url"].removeprefix("/audio/")
        mp3 = audio_root / rel
        if not mp3.exists() or mp3.stat().st_size < 1000:
            fail(f"turn line MP3 bad: {mp3}")
    ok(f"/turn: {n_lines} lines, all with valid audio files on disk")

    # Verify audio_url is a serveable URL via the /audio static mount
    r = client.get(opener["audio_url"])
    if r.status_code != 200 or len(r.content) < 1000:
        fail(f"GET opener.audio_url failed: status={r.status_code} size={len(r.content)}")
    ok(f"GET {opener['audio_url']} returns MP3 ({len(r.content):,} bytes)")


# ---------------- Runner ----------------

def main() -> int:
    print("Firefly Dialogue Server — TTS smoke test")
    print("=" * 50)

    direct_dir = test_direct_edge_tts()
    test_endpoint_returns_audio_urls()

    print("\n" + "=" * 50)
    print(f"\033[32mALL PASS\033[0m — direct MP3s in {direct_dir}")
    print("Listen to them to verify voice quality.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
