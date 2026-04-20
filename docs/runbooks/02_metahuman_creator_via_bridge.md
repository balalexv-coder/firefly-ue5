# 02. Создание и импорт MetaHuman через Bridge (не через web Creator)

**Дата:** 2026-04-20. **UE версия:** 5.7.4.

## Цель

Получить в Firefly UE проект готового MetaHuman'а (с BP wrapper, body + face mesh, grooms, материалами). Для нашего кейса — 5 персонажей экипажа Serenity.

## Почему через Bridge, а не через web Creator

**Web Creator** (https://metahuman.unrealengine.com) — классический путь: делаешь MetaHuman в браузере, сохраняешь в облако, потом в UE открываешь Fab/Bridge, выбираешь из своей библиотеки, Add to Project.

**В 2026 у Web Creator проблемы:**
- Часто залипает в загрузке
- UI подвисает при работе с волосами/одеждой
- Синхронизация с Bridge-библиотекой не всегда мгновенная

**Bridge (встроенный в UE)** — прямой путь без браузера:
1. `+Add` (верхняя панель Content Browser) → `Quixel Bridge`.
2. Открывается окно Bridge внутри UE.
3. Слева вкладки: Home, World (environments), MetaHumans, Displays.
4. Секция **MetaHumans → MetaHuman Presets** — встроенная библиотека готовых персонажей (те же что в web Creator как base).
5. Клик по превью персонажа → открывается страница с опциями **Customize / Download / Add to Project**.

Можно взять готового preset, кастомизировать (лицо, волосы, одежда, цвет кожи), и Add to Project одной кнопкой — без ухода в браузер.

## Шаги

### 1. Открыть Bridge

1. В UE Editor → верхняя панель Content Browser → **`+Add`** → **Quixel Bridge**.
2. Откроется окно Bridge.
3. Login — обычно уже авторизован через UE.

### 2. Выбрать или создать MetaHuman

**Вариант A — использовать готовый preset:**
1. Слева выбрать иконку **MetaHumans** (силуэт человека).
2. Вверху выбрать категорию: **MetaHuman Presets** (встроенные) или **My MetaHumans** (твои собственные из web Creator).
3. Клик по превью нужного персонажа.
4. Справа появятся детали + кнопка **Download** (скачает ассеты в кеш).

**Вариант B — создать нового:**
1. Там же есть кнопка **Create MetaHuman** → откроет встроенный редактор (аналог web Creator).
2. Редактировать лицо/волосы/одежду.
3. Save → появится в My MetaHumans.

### 3. Кастомизация (опционально)

На странице MetaHuman'а в Bridge есть вкладки:
- **Physique** — тело (Normal/Thin/Heavy, рост).
- **Face** — лицо (возраст, этнос, fine details).
- **Groom** — волосы, борода, брови, ресницы.
- **Clothing** — наряд (базовые пресеты + подключённые Fab outfits типа `techwearOutfit`).

Всё что меняется здесь — сохраняется в конкретный «snapshot» персонажа.

### 4. Add to Project

1. Верхний правый угол Bridge окна → кнопка **Add to Project**.
2. Появится диалог с deps list (тысячи файлов — лицо, тело, волосы, материалы, common shared).
3. Подтвердить → Bridge скопирует всё в `Content/MetaHumans/<CharacterName>/` и `Content/MetaHumans/Common/`.
4. В зависимости от размера (~500-700 MB) — импорт 2-5 минут.

### 5. Проверка

1. Content Browser → навигация в `Content/MetaHumans/<CharacterName>/`.
2. Должен быть **`BP_<CharacterName>.uasset`** (корневой Blueprint с иконкой лица персонажа).
3. Двойной клик → откроется Character Blueprint с компонентами: Body SkeletalMesh, Face SkeletalMesh, Groom Components (hair/brows/lashes/beard), etc.
4. Перетащи этот BP в сцену — персонаж появится.

## Подводные камни

- **Interchange Import dialog при импорте `.dna`** — при Add to Project Bridge может показать стандартный Interchange pipeline dialog (Import Content → Default Assets Pipeline) с параметрами для `.dna` файла из `SourceAssets/`. Это нормально: `.dna` — дескриптор лицевого rig'а MetaHuman. Ничего менять не нужно — **Use Pipeline Defaults → Import**. Дефолтные галки (Use Source Name for Asset, Auto Detect Mesh Type, Import Lods, Bake Meshes) корректны для MetaHuman.
- **Долгая шейдер-компиляция при первом дропе в сцену** — MetaHuman использует много material-instances, UE будет их компилировать 30-60 сек. Viewport может фризиться. Это нормально, один раз.
- **Если нет `Add to Project` кнопки** — возможно не выбран конкретный персонаж, или не залогинен. Перелогиниться.
- **MetaHuman и Common мигрируются отдельно если нужно перенести между проектами** — Bridge делает это автоматически. Если мигрируешь вручную через `Migrate` — не забудь `MetaHumans/Common/` обязательно.
- **BP_<Name>.uasset должен быть ровно в `Content/MetaHumans/<Name>/`** — если миграция положила только подпапки (Body, Face, Hair, Materials) без root BP, значит импорт был прерван. Пересиздай через Bridge → Add to Project.
  - **У нас такой случай был с Kristofer** — ассеты были в `/Assets/Content/MetaHumans/Kristofer/` (без BP), пришлось забить и сделать нового через Bridge.
- **LFS квота** — один MetaHuman ~500-700 MB. 5 MetaHumans = 2.5-3.5 GB. GitHub LFS free-tier = 1 GB. Решение (применяем у нас): **не коммитим `Content/MetaHumans/` в git**, держим локально, на fresh clone пере-импортируем через Bridge. См. [ASSETS_SOURCES.md](../ASSETS_SOURCES.md).

## Для нашего Firefly кейса

5 персонажей экипажа:
- **Mal** (Malcolm Reynolds) — мужчина ~40, тёмные волосы, военная стрижка, жёсткое лицо. Одежда: casual + rugged (shirt + jeans + boots).
- **Zoe** (Washburne) — женщина ~35, афроамериканка, короткие волосы, военная выправка. Leather vest + cargo pants.
- **Wash** (Hoban Washburne) — мужчина ~35, светлые взъерошенные волосы, мягкое лицо, лёгкая рубашка в цветочек.
- **Kaylee** — женщина ~25, шатенка, милое лицо с веснушками, комбинезон механика, грязные пятна.
- **Jayne** (Cobb) — мужчина ~40, квадратная челюсть, короткая щетина, футболка + жилет с кобурами.

Финальная одежда (Firefly-иконическая: длинные коричневые шинели, cowboy элементы) — отдельная работа через Fab outfit-packs или custom Blender модели. На этапе MetaHuman Creator подберём «похоже, но без фанатизма».

## Источники

- [MetaHuman Creator in Unreal Engine — UE 5.7 Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/metahumans-in-unreal-engine)
- [Quixel Bridge in Unreal Engine — UE 5.7 Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/quixel-bridge)
