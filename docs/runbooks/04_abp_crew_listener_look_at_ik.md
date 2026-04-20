# 04. ABP_Crew — Listener LookAt IK (голова трекает цель)

**Дата:** 2026-04-20. **UE версия:** 5.7.4.

## Цель

Добавить в `ABP_Crew` постобработку: **bone `head` поворачивается к заданной мировой точке**. Цель задаётся извне через public FVector переменную — в будущем `BP_DialogueManager` будет ставить её на координату головы текущего спикера для всех слушателей.

Итог: слушатели поворачивают голову на говорящего. Если цель (0,0,0) — голова смотрит вперёд (neutral).

## Пререквизиты

- `ABP_Crew` с работающим state machine Idle↔Talking (runbook 03, milestone `747ba46`).
- State machine ноду на главном AnimGraph переименовали в `SM_CrewBody` (или осталось `New State Machine` — неважно).

## Что именно добавим

1. **Переменная `HeadTargetWorld`** (FVector, Instance Editable) — цель в мировых координатах. Извне выставляется на `speaker.mesh.GetSocketLocation("head")`. Default (0,0,0) = «нет цели».
2. **Переменная `HeadTargetCS`** (FVector, private) — та же цель, но в **Component Space** скелета. Пересчитывается каждый тик.
3. **Event Graph logic** — в `Blueprint Update Animation` конвертит World → Component Space и обрабатывает «нет цели» (fallback на взгляд вперёд).
4. **AnimGraph — `Look At` node** — после state machine, перед Output Pose. Поворачивает `head` к `HeadTargetCS`.

## Шаги

### 1. Добавить переменные

Открой `ABP_Crew.uasset`.

**Variable 1 — HeadTargetWorld:**
1. My Blueprint → Variables → `+` → **Name: `HeadTargetWorld`**, **Type: Vector** (не Transform, не Rotator — именно Vector).
2. Details справа:
   - **Instance Editable:** ON.
   - **Blueprint Read Write:** ON.
   - **Default Value:** (0, 0, 0).
   - **Category:** `LookAt` (чтобы в Details сцены эти переменные были в одной группе — удобство).

**Variable 2 — HeadTargetCS:**
1. `+` → **Name: `HeadTargetCS`**, **Type: Vector**.
2. Details:
   - Instance Editable: OFF (приватная, считается внутри).
   - **Category:** `LookAt`.
3. Default не важен, будет перезаписан в Update.

Compile.

### 2. Event Graph — расчёт HeadTargetCS

1. Открой **EventGraph** (раздел Graphs в My Blueprint).
2. Найди ноду **`Event Blueprint Update Animation`** (уже там должна быть, иначе правый клик → поиск). К ней подключён execute pin.
3. **Drag wire** от execute этой ноды в пустоту → правый клик → поиск **`Try Get Pawn Owner`**. Это вернёт Pawn (наш character). Если нет — вернёт null, поэтому делаем guard.
4. **Drag** от output (Pawn) → `Is Valid` → если valid, идём дальше; если нет — пропускаем.

Проще альтернатива (меньше нод) — использовать **`Get Owning Component`** (возвращает SkeletalMeshComponent который owns этот AnimInstance). Это то что нам нужно для World→CS конверсии.

**Цепочка нод:**
1. `Event Blueprint Update Animation` (execute) →
2. `Get Owning Component` → output `Return Value` (SkeletalMeshComponent).
3. От компонента drag → `K2 Inverse Transform Location` (или просто **`InverseTransformLocation`** в поиске) — принимает World Location, возвращает Component-Space Location.
4. На input `Location` этой ноды — подай **`Get HeadTargetWorld`** (перетащи переменную с панели My Blueprint с зажатым Ctrl — получишь Get).
5. Output `InverseTransformLocation` → подключи к **`Set HeadTargetCS`** (перетащи переменную с Alt).

**Обработка zero-target (голова смотрит вперёд когда цели нет):**

Вариант A (минимум): ничего не делаем. Когда HeadTargetWorld=(0,0,0), `HeadTargetCS` окажется где-то под ногами (origin component space), и Look At будет тянуть голову вниз. Некрасиво.

Вариант B (рекомендую): перед InverseTransform сделай проверку:
1. От `Get HeadTargetWorld` → `Vector Length` → сравни с 0.1 через `>` (`Float > Float`).
2. **Branch** — если True (есть цель): идём в ветку с InverseTransform и Set HeadTargetCS.
3. Если False (цели нет): в другой ветке — **Get Owning Component** → `Get Forward Vector` → умножить на 100 (`Vector * Float`) → **это локальная точка «в метре перед персонажем», но в world space**. Её тоже прогнать через InverseTransformLocation → Set HeadTargetCS.

Получается: когда цель есть — голова смотрит на неё; когда нет — голова смотрит на метр вперёд в neutral.

### 3. AnimGraph — добавить Look At

1. Открой **AnimGraph**.
2. Сейчас: `SM_CrewBody` (state machine) → `Output Pose`. Нужно вставить Look At **между** ними.
3. Клик на wire между SM_CrewBody и Output Pose → Delete.
4. Правый клик в пустом месте → поиск **`Look At`** → выбрать ноду **`Look At`** (должна быть в категории «Skeletal Controls»).
5. Соедини: **`SM_CrewBody` (output)** → **`Look At` (Source Pose / Component Pose input)** → **`Output Pose` (Result)**.

### 4. Настроить Look At параметры

Выдели ноду Look At → Details справа. Выставь:

