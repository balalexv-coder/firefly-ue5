# External Assets — Source of Truth

Эти папки **не коммитятся в git** (см. `.gitignore`) из-за их размера и LFS-ограничений. При fresh clone их нужно докачать вручную. Храни оригиналы локально и не теряй.

## UnrealProject/Content/MetaHumans/

**Источник:** MetaHuman Creator (Epic Games Bridge / Fab).

**Текущий состав (2026-04-19):**
- `Common/` — shared MetaHuman rig/controls/shared assets (~615 MB).
- `Kristofer/` — кастомный MetaHuman (m_med_nrw body, ~585 MB). Прототип Mal.

**Как восстановить:**
1. Открыть Quixel Bridge / Fab Bridge plugin в UE.
2. Download Kristofer → Add to Project (если сохранён в личной библиотеке).
3. Либо пересоздать в MetaHuman Creator (https://metahuman.unrealengine.com) по референсу из `docs/CHARACTERS.md`.

**Локальный backup:** `C:\Users\balal\Assets\Content\MetaHumans\Kristofer\` (отдельный UE проект для хранения MetaHuman'ов).

## UnrealProject/Content/Sketchfab/

**Источник:** Sketchfab.com.

**Текущий состав:**
- `serenity/` — модель корабля Serenity (exterior), 97 MB imported. Для Акта II (landing).
- `Planet/` — планета. Для Акта II/III.

**Лицензия:** проверить индивидуально на sketchfab.com, бывают CC BY.

**Локальный backup:** `C:\Users\balal\Assets\Content\Sketchfab\`.

## UnrealProject/Content/Fab/

**Источник:** Fab.com (бывший Marketplace + Quixel).

**Текущий состав:**
- `MetaHuman/techwearOutfit/` — одежда для MetaHuman.

**Как восстановить:** Fab plugin в UE → My Library → re-download.

## При fresh clone — пошагово

1. `git clone https://github.com/balalexv-coder/firefly-ue5.git`
2. Открыть `Assets.uproject` (локальный backup-проект со всеми ассетами).
3. Content Browser → правый клик на `MetaHumans/Kristofer` → Asset Actions → **Migrate** → target: `firefly-ue5/UnrealProject/Content/`.
4. Повторить для `MetaHumans/Common`, `Sketchfab/serenity`, `Fab/`.
5. Открыть Firefly проект — все ассеты должны быть на месте.

Альтернатива — хранить всё в облаке (Google Drive / S3) и качать скриптом, но пока локального backup хватает.
