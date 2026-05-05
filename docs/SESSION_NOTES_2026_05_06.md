# Session notes — 2026-05-05/06 (compact handoff)

Длинная сессия — массовый рефакторинг BP→C++ + интеграция LLM dialogue loop через UE Python Remote Execution. До компакта.

## TL;DR где мы

- **Step 6D-2 done** (committed `aa9829d`): BP_DialogueManager EventGraph целиком переписан в C++ `ADialogueManager`. Один метод `PlayLine(speaker, line_id)` загружает LS по convention path, вызывает `IsSpeaking=true` через FBoolProperty reflection (с trim для whitespace в BP variable names), spawn LSPlayer + Bind OnFinished + Play, на финише cleanup spawned actor + IsSpeaking=false.
- **Step 6D-2 cleanup** (committed `a929309`): SpawnedLSActor variable, Destroy Actor on OnLineFinished — Outliner больше не засоряется.
- **Step 6D-3 done** (committed `1cbad59`): полный LLM dialogue loop работает end-to-end. PIE → `/start` → LLM opener → server из demo pool назначает `line_id` → C++ FlowActor → `ADialogueManager.PlayLine` → pre-gen LS играется с lipsync + gestures + cleanup. `/turn` цикл работает.

## Working architecture

```
UE Editor (Python Remote Execution enabled)
   │
   │ PIE start
   ▼
[FireflyDialogueFlow C++ actor] ──HTTP──▶ [Python dialogue server :8765]
   │  ▲                                   │  ▲
   │  │ /turn response                    │  │ (LLM, TTS)
   │  │ {lines: [{speaker, line, line_id, ...}]}
   │  │                                   │
   │  └─── server demo pool (8 lines):    │
   │       Mal: intro_atmo, orders         │
   │       Zoe: status, cargo              │
   │       Wash: vote, dramatic            │
   │       Inara: sinclair, surprise       │
   │                                       │
   ▼ (per line in pending queue)
[ADialogueManager.PlayLine(speaker, line_id)]
   │
   │ FSoftObjectPath("/Game/Audio/Dialogue/Generated/<speaker>/<line_id>/LS_<speaker>_<line_id>").TryLoad()
   ▼
[ULevelSequencePlayer + ALevelSequenceActor spawn + Play]
   │
   │ Set IsSpeaking=true on speaker.Body.AnimInstance
   │   (find via UnrealEditorSubsystem.get_editor_world + GameplayStatics)
   │
   │ Bind OnFinished delegate
   ▼
[LS plays — lipsync + Random Sequence Player gestures]
   │
   │ OnFinished fires
   ▼
[Set IsSpeaking=false → smooth Talking→Idle transition (0.6s)]
[Destroy SpawnedLSActor — Outliner clean]
[Broadcast OnLineFinished delegate → FlowActor.PlayNextLineOrShowOptions]
   │
   ▼ next line OR options shown to player
```

## Pre-generated LS assets

8 LSes lying in `/Game/Audio/Dialogue/Generated/<Speaker>/<line_id>/`:
```
Mal/intro_atmo,  Mal/orders
Zoe/status,      Zoe/cargo
Wash/vote,       Wash/dramatic
Inara/sinclair,  Inara/surprise
```

⚠️ **Folder is `.gitignore`d**. Regenerate via:
```bash
cd tools/dialogue_server
.venv/Scripts/python.exe pregenerate_demo_assets.py
```
(UE Editor must be open, Python Remote Execution enabled, **no PIE running**.)

## Architecture pivots/lessons

### Pivot: BP → C++ for dialogue manager (committed aa9829d)
- BP_DialogueManager EventGraph был 30+ нод с brittle Cast logic, multiple debugging sessions потрачены
- Переписан в `ADialogueManager` (~150 строк self-documenting C++)
- BP_DialogueManager теперь — пустой child class только для Speakers map в Details
- **Урок**: C++ кратно быстрее по итерации когда пишет агент vs визуальная сборка нод вручную

### Pivot: UE Python Remote Execution (committed 1cbad59)
- Изначальный план: server запускает pipeline subprocess (UnrealEditor-Cmd.exe). **Не работает** — UE-Cmd конфликтует с editor на project lock.
- Новый подход: server использует UE Python Remote Execution → отправляет команды в **открытый UE Editor**, pipeline runs in editor's Python interpreter
- Setup: `Project Settings → Plugins → Python → Enable Remote Execution = True`
  - Также `bRemoteExecution=True` в `Config/DefaultEngine.ini` под `[/Script/PythonScriptPlugin.PythonScriptPluginSettings]`
- Discovery: multicast UDP `239.0.0.1:6766`, client bind `0.0.0.0`, TTL=1
- Command mode: **`MODE_EXEC_FILE`** для multi-line statements, не `MODE_EXEC_STATEMENT`
- Module reloading: `sys.modules.pop('firefly_face_pipeline', None)` перед import — `importlib.reload` ненадёжен в UE Python

### Pivot: on-demand pipeline → pre-gen pool
- Изначальный план (Step 6D-3 attempt 1): server при каждом `/start`/`/turn` вызывает pipeline → генерит свежий LS под текст LLM
- **Проблемы**:
  1. `MetaHumanPerformance.Process()` race condition при rapid back-to-back invocations — только 1-я реплика проходит export, остальные fail на `export_animation_sequence returned None` (Frame range 1)
  2. `unreal.EditorLoadingAndSavingUtils.load_map(L_SerenityCabin)` во время PIE убивает play session (load editor world unloads PIE)
  3. `EditorActorSubsystem.get_all_level_actors()` во время PIE возвращает empty list в remote exec context
