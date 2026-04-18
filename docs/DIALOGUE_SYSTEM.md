# Диалоговая система

Полная спецификация: как LLM превращается в говорящий экипаж.

---

## Общая логика

1. Игрок видит 3 варианта ответа.
2. Клик → POST на dialogue server.
3. Сервер строит промпт из:
   - system prompt с сеттингом и правилами,
   - персонажными карточками 9 членов команды,
   - историей реплик,
   - текущим выбором игрока,
   - метаданными (фаза полёта, прогресс орбиты).
4. Сервер вызывает Claude с **structured output** (tool-use / JSON Schema).
5. Модель возвращает 2–3 реплики (speaker + line + emotion) + 3 варианта следующего ответа игрока.
6. (Опционально) Сервер дёргает TTS на каждую line, сохраняет mp3, возвращает URL.
7. UE проигрывает по очереди, анимирует говорящего, показывает сабы, в конце — снова показывает кнопки.

---

## Контракт API

### `POST /start`

Открывает новую сессию. Возвращает первое слово Мала и 3 варианта ответа.

Request:
```json
{ "seed": "optional_random_seed" }
```

Response:
```json
{
  "session_id": "sess_3f2a",
  "opener": { "speaker": "Mal", "line": "...", "emotion": "casual", "audio_url": null },
  "next_player_options": [ "...", "...", "..." ],
  "phase": "cruise",
  "orbit_progress": 0.0
}
```

### `POST /turn`

