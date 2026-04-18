# WALKTHROUGH — пошаговые действия в UE редакторе

Это живой документ. Здесь — точные клики и настройки для каждой фазы из [PLAN.md](PLAN.md), с прицелом на **профессиональное качество демо**. Чек-боксы отмечаем по мере прохождения.

> **Читайте как чек-лист.** Если что-то непонятно — смотрите соответствующий subsystem-doc (ссылки в PLAN.md).

---

## Фаза 0 — Первичная настройка UE (~30 мин)

### 0.1 Установка UE 5.7.4

- [ ] Epic Games Launcher → Unreal Engine → Library → Install → **5.7.4**.
- [ ] Компоненты: `Starter Content`, `Templates and Feature Packs`, `Engine Source` (для возможной модификации).
- [ ] FFmpeg (понадобится для конвертации рендера в MP4):
  ```powershell
  winget install Gyan.FFmpeg
  ```
  Проверить: новый терминал → `ffmpeg -version`.

### 0.2 Инициализация проекта

У вас уже есть в репозитории `UnrealProject/FireflyUE5.uproject` и `UnrealProject/Source/` — при первом открытии UE соберёт C++ модуль сам.

- [ ] Right-click на `UnrealProject/FireflyUE5.uproject` → **Generate Visual Studio project files**.
- [ ] Открыть `FireflyUE5.sln` в **Visual Studio 2022** (workload «Game development with C++» должен быть установлен).
- [ ] Build configuration: **Development Editor** / platform **Win64** → **Build**.
- [ ] Двойной клик `FireflyUE5.uproject` — редактор запустится.

При первом запуске UE спросит про отсутствующие default assets: создайте `L_Main.umap` (пустой уровень, Save As → `Content/Levels/L_Main`). Если редактор создаст дефолтную сцену ThirdPerson — её содержимое потом перетащите в `Content/Prototype/`.

### 0.3 Плагины

Edit → Plugins → включить (и перезапустить UE):

- [ ] MetaHuman (+ MetaHuman Animator)
- [ ] Movie Render Queue
- [ ] Apple ProRes Media
- [ ] Sequencer Scripting
- [ ] Niagara (уже включён)
- [ ] PCG Framework
- [ ] Enhanced Input (уже включён)
- [ ] Live Link + Apple ARKit Face Support
- [ ] Quixel Bridge
- [ ] Datasmith (для импорта из Blender если понадобится)

### 0.4 Project settings

Edit → Project Settings:

#### Rendering
- [ ] **Dynamic Global Illumination Method** = `Lumen`.
- [ ] **Reflection Method** = `Lumen`.
- [ ] **Shadow Map Method** = `Virtual Shadow Maps`.
- [ ] **Forward Shading** = Off (нужен Deferred для Lumen).
- [ ] **Nanite** → Enable.
- [ ] **Hardware Ray Tracing** = On (если GPU поддерживает).
- [ ] **Anti-Aliasing Method** = `TSR` (Temporal Super Resolution, лучше TAA).
- [ ] **Motion Blur Amount** = 0.35–0.5.
- [ ] **Post Processing → Bloom Method** = `Standard`.
- [ ] **Tonemapper** = ACES (project-default, не выкл.).

#### Engine — General Settings
- [ ] **Smooth Frame Rate** = On, 30–120.
- [ ] **Pause On Loss Of Focus** = Off (удобно для отладки HTTP).

#### Platforms → Windows
- [ ] Default RHI = **DirectX 12**.

#### Maps & Modes
- [ ] Editor Startup Map / Game Default Map: `/Game/Levels/L_Main`.

### 0.5 Основные карты

Создайте в `Content/Levels/` (все как Empty Level):
- [ ] `L_Main` — persistent (его загружаем по-умолчанию).
- [ ] `L_SerenityCabin` — подуровень с кают-компанией.
- [ ] `L_OrbitalScene` — микро-сцена: корабль + планета, на SceneCapture.
- [ ] `L_Landing` — кинематографический уровень.
- [ ] `L_Town` — городок.

