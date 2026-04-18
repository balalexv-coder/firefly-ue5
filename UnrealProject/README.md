# UnrealProject/

Сюда кладётся UE-проект `FireflyUE5.uproject` и всё, что с ним. Создание — по шагам из [../docs/UE_SETUP.md](../docs/UE_SETUP.md).

Эта папка в основном в `.gitignore`: не коммитятся `Content/`, `Saved/`, `Intermediate/`, `Binaries/`, `DerivedDataCache/`. Коммитим только:

- `*.uproject`
- `Config/` — DefaultEngine.ini и т.д.
- `Source/` — C++ модули (`DialogueClientComponent` и прочее).
- `Plugins/FireflyUE5/` — если решите обернуть свой код как плагин.

Большие ассеты (MetaHuman, меши кораблика, анимации) хранятся локально или в отдельном LFS/CDN (см. UE_SETUP.md §6).
