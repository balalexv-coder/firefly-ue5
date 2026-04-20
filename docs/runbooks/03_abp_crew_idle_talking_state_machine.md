# 03. ABP_Crew — state machine Idle ↔ Talking

**Дата:** 2026-04-20. **UE версия:** 5.7.4.

## Цель

Заменить статичный Sitting_Idle в ABP_Crew на state machine с переключением между:
- **Idle** — Sitting_Idle_Manny (спокойное сидение).
- **Talking** — Sitting_Talking_Manny (жестикуляция, покачивания).

Переключение управляется переменной **IsSpeaking** (bool) на AnimBlueprint. Character Blueprint (BP_Mal / BP_Zoe / BP_Wash / BP_Inara) будет выставлять её извне когда этот конкретный crew member говорит.

Результат: во время речи персонаж выглядит живым (руки двигаются, корпус чуть качается), а не висит в Idle как статуя.

## Пререквизиты

- `ABP_Crew` уже существует и работает (Sitting_Idle играет через Live Retarget на MetaHuman'ов) — см. milestone `bc9d8e3`.
- `Sitting_Talking_Manny.uasset` ретаргечен и лежит в `Content/Crew/Animation/Retargeted/`.

## Семантическая подсказка по UE 5.7 UI

В UE 5.7 точные названия пунктов right-click меню могут отличаться от туториалов на YouTube (часто UE 5.2-5.4). Если инструкция говорит «найди опцию `X`» и такой опции нет — **ищи по смыслу** (часто переименовывается на близкое). Скриншот в чат → быстрее чем слепой гугл.

## Шаги

### 1. Объявить переменную IsSpeaking на ABP_Crew

1. Открой `Content/Crew/Animation/AnimBP/ABP_Crew.uasset` (двойной клик).
2. Слева в панели **My Blueprint** → раздел **Variables** → кнопка **`+`** (Add Variable).
3. Имя: **`IsSpeaking`**, тип: **Boolean** (в выпадашке справа от имени).
4. **Default Value:** False (в Details справа после compile).
5. **Instance Editable:** ON (чекбокс в Details — чтобы извне можно было писать).
6. **Blueprint Read Write:** ON (чтобы BP_Mal и т.д. могли её менять).
7. Compile (кнопка вверху).

### 2. Открыть AnimGraph и убрать старый wire

1. В My Blueprint → раздел **Graphs** → **AnimGraph** (двойной клик).
2. Увидишь текущий граф: `Sitting_Idle_Manny` (Sequence Player нода) → `Output Pose` (Final Animation Pose).
3. Нажми Alt+клик по wire'у между ними — wire удалится. Или удали саму Sequence Player ноду (клик на неё → Delete).

Не удаляй `Output Pose` — она одна на граф.

### 3. Создать state machine

1. Правый клик в пустом месте AnimGraph.
2. В поиске набери **`state machine`**.
3. Выбери опцию «**Add New State Machine**» (или похожую по смыслу — «New State Machine», «State Machine»). В UE 5.7 это обычно первый результат поиска по «state machine».
4. Появится новая нода с пиктограммой state machine'а. Назови её **`SM_CrewBody`** (клик по имени на ноде → rename) — удобнее потом искать.
5. Соедини **output pin** этой ноды со входом **`Output Pose`** (drag wire).

### 4. Зайти в state machine и добавить состояния Idle + Talking

1. Двойной клик по ноде `SM_CrewBody` — откроется редактор state machine с одной нодой **`Entry`**.
2. Правый клик в пустом месте → **Add State** (или похожее). Назови состояние **`Idle`**.
3. Повтори — добавь состояние **`Talking`**.
4. Drag wire от **`Entry`** → **`Idle`** (начальное состояние после старта).

### 5. Заполнить содержимое состояний анимациями

**Состояние Idle:**
1. Двойной клик по `Idle` state → откроется его внутренний граф.
2. Из Content Browser **перетащи** `Sitting_Idle_Manny.uasset` прямо в граф. Появится нода **Sequence Player** с этой анимацией.
3. В Details ноды:
   - **Loop Animation:** True (чтобы играло бесконечно).
   - **Play Rate:** 1.0.
4. Соедини output этой ноды с **`Output Animation Pose`** (или как она называется в 5.7 — это финальная нода состояния).

**Состояние Talking:**
1. Вернись в state machine editor (breadcrumb вверху или клик по иконке `SM_CrewBody` в навигации).
2. Двойной клик по `Talking` state.
3. Перетащи `Sitting_Talking_Manny.uasset` в граф.
4. Loop=True, Play Rate=1.0.
5. Соедини с `Output Animation Pose`.

### 6. Добавить переходы (transitions)

Переходы — это стрелки между состояниями с условиями.

1. Вернись в state machine editor.
2. **Drag** от границы `Idle` state → к `Talking` state. Появится стрелка-переход.
3. Двойной клик по маленькой круглой иконке на стрелке (это *transition rule*) — откроется граф с одной нодой `Result` (Can Enter Transition, Bool).
4. Правый клик → поиск **`IsSpeaking`** → **Get IsSpeaking** (получить значение переменной).
5. Соедини output `IsSpeaking` с input `Result`.
6. Transition rule готов: «Переходить из Idle в Talking, когда IsSpeaking=true».

**Обратный переход (Talking → Idle):**
1. Drag от `Talking` → `Idle`.
2. Двойной клик на transition rule.
3. **Get IsSpeaking** → **NOT Boolean** (правый клик → `not`) → **Result**.
4. Rule: «Переходить обратно когда IsSpeaking=false».

### 7. Настроить blend time переходов (сглаживание)

Без этого переключение будет резким (поп-анимация).

1. Клик на стрелку-переход Idle → Talking.
2. Details справа → **Duration** (или **Transition Duration**): **0.2** сек. Это кросс-фейд между состояниями.
3. То же для обратного перехода.

### 8. Compile + Save + Test

1. Кнопка **Compile** вверху — если ошибок нет, галочка зелёная.
2. Save (Ctrl+S).
3. Возвращайся в L_SerenityCabin → Play in Editor.
4. Все 4 персонажа должны сидеть в Idle (пока никто не говорит, IsSpeaking=false везде).

### 9. Ручной тест: включить Talking у одного персонажа

Быстрый способ проверить что state machine работает без подключения dialogue dispatcher'а:

1. В Editor (не в Play mode) — выбери `Mal_MetaHuman` в Outliner.
2. Details → найди component **MetaHuman** (или тот, к которому прикреплён ABP через Retarget Orig Anim Class).
3. Ищи категорию свойств **Anim** или **Animation** → свойство **Is Speaking** (наша переменная, exposed через Instance Editable) — **ON**.
4. Запусти Play — Mal должен играть Sitting_Talking вместо Idle.

Если `Is Speaking` не видна в Details — переменная не exposed. Вернись к шагу 1.5 и проверь Instance Editable.

## Подводные камни

- **State Machine не появляется в поиске right-click** → возможно надо переключиться в режим AnimGraph (не в Event Graph или Functions). Проверь что ты именно в AnimGraph tab.
- **Sequence Player'у нужно назначить анимацию** — если перетащил asset из Content Browser, но ноду создал вручную (через right-click → Sequence Player), не забудь в её Details указать **Sequence** = `Sitting_Idle_Manny` / `Sitting_Talking_Manny`.
- **Transition rule blueprint пустой после создания** — это нормально. Надо **двойным кликом по маленькому кружку на стрелке**, а не по самой стрелке (клик по стрелке просто её выделяет).
- **`NOT Boolean` нода называется в UE 5.7 «Not Boolean» в поиске, но на холсте отображается как `NOT`.** Не пугайся.
- **Transition не срабатывает при IsSpeaking=true** → проверь что rule reading *правильную* переменную (если есть копии — выдели ноду и в Details посмотри, какая переменная).
- **Duration=0 → пугающий «щёлк» при смене** — ставь минимум 0.15-0.25.
- **Live Retarget на MetaHuman'ах** использует этот самый ABP_Crew через Retarget Orig Anim Class → наши изменения автоматически применятся ко всем 4. Отдельно для MetaHuman-скелета ничего настраивать не нужно.

## Что получим

- Все 4 crew member'а делят один `ABP_Crew` (экономия).
- Каждый имеет свой `IsSpeaking` bool (независимый, потому что AnimInstance персонален).
- BP_FireflyDialogueFlow в будущем будет переключать `IsSpeaking` на нужном персонаже в момент play line.

## Отложенное (iteration 2)

- **Рандомизация Talking анимаций** — сейчас всегда Sitting_Talking_Manny. Когда докачаем Sitting_Talking_2 / Sitting_Disapproval_Manny как альтернативы, заменим Sequence Player в состоянии Talking на **Blend List by Int** (индекс = random на entry) или на несколько sub-state'ов с рандомной transition.
- **Жестикуляция по эмоции** — LLM возвращает поле `emotion` (calm/gruff/amused/serious/...). Когда будет 3-5 Talking анимаций, emotion → выбор конкретной.

## Источники

- [Animation Blueprint Node Functions — UE Docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-node-functions-in-unreal-engine)
- [State Machines in Unreal Engine — UE Docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/state-machines-in-unreal-engine)
