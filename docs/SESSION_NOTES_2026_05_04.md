# Session notes — 2026-05-03/04 (compact handoff)

Спасательный круг перед `/compact`. Длинная сессия с архитектурными разворотами, важно зафиксировать.

## TL;DR где мы

- **8 demo LSs** работают (committed `b9b1331`). Каждый в `Content/Cinematics/LS_<Char>_<line_id>` с Possessable binding на нужный character actor + Audio + Skeletal Animation track на Face. **Воспроизводятся через Sequencer Play и в Simulate runtime** через AutoPlay.
- **BP_DialogueManager** существует с **POC TestPlay** event'ом (Call In Editor) — нажимаешь кнопку → spawnится LevelSequenceActor + Player.Play() → Mal говорит. Это проверено.
- **Pivot принят:** не делаем Map+8events для статического демо, идём сразу на **dynamic generator** (LLM /turn → on-demand pipeline → on-demand LS → BP_DialogueManager Play).
- **9 Mixamo sitting анимаций** скачаны в `C:\Users\balal\Downloads\firefly_anims\`, staged для будущего import + retarget (Step 1b).
- **Не успел:** написать Python для **auto-gen Possessable LS** — это next-step главная блокирующая задача для динамики.

## Коммиты этой сессии

```
fc6aa48  Step 6B: MetaHuman Audio-Driven Face — pipeline validated, body-attach unresolved
e184b7f  Step 6B-fix: lipsync on full Mal works via Sequencer + Track → Animation
37d99df  Step 6C: headless WAV → MetaHuman face AnimSequence pipeline
b9b1331  Checkpoint: 8 per-line LSs ready for runtime dialogue playback
```

## Архитектурные решения (важно для контекста)

### Какие подходы отклонены (и почему)

**1. Custom Face_AnimBP Slot (Step 6D-1 — abandoned)**
- Forkнули Face_AnimBP → ABP_FireflyFace, добавили DefaultSlot, попробовали `PlaySlotAnimationAsDynamicMontage`.
- **Не работает**: slot at full weight перетирает master-pose link к head bone Body → Face mesh отделяется.
- Ответ от MetaHuman архитектуры: face-only slot injection не предусмотрен. Sequencer "+ Track → Animation" — единственный stock-UE 5.7 path.
- Артефакты остались в репо как experimental: `ABP_FireflyFace.uasset`, `duplicate_face_animbp.py`, `reexport_no_head_movement.py`, `A_Mal_Demo_Lipsync_NoHead.uasset`. **Не использовать**.
- Подробности: `docs/runbooks/05_metahuman_audio_driven_face.md`.

**2. RMHLipSync plugin (paid, Path C — declined)**
- Плагин Georgy Treshchev на Fab (~$60-160 total с Runtime Audio Importer) даёт **runtime** lipsync через 81 facial control + AnimGraph node `Blend Realistic MetaHuman Lip Sync`.
- Архитектурно идеально подошёл бы (real-time из streaming PCM) — без pre-baked LS, без offline pipeline.
- **Декcлайн причина**: проект не настолько серьёзный + latency не критична. Платить $60-160 не оправдано. Запомнено как опция если scope расширится.
- Конспект исследования (`docs.georgy.dev`) в этой же сессии — найди в transcript.

**3. Auto-gen Spawnable LS через Epic API (Step 6C-extended attempt 1 — abandoned)**
- Pipeline пытался создать LS с `target_meta_human_class = BP_Mal` через `MetaHumanPerformanceExportUtils.export_level_sequence` → создавал **Spawnable BP_Mal**.
- **Не работает в нашей сцене**: Spawnable Mal требует ~4.5 GB MetaHuman текстур в memory pool, у проекта budget ~3.2 GB. Mesh не материализовался, audio играл а Mal не появлялся.
- В коде revert'нуто, generated артефакты в `.gitignore`d папке `Generated/`.

### Какой подход рабочий (Path B — pre-baked Possessable LS)

```
WAV (TTS из dialogue server, edge-tts, 22050 Hz mono 16-bit)
  ↓
firefly_face_pipeline.py (UE-Cmd headless, ~45 сек/реплика)
  ↓
SoundWave + MetaHumanPerformance + AnimSequence
  (в /Game/Audio/Dialogue/Generated/<char>/<line_id>/)
  ↓
Level Sequence (Possessable binding на Mal_MetaHuman/BP_Zoe/BP_Wash/BP_Inara
  + Audio track + Skeletal Animation track на Face component)
  ↓
