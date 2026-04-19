# 01. Ретаргет Mixamo-анимаций на UE5 Mannequin (UE 5.7)

**Дата написания:** 2026-04-20. **UE версия:** 5.7.4. **Interchange pipeline:** да (дефолт с 5.5).

## Цель

Взять анимацию с mixamo.com, импортировать в UE, и проиграть её на `SKM_Manny_Simple` (UE5 Third Person Mannequin) через IK Retargeter.

## Пререквизиты

- UE 5.7 проект открыт.
- В проекте есть **SKM_Manny_Simple** (через `Content Browser → +Add → Add Feature or Content Pack → Blueprint Feature → Third Person`). Появится `Content/Characters/Mannequins/...`.
- Аккаунт Adobe (бесплатный) для входа на mixamo.com.
- Опционально: GPU с достаточной памятью для шейдер-компиляции при импорте mesh.

## Шаги

### 1. Скачать T-Pose с Mixamo (один раз, эталон скелета)

1. https://www.mixamo.com → Sign in (Adobe account).
2. В поиске анимаций: `t-pose` → выбрать первую (описание «Standard T-Pose»).
3. Нажать **Download** (оранжевая кнопка справа сверху).
4. В диалоге настроек:
   - **Format:** `FBX Binary(.fbx)`.
   - **Skin:** **With Skin** ← важно именно для T-Pose (создаст skeleton+mesh как reference).
   - **Frames per Second:** `30`.
   - **Keyframe Reduction:** `none`.
5. Нажать второй Download. Файл `T-Pose.fbx` падает в `C:/Users/<user>/Downloads/`.

### 2. Скачать анимации (без skin)

Поиск `sitting` (или другое). Для каждой нужной анимации:
1. Клик на превью → справа `Download`.
2. Настройки:
   - **Format:** `FBX Binary(.fbx)`.
   - **Skin:** **Without Skin** ← только анимация, без mesh.
   - **Frames per Second:** `30`.
3. Второй Download.

Для нашего проекта скачали: `Sitting Idle` (описание «Sitting Still In A Chair»), `Sitting Talking`, `Sitting Disapproval`.

### 3. Импортировать T-Pose в UE (создаёт Mixamo-скелет)

1. Content Browser → навигация в папку для анимаций (у нас — `Content/Crew/Animation/Raw/`).
2. Перетащить `T-Pose.fbx` в неё.
3. Откроется **Import Content** диалог с `Default Assets Pipeline (InterchangeGenericAssetsPipeline)`. Это новый Interchange-пайплайн UE 5.5+, опции отличаются от legacy FBX importer.
4. Настройки (через фильтры `All / Static Meshes / Skeletal Meshes / Animations`):
   - Оставить defaults большинства.
   - Skeletal Meshes → `Import Skeletal Meshes` ✓ (нужно для эталонного меша).
   - Animations → `Import Animations` ✓ (T-Pose 1-frame, не мешает).
   - Skeleton → пусто (создастся новый).
5. **Import**.
6. Создадутся: `T-Pose` (SkeletalMesh), `T-Pose_Skeleton`, `T-Pose_Anim` (1-frame), `T-Pose_PhysicsAsset`, + текстуры/материал `Peasant_Girl_*`. Это стандартный Mixamo preview-персонаж (female, не парься о поле — скелет один).

### 4. Импортировать три анимации на Mixamo-скелет

Для каждого FBX (`Sitting Idle.fbx`, `Sitting Talking.fbx`, `Sitting Disapproval.fbx`):
1. Перетащить FBX в `Content/Crew/Animation/Raw/`.
2. В диалоге Import Content:
   - Skeletal Meshes → `Import Skeletal Meshes` **OFF**.
   - Animations → `Import Animations` **ON**.
   - Animations → `Animation Length` → **`Source Timeline`** ← важно, **`Animated Time` баг в 5.5+, импортит пустые анимации**.
   - `Custom Bone Animation Sample Rate` если есть → `30`.
   - Skeleton → выбрать **`T-Pose_Skeleton`** (из шага 3).
   - Materials / Textures → Import **OFF** (уже есть из T-Pose).
3. **Import**.

Должны появиться `Sitting_Idle`, `Sitting_Talking`, `Sitting_Disapproval` — AnimationSequence на `T-Pose_Skeleton`.

### 5. Создать IK Rig для Mixamo-скелета

