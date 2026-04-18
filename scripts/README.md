# scripts/

Helper-скрипты для развёртывания UE-проекта без редактора.

## build_editor.bat

Собирает модуль `FireflyUE5Editor` (Win64 / Development). Запускать:
- после первого клона репо,
- после любых правок в `UnrealProject/Source/`,
- после обновления плагинов в `.uproject`.

```
scripts\build_editor.bat
```

## generate_project_files.bat

Пересобирает `FireflyUE5.sln` и VS-проекты под текущую версию UBT и план модулей.

```
scripts\generate_project_files.bat
```

## init_project.bat

Запускает UE headless'ом и прогоняет [`UnrealProject/Content/Python/init_project.py`](../UnrealProject/Content/Python/init_project.py), который:
- создаёт все папки `Content/` согласно [../docs/CONTENT_STRUCTURE.md](../docs/CONTENT_STRUCTURE.md),
- создаёт 5 пустых уровней (`L_Main`, `L_SerenityCabin`, `L_OrbitalScene`, `L_Landing`, `L_Town`),
- создаёт `BP_FireflyGameMode` (parent `GameModeBase`) и `BP_FireflyPlayer` (parent `Character`).

Идемпотентно — повторные запуски безопасны.

```
scripts\init_project.bat
```

## Путь к UE

Все скрипты хардкодят `C:\Program Files\Epic Games\UE_5.7\`. Если у вас другой путь — отредактируйте переменную `UE_ROOT` / `UE_CMD` / `UBT` в начале нужного скрипта.

## Порядок первого запуска

После клонирования свежего чекаута:

```
scripts\generate_project_files.bat      # сгенерить VS-проект
scripts\build_editor.bat                # собрать C++ модуль
scripts\init_project.bat                # создать Content/ и карты
```

Только после этого двойной клик на `UnrealProject/FireflyUE5.uproject` корректно откроется в UE.
