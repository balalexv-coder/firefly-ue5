# 05. MetaHuman Audio-Driven Face Animation — pipeline и gotcha

**Дата:** 2026-05-03. **UE версия:** 5.7.4. **MetaHuman plugin:** включён через Edit → Plugins → "MetaHuman".

## Цель

Озвучка персонажа (WAV из dialogue server) → автоматический lipsync на лице MetaHuman без записи MoCap, без NVIDIA Audio2Face, без облачных сервисов. Использует встроенную в UE 5.5+ фичу **MetaHuman Performance: Audio Input**.

Pipeline:

```
TTS (edge-tts, 22050 Hz mono 16-bit WAV)
  → импорт в Content/Audio/Dialogue/Test/ как SoundWave
  → MetaHuman Performance asset (Input Type = Audio)
  → Process → 260 face curves (CTRL_expressions_*, jaw, mouth)
  → Export Animation → AnimSequence на Face_Archetype_Skeleton
  → проигрывание на Mal_MetaHuman.Face через Sequencer / runtime
```

## Статус (Step 6B)

| Этап | Статус |
|---|---|
| WAV генерация (`tts.py output_format=wav`) | ✅ closed |
| Импорт WAV в UE как SoundWave | ✅ closed |
| Создание MetaHuman Performance asset | ✅ closed |
| Process → curves сгенерированы | ✅ closed (260 curves подтверждено в Persona) |
| Export Animation Sequence | ✅ closed (`A_Mal_Demo_Lipsync` на Face_Archetype) |
| Воспроизведение в Persona standalone | ✅ closed (рот/брови двигаются) |
| **Воспроизведение на полном Mal'е (с телом) в уровне через Sequencer** | ✅ closed (см. "Solution" ниже) |

## Solution — `+ Track → Animation` на Face компоненте

**Корректный workflow подтверждён:**

1. Создать Level Sequence (`LS_*`) с возможностью посадки актора и аудио-трека.
2. В Sequencer добавить актора (Mal_MetaHuman) — Possessable достаточно (Spawnable не требуется).
3. Развернуть актор → найти подтрек **Face**.
4. На строке **Face** нажать **`+`** (кнопка "Track") → подменю → выбрать **Animation** → из списка ассетов выбрать `A_*_Lipsync` AnimSequence.
5. На Audio track добавить соответствующий SoundWave (`mal_demo_long`).
6. Жать **Play в Sequencer** (треугольник в нижней панели Sequencer окна, не главный editor Play).

