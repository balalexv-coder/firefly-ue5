# UnrealProject/

Сюда кладётся UE-проект `FireflyUE5.uproject` и всё, что с ним. Создание — по шагам из [../docs/UE_SETUP.md](../docs/UE_SETUP.md).

В git коммитится **весь** UE-проект: `.uproject`, `Config/`, `Source/`, `Content/` (бинарники через Git LFS — см. [`../.gitattributes`](../.gitattributes)).

Не коммитятся только авто-генерируемые: `Intermediate/`, `Binaries/`, `Saved/`, `DerivedDataCache/`, `.vs/`, `*.sln`.

На чистой машине: `scripts\generate_project_files.bat` → `scripts\build_editor.bat` — восстанавливает `.sln` и бинарники модуля из Source/.