В `L_Main`: Window → Levels → + → **Streaming Method: Always Loaded** для Cabin и Orbital, **Blueprint** streaming для Landing и Town (подгружаем по триггеру).

### 0.6 Папки Content/

Создать согласно [CONTENT_STRUCTURE.md](CONTENT_STRUCTURE.md) правым кликом в Content Browser → New Folder. Не ленитесь — ассетов будет сотни, без структуры потеряете время.

---

## Фаза 1 — Dialogue server (уже готово)

Если ещё не поднимали локально:

- [ ] `cd tools/dialogue_server`
- [ ] Двойной клик `start_server.bat` (Windows) — первый запуск создаст venv и поставит зависимости. Ollama должен быть запущен (`ollama serve` или tray-app).
- [ ] Отдельно: `python test_client.py` → должен вывести opener от Мала и 3 варианта. 1/2/3 — выбор.

Смотрим логи: `tools/dialogue_server/logs/<session>.jsonl`. Если там чушь — см. `README.md → Частые проблемы`.

**Для финального демо** — переключить `.env` на `DIALOGUE_BACKEND=anthropic`. Один раз.

---

## Фаза 2 — Экипаж (MetaHuman'ы) (~3–5 дней)

### 2.1 MetaHuman Creator

- [ ] Window → Quixel Bridge → MetaHumans → **MetaHuman Creator Online**. Войдите в Epic account.
- [ ] Для каждого персонажа из [CHARACTERS.md](CHARACTERS.md) — **Create New Metahuman** от прессета, максимально близкого к целевому (см. ниже).

Рецепты стартовых прессетов (выбирайте как базу, затем правьте):

| Персонаж | Preset-основа в MetaHuman Creator |
|---|---|
| Mal    | Preset "Jesse" или "Vincent" → похудеть лицо, коротко тёмные волосы |
| Zoe    | Preset "Naomi" или "Amara" → атлетичнее, кудрявые собранные волосы |
| Wash   | Preset "Danielle" (male variants) / "Lewis" → песочные волосы, round face |
| Jayne  | Preset "Tomas" / "Vincent" → шире, массивнее, короткий ёжик, небритость |
| Kaylee | Preset "Seneca" / "Bea" → молодой, веснушки, прямые каштановые волосы, хвост |
| Inara  | Preset "Taro" (female) / "Asha" → восточная примесь, длинные тёмные волосы |
| Simon  | Preset "Hideo" / "Glenda" (M) — строгий, пробор, бэнды выше скул |
| River  | Preset "Ada" / "Bea" (young) — длинные чёрные волосы, худое лицо |
| Book   | Preset "Omar" / "Jesse" (stylized older, седые дреды) |

Для каждого:
- [ ] Настроить лицо (пропорции, сморщенность кожи, детали).
- [ ] Body → рост/вес.
- [ ] Hair → ближайшая стрижка.
- [ ] Clothing — на этом этапе любая, позже заменим пак-ом.
- [ ] Save as: `MH_<Key>` (например, `MH_Mal`).

### 2.2 Экспорт в проект

- [ ] Quixel Bridge → My MetaHumans → для каждого → **Download** (Quality: **Cinematic**) → **Add**.
- [ ] В Content Browser появится `Content/MetaHumans/<Name>/BP_<Name>.uasset`.
- [ ] Переместить в `Content/Crew/MetaHumans/` (Migrate → Move).

**Проверка.** Открыть BP_<Name>, Viewport → должен показывать персонажа без ошибок материалов (если красный/розовый — MetaHuman материалы не подгрузились, проверить плагин).

### 2.3 Одежда

Для pro-вида — **обязательно** сменить стоковую одежду. Варианты (по убыванию цены/качества):

1. **Fab Marketplace** → «Western Outfit Pack for MetaHuman» (~$40–80).
2. **CC4 / Reallusion Character Creator** → экспорт цельного персонажа с одеждой.
3. **Marvelous Designer** cloth → CC4/Blender → UE (сложно, но уникальный вид).
4. Временно — стоковые MetaHuman наряды.