В этом сетапе:
- Face Animation Mode остаётся `Use Animation Blueprint`, Anim Class = `Face_AnimBP_C` (стандарт MetaHuman'а).
- Face привязан к Body head bone (как обычно), голова не отделяется.
- Skeletal Animation секция Sequencer'а инжектируется поверх AnimBP — curves достигают Face_PostProcess_AnimBP и применяются к мешу.

## Что НЕ работает / тупик'и (для будущего)

Чтобы не наступить повторно:

| Подход | Результат |
|---|---|
| Override Animation Mode на компоненте Face → Use Animation Asset, Anim to Play = `A_*_Lipsync` | Lipsync **играет**, но голова **отделяется от тела** (Face теряет master-pose link к Body head bone). |
| `+ Track → Control Rig` или авто-добавление Control Rig'а при drag-drop AnimSequence на Face | Перехватывает Face controls — curves не доходят до меша. Удалять Control Rig трек. |
| Drag-drop AnimSequence из Content Browser на строку Face | Часто промахивается и кидается в parent (Mal_MetaHuman), а не в Face. Использовать **`+ Track → Animation`** через menu — стабильнее. |
| Editor Mode = "Animation Mode" во время Play | Может ложить Control Rig override на скелет. Использовать **Selection Mode** во время Sequencer Play. |
| PIE (Alt+P / главный Play в редакторе) для проверки lipsync | Спавнит player pawn → камера улетает на Player Start, актор в level вне фокуса. Использовать **Sequencer Play** (треугольник в нижней панели Sequencer). |

## Step-by-step (что закрыто)

### 1. Включить MetaHuman plugin
- **Edit → Plugins** → поиск `MetaHuman` → включить плагин **"MetaHuman"** (не "MetaHuman SDK", это legacy).
- Перезапустить редактор.

### 2. Сгенерировать WAV (не MP3)
В `tools/dialogue_server/`:

```python
from tts import EdgeTTSBackend
backend = EdgeTTSBackend(output_format="wav")  # или TTS_OUTPUT_FORMAT=wav в env
wav = backend.synthesize(text="...", character_key="Mal", output_dir=Path("./out"))
# → 22050 Hz mono 16-bit PCM
```

### 3. Импортировать WAV в Content
Скопировать `.wav` в `UnrealProject/Content/Audio/Dialogue/Test/` (или drag&drop в Content Browser). UE auto-import создаёт `SoundWave` ассет.

### 4. Создать MetaHuman Performance asset
- Content Browser → правый клик в пустоте → **MetaHuman → MetaHuman Performance**.
- Имя: `MHP_<character>_<line>` (напр. `MHP_Mal_Demo`).
- Открывается редактор Performance (в окне сверху menu bar появляется **MetaHuman Animator**).

### 5. Настройки Performance
В Details панели:
- **Data → Input Type:** `Audio`
- **Audio:** drag `SoundWave` ассет в это поле.
- **Visualization → Control Rig:** опционально (для preview в редакторе; не нужно для генерации curves).

### 6. Process
Кнопка **Process** на верхней панели редактора Performance. Время: ~30 сек на 16-секундный WAV.

После — на тайм-лайне внизу появятся frames с данными.

### 7. Export Animation
Кнопка **Export Animation** на верхней панели. Сохранить как `A_<character>_<line>_Lipsync` рядом с Performance ассетом.

Skeleton автоматически выставляется в `Face_Archetype_Skeleton` (стандартный MetaHuman face skeleton).

### 8. Verify в Persona
Двойной клик на `A_*_Lipsync` → откроется Animation Editor. Жми Play. Должны:
- Двигаться кости/curves (видно на превью-меше: jaw, mouth, brow shapes).
- Внизу в Curves секции отображаться ~260 curves (CTRL_expressions_*, ...).
- Виден баннер: "Post process Animation Blueprint 'Face_PostProcess_AnimBP' is running" — это норма.

## Open question — runtime-режим для dialogue server

Текущее решение — **Sequencer-based**, рассчитано на **pre-baked Level Sequence**: для каждой реплики экипажа нужен свой `LS_<character>_<line>` с привязанным `A_*_Lipsync` и SoundWave.

Для **dynamic dialogue** (когда реплика приходит от LLM в runtime через `/turn` endpoint) нужен другой механизм:

| Подход | Идея |
|---|---|
| **Runtime Sequencer construction** | Blueprint actor получает `audio_url` + path к AnimSequence, на лету собирает Level Sequence и проигрывает через Level Sequence Player. |
| **Anim Slot в Face_AnimBP_C fork'е** | Duplicate Face_AnimBP, добавить DefaultSlot, в BP-actor вызывать `PlaySlotAnimation` с динамически загруженным AnimSequence. Минус — поддержка форка AnimBP. |
| **Linked Anim Graph** | Подключать sub-AnimBP с Animation Sequence Player, динамически меняя AnimSequence через AnimGraph переменную. |

Решается в Step 6D (UE runtime playback из dialogue server'а).

## Артефакты в репо

- `UnrealProject/Content/Audio/Dialogue/Test/mal_demo_long.wav` — source WAV (16 sec, "Two hours to atmo, folks…")
- `UnrealProject/Content/Audio/Dialogue/Test/mal_demo_long.uasset` — SoundWave
- `UnrealProject/Content/Audio/Dialogue/Test/MHP_Mal_Demo.uasset` — MetaHuman Performance
- `UnrealProject/Content/Audio/Dialogue/Test/A_Mal_Demo_Lipsync.uasset` — exported AnimSequence (260 curves)
- `UnrealProject/Content/Cinematics/LS_Test_Mal_Lipsync.uasset` — рабочий Level Sequence: Audio + Face/Animation tracks, lipsync воспроизводится через Sequencer Play.

## Ссылки

- [MetaHuman Audio-Driven Animation — official docs](https://dev.epicgames.com/documentation/en-us/metahuman/audio-driven-animation)
- [MetaHuman Performance Asset — official docs](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-performance-asset)
- [MetaHuman 5.7 Release — feature list](https://www.metahuman.com/releases/metahuman-5-7-is-now-available)
- [UE Forum — Can't create MetaHuman Performance asset (plugin enable)](https://forums.unrealengine.com/t/cant-create-metahuman-performance-asset-in-5-5-0/2132487/2)
- [Community tutorial — Adding Expressive Performance to MetaHuman Audio Face Animations UE 5.5](https://forums.unrealengine.com/t/community-tutorial-adding-expressive-performance-to-metahuman-audio-face-animations-in-unreal-engine-5-5/2296328)