1. Content Browser → `Content/Crew/Animation/IK/` (или любая удобная папка).
2. Правый клик в пустом месте → **Animation → Retargeting → IK Rig**.
3. Имя: `IK_Mixamo`. Сразу создастся без диалога.
4. Двойной клик → IK Rig Editor откроется.
5. В **Details** справа, секция **Preview → Preview Skeletal Mesh** → выбрать `T-Pose`.
6. В Hierarchy слева появится иерархия костей (Hips, Spine, Neck, Head и т.д. — Mixamo-префикс `mixamorig:` стрипнется при импорте).
7. Правый клик на **Hips** → в секции `RETARGETING` → **Set Pelvis**.
8. Сверху нажать кнопку **Auto Create Retarget Chains**. UE распознает Mixamo template (уведомление «Using Mixamo template. Skeletal structure matches with 100% accuracy.»), создаст chains: Spine, Neck, Head, LeftArm/RightArm, LeftClavicle/RightClavicle, LeftLeg/RightLeg, LeftThumb/Index/Middle/Ring/Pinky + Right.
9. **Ctrl+S**, закрыть.

### 6. Создать IK Rig для UE5 Mannequin

Самый простой способ:
1. Content Browser → `Content/Characters/Mannequins/Meshes/` → правый клик на **SKM_Manny_Simple** → **Create → IK Rig**.
2. Имя автоматом `IK_SKM_Manny_Simple`, можно F2 переименовать в `IK_Mannequin`.
3. Двойной клик.
4. В Hierarchy правый клик на **pelvis** (lowercase) → **Set Pelvis**.
5. **Auto Create Retarget Chains**. UE применит template **Fortnite Humanoid** (это и есть UE5 Mannequin skeleton — Epic переиспользует).
6. Проверить что chain names совпадают с IK_Mixamo: Spine, Neck, Head, LeftArm/RightArm, LeftLeg/RightLeg, LeftClavicle, LeftThumb/Index/Middle/Ring/Pinky (+ Right). Обычно совпадают если оба auto-generated по templates.
7. Ctrl+S.

### 7. Создать IK Retargeter

1. Content Browser → `Content/Crew/Animation/IK/` → правый клик → **Animation → Retargeting → IK Retargeter**.
2. Создастся `RTG_New_Retargeter` без диалога. F2 → переименовать в `RTG_Mixamo_to_Mannequin`.
3. Двойной клик.
4. В Details справа → секция **Source** → **Source IKRig Asset** → `IK_Mixamo`.
5. Секция **Target** → **Default Target IK Rig** → `IK_Mannequin`.
6. В viewport появятся две фигуры: слева Peasant Girl, справа Manny.

### 8. Выровнять позу Target под Source (Auto Align)

По дефолту Mixamo скелет в T-pose (руки горизонтально), UE Mannequin — в A-pose (руки под углом 45°). Без выравнивания анимации получатся с вывернутыми руками.

1. В Retargeter editor → вкладка **Target** (слева вверху, рядом с Source).
2. `Current Retarget Pose: Default Pose` — он read-only. Сначала создаём новую pose:
   - Нажать **Create** → имя `TPose_Matched`.
   - В dropdown `Current Retarget Pose` выбрать `TPose_Matched`.
3. Теперь **Auto Align** в toolbar → **Align All Bones**.
4. Alignment Method — **Direction** (default, безопаснее всего).
5. Manny в viewport примет T-pose (руки горизонтально).
6. Ctrl+S.

### 9. Отключить finger chains (пальцы ломаются иначе)

Mixamo и UE Mannequin имеют разные оси вращения пальцев. При ретаргете пальцы скручиваются. Проще отключить retarget пальцев — они останутся в UE default rest pose.

1. Открыть вкладку **Op Stack** (слева вверху, рядом с Hierarchy).
2. В списке op'ов найти родной **FK Chains** (не добавляйте новый, иначе получится конфликт двух FK Chains op'ов).
3. Клик на FK Chains → в Details справа появится **Retarget Chains Settings**.
4. В фильтре поиска чейнов набрать `thumb`, `index`, `middle`, `ring`, `pinky` по очереди — для каждой строки `Left*/Right*` в колонке **Source Chain** выбрать **None**.
5. Также отключить **Metacarpal**-chains (у UE Mannequin есть отдельные кости `index_metacarpal_l` и т.д., если их retargeter тоже ломает):
   - `LeftIndexMetacarpal` → Source Chain = **None**.
   - `LeftMiddleMetacarpal`, `LeftPinkyMetacarpal`, `LeftRingMetacarpal` → None.
   - То же для Right.
6. Ctrl+S.

### 10. Экспорт retargeted анимаций