| Параметр | Значение | Комментарий |
|----------|----------|-------------|
| **Bone to Modify** | `head` | Главная кость. |
| **Look At Bone** | (empty) | Не используем, у нас точка. |
| **Look At Socket** | (empty) | Тоже не используем. |
| **Look At Location** | (подключить к переменной) | Drag `Get HeadTargetCS` из My Blueprint → на input pin `Look At Location`. |
| **Look At Axis** | `Y Axis` (starting point) | ⚠️ Forward axis головы может быть +X или +Y — проверим в runtime, если голова смотрит вбок — переключим. |
| **Use Look Up Axis** | ON | Иначе голова будет крутиться вокруг оси взгляда. |
| **Look Up Axis** | `Z Axis` | Мир — UE стандарт, Z — up. |
| **Look At Clamp** | `60` | Максимум 60° от neutral. Больше — смотрится неестественно. |
| **Interpolation Type** | `Ease In Out` | Плавное начало/конец движения. |
| **Interpolation Time** | `0.25` | Четверть секунды на плавный поворот. |
| **Interpolation Trigger Threshold** | `0` | Dead-zone на старте (по умолчанию 0, не трогаем). |

Compile. Save.

### 5. Sanity-тест: поставить фиктивную цель, посмотреть поворот

Самый быстрый способ — временно задать Default Value переменной `HeadTargetWorld`:

1. My Blueprint → `HeadTargetWorld` → Default Value = **(0, 200, 160)** (200 см справа от origin, 160 см вверх — примерно высота головы на пол-шага вбок).
2. Compile.
3. Переключись в **L_SerenityCabin** (не Play, just viewport).
4. Посмотри на всех 4 персонажей — их головы должны повернуться **вправо**, к точке (0, 200, 160).

**Интерпретация результата:**

| Что видишь | Значит |
|------------|--------|
| Головы повернулись к точке в мире (все на одну точку смотрят) | ✅ Работает, axis правильный |
| Головы смотрят вбок но не на точку | Forward axis перепутан — зайди в Details ноды Look At → поменяй `Look At Axis` с `Y Axis` на `X Axis`, compile, проверь снова. Если не помогло — попробуй `-X`, `-Y`. |
| Головы наклонились вниз / вверх странно | Use Look Up Axis выключен или Look Up Axis на неправильной оси. Должно быть ON + Z Axis. |
| Ничего не изменилось | Look At не получает данные. Проверь что wire `Get HeadTargetCS` идёт в input `Look At Location`. |

**После успешного теста** — верни Default Value **HeadTargetWorld → (0, 0, 0)**, Compile, Save. Это подготовленное состояние для шага 2B (внешний драйвер из BP_DialogueManager).

## Подводные камни

- **World vs Component Space.** Cамая частая ошибка по форумам UE 5.x. Если забыть InverseTransformLocation и прокинуть world-координату напрямую в Look At — голова будет смотреть «в угол мира» а не на цель. У нас это решается конверсией в Event Graph.
- **Forward axis головы.** Для UE5 Mannequin / MetaHuman skeleton он может быть +X или +Y в local bone space — **документация не однозначна**. Проверяй в runtime, см. таблицу в шаге 5.
- **Очерёдность в AnimGraph критична.** Look At должна стоять **после** state machine (Idle/Talking) — мы это и делаем. Если поставить до — анимация поверх Look At'а «съест» поворот.
- **Layered Blend Per Bone upstream** может сломать Look At — но у нас такого нет.
- **HeadTargetWorld=(0,0,0)** как «нет цели» — хрупкий sentinel. Если персонаж реально окажется на (0,0,0) — баг. Для v1 ок (у нас все на Z=0 но X,Y смещены), для полировки — лучше завести bool `HasHeadTarget`.
- **«Пустой поворот» в начале.** При старте Interpolation может «вытянуть» голову из дефолта плавно — выглядит как подёргивание. Increase Interpolation Time до 0.5с если заметно.

## Что получим после этого шага

- Каждый из 4 персонажей имеет `HeadTargetWorld` переменную на своём AnimInstance.
- Снаружи (BP_DialogueManager в будущем) прописываешь `mal.AnimInstance.HeadTargetWorld = speaker.head.WorldLocation` — голова плавно поворачивается.
- Когда цель не задана — голова смотрит вперёд (neutral).

## Отложенное (для шага 2B)

- **BP_DialogueManager** (новый actor или расширение FireflyDialogueFlow) — слушает события начала/конца реплики, назначает HeadTargetWorld всем не-спикерам на `speaker.mesh.GetSocketLocation("head")`, спикеру — на `addressee.head` (из step 3/4).
- **Добавочный LookAt на `neck_01`** (clamp 20-25°) — для более натурального поворота с задействованием шеи, не только черепа.

## Источники

- [Animation Blueprint Head Look At — UE 5.7 docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-head-look-at-in-unreal-engine)
- [Look At — UE 4.27 node reference (параметры те же в 5.x)](https://docs.unrealengine.com/4.27/en-US/AnimatingObjects/SkeletalMeshAnimation/NodeReference/SkeletalControls/LookAt/)
- [Skeletons in Unreal Engine — Epic humanoid bone naming](https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletons-in-unreal-engine)
- [UE 5.7 forum: LookAt head/neck twist direction issues](https://forums.unrealengine.com/t/ue-5-7-animbp-lookat-with-transform-modify-bone-head-neck-twist-wrong-direction-can-t-get-stable-fixated-look-at-target/2700861)
- [Forum: specifying custom forward axis for Look At](https://forums.unrealengine.com/t/anim-graph-look-at-node-how-to-tell-it-i-have-a-different-fwd-axis/2652467)
