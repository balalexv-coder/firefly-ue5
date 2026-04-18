# Content/ — структура папок

Организация ассетов внутри UE. Создавайте эти папки **до** импорта чего-либо.

```
Content/
├── Prototype/                   — тестовые ассеты, не пойдут в релиз
│   ├── Levels/
│   └── Materials/
│
├── Crew/                        — всё про экипаж
│   ├── MetaHumans/
│   │   ├── Mal/
│   │   ├── Zoe/
│   │   ├── Wash/
│   │   ├── Jayne/
│   │   ├── Kaylee/
│   │   ├── Inara/
│   │   ├── Simon/
│   │   ├── River/
│   │   └── Book/
│   ├── Animation/
│   │   ├── Raw/                 — импорт из Mixamo (Y-Bot)
│   │   ├── Retargeted/          — сконвертированные на MH skeleton
│   │   ├── Montages/            — AnimMontages для SpeakLine
│   │   └── AnimBP/              — ABP_SeatedCrew, ABP_TownCrew
│   ├── Blueprints/
│   │   ├── BP_SeatActor.uasset
│   │   ├── BP_ChairActor.uasset
│   │   └── BP_DialogueClient.uasset
│   └── DataAssets/
│       ├── DA_CrewRoster.uasset — массив CharacterDef
│       └── DA_VoiceProfiles.uasset
│
├── Ship/                        — внешняя модель, визуал
│   ├── Mesh/
│   │   ├── SM_Serenity_Hull.uasset
│   │   ├── SM_Serenity_Engine_L.uasset
│   │   ├── SM_Serenity_Engine_R.uasset
│   │   └── SM_Serenity_LandingGear.uasset
│   ├── Materials/
│   │   ├── M_Hull.uasset
│   │   └── MI_Hull_Weathered.uasset
│   ├── Textures/
│   │   ├── T_Hull_BaseColor.uasset
│   │   ├── T_Hull_Normal.uasset
│   │   └── T_Hull_Roughness.uasset
│   └── Blueprints/
│       └── BP_SerenityShip.uasset
│
├── Cabin/                       — помещение кают-компании
│   ├── Meshes/
│   ├── Materials/
│   ├── Lights/                  — sublevel с освещением
│   └── Blueprints/
│       ├── BP_DiningTable.uasset
│       ├── BP_CabinFlow.uasset
│       └── BP_CabinScreen.uasset  — экран, на который идёт RT с орбитальной сцены
│
├── OrbitalScene/                — sublevel показа корабля из иллюминатора
│   ├── Meshes/
│   │   └── SM_Planet_Proxy.uasset
│   ├── Materials/
│   │   └── M_Planet_Surface.uasset — ваша NASA-текстура
│   └── BP_OrbitalCapture.uasset
│
├── Landing/                     — синематик посадки
│   ├── Niagara/
│   │   ├── NS_EntryHeat.uasset
│   │   ├── NS_EngineExhaust.uasset
│   │   └── NS_LandingDust.uasset
│   ├── Sounds/
│   │   ├── SoundCue_EngineCruise.uasset
│   │   ├── SoundCue_EngineHover.uasset
│   │   └── SoundCue_Touchdown.uasset
│   └── Cinematics/
│       └── LS_Landing.uasset
│
├── Town/                        — ковбойский городок
│   ├── Buildings/
│   │   ├── Saloon/
│   │   ├── Sheriff/
│   │   ├── Stable/
│   │   ├── Blacksmith/
│   │   ├── GeneralStore/
│   │   └── Houses/
│   ├── Props/
│   │   ├── Barrels/
│   │   ├── Crates/
│   │   ├── Lanterns/
│   │   └── Signs/
│   ├── NPCs/
│   │   ├── Meshes/
│   │   ├── Animation/
│   │   ├── BP_TownNPC.uasset
│   │   └── BehaviorTrees/
│   │       ├── BT_TownNPC.uasset
│   │       └── BB_TownNPC.uasset
│   ├── Horses/
│   │   ├── Mesh/
│   │   ├── Animation/
│   │   └── BP_Horse.uasset
│   ├── PCG/
│   │   ├── PCG_MainStreet.uasset
│   │   └── PCG_PropsScatter.uasset
│   └── Landscape/
│       ├── M_DesertGround.uasset
│       └── T_Desert_*.uasset
│
├── UI/                          — виджеты
│   ├── WBP_DialogueHUD.uasset
│   ├── WBP_MainMenu.uasset
│   ├── WBP_PauseMenu.uasset
│   └── WBP_Subtitle.uasset
│
├── Levels/                      — сами карты
│   ├── L_Main.umap              — persistent level
│   ├── L_SerenityCabin.umap     — sublevel: кают-компания
│   ├── L_OrbitalScene.umap      — sublevel: корабль + планета для RT
│   ├── L_Landing.umap           — sublevel: синематик посадки
│   └── L_Town.umap              — sublevel: городок
│
├── Audio/
│   ├── Dialogue/                — TTS-сгенерированный кеш (НЕ в git)
│   ├── Music/
│   ├── Ambient/
│   └── SFX/
│
├── Cinematics/                  — master sequences
│   └── LS_Landing.uasset        (link в Content/Landing/Cinematics/)
│
└── Config/                      — config-like ассеты
    └── DA_DialogueServerConfig.uasset  — IP/port/timeouts
```

## Правила именования

- **Класс** — префикс:
  - `BP_` — Blueprint class.
  - `SM_` — Static Mesh.
  - `SK_` — Skeletal Mesh.
  - `A_` — Anim Sequence/Blueprint/Montage.
  - `ABP_` — Anim Blueprint.
  - `IK_` — IK Rig.
  - `RTG_` — Retargeter.
  - `M_` — Material (master).
  - `MI_` — Material Instance.
  - `T_` — Texture. Суффиксы: `_BaseColor`, `_Normal`, `_ORM`, `_Roughness`.
  - `MF_` — Material Function.
  - `NS_` — Niagara System.
  - `NE_` — Niagara Emitter.
  - `S_` — Sound Wave.
  - `SC_` — Sound Cue.
  - `MX_` — Metasound.
  - `L_` — Level (map).
  - `LS_` — Level Sequence.
  - `WBP_` — Widget Blueprint.
  - `DA_` — Data Asset.
  - `BT_` / `BB_` — Behavior Tree / Blackboard.

## Что хранит git

Коммитим **всё**: `.uproject`, `Source/`, `Config/`, `Plugins/`, и **всё `Content/`** (бинарники идут через Git LFS — см. [`.gitattributes`](../.gitattributes)).

**Не коммитим** (авто-генерируется, в `.gitignore`):
- `UnrealProject/Intermediate/` — результат сборки.
- `UnrealProject/Binaries/` — DLL'ки модулей, пересобираются.
- `UnrealProject/Saved/` — кеши, логи, автосейвы.
- `UnrealProject/DerivedDataCache/` — шейдер/mesh-кеш.
- `*.sln`, `.vs/` — генерируются `scripts/generate_project_files.bat`.
- `Content/Collections/`, `Content/Developers/` — пользовательские закладки редактора.

LFS tracks: `*.uasset *.umap *.fbx *.wav *.mp3 *.exr *.hdr *.png *.jpg *.tga *.psd *.blend *.ttf *.otf *.mov *.mp4 *.avi`.

## Migration tool

Когда будете импортировать готовые модульные паки — используйте **Migrate** (Right click → Asset Actions → Migrate). Он принесёт все зависимости и не сломает ссылки.