1. В Retargeter editor → панель **Asset Browser** (слева внизу).
2. Выделить 3 sitting анимации.
3. Кнопка **Export Selected Animations**.
4. Диалог **Export Animations**: Target Path = `/Game/Crew/Animation/Retargeted`, Suffix = `_Manny`.
5. Далее появляется **Batch Export Options**:
   - Overwrite Existing Files: при ре-экспорте (после фикса пальцев) — **ON**. На первом экспорте — OFF норм.
   - Include Referenced Assets: ON.
   - Retain Additive Flags: ON.
6. Export.

Создадутся `Sitting_Idle_Manny`, `Sitting_Talking_Manny`, `Sitting_Disapproval_Manny` на UE Mannequin skeleton.

### 11. Применить к скелетному мешу в сцене

1. Открыть уровень с SKM_Manny_Simple.
2. Details → Animation → **Animation Mode** → `Use Animation Asset`.
3. **Anim to Play** → `Sitting_Idle_Manny`.
4. Ctrl+S.

При PIE Manny будет проигрывать sitting idle в loop.

## Подводные камни

- **Animation Length = Animated Time (UE 5.5+) имеет баг** — создаёт пустые анимации. Всегда ставить `Source Timeline`. [[forum link](https://forums.unrealengine.com/t/5-5-1-animation-settings-on-import/2200864)]
- **«Set Retarget Root» в UE 5.7 называется «Set Pelvis»** — в правом клике в Hierarchy, секция `RETARGETING`.
- **UE 5.6+ переместил Chain Mapping в Op Stack** — отдельной панели больше нет. Ищи в «Op Stack» вкладке, клик на `FK Chains` op → Details.
- **Не создавай новый `Add New Retarget Op → Retarget FK Chains` если уже есть родной FK Chains** — получится два op'а в стеке и они будут противоречить. Редактируй родной.
- **Default Pose — read-only.** Для Auto Align сначала `Create` новую pose, выбрать её, потом Align.
- **Retargeting без T-pose match вывернёт руки** — Mixamo T-pose vs UE Mannequin A-pose. Auto Align → Align All Bones → Direction решает.
- **Пальцы всё равно кривые после Auto Align** — disable finger chains + metacarpal chains в FK Chains op (Source Chain = None).
- **Mixamo forward axis = +Y, UE5 Mannequin forward = +X** — при размещении в сцене SKM_Manny: Rotation Yaw=0 смотрит в +Y (вдоль оси Y), для поворота на +X поставить Yaw=-90°. [[forum link](https://forums.unrealengine.com/t/why-skeletal-meshs-forward-is-y-axis/58481)]
- **Metacarpal chains у UE Mannequin нет в Mixamo** — 4 дополнительных chain у target без source. Оставить как None в Chain Mapping.
- **Re-export после изменений в Retargeter требует Overwrite Existing = ON** — иначе UE пропустит существующие файлы, и изменения не применятся.
- **Peasant Girl texturek/материалы** создадутся при импорте T-Pose With Skin. Не удалять `T-Pose` (SkeletalMesh) — пригодится как Source Preview Mesh в Retargeter.
- **Пропорции Mixamo персонажа не совпадают с Manny** — незначительный клиппинг рук в ноги при сидящей анимации. Не критично, при переносе на MetaHuman (с другими пропорциями) решится отдельно.

## Источники

- [IK Rig Animation Retargeting — UE 5.7 Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine)
- [Retargeting Bipeds with IK Rig — UE 5.7 Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/retargeting-bipeds-with-ik-rig-in-unreal-engine)
- [Auto Retargeting in Unreal Engine — UE 5.7 Documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-retargeting-in-unreal-engine)
- [UNAmedia Mixamo Animation Import Guide](https://www.unamedia.com/ue5-mixamo/docs/import-mixamo-animation-in-ue5/)
- [Manos Miras: Mixamo X Bot to UE 5 Mannequin](https://manosmiras.com/blog/retarget-mixamo-xbot-to-ue5-mannequin/)
- [Forum: Где Chain Mapping в UE 5.6?](https://forums.unrealengine.com/t/do-you-know-where-is-chain-mapping-in-ue-5-6/2583179)
- [Forum: Animated Time bug in UE 5.5.1](https://forums.unrealengine.com/t/5-5-1-animation-settings-on-import/2200864)
- [Forum: Why skeletal mesh's forward is +Y axis](https://forums.unrealengine.com/t/why-skeletal-meshs-forward-is-y-axis/58481)