- Workarounds applied:
  1. Pre-gen с 3-сек паузой между вызовами — successful 8/8
  2. `_ensure_level_loaded` теперь NO-OP, не вызывает load_map (актёры уже в editor world)
  3. `_find_actor_by_label` использует `UnrealEditorSubsystem.get_editor_world() + GameplayStatics.get_all_actors_of_class` (надёжнее в PIE)
- **Demo pool decision**: 8 pre-gen LSes, server циклит per-session. Audio attached к фиксированным line_ids (intro_atmo etc), text от LLM. Несовпадение текст/аудио для демо приемлемо.

### True on-demand generation (Step 6D-4 — deferred)
Не реализовано. Нужно одно из:
- Отдельный UE-Cmd процесс per line (медленно, требует UE Editor закрытым)
- Fix Performance Process race condition в Epic API (нет documented способа)
- Sleep между вызовами в /start handler (работает но добавляет 3-15с latency на /turn)

## Что ВРЕМЕННО не работает

1. **Welcome line on BeginPlay** — `bPlayWelcomeOnBeginPlay = false` default, нужен rebuild C++. Не критично (LLM opener из /start играет первой репликой).
2. **TestPlay button в editor mode** (без PIE) — IsSpeaking toggle не работает потому что LiveRetargetSetup на BP_Cooper не triggered'ится без PIE. Use **Play in Editor** для тестирования.
3. **PIE Stop crash** — known issue, использовать Simulate (Alt+S) для дебага без PIE end.

## Файлы важные для контекста

- `UnrealProject/Source/FireflyUE5/Public/Dialogue/DialogueManager.h` + `.cpp` — главный actor класс
- `UnrealProject/Source/FireflyUE5/Public/Dialogue/FireflyDialogueFlowActor.h` + `.cpp` — HTTP flow + ADialogueManager integration
- `UnrealProject/Content/Python/firefly_face_pipeline.py` — pipeline (run_pipeline + create_level_sequence)
- `tools/dialogue_server/server.py` — FastAPI с demo pool
- `tools/dialogue_server/ue_pipeline_client.py` — UE remote exec wrapper
- `tools/dialogue_server/pregenerate_demo_assets.py` — batch script
- `tools/dialogue_server/remote_execution.py` — Epic's UDP multicast client (vendored)

## TODO queue (post-compact)

### Quick wins
- **Rebuild C++** to apply `bPlayWelcomeOnBeginPlay = false` (не блокер)
- **Tune Random Sequence Player weights** в ABP_Crew — head-down позы доминируют (Disapproval/Rubbing_Arm/Laughing weight 0.7/0.5 → пробовать 0.3/0.2)
- **Expand demo pool** до 16-20 lines (4-5 на speaker'a) — больше variety на длинных сессиях

### Step 6D-4: real on-demand generation
Нужно одно из:
- Sleep `n` сек после Performance create перед export — fix race
- Reset Performance asset state между runs (force unload?)
- Spawn separate UE process per line (slow but reliable)

### Step 6D-5: смягчить text/audio mismatch
LLM генерит уникальный text, но audio один и тот же intro_atmo. Решения:
- Либо реальный on-demand (Step 6D-4)
- Либо show only LLM subtitle, mute pre-gen audio (но lipsync cosmetic пострадает)
- Либо expand pool 50+ lines с большим разнообразием

### Дальше из original TODO
- Mixamo retarget intergration в ABP_Crew (Step 1b — почти done)
- Speaker LookAt (Step 3)
- Foot IK (Step 5)
- Cinematic cameras
- AAA Serenity dining room

## Если что-то пошло не так post-compact

- **PIE crashes на pipeline call** → проверь что `firefly_face_pipeline.py` имеет NO-OP `_ensure_level_loaded`. UE Python кеширует модуль — `sys.modules.pop` в `ue_pipeline_client.py` должен сбросить.
- **`UE node found` потом `success=False`** → multi-line statement через `MODE_EXEC_FILE`, не `STATEMENT`. Проверь `exec_mode=ue_re.MODE_EXEC_FILE` в `run_command`.
- **`No UE Editor with Python Remote Execution found`** → UE Project Settings → Plugins → Python → Enable Remote Execution must be ON. **Полный restart UE** требуется после первого включения (config иногда не подхватывается hot).
- **`Actor with label X not found`** → Speakers map в Outliner Details на BP_DialogueManager должен быть заполнен (4 entries).
- **LS не loads в PlayLine** → проверь что `Generated/<Speaker>/<line_id>/LS_<Speaker>_<line_id>.uasset` существует на disk. Если нет → run `pregenerate_demo_assets.py`.

## Ключевые коммиты этой сессии

```
ae9dca5  Step 6D-2 partial: BP_DialogueManager body gesture toggle (PIE-validated)
26a5d76  Step 6D-2 cont: OnFinished IsSpeaking=False + smoother state blend
aa9829d  Step 6D-2 done: BP_DialogueManager → C++ ADialogueManager refactor
a929309  Step 6D-2 cleanup: destroy spawned LevelSequenceActors on line finish
1cbad59  Step 6D-3: full LLM dialogue loop with lipsync+gestures via UE Python remote exec
```
