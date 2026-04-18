# Настройка Unreal Engine 5.7.4 проекта

Пошаговая инициализация. Один раз.

---

## 1. Установка UE 5.7.4

1. Epic Games Launcher → Unreal Engine → Library → Install → Version **5.7.4**.
2. Компоненты:
   - Starter Content ✓
   - Templates and Feature Packs ✓
   - Engine Source — по желанию (нужен для модификации движка).

## 2. Создание проекта

1. Launcher → Launch UE 5.7.4.
2. New Project → Games → **Third Person** (не Blank — нам нужен готовый Character/Controller).
3. Параметры:
   - Project Type: **C++** (нужен для DialogueClientComponent).
   - Quality Preset: **Maximum**.
   - Target Platform: **Desktop**.
   - Raytracing: **On**.
   - Starter Content: **On** (для первых тестов).
4. Location: `C:/Users/balal/Claude Code Projects/Firefly v1/UnrealProject/`.
5. Project Name: `FireflyUE5`.
6. Create.

После сборки Visual Studio откроется автоматически. Убедитесь, что `Build & Run` работает.

## 3. Плагины

Edit → Plugins. Включите (перезапуск после):

| Плагин | Категория | Для чего |
|---|---|---|
| MetaHuman | Animation | Персонажи экипажа |
| MetaHuman Animator | Animation | Лицевая анимация |
| Movie Render Queue | Rendering | Экспорт кинематика |
| Apple ProRes Media | Media | Опционально: прямой рендер MOV/ProRes |
| Sequencer Scripting | Animation | Python утилиты для Sequencer |
| PCG | Procedural | Раскладка городка |
| Niagara | FX | Эффекты (есть по умолчанию) |
| Enhanced Input | Input | Современный input (по умолчанию on) |
| Live Link | Animation | Если снимаете лицо с iPhone |
| ARKit Face Support | Animation | С LiveLink |
| HTTP Blueprints (если нужно BP-обёрткам) | Web | Альтернатива кастому C++ |
| Quixel Bridge | Content | Megascans и MetaHuman в один клик |

## 4. Project Settings — критичные опции

Edit → Project Settings:

### Maps & Modes
- Default GameMode: **BP_FireflyGameMode** (создать наследник от AGameModeBase).
- Default Pawn: **BP_FireflyPlayer**.
- Editor Startup Map: `L_Main`.
- Game Default Map: `L_Main`.

### Engine → Rendering
- **Lumen**: Dynamic Global Illumination = Lumen, Reflections = Lumen. (По умолчанию в 5.x.)
- **Virtual Shadow Maps** = On.
- **Nanite**: Support Nanite = On.
- **Motion Blur**: Enable, intensity как вкус.
- **Post Process Materials**: Tonemapper = ACES.

### Engine → General Settings
- **Max FPS**: 120 в editor, unlimited в runtime.

### Platforms → Windows
- **Rendering API**: DX12.

### Input (Enhanced Input)
- `IA_Move` (Vector2D), `IA_Look` (Vector2D), `IA_Jump` (bool), `IA_Interact` (bool), `IA_DialogueOption1/2/3` (bool).
- Context: `IMC_Default` для ходьбы, `IMC_Dialogue` для сцены за столом.

## 5. Структура Content/

См. [CONTENT_STRUCTURE.md](CONTENT_STRUCTURE.md). Создать эти папки **перед** импортом ассетов — потом переносить больно.

## 6. Git + LFS setup

### Git

В корне `Firefly v1/` уже есть репозиторий (см. общий README.md). UE игнорируется селективно (см. `.gitignore`).

### Git LFS

Большие бинарники (.uasset, .umap) — через LFS. Иначе репо вырастет до гигабайтов и git будет медленным.

1. Установить: `winget install Git.Git` уже включает LFS в новых версиях. Либо https://git-lfs.com.
2. В корне репо:
   ```bash
   git lfs install
   git lfs track "*.uasset"
   git lfs track "*.umap"
   git lfs track "*.wav"
   git lfs track "*.mp3"
   git lfs track "*.png"  # опционально — для crew текстур
   git lfs track "*.exr"
   ```
3. `git add .gitattributes` — файл создаётся автоматически.

**Вариант на v0.1:** не коммитить Content/ вообще (см. `.gitignore`). Тогда LFS не нужен. Binary'и хранятся локально. Это ок, пока вы единственный разработчик.

## 7. Source control в UE

Editor Preferences → Source Control:
- Provider: **Git** (плагин уже включён по умолчанию).
- Path to Git: `C:/Program Files/Git/cmd/git.exe`.
- LFS: True.

После — в Editor нижняя правая кнопка «Submit to Source Control».

## 8. Linter и стили

Editor Preferences → Blueprint Editor:
- **Blueprint Compilation Manager** = On.
- Compile → Save Warnings = On.

## 9. Первый коммит в UE

1. Открыть проект.
2. Создать папки согласно CONTENT_STRUCTURE.md (правый клик на Content → New Folder).
3. Переместить дефолтный ThirdPersonContent в `Content/Prototype/` — будем использовать как тестовую плейграунд.
4. Сохранить всё → Submit to Source Control.

## 10. Сборка Debug билда

Для профилирования:
- Build configuration: **DebugGame Editor**.
- Runtime: **DebugGame**.
- Стеки понятнее, но FPS упадёт 2-3x.

## Частые проблемы

### Visual Studio не видит UE проект

- File → Generate Visual Studio project files (правый клик на `.uproject`).
- VS 2022 Community или Professional, Workload «Game development with C++».

### MetaHuman Creator не открывается

- Требует интернета и вход в Epic account.
- Если crash — Quixel Bridge → Sign in.

### Quixel Bridge Download stuck

- Закрыть → переоткрыть от админа → Login.
- Download location настройте в Bridge settings на быстрый SSD.

### Packaging fails with «LogLinker»

- Обычно какой-то пустой asset или circular reference. Fix up redirectors (Right click на папке Content → Fix Up Redirectors in Folder).

## Минимальные sys-требования

Тестировать на:
- Windows 10/11 64-bit.
- GPU: RTX 2070 minimum (Nanite требует DX12 с соответствующей поддержкой).
- RAM: 32 GB рекомендовано, 16 GB — предел.
- Storage: SSD, 50+ GB свободно под проект.
