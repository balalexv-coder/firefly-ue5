"""
CLI-клиент для ручного теста dialogue server.

Запуск (сервер должен быть поднят на 127.0.0.1:8765):
    python test_client.py

Управление:
    1 / 2 / 3  — выбрать вариант ответа
    q          — выйти
    n          — пропустить раунд (без реплики игрока)
"""

from __future__ import annotations

import sys

import requests

BASE = "http://127.0.0.1:8765"


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


SPEAKER_COLORS = {
    "Mal":    "38;5;208",  # orange
    "Zoe":    "38;5;166",
    "Wash":   "38;5;220",
    "Jayne":  "38;5;196",
    "Kaylee": "38;5;213",
    "Inara":  "38;5;177",
    "Simon":  "38;5;111",
    "River":  "38;5;141",
    "Book":   "38;5;250",
    "player": "38;5;46",
}


def print_line(speaker: str, line: str, emotion: str = "") -> None:
    color = SPEAKER_COLORS.get(speaker, "0")
    tag = _color(f"{speaker:>7}", color)
    em = _color(f"[{emotion}]", "38;5;240") if emotion else ""
    print(f"  {tag} {em} {line}")


def main() -> int:
    print("Firefly Dialogue Server — test client\n")

    r = requests.get(f"{BASE}/health", timeout=5)
    r.raise_for_status()
    print(f"Server: {r.json()}\n")

    # /start
    r = requests.post(f"{BASE}/start", json={}, timeout=60)
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    opener = data["opener"]
    options = data["next_player_options"]

    print(_color(f"=== Session {session_id} ===\n", "1;33"))
    print_line(opener["speaker"], opener["line"], opener.get("emotion", ""))
    history = [{"speaker": opener["speaker"], "line": opener["line"]}]

    orbit = 0.0
    round_no = 0

    while True:
        print()
        for i, opt in enumerate(options, 1):
            print(f"   [{i}] {opt}")
        choice = input("> ").strip().lower()

        if choice in ("q", "quit", "exit"):
            print("bye")
            return 0

        if choice == "n":
            player_choice = ""
        elif choice in ("1", "2", "3") and 1 <= int(choice) <= len(options):
            player_choice = options[int(choice) - 1]
            history.append({"speaker": "player", "line": player_choice})
            print_line("player", player_choice)
        else:
            print("use 1/2/3, 'n' to skip, 'q' to quit")
            continue

        round_no += 1
        orbit = min(1.0, orbit + 0.12)

        payload = {
            "session_id": session_id,
            "history": history,
            "player_choice": player_choice,
            "orbit_progress": orbit,
        }
        r = requests.post(f"{BASE}/turn", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        for ln in data["lines"]:
            print_line(ln["speaker"], ln["line"], ln.get("emotion", ""))
            history.append({"speaker": ln["speaker"], "line": ln["line"]})

        options = data["next_player_options"]
        phase = data["phase"]
        cont = data["continue"]

        print(_color(f"[phase={phase} orbit={orbit:.2f} continue={cont}]", "38;5;240"))

        if not cont:
            print(_color("\n=== Conversation ends — cinematic landing triggers ===", "1;33"))
            return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"\nrequest error: {e}")
        sys.exit(2)