Один сет для всей команды — это *визуально читается как группа*. Разумный компромисс: один базовый пак «западный фронтир», внутри него 9 вариантов (Mal — кожанка, Zoe — кожаный корсет, Wash — гавайская рубашка из Marketplace по запросу «Hawaiian shirt», и т.д.).

---

## Фаза 3 — Кают-компания и рассадка (~2–3 дня)

### 3.1 Помещение

Два пути:

**A. Купить / скачать sci-fi модульный кит** (быстрее):
- [ ] Fab → «Modular Spaceship Interior» (~$30–60). Стены/пол/потолок.
- [ ] Migrate в `Content/Cabin/Meshes/`.

**B. Собрать руками** (гибче, но дольше):
- [ ] В L_SerenityCabin поставить Cube 800×600×300 cm → Modeling Mode → Model Cube → Boolean Subtract для окон и двери.

### 3.2 Стол и стулья

- [ ] В Cabin/Meshes поставить ваш `SM_DiningTable` (импорт из Blender или купить).
- [ ] 9 × `BP_ChairActor` по периметру стола. Рассадка — [CHARACTERS.md](CHARACTERS.md#итоговая-рассадка-за-столом).

Для каждого `BP_ChairActor`:
- [ ] Open BP → Components → + **Scene Component** → Rename `SeatSocket`.
- [ ] Set its Location: `X=0 Y=0 Z=45 cm` (высота сиденья), Rotation вперёд.

### 3.3 Скачать Mixamo анимации

- [ ] https://www.mixamo.com, вход через Adobe account.
- [ ] Выбрать Character: **Y-Bot**.
- [ ] Скачать (FBX Binary, 30 fps, without skin):
  - `Sitting Idle`
  - `Sitting Talking 1`, `Sitting Talking 2`, `Sitting Talking 3`
  - `Sitting Yell`
  - `Sitting Clap`, `Sitting Rub Hands`, `Sitting Victory`, `Sitting Disappointed`
- [ ] Сложить в `Content/Crew/Animation/Raw/Mixamo/` (импорт: при импорте создать новый скелет `SK_MixamoYBot_Skeleton`).

### 3.4 Ретаргетинг на MetaHuman

- [ ] Content → New → Animation → **IK Rig**.
  - Source: `SK_MixamoYBot_Skeleton` → `IK_MixamoYBot`.
  - Настроить chains: Spine, LeftArm, RightArm, LeftLeg, RightLeg, Head, IKGoals на hands и feet.
- [ ] Аналогично — `IK_MetaHuman` на MetaHuman skeleton (или использовать встроенный из `Content/MetaHumans/Common/Common/MetaHuman_Base_Skel/IK_MetaHuman`).
- [ ] Content → New → Animation → **IK Retargeter** → `RTG_MixamoToMetaHuman`.
  - Source: `IK_MixamoYBot`. Target: `IK_MetaHuman`.
  - Проверить Chain Mapping автоматически заполнился.
  - Asset Browser → select все Mixamo Sitting_*.* → Right click → **Export Selected Animations** → путь `Content/Crew/Animation/Retargeted/`.

### 3.5 Animation Montages

Для каждой retargeted анимации:
- [ ] Right click → Create Animation Montage → в Details назвать слот `UpperBody` (нужен для layered blend).

### 3.6 Animation Blueprint ABP_SeatedCrew

- [ ] Content/Crew/Animation/AnimBP/ → New → Animation Blueprint → Target Skeleton `metahuman_base_skel` → `ABP_SeatedCrew`.
- [ ] Open → Graph → **State Machine** `Main`:
  - States: `Idle`, `Talking`, `Reacting`.
  - Idle state: **Blend Space** из SitIdle variations (с mild random factor).
  - Talking / Reacting — заглушки, управляются через Montage `UpperBody` slot.
- [ ] AnimGraph root:
  ```
  [State Machine Main] → [Layered Blend Per Bone slot UpperBody, bone spine_03] → Output Pose
  ```
- [ ] Post-process → Modify Bone on `head` → alpha driven by `HeadLookAlpha` variable; target rotation from `LookAtSpeakerDir` variable.

### 3.7 Cборка BP_<CrewName> Actor

Один раз сделать `BP_Mal`, остальных копировать.

- [ ] Content/Crew/Blueprints/ → New BP → parent **ASeatActor** (ваш C++ класс).
- [ ] В BP_Mal:
  - BodyMesh: Mesh = `Mal_body` (из MetaHuman BP_Mal).
  - Добавить 4 SkeletalMesh компонента под BodyMesh: `FaceMesh`, `TorsoMesh`, `LegsMesh`, `FeetMesh` (стандарт MetaHuman). Set Master Pose Component = BodyMesh.
  - AnimClass для BodyMesh = `ABP_SeatedCrew`.
  - CharacterKey = "Mal".
  - TalkMontagesByEmotion: calm → SitTalk_1_Montage, gruff → SitTalk_2_Montage, bright → SitTalk_3_Montage, и т.д.
  - FallbackTalkMontage → любая из них.
- [ ] Duplicate BP_Mal → BP_Zoe и т.д. Заменить Mesh, AnimClass можно оставить общий.

### 3.8 Расстановка в L_SerenityCabin

- [ ] Drag BP_Mal в уровень. Set **TargetChair** = BP_ChairActor_Mal (через picker в Details).
- [ ] Повторить для 9.
- [ ] Play — все 9 должны быть в своих креслах в sitting pose.

---

## Фаза 4 — Диалоговая система в UE (~3–5 дней)

### 4.1 BP_CabinFlow (master level BP)

- [ ] Content/Cabin/Blueprints/ → New BP → parent `Actor` → `BP_CabinFlow`.
- [ ] Component: **DialogueClientComponent** (ваш C++).
- [ ] В Level Blueprint L_SerenityCabin на BeginPlay — Spawn `BP_CabinFlow` (или просто поставить на уровень).

### 4.2 WBP_DialogueHUD (UMG виджет)

- [ ] Content/UI/ → New → User Interface → Widget Blueprint → `WBP_DialogueHUD`.
- [ ] Designer:
  ```
  Canvas
    └─ VerticalBox (Anchor: bottom-center, size-to-content)
        ├─ SpeakerPlate (HorizontalBox)
        │   ├─ Image SpeakerPortrait (64×64)
        │   └─ TextBlock SpeakerName (font: Exo 2 / Oswald, 24pt bold, color white, dropshadow)
        ├─ SubtitleText (TextBlock, font 22pt, max-width 1000, letter-by-letter typewriter)
        └─ OptionsRow (HorizontalBox)
            ├─ Button Option1 → Text Block
            ├─ Button Option2
            └─ Button Option3
  ```
- [ ] Functions:
  - `ShowLine(Speaker, Line)` — установить SpeakerName и запустить typewriter по SubtitleText.
  - `ShowOptions(Array<String>)` — fill buttons, enable.
  - `HideOptions()` — disable + fade-out.
- [ ] В Event Construct — спрятать OptionsRow.

### 4.3 Wire up flow

В `BP_CabinFlow`:
```
Event BeginPlay
  → HUD = Create Widget WBP_DialogueHUD → Add to Viewport
  → DialogueClient.StartSession

Event DialogueClient.OnSessionStarted (Turn)
  → HUD.ShowLine(Turn.Lines[0].Speaker, Turn.Lines[0].Line)
  → SeatActor_<Speaker>.SpeakLine(...)
  → wait OnLineFinished
  → HUD.ShowOptions(Turn.NextPlayerOptions)

Event HUD.OnOptionPicked (text)
  → HUD.HideOptions
  → DialogueClient.SubmitChoice(text)

Event DialogueClient.OnTurnReceived (Turn)
  → ForEachLoop Turn.Lines:
       HUD.ShowLine(line.Speaker, line.Line)
       Find SeatActor by CharacterKey (map<string, BP_SeatActor>)
       SeatActor.SpeakLine(line.Line, line.Emotion, <audio>, line.DurationMs/1000)
       Delay until OnLineFinished
  → OrbitSequencer.SetTime(OrbitSequencer.Duration * progress)  // продвигаем орбиту
  → DialogueClient.SetOrbitProgress(progress + 1/N)
  → If Turn.bContinue == false OR progress >= 0.95:
       TransitionToLanding
     Else:
       HUD.ShowOptions(Turn.NextPlayerOptions)
```

### 4.4 Camera coverage

- [ ] В L_SerenityCabin → 11 **CineCameraActor**: `CAM_Mal_Close`, ..., `CAM_Player`, `CAM_Master`.
- [ ] Focal length 50–85 мм, f/2.8 для speaker close-ups (лёгкий DoF).
- [ ] В BP_CabinFlow — функция `PickCameraForSpeaker(name)` возвращает нужный CameraActor.
- [ ] Плагин **"Set View Target With Blend"** 0.3 сек при смене.

### 4.5 Тестирование

- [ ] Запустить dialogue server.
- [ ] Play in Editor.
- [ ] Мал говорит, появляются 3 кнопки. Клик — команда отвечает. Цикл работает 4–5 раундов.
- [ ] Если DialogueClientComponent ругается на 127.0.0.1 — проверить что сервер действительно на 8765.

---

## Фаза 5 — Орбитальный экран (~1–2 дня)

### 5.1 Sub-level L_OrbitalScene

- [ ] Открыть `L_OrbitalScene`. Кромешная темень (нет Sky Sphere, только космос).
- [ ] Drop Directional Light — этот будет солнце (tempurature 5000K, intensity 5 lux).
- [ ] SkySphere: либо кастомный Background Actor с `HDRIBackdrop`, либо просто Skybox меш с чёрной текстурой + звёзды.
- [ ] Drop BP_SerenityShip (ваш корабль), поставить в ~5000 cm от origin.
- [ ] Drop SM_Planet_Proxy (ваша планета из NASA-текстур) в ~30000 cm от origin.

### 5.2 SceneCapture → Render Target

- [ ] Drop **SceneCapture2D** в уровень. Set Transform в камеру, которая видит корабль и планету.
- [ ] Create `Content/Cabin/RT_CabinScreen` — Render Target 1920×1080.
- [ ] В Details SceneCapture2D: **Texture Target** = `RT_CabinScreen`. **Capture Source** = `Final Color (HDR) in RGB`.

### 5.3 Материал экрана в кают-компании

- [ ] Content/Cabin/Materials/ → New Material → `M_CabinScreen`.
  - BaseColor: TextureSample на `RT_CabinScreen`.
  - Emissive: BaseColor × 2 (чтобы экран сам светился).
  - Roughness: 0.1 (блик).
- [ ] Apply на плоскости стены в L_SerenityCabin.

### 5.4 Level Sequence LS_OrbitApproach

- [ ] Content/Cinematics/ → New → LevelSequence → `LS_OrbitApproach`, длительность 60 сек.
- [ ] Add → BP_SerenityShip (если в уровне). Transform track: 60 сек пути от дальней точки до атмосферы.
- [ ] В BP_CabinFlow после каждого OnTurnReceived:
  `LS_OrbitApproach_Actor.SetPlaybackPosition(Duration * OrbitProgress)`.

### 5.5 Проверка

Play → на экране на стене в кают-компании должно быть видно корабль, который с каждым раундом разговора заметно приближается к планете.

---

## Фаза 6 — Синематик посадки (~3–5 дней)

См. [CINEMATIC.md](CINEMATIC.md) и [RENDER_EXPORT.md](RENDER_EXPORT.md).

Краткая последовательность:

### 6.1 Ландшафт

- [ ] `L_Landing` → Create Landscape 4032×4032, 3 components.
- [ ] Sculpt: дюны (пустынная местность, rolling hills).
- [ ] Material: `M_DesertGround` из Megascans → Layer Blend (sand / rock / dust).
- [ ] Foliage: редкие Mesh'а из Megascans → desert plants, scattered stones.

### 6.2 Небо

- [ ] **Sky Atmosphere**, **Exponential Height Fog**, **Volumetric Cloud** (для красивой entry).
- [ ] Directional Light = солнце, 6500K.

### 6.3 Riging корабля

- [ ] Открыть BP_SerenityShip: разделить mesh на 3 компонента (Hull + Engine_L + Engine_R), каждому свой pivot.
- [ ] Expose `EngineRotation` (float) — в Construction Script:
  `Engine_L.SetRelativeRotation(FRotator(EngineRotation, 0, 0))`, аналогично Engine_R.

### 6.4 Niagara

- [ ] `NS_EntryHeat`, `NS_EngineExhaust`, `NS_LandingDust` — шаблоны в [CINEMATIC.md](CINEMATIC.md).
- [ ] Attach `NS_EngineExhaust` как child к каждому Engine в BP_SerenityShip (parameter `Throttle`).

### 6.5 LS_Landing

- [ ] 4 shot'а (A/B/C/D) + CineCamera каждому, транзишены hard cut.
- [ ] Track BP_SerenityShip Transform + EngineRotation.
- [ ] Audio track: 6–8 слоёв (см. CINEMATIC.md).

### 6.6 Переход из кают-компании

- [ ] В BP_CabinFlow `TransitionToLanding`:
  - Camera Fade to black (0.8 sec).
  - LoadStreamLevel(L_Landing, MakeVisibleAfterLoad).
  - UnloadStreamLevel(L_SerenityCabin).
  - PlaySequence LS_Landing.
  - OnFinished → LoadStreamLevel(L_Town).

### 6.7 Рендер для ролика

- [ ] Sequencer → Render Movie → Movie Render Queue → Settings:
  - Output: .png Sequence
  - TS 8, SS 4, Game Overrides Cinematic.
- [ ] После рендера: FFmpeg команда из [RENDER_EXPORT.md](RENDER_EXPORT.md).

---

## Фаза 7 — Городок (~7–10 дней)

См. детальные шаги в [TOWN_DESIGN.md](TOWN_DESIGN.md).

### 7.1 Ассет-пак

- [ ] Fab / Marketplace → купить pro-пак:
  - **"Western Town" by PolyPixel** (~$70) — 30+ зданий, пропсы, хай-поли.
  - или **"Wild West Environment" by Leartes Studios** (~$100) — кинематографическое качество.
- [ ] Migrate → `Content/Town/Buildings/`.

### 7.2 PCG layout

- [ ] `PCG_MainStreet` граф — см. [TOWN_DESIGN.md](TOWN_DESIGN.md#pcg-procedural-content-generation-раскладка).
- [ ] `PCG_Props` для мелких предметов в проулках.

### 7.3 NPC

- [ ] Купить **Paragon** characters (бесплатные) или Animset MPC (~$40).
- [ ] `BP_TownNPC` с behavior tree `BT_TownNPC`.

### 7.4 Лошади

- [ ] **Horse Animset Pro** (~$50) + mesh из Sketchfab CC0.
- [ ] `BP_Horse` + `ABP_Horse` state machine.

### 7.5 Ambience

- [ ] Wwise или MetaSounds: 6–8 слоёв, см. TOWN_DESIGN.md.

---

## Фаза 8 — Полировка и сборка

- [ ] Главное меню `WBP_MainMenu` — Play / Options / Quit.
- [ ] Пауза по Esc → `WBP_PauseMenu`.
- [ ] Subtitle settings в опциях (on/off, size).
- [ ] Project Settings → Packaging → Use Pak File = True.
- [ ] File → Package Project → Windows (Shipping).
- [ ] Проверить на **чистой** Windows-машине: стартует, играбельно, без крашей.

---

## Статус прохождения

Обновляйте чек-боксы в этом файле по мере прогресса. Раз в пару дней — коммит с сообщением в духе `walkthrough: phase 3.4 retargeting done`.
