"""
System-prompt и JSON-схема для dialogue server.

Один system prompt, одна схема на структурированный ответ. Подходит и для
Ollama (format=schema), и для Anthropic (tool input_schema).
"""

from characters import CHARACTER_KEYS, characters_block


EMOTIONS = [
    "calm", "gruff", "bright", "dry", "cryptic",
    "warm", "flirty", "amused", "serious", "deadpan",
]


def system_prompt() -> str:
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

STRICT RULES
- OUTPUT MUST BE PURE JSON. No markdown, no code fences, no prose, no <think> tags.
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
- Keep lines natural English. Mild Western drawl only for Mal/Jayne/Kaylee.

VALID SPEAKER KEYS: {", ".join(CHARACTER_KEYS)}
VALID EMOTIONS: {", ".join(EMOTIONS)}
VALID PHASES: cruise, approach, atmo_entry

OUTPUT JSON SHAPE (example, values illustrative):
{{
  "lines": [
    {{"speaker": "Mal",   "line": "Two hours to atmo.",            "emotion": "calm"}},
    {{"speaker": "Jayne", "line": "I'm hungry.",                   "emotion": "gruff"}}
  ],
  "next_player_options": [
    "How's the cargo?",
    "Any chance this one doesn't go sideways?",
    "You hanging in there, Kaylee?"
  ],
  "phase": "cruise",
  "continue": true
}}
Keys MUST be exactly: speaker, line, emotion, next_player_options, phase, continue.
"next_player_options" MUST be an array of 3 strings (not objects).

CHARACTERS

{characters_block()}
"""


def turn_schema() -> dict:
    """JSON Schema ответа. Годится для Ollama format=, и для Anthropic tool input_schema."""
    return {
        "type": "object",
        "properties": {
            "lines": {
                "type": "array",
                "minItems": 2,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {"type": "string", "enum": CHARACTER_KEYS},
                        "line":    {"type": "string", "minLength": 3, "maxLength": 200},
                        "emotion": {"type": "string", "enum": EMOTIONS},
                    },
                    "required": ["speaker", "line", "emotion"],
                    "additionalProperties": False,
                },
            },
            "next_player_options": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string", "minLength": 3, "maxLength": 100},
            },
            "phase": {"type": "string", "enum": ["cruise", "approach", "atmo_entry"]},
            "continue": {"type": "boolean"},
        },
        "required": ["lines", "next_player_options", "phase", "continue"],
        "additionalProperties": False,
    }


def opener_schema() -> dict:
    """Специальная схема для /start — ровно 1 реплика от Mal."""
    s = turn_schema()
    s["properties"]["lines"]["minItems"] = 1
    s["properties"]["lines"]["maxItems"] = 1
    return s


def opener_instruction() -> str:
    return (
        "Generate the VERY FIRST line of the scene. Mal speaks first, a short "
        "opener that sets the mood (a few hours to atmo vibe). Produce EXACTLY "
        "ONE entry in `lines` (speaker=Mal), 3 player options, "
        "phase=cruise, continue=true. Output JSON only."
    )


def turn_instruction() -> str:
    return (
        "Produce the next turn. 2-3 crew lines (different speakers) reacting to "
        "the most recent PLAYER line, then 3 next player options. Output JSON only."
    )
