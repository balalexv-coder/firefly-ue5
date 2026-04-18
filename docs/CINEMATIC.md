# Синематик посадки «Serenity»

Детали реализации Акта II — см. общий шот-лист в [SCENES.md](SCENES.md#акт-ii--синематик-посадки-30-сек).

---

## Идея

«Serenity» не садится «вертолётом» сверху вниз, как Falcon или СК-61. Она:
1. Входит в атмосферу по пологой траектории, носом вперёд.
2. Снижается над пейзажем на крейсерском режиме.
3. Двигатели-гондолы (две по бокам) поворачиваются **из горизонтального положения в вертикальное (VTOL)**.
4. Корабль переходит в висение над точкой приземления.
5. Плавно садится на шасси.

Это канон сериала — смотрите опенинг, серию «Out of Gas», серию «Objects in Space». Ключевые моменты:
- Гондолы видимо поворачиваются (на шарнирах).
- Двигатели излучают тёплый оранжево-жёлтый свет снизу при висении.
- Поднятая пыль — большое, почти непрозрачное облако.

---

## Rigging корабля

Ваш mesh Serenity (у вас уже есть «нормальный снаружи»):

1. В Blender (или любом DCC) разделите mesh на:
   - `Serenity_Hull` — основной корпус.
   - `Engine_L` — левая гондола (pivot на оси вращения).
   - `Engine_R` — правая гондола.
2. Экспорт в FBX с иерархией. Pivot гондол должен быть на реальной оси шарниров.
3. В UE импортировать как **Skeletal Mesh** с простейшим скелетом: root → hull_bone → engine_L_bone + engine_R_bone. Либо — как Static Mesh группу с отдельными компонентами в Actor.
4. Создать `BP_SerenityShip`:
   - 3 Static Mesh компонента: Hull, Engine_L, Engine_R.
   - Переменная `EngineRotation` (0 = cruise, 90 = hover).
   - В Construction Script: `Engine_L.SetRelativeRotation(FRotator(EngineRotation, 0, 0))`.
   - Exposed в Sequencer для keyframing.

## Ключевые шоты (детализация)

### Shot 2.A — Atmospheric entry (0–6 сек)

- Камера: боковой план, слегка сзади-сверху. Движется параллельно кораблю.
- Корабль: наклон 10–15° нос вниз, скорость очевидна.
- Эффекты:
  - `NS_EntryHeat` на вентральной части — оранжевый плазменный след, постепенно слабеет.
  - Lens: легкий lens flare от солнца.
- Фон: 20 км воздуха, внизу — верхушки дюн в дымке.
- Свет: сильный контровой свет (entry angle).

### Shot 2.B — Cruise over terrain (6–14 сек)

- Камера: низко над землёй (30 м), ровно, корабль проходит сверху.
- Наклон корабля: выравнивается до 0°.
- **Гондолы начинают поворот** (animated 0° → 45° в течение этих 8 секунд).
- `NS_EngineExhaust`:
  - При 0° — длинная реактивная струя назад.
  - При 45° — начинает направляться под корабль.
- Shadow: чёткая тень корабля бежит по дюнам.
- Звук: низкий гул двигателей.

### Shot 2.C — Hover descent (14–22 сек)

- Камера: от земли вверх (worm's eye), корабль заполняет верхнюю треть кадра.
- Гондолы: 45° → 90° (полностью вниз).
- Корабль: теряет forward velocity, начинает снижаться (0.5–1 м/с).
- `NS_EngineExhaust`:
  - Широкие жёлто-оранжевые струи вниз.
  - Видимое искажение воздуха (heat haze).
- `NS_LandingDust`:
  - Начинается со скромного облачка под соплами.
  - Нарастает до gigantic волны пыли, захлёстывающей кадр.
- Звук: нарастающий рёв.

### Shot 2.D — Touchdown + dust settle (22–28 сек)

- Камера: средний план сбоку. Видно только пыль, из неё проступает силуэт на грунте.
- Корабль: шасси выпущены, касание земли.
- Эффекты: пыль начинает оседать. Сопла затухают.
- Звук: двигатели глохнут каскадом (F1-shutdown стиль), cooling-гудение, металл трещит, ветер.
- Переход: fade to black или through-dust-wipe.

---

## Niagara систем подробнее

### NS_EntryHeat
- Emitter 1: длинный трейл плазмы — yellow/orange, stretched particles, fades.
- Emitter 2: mini sparks — random hot debris.
- Параметр `Intensity` (0–1), анимируемый в Sequencer.

### NS_EngineExhaust (attached to each Engine_L / Engine_R)
- Один системы на гондолу, на socket `Nozzle`.
- Параметры:
  - `Throttle` (0–1) — интенсивность.
  - `AngleFactor` — когда гондола повёрнута, меняет направление.
  - `GroundProximity` — если близко к земле, струя «расплющивается» (ground effect).

### NS_LandingDust
- Привязана к земле под кораблём.
- Параметры:
  - `Activate` (boolean).
  - `Ramp` (0–1) — нарастание.
  - `WindDirection` — лёгкий дрейф.
- Структура:
  - Ground particles: wide radial bursts, brown/tan, long lifetime.
  - Airborne: sparse dust, darker.
  - Debris: редкие камни, vegetation fragments.

---

## Звук

Многослойный:

| Слой | Пример источника | Roll-in | Roll-out |
|---|---|---|---|
| Atmospheric howl (ветер при re-entry) | `Wind_High_Altitude.wav` | 0s | 8s |
| Engine cruise hum | `Engine_Cruise_Loop.wav` | 4s | 18s |
| Engine hover roar | `Engine_Hover_Loop.wav` | 16s | 27s |
| Nozzle angle change (servo) | `Servo_Heavy.wav` | 8s, 12s | impulse |
| Touchdown thump | `Ship_Land_Heavy.wav` | 25s | impulse |
| Shutdown cascade | `Engine_Cooldown.wav` | 26s | 32s |
| Ambience (wind + birds) | `Desert_Ambience.wav` | 27s | → next level |

Используйте **MetaSounds** в UE 5.x для модуляции (doppler, random pitch на engine).

---

## Sequencer structure

`LS_Landing` (LevelSequence):

```
Track: Camera
  ├─ CineCamera_A (0s – 6s)    — side crane
  ├─ CineCamera_B (6s – 14s)   — low follow
  ├─ CineCamera_C (14s – 22s)  — worm's eye
  └─ CineCamera_D (22s – 28s)  — side medium

Track: BP_SerenityShip
  ├─ Transform (whole duration) — path from high-altitude entry to ground
  └─ EngineRotation float       — 0 → 45 → 90

Track: NS_EntryHeat (spawnable, active 0-8s)
  └─ Intensity float            — fade in/out

Track: NS_EngineExhaust_L / _R (attached to ship engines)
  └─ Throttle float
  └─ AngleFactor float

Track: NS_LandingDust (spawnable at landing spot, active 14-30s)
  └─ Ramp float

Track: Audio
  └─ (layers above)

Track: Fade
  └─ 0s: from black (1s)
  └─ 27s: to black (2s)

Track: Events
  └─ 28s: Trigger "LandingComplete" → Level Blueprint loads L_Town
```

## Как тестировать без всех ассетов

Пока нет кораблика с риггингом:
- Используйте `StarterContent / Shape_Cube` как proxy.
- Niagara systems можно собрать до финальной модели — параметры работают с любым mesh.
- Ландшафт — sculpt пустыня, material из Megascans Desert Sand.

## Альтернативное направление

Если не хотите возиться с риггингом двигателей — **фиксированный angle**, двигатели всегда повёрнуты на 30°. Тогда корабль «полуVTOL» — не хуже, чем в сериале смотрится. Но оригинальный вариант с поворотом — визуально нагляднее, «в стиле».