BP_DialogueManager: spawn LevelSequenceActor + Play() → character говорит
```

**Подтверждённый Sequencer recipe (Step 6B-fix):**
- Possessable LS, не Spawnable
- На Face подтреке: **`+ Track → Animation`** через menu (НЕ drag-drop, НЕ Control Rig track)
- AutoSize sections под длину контента
- Playback Range подогнать под секции
- Запуск через Sequencer Play **или** AutoPlay+Simulate **или** runtime `ULevelSequencePlayer.Play()`

## Состояние проекта прямо сейчас

### Сцена `L_SerenityCabin`
4 MetaHuman'а на канонических позициях (см. `docs/SCENES.md`):
- **Mal_MetaHuman** at (-220, 10, 0), Yaw=-90° — instance class BP_Mal (имя в Outliner ≠ имя класса)
- **BP_Zoe** at (-60, -90, 0), Yaw=0°
- **BP_Wash** at (-60, 110, 0), Yaw=180°
- **BP_Inara** at (100, 110, 0), Yaw=180°

Все используют **общий ABP_Crew** через MetaHuman Live Retarget.

### `LS_Test_Mal_Lipsync` (Auto Play OFF)
Изначальный LS-template для manual creation остальных. Auto Play отключён, чтобы при PIE не запускался без команды.

### `BP_DialogueManager` (Content/Crew/Blueprints/)
- Variable: `LSToPlay` (Level Sequence Object Reference, default = LS_Mal_intro_atmo)
- Custom Event `TestPlay` с Call In Editor flag
- Логика: `TestPlay → CreateLevelSequencePlayer(LSToPlay) → Play()`
- Размещён в L_SerenityCabin как actor.
- **Test Play** кнопка в Details — нажми, Mal заговорит. **Подтверждено работает**.
- Spawned LevelSequenceActor'ы НЕ чистятся (накапливаются в Outliner). Нужен cleanup через `OnFinished` delegate (TODO).

### `firefly_face_pipeline.py` (UnrealProject/Content/Python/)
- Headless UE-Cmd Python.
- Принимает env vars: `FIREFLY_WAV`, `FIREFLY_CHAR`, `FIREFLY_LINE_ID`, `FIREFLY_OVERWRITE`.
- Выход: SoundWave + Performance + AnimSequence (без LS — auto-gen LS отказался работать через Spawnable).
- Запуск: `scripts/process_face_audio.bat <wav_path> <Mal|Zoe|Wash|Inara> [line_id]`.
- ~45 сек/реплика (UE startup + 14 сек Process + I/O).
- **Не модифицирован для Possessable LS** — это next-task.

### `tools/dialogue_server/generate_demo_lines.py`
Утилита генерации demo WAV через `EdgeTTSBackend` для 8 фиксированных реплик. Использовалась для bootstrapping.

## 8 демо реплик — артефакты в репо

```
/Game/Audio/Dialogue/Generated/Mal/intro_atmo/      (intro_atmo.uasset, MHP_intro_atmo, A_Mal_intro_atmo_Lipsync)
/Game/Audio/Dialogue/Generated/Mal/orders/          (orders, MHP_orders, A_Mal_orders_Lipsync)
/Game/Audio/Dialogue/Generated/Zoe/status/          (status, MHP_status, A_Zoe_status_Lipsync, +тестовые Zoe_status_long, Zoe_status_minute)
/Game/Audio/Dialogue/Generated/Zoe/cargo/           (cargo, ...)
/Game/Audio/Dialogue/Generated/Wash/vote/           (vote, ...)
/Game/Audio/Dialogue/Generated/Wash/dramatic/       (dramatic, ...)
/Game/Audio/Dialogue/Generated/Inara/sinclair/      (sinclair, ...)
/Game/Audio/Dialogue/Generated/Inara/surprise/      (surprise, ...)

/Game/Cinematics/LS_Mal_intro_atmo, LS_Mal_orders, LS_Zoe_status, LS_Zoe_cargo,
                 LS_Wash_vote, LS_Wash_dramatic, LS_Inara_sinclair, LS_Inara_surprise
