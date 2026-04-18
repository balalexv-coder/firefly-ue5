# Архитектура

Схема взаимодействия подсистем. Один диалог — один раунд.

```
┌─────────────────────────────────────────────────────────────────┐
│                         UNREAL ENGINE 5.7                       │
│                                                                 │
│  ┌──────────────────┐      ┌──────────────────────────────┐    │
│  │   Level:         │      │   UMG: WBP_DialogueHUD       │    │
│  │   L_Serenity     │◄─────┤   - speaker name             │    │
│  │   Cabin          │      │   - line text (typewriter)   │    │
│  │                  │      │   - 3 player options         │    │
│  │ ┌──────────────┐ │      └──────────▲───────────────────┘    │
│  │ │ BP_SeatActor │ │                 │ binds to events        │
│  │ │ × 9 (crew)   │ │      ┌──────────┴───────────────────┐    │
│  │ └──────┬───────┘ │      │ UDialogueClientComponent     │    │
│  │        │play mon │      │  - ConversationHistory       │    │
│  │ ┌──────▼───────┐ │      │  - Pending state             │    │
│  │ │ ABP_Seated   │◄┼──────┤  - RequestNextTurn()         │    │
│  │ │ Crew         │ │      │  - OnTurnReceived event      │    │
│  │ └──────────────┘ │      └──────────┬───────────────────┘    │
│  │                  │                 │ HTTP POST              │
│  │ ┌──────────────┐ │                 │                        │
│  │ │ Render       │ │                 │                        │
│  │ │ Target       │ │                 │                        │
│  │ │ (Orbit View) │ │                 │                        │
│  │ └──────┬───────┘ │                 │                        │
│  │        │         │                 │                        │
│  └────────┼─────────┘                 │                        │
│           │                           │                        │
│  ┌────────▼─────────┐                 │                        │
│  │ L_OrbitalScene   │                 │                        │
│  │ (sublevel)       │                 │                        │
│  │  - Serenity mesh │                 │                        │
│  │  - Planet        │                 │                        │
│  │  - SceneCapture  │                 │                        │
│  └──────────────────┘                 │                        │
└───────────────────────────────────────┼────────────────────────┘
                                        │
                                   HTTP │ POST /turn {history, player_choice}
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DIALOGUE SERVER (Python)                   │
│                                                                 │
│   FastAPI  (uvicorn, port 8765)                                 │
│     │                                                           │
│     ├── /turn           — generate next 2-3 lines + options     │
│     ├── /start          — open a session, return opener lines   │
│     ├── /tts?line=...   — optional: TTS proxy, returns mp3 url  │
│     └── /health                                                 │
│                                                                 │
│   Pipeline per /turn:                                           │
│     1. build prompt from characters.py + history                │
│     2. call Claude (claude-opus-4-7 with [1m] context)          │
│     3. parse structured output → TurnResponse model             │
│     4. (optional) request TTS for each line, cache              │
│     5. return JSON                                              │
└─────────────────────────────────────────────────────────────────┘
                                        │
                                        │ TTS API (optional)
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TTS PROVIDER (external)                     │
│   ElevenLabs / OpenAI / local Kokoro                            │
│   returns WAV/MP3 URL or bytes                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Почему внешний Python-сервер, а не всё в UE

1. **Итерация.** Менять промпты и логику разговора в Python быстрее, чем пересобирать UE.
2. **Секреты.** API-ключ Claude не зашит в сборку.
3. **Переносимость.** Тот же сервер можно переиспользовать для других проектов или CLI-тестов.
4. **Отладка.** Запросы и ответы логируются в JSON-файлы.

Недостаток: один лишний процесс. Решается — сервер стартует автоматически вместе с UE в dev-режиме (через `pre_compile_steps.bat` или `.uproject` launcher скрипт) или вручную.

## Форматы данных

### Запрос `POST /turn`
```json
{
  "session_id": "sess_abc123",
  "history": [
    {"speaker": "Mal",   "line": "We've got about two hours 'til atmo."},
    {"speaker": "player","line": "How's the cargo?"}
  ],
  "player_choice": "How's the cargo?",
  "orbit_progress": 0.35
}
```

### Ответ
```json
{
  "lines": [
    {"speaker": "Jayne",  "line": "Still there. Ain't walkin' off.",  "emotion": "gruff",  "audio_url": "/tts/cache/xxx.mp3", "duration_ms": 1800},
    {"speaker": "Kaylee", "line": "Strapped it down myself, cap'n!", "emotion": "bright",  "audio_url": "/tts/cache/yyy.mp3", "duration_ms": 2100}
  ],
  "next_player_options": [
    "Any surprises in the manifest?",
    "What do we know about the contact?",
    "Just get us down in one piece."
  ],
  "phase": "cruise",
  "continue": true
}
```

## Состояние разговора

- **UE side:** `UDialogueClientComponent` хранит `TArray<FDialogueTurn>` — полную историю текущей сессии. Серверу передаёт hash/ID сессии и добавочные реплики.
- **Server side:** по `session_id` кеширует системный промпт и последние N реплик (для уменьшения токенов). Если сервер перезапущен — UE пришлёт полную историю, сервер восстановит контекст.

## Flow-контроллер (Level Blueprint `BP_CabinFlow`)

```
BeginPlay
  ├─ Seat all 9 crew actors
  ├─ Start orbit sequence at progress=0
  └─ DialogueClient.StartSession()
         └─ server returns opener (Mal speaks + 3 options)
              └─ HUD displays

PlayerChooseOption(index)
  ├─ HUD hides options, shows "..."
  ├─ DialogueClient.SubmitAnswer(text)
  │     └─ server returns lines + next options
  ├─ foreach line:
  │     ├─ camera cut to speaker
  │     ├─ actor plays talk montage
  │     ├─ play audio (if any), show subtitle
  │     └─ wait duration
  └─ HUD shows new options
      advance orbit_progress by 0.1

orbit_progress >= 0.9
  └─ stop accepting new options, play final exchange
       └─ OpenLevel(L_Landing)
```

## Модули UE, которые мы пишем

| Модуль | Где | Язык | Назначение |
|---|---|---|---|
| `DialogueClientComponent` | `Source/FireflyUE5/Dialogue/` | C++ | HTTP-клиент и state |
| `SeatActor` | `Source/FireflyUE5/Crew/` | C++ | снап MetaHuman в кресло |
| `ABP_SeatedCrew` | `Content/Crew/Animation/` | Blueprint | AnimBP для сидячих поз |
| `WBP_DialogueHUD` | `Content/UI/` | UMG | HUD с кнопками |
| `BP_CabinFlow` | `Content/Levels/Cabin/` | Blueprint | мастер-логика сцены |
| `LS_Landing` | `Content/Cinematics/` | Sequencer | синематик посадки |
| `BP_TownNPC` | `Content/Town/NPC/` | Blueprint | простой NPC с behavior tree |

## Dependencies graph

```
DialogueClientComponent ───┬──► HTTP Module (UE core)
                           └──► JsonObjectConverter (UE core)

SeatActor ──► SkeletalMesh (MetaHuman)
          └─► AnimInstance (ABP_SeatedCrew)

BP_CabinFlow ──► DialogueClientComponent
              └► Array<SeatActor>
              └► LevelSequenceActor (orbit + landing)
              └► WBP_DialogueHUD
```
