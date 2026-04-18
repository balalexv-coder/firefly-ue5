"""
System-prompt и tool-schema для dialogue server.

Держим здесь всё связанное с LLM-контрактом, чтобы менять промпты,
не трогая серверную обвязку.
"""

from characters import CHARACTER_KEYS, characters_block


EMOTIONS = [
    "calm", "gruff", "bright", "dry", "cryptic",
    "warm", "flirty", "amused", "serious", "deadpan",
]


def system_prompt() -> str:
    """Возвращает полный system prompt. Кешируется на клиенте Claude."""
    return f"""You are a dialogue director for a video game set in the Firefly universe.
The player is a silent passenger aboard the Firefly-class ship "Serenity". The crew
is having an informal conversation in the ship's dining room during approach to
a sparsely populated frontier planet.

YOUR TASK
On each turn you receive:
  - the full conversation history so far
  - the line the player just chose
  - the current flight phase (cruise / approach / atmo_entry) and orbit progress [0..1]

You must produce 2 or 3 short reply lines from different crew members, then 3
candidate lines the player might choose next.

RULES
- Each crew line: 3-18 words, one sentence (occasionally two very short).
- Stay strictly in character (personas below).
- Rotate who speaks. Mal speaks often but not always. River rarely, and when she
  does it's cryptic and short (5-10 words).
- NEVER have the player speak in your output. Player speaks only via next_player_options.
- Keep subject matter grounded: the job, the ship, crew quirks, banter about this planet.
  Avoid overt show-quote Easter eggs that break immersion; subtle nods are ok.
- Advance the flight phase subtly. At orbit_progress >= 0.85, someone (usually Wash
  or Mal) should reference real entry prep. Set phase="atmo_entry" and continue=false
  when it's time to end the chat and land.
- next_player_options must be 3 distinct tones: one practical, one snarky, one warm/personal.
- Keep lines natural English, not anachronistic. Mild Western drawl only for Mal/Jayne/Kaylee.

CHARACTERS

{characters_block()}

OUTPUT
Call the tool `emit_turn` with the structured result. Do not output prose.
"""


def tool_schema() -> dict:
    """Anthropic tool-use schema. Модель обязана вызвать emit_turn."""
    return {
        "name": "emit_turn",
        "description": (
            "Emit the next round of crew dialogue and three player response options. "
            "The response must match the JSON schema exactly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 3,
                    "description": "Crew reply lines this turn",
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {
                                "type": "string",
                                "enum": CHARACTER_KEYS,
                            },
                            "line": {
                                "type": "string",
                                "minLength": 3,
                                "maxLength": 200,
                            },
                            "emotion": {
                                "type": "string",
                                "enum": EMOTIONS,
                            },
                        },
                        "required": ["speaker", "line", "emotion"],
                        "additionalProperties": False,
                    },
                },
                "next_player_options": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "3 distinct reply options for the player",
                    "items": {
                        "type": "string",
                        "minLength": 3,
                        "maxLength": 100,
                    },
                },
                "phase": {
                    "type": "string",
                    "enum": ["cruise", "approach", "atmo_entry"],
                },
                "continue": {
                    "type": "boolean",
                    "description": (
                        "true if conversation continues, false if it's time to "
                        "transition to the landing cinematic"
                    ),
                },
            },
            "required": ["lines", "next_player_options", "phase", "continue"],
            "additionalProperties": False,
        },
    }


def opener_prompt() -> str:
    """Инструкция для /start — просто первая реплика от Mal + 3 варианта."""
    return (
        "Generate the very first line of the scene. Mal speaks first, a short "
        "opener that sets the mood ('few hours to atmo' vibe). Do NOT produce "
        "other crew lines yet — only Mal's one line, and three player options. "
        "Return it through emit_turn with phase='cruise', continue=true, "
        "and exactly ONE entry in `lines` (Mal)."
    )