Основной эндпойнт. См. [ARCHITECTURE.md](ARCHITECTURE.md#форматы-данных).

Request:
```json
{
  "session_id": "sess_3f2a",
  "history": [
    {"speaker": "Mal",    "line": "Two hours to atmo."},
    {"speaker": "player", "line": "How's the cargo?"}
  ],
  "player_choice": "How's the cargo?",
  "orbit_progress": 0.35
}
```

Response:
```json
{
  "lines": [
    {"speaker": "Jayne",  "line": "Still there.",            "emotion": "gruff",   "audio_url": null, "duration_ms": 1500},
    {"speaker": "Kaylee", "line": "Strapped her down myself.","emotion": "bright", "audio_url": null, "duration_ms": 2000}
  ],
  "next_player_options": [
    "Anything weird in the manifest?",
    "Tell me about the buyer.",
    "Let's just get planetside."
  ],
  "phase": "cruise",
  "continue": true
}
```

`continue: false` → сервер считает, что разговор можно закрывать (достаточно раундов прошло, фаза перешла в `atmo_entry`). UE в этом случае играет последнюю реплику и запускает посадку.

### `GET /health`

Просто 200 OK. Используется в UE для проверки перед началом.

### `GET /tts/{filename}` (опционально)

Отдаёт mp3 из кеша.

---

## System prompt (shape)

Сервер собирает один большой system prompt:

```
You are a dialogue director for a video game set in the Firefly universe.
The player is a silent passenger / new crew member aboard "Serenity". The crew is
having an informal conversation in the ship's dining room during approach to
a sparsely populated frontier planet.

YOUR TASK
On each turn, you will receive:
  - the full conversation history so far
  - the line the player just chose
  - the phase of the flight (cruise / approach / atmo_entry) and orbit progress [0..1]

You must produce 2 or 3 short reply lines from crew members, then 3 candidate
next lines the player might choose.

RULES
- Each crew line: 3-18 words, max one sentence (occasionally two short).
- Stay in character (personas below).
- Not every crew member speaks every turn. Rotate naturally. Mal speaks often
  but not always. River rarely speaks, and when she does it's cryptic and short.
- Keep subject matter grounded: the job, the ship, crew quirks, banter, this planet.
  No direct Easter eggs that break immersion.
- Advance the flight phase subtly over turns. Around orbit_progress >= 0.85,
  someone (usually Wash or Mal) should reference actual entry prep.
- The player's 3 options must be distinct in tone: one practical, one snarky,
  one personal/warm.
- Return ONLY the structured JSON, no prose.

CHARACTERS
<full character personas from CHARACTERS.md>

RECENT HISTORY
<last 8 turns>
```

Промпт + персоны целиком = ~2500 токенов. Это кешируемо (см. ниже).

---

## Prompt caching

Claude поддерживает prompt caching. Мы кешируем:
- весь system prompt с описанием игры и правилами,
- блок с персонажами,
- всё, что до `RECENT HISTORY`.

Обновляется только история и user message. Это экономит ~70% токенов и в разы ускоряет ответ.

Реализовано в `server.py` через `anthropic_client.messages.create(..., system=[{type: 'text', text: ..., cache_control: {type: 'ephemeral'}}])`.

---

## Structured output

Мы НЕ полагаемся на то, что модель сама вернёт валидный JSON. Используем **tool use** — объявляем tool `emit_turn` со схемой:

```python
tools = [{
  "name": "emit_turn",
  "description": "Emit the next round of crew dialogue and player options.",
  "input_schema": {
    "type": "object",
    "properties": {
      "lines": {
        "type": "array",
        "minItems": 2, "maxItems": 3,
        "items": {
          "type": "object",
          "properties": {
            "speaker": {"type": "string", "enum": ["Mal","Zoe","Wash","Jayne","Kaylee","Inara","Simon","River","Book"]},
            "line":    {"type": "string", "minLength": 3, "maxLength": 200},
            "emotion": {"type": "string", "enum": ["calm","gruff","bright","dry","cryptic","warm","flirty","amused","serious","deadpan"]}
          },
          "required": ["speaker","line","emotion"]
        }
      },
      "next_player_options": {
        "type": "array",
        "minItems": 3, "maxItems": 3,
        "items": {"type": "string", "minLength": 3, "maxLength": 100}
      },
      "phase": {"type": "string", "enum": ["cruise","approach","atmo_entry"]},
      "continue": {"type": "boolean"}
    },
    "required": ["lines","next_player_options","phase","continue"]
  }
}]
```

И форсируем вызов: `tool_choice = {"type": "tool", "name": "emit_turn"}`.

Модель **всегда** возвращает валидный JSON по схеме.

---

## UE side

### `UDialogueClientComponent` (C++)

Actor component, прикреплён к `BP_CabinFlow`.

Публичный API (для Blueprints):

```cpp
UCLASS(ClassGroup=(Firefly), meta=(BlueprintSpawnableComponent))
class FIREFLYUE5_API UDialogueClientComponent : public UActorComponent
{
  GENERATED_BODY()
public:
  // Config
  UPROPERTY(EditAnywhere) FString ServerBaseUrl = TEXT("http://127.0.0.1:8765");

  // Events
  UPROPERTY(BlueprintAssignable) FOnSessionStarted     OnSessionStarted;
  UPROPERTY(BlueprintAssignable) FOnTurnReceived       OnTurnReceived;     // (TArray<FDialogueLine> lines, TArray<FString> options, FString phase, bool bContinue)
  UPROPERTY(BlueprintAssignable) FOnDialogueError      OnDialogueError;

  // Calls
  UFUNCTION(BlueprintCallable) void StartSession();
  UFUNCTION(BlueprintCallable) void SubmitChoice(const FString& Text);

  // State
  UFUNCTION(BlueprintPure) const TArray<FDialogueLine>& GetHistory() const { return History; }
  UFUNCTION(BlueprintPure) float GetOrbitProgress() const { return OrbitProgress; }

private:
  FString SessionId;
  TArray<FDialogueLine> History;
  float   OrbitProgress = 0.0f;

  void SendPost(const FString& Endpoint, const FString& JsonBody, TFunction<void(TSharedPtr<FJsonObject>)> OnSuccess);
};
```

Имплементация — стандартный `FHttpModule::Get().CreateRequest()`, асинхронный. 150 строк C++.

### `BP_CabinFlow` (Blueprint)

Level Blueprint (или отдельный Actor в уровне). Обёртка над DialogueClient:

- `BeginPlay`:
  - `DialogueClient.StartSession`.
  - Регистрируется на `OnTurnReceived`.
- `OnTurnReceived(lines, options, phase, cont)`:
  - Lock HUD (скрыть кнопки).
  - For each line:
    - Pick speaker actor.
    - `SpeakerActor.SpeakLine(line, emotion, audio_url)` — плеер ставит animation montage + звук + сабы.
    - Await end.
  - Advance orbit timeline by (1/N_rounds).
  - If `cont == false` → trigger `TransitionToLanding`.
  - Else → `HUD.ShowOptions(options)`.

- `OnPlayerChooseOption(text)`:
  - `DialogueClient.SubmitChoice(text)`.

- `TransitionToLanding`:
  - Fade to black.
  - Load sublevel `L_Landing`, play `LS_Landing`.

### `WBP_DialogueHUD` (UMG)

Widget с тремя зонами:
1. **Speaker plate** (top-left or bottom-left): имя + портрет.
2. **Subtitle band** (bottom-center): текст с эффектом «печатной машинки».
3. **Options row** (bottom): 3 кнопки, только во время выбора игрока.

Поведение:
- При `OnTurnReceived` — subtitle по одной реплике за раз, переключается по событию от `SpeakerActor`.
- Options скрыты во время воспроизведения, fade-in за 0.3 с после окончания.

### `BP_SeatActor.SpeakLine`

Публичная функция на актёре-на-стуле:

```
SpeakLine(FString Text, FString Emotion, FString AudioUrl)
  1. Pick talk montage by emotion:
       calm/warm   → SitTalk_Neutral
       gruff       → SitTalk_Assertive
       cryptic     → SitTalk_Subtle
       ...
  2. Play montage on head/face (if present).
  3. If AudioUrl: download to Sound Cue, play.
     Else: show subtitle with typewriter timing based on text length.
  4. Broadcast OnLineFinished after montage + audio duration.
```

---

## TTS pipeline (опционально на v0.1)

### Выбор провайдера

| Провайдер | Качество | Цена | Скорость | Разные голоса | Комментарий |
|---|---|---|---|---|---|
| **ElevenLabs** | ★★★★★ | ~$0.30 / 1k chars | 1-2 сек | 1000+ голосов | Лучший выбор для реалистичных голосов |
| **OpenAI TTS** | ★★★☆☆ | $15/1M chars (gpt-4o-mini-tts) | < 1 сек | 6-11 голосов | Дёшево, но голоса похожие |
| **Kokoro** | ★★★☆☆ | Бесплатно | < 1 сек на GPU | ~50 | Локально, лицензионно чистый |
| **XTTS v2** | ★★★★☆ | Бесплатно | 2-3 сек | Voice cloning | Можно клонировать, но качество колеблется |

**Рекомендация:** ElevenLabs для v0.1 показа, Kokoro — если API дорого.

### Voice mapping

В `tools/dialogue_server/characters.py` у каждого персонажа есть поле `voice_id` (для ElevenLabs) и `openai_voice` (fallback). На первый запуск — выберите по голосовой библиотеке ElevenLabs что-то подходящее.

### Кеширование

Ключ: `sha256(f"{provider}|{voice_id}|{line_text}")` → файл `tts_cache/<hash>.mp3`.

Если реплика повторяется (один и тот же диалог, или похожие фразы) — TTS не вызывается, возвращается URL файла.

Размер кеша: при 200 реплик по ~3 сек × 30 KB = 6 MB. Ставим 500 MB limit.

---

## Production checklist

- [ ] Сервер поднимается одной командой.
- [ ] `/health` возвращает 200.
- [ ] `/start` даёт opener.
- [ ] `/turn` на 5 итераций подряд — без ошибок, все реплики валидны.
- [ ] Cache hit rate >0 после 2-го прохода (проверяется по логу).
- [ ] UE получает ответ за <3 сек (без TTS) и <6 сек (с TTS).
- [ ] При разрыве соединения — UE показывает fallback-реплику и продолжает.