```

**Generated/ папка в `.gitignore`** — assets регенерятся из source WAV.
**LSы в Cinematics/ закоммичены** (~1.6 MB каждый).

## Важные UE 5.7 gotchas (запомнены кровью)

1. **Sequencer "+ Track → Animation" работает, slot system нет** — для face injection.
2. **Spawnable MetaHuman = ~4.5 GB textures memory budget overshoot** в нашем проекте. Используй Possessable.
3. **`enable_head_movement=False`** в pipeline — без этого AnimSequence имеет head bone translations, через slot ломает Face attachment. (Через Sequencer track не страшно.)
4. **`.bat` файлы — pure ASCII**, никакого Cyrillic/em-dash в комментариях. CMD ломается.
5. **UE-Cmd на Windows криво форвардит quoted args через `-script="..."`** — env vars обходят это.
6. **PlaySlotAnimationAsDynamicMontage с custom slot** — slot full weight перетирает Face master-pose link → отрыв головы. Не использовать для face.
7. **Asset Search в UE 5.7** иногда не находит ассеты по имени из-за registry задержки. Workaround: подождать, или Refresh.
8. **Mixamo soundwave naming**: pipeline сохраняет `intro_atmo` (без префикса character'а), потому что `<character>_<stem>` это для AnimSequence (`A_Mal_intro_atmo_Lipsync`).

## PIE crash on Stop (low priority issue)

UE крашится при `Stop` в PIE. Точная причина не диагностирована. Подозрение — конфликт shutdown между HTTP клиентом `BP_FireflyDialogueFlow0` actor (зовёт `/start`) и audio engine. **Workaround**: использовать **Simulate** (Alt+S) вместо PIE для тестирования lipsync.

## Что ДЕЛАТЬ дальше (приоритет)

### 1. Python pipeline → auto-gen Possessable LS (главный блокер)
Расширить `firefly_face_pipeline.py`:
- Загружать `L_SerenityCabin` в headless UE
- Найти actor по имени (`Mal_MetaHuman`, `BP_Zoe`, `BP_Wash`, `BP_Inara`)
- Программно создать LevelSequence asset
- Добавить **Possessable binding** на actor через `MovieSceneBindingProxy.add_possessable_from_actor` (или похожий API)
- Добавить sub-binding на Face component
- На Face binding добавить `MovieSceneSkeletalAnimationTrack` + section с AnimSequence
- На root sequence добавить `MovieSceneAudioTrack` + section с SoundWave
- Set Playback Range = section length
- Save asset как `LS_<character>_<line_id>` в `/Game/Audio/Dialogue/Generated/<char>/<line_id>/`

**Ссылки на исследование**:
- Epic example: `{UE 5.7}/Engine/Plugins/MetaHuman/MetaHumanAnimator/Content/Python/export_performance.py` — там `run_meta_human_level_sequence_export` (Spawnable вариант, но API для Sections / Tracks полезен как reference).
- UE Python API: `unreal.LevelSequenceFactoryNew`, `unreal.MovieSceneAudioTrack`, `unreal.MovieSceneSkeletalAnimationTrack`, `unreal.MovieSceneBindingProxy`.

### 2. BP_DialogueManager → universal PlayLine (юзерская задача)
- Заменить `LSToPlay` variable + TestPlay на:
  - Function `PlayLine(speaker String, line_id String)` принимающую параметры
  - Внутри: построить path `/Game/Audio/Dialogue/Generated/<speaker>/<line_id>/LS_<speaker>_<line_id>` → `Load Asset Blocking` → spawn LevelSequenceActor → Play
  - Добавить **`IsSpeaking=true` toggle** на Body AnimInstance speaker'а перед Play (чтобы тело анимировалось через `Sitting_Talking_Manny` state в ABP_Crew)
  - Bind `OnFinished` → `IsSpeaking=false` + cleanup spawned actor
- Custom Event'ы для тестирования с Call In Editor (или один универсальный `TestPlayLine(LineKey)` со String параметром)

### 3. HTTP integration /turn → BP_DialogueManager
- Существует actor **`FireflyDialogueFlow`** в L_SerenityCabin (зовёт `/start`). Расширить:
- После `/turn` response → парсить JSON → для каждой реплики вызвать `BP_DialogueManager.PlayLine(speaker, line_id)`
- Reference: dialogue server `tools/dialogue_server/server.py` уже работает, в `prompts.py` есть JSON schema response

### 4. Mixamo retarget (юзерская задача, не блокер)
- Импортировать 9 FBX из `C:\Users\balal\Downloads\firefly_anims\` в `Content/Crew/Animation/Raw/Mixamo/`
- Retarget каждую через IK Retargeter (runbook `01_mixamo_to_ue_mannequin_retarget.md`) → создать `Sitting_*_Manny` ассеты
- Добавить в ABP_Crew **state Talking** через **Random Sequence Player** ноду — body будет рандомно выбирать жест на каждый цикл диалога

## Файлы важные для контекста

- `docs/runbooks/05_metahuman_audio_driven_face.md` — main руководство по lipsync архитектуре + gotcha'и
- `docs/runbooks/01_mixamo_to_ue_mannequin_retarget.md` — для Mixamo retarget
- `docs/runbooks/03_abp_crew_idle_talking_state_machine.md` — для интеграции Mixamo вариантов в ABP_Crew
- `UnrealProject/Content/Python/firefly_face_pipeline.py` — main pipeline
- `scripts/process_face_audio.bat` — wrapper
- `tools/dialogue_server/generate_demo_lines.py` — TTS batch helper
- `tools/dialogue_server/server.py` — dialogue server (FastAPI + Ollama + edge-tts)
- `tools/dialogue_server/prompts.py` — system prompt + JSON schema

## Если что-то пошло не так

- **PIE crash** → используй Simulate (Alt+S)
- **UE-Cmd headless занят** → проверь не открыт ли editor на тот же uproject
- **Mixamo download через chrome plugin** → залогинен в Adobe ID, browser tab id 396982442 в Work laptop
- **Generated/ папка в .gitignore** — не добавляй её в коммиты руками
- **Spawnable Mal в LS** → плохой путь, используй Possessable
