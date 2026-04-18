# Ковбойский городок (Акт III)

Цель — компактный, но живой фронтир-городок, без которого «планетная» часть миссии будет пустой. На v0.1 — **одна главная улица длиной 150–200 м, 8–10 зданий, 15–25 NPC, 4–6 лошадей**.

---

## Настроение и стиль

Визуальный референс: смесь классического Weird West с Firefly-добавкой «тех чуть поверх дерева».

- Дерево, железо, керосиновые лампы, вывески кириллицей/китайскими иероглифами (в сериале так).
- Редкие солнечные батареи на крыше, спутниковая тарелка, провода — показать что «это не просто 1880-й, это космофронтир».
- Краска выцветшая, всё в пыли.
- Цветовая палитра: jaune / бледно-коричневый / красновато-оранжевый для неба, белёсое солнце.

---

## Список зданий

Главная улица, от трапа «Serenity» до дальнего конца:

1. **Салун** (`BP_Saloon`) — двустворчатые двери, вывеска, окна с мутным стеклом. Самое шумное место: пианино, голоса, стук стаканов. Внутрь входим или нет? На v0.1 — нет, просто звук и фигурки в окне.
2. **Лавка торговца** (`BP_GeneralStore`) — мешки, бочки, вывеска «ТОВАРЫ» или «商店». Снаружи продавец, подсаживающий NPC.
3. **Шерифский офис + тюрьма** (`BP_Sheriff`) — штат-звезда на двери, скамейка снаружи, шериф (NPC) сидит в кресле-качалке.
4. **Кузница** (`BP_Blacksmith`) — дым из трубы, кузнец бьёт молотом (looping animation), искры (Niagara).
5. **Конюшня / коновязь** (`BP_Stable`) — 3–4 стойла, лошади внутри и привязанные снаружи, сено.
6. **Колодец / водокачка** (`BP_Water`) — ветряк, колесо крутится.
7. **Почта / телеграф** (`BP_Telegraph`) — мелкая постройка с антенной.
8. **Жилые дома** (×2–3) — простые cabin, окна с ламповым светом.
9. **Маленькая церковь / молельня** (`BP_Chapel`) — простой крест, куранты раз в минуту.
10. **Хитчинг post** вдоль улиц — столбики для привязи лошадей и несколько велосипедов (почему нет, на фронтире).

---

## Ассеты — где взять

### Паки (платные, но окупают время)

- **Fab / UE Marketplace «Western Town Bundle»** или аналог — $30–60. Содержит модульные здания.
- **Quixel Megascans** — бесплатны для UE, 1000+ ассетов (дерево, грунт, трава, камни, мусор).
- **Modular Western Props Vol. 1 & 2** — $20–40 каждый.

### Бесплатно

- **Megascans** — бесплатен в UE.
- **Sketchfab CC0** коллекции — всякий мелкий реквизит.
- **Mixamo** — анимации ходьбы / idle NPC.

### Для лошадей

- **Horse Animset Pro** — $40–70, лучшая анимация.
- Меш лошади — **Sketchfab CC0** или **Marketplace** ($10–30).
- **UEFN / Fortnite horse rig** — есть копии с совместимыми scelet.

## PCG (Procedural Content Generation) раскладка

UE 5.x PCG Framework удобно для «улицы с домами». Но на v0.1 **не обязательно** — можно и руками расставить 10 зданий, быстрее.

**Если всё же через PCG:**

`PCG_MainStreet` граф:
```
[SplineInput: BP_StreetSpline]  — кривая по главной улице
         │
         ▼
[SampleSpline 8m step]  — точки через каждые 8 м
         │
         ▼
[FilterByIndex]  — выкидывает каждый 3-й (чтобы были промежутки)
         │
         ▼
[TransformNoise]  — ±0.5 м разброс, ±5° ротация
         │
         ▼
[MeshInstanceSpawner]  — из списка BuildingMeshList (с весами)
```

Плюс — генератор **пропсов вокруг зданий** (бочки, ящики, дрова) через другой граф с точками-семплами внутри bounding box здания.

## NPC

### Список ролей

| Роль | Кол-во | Behavior |
|---|---|---|
| Ковбой / прохожий | 6–8 | Wander → occasional Stop & Look → Wander |
| Торговец у лавки | 1 | Standing Idle, hand gestures, occasional Wave |
| Шериф на крыльце | 1 | Sitting idle |
| Кузнец | 1 | Hammer animation loop |
| Барт у салуна | 1 | Smoking idle, leaning on post |
| Пьяница | 1 | Swaying walk (slow wander) |
| Дама в окне | 1 | Window NPC, simple idle |
| Ребёнок | 1–2 | Faster wander, occasional run |
| Пианист | 1 | Behind window, piano animation loop (рука видна) |

### Skeleton

Не MetaHuman (тяжёлые). Используем **Manny/Quinn** скелет (дефолт UE) или **Paragon characters** (бесплатные в Marketplace). Одежда — меши поверх, ковбойские.

Для 15+ NPC с MetaHuman FPS упадёт значительно.

### Behavior tree

`BT_TownNPC` простой:

```
Root Selector
 ├─ Sequence (Talk)
 │    ├─ Is near other NPC (condition)
 │    ├─ Random 15% chance
 │    └─ Task: Turn to NPC, play "Talking" anim 3-8s
 ├─ Sequence (Wander)
 │    ├─ Task: Find random point in NavMesh (radius 15m)
 │    └─ Task: MoveTo with random speed
 └─ Sequence (Idle)
      └─ Task: Wait 2-5s with random idle anim
```

Параметры NPC (`DataAsset_NPCProfile`):
- WalkSpeed (800–1400 cm/s... шучу: 80–140 для ходьбы)
- IdleAnimSet
- WalkAnim
- TalkChance
- TalkRangeCm
- WanderRadius

## Лошади

Конфигурация:
- 2 лошади у коновязи салуна — `BP_Horse` в `HitchedIdle` state (слегка качают головой, хвостом).
- 1 лошадь в стойле конюшни — ест из кормушки.
- 1 всадник — едет по улице от одного конца к другому, loop через respawn (дёшево).
- На главной площади — ещё 1–2 спокойные лошади без всадников.

`BP_Horse`:
- Components: SkeletalMesh (horse), ABP_Horse.
- States: Idle, Walk, Trot, Gallop, HitchedIdle (к столбику), Rear (редкое удивление).
- Sound: ржание рандомно раз в 20–40 сек (AmbientSound с random trigger).

## Звуковой ambience

`BP_TownAmbience`:

| Слой | Volume | Loop | Spatial |
|---|---|---|---|
| Wind (low) | 0.3 | да | нет |
| Footsteps of offscreen NPC | 0.15 | рандомно triggered | sphere attenuated |
| Distant dog bark | 0.1 | каждые 30-90 сек | 3D attenuated |
| Saloon piano | 0.5 | loop | inside saloon attenuated |
| Blacksmith hammer | 0.4 | sporadic | at blacksmith |
| Horse whinny | 0.3 | random 30-60s | at stable / road |
| Church bell | 0.2 | каждую минуту | at chapel |
| Creaking wood | 0.1 | continuous | random house |

Reverb zone: главная улица — мягкий open-air reverb. Внутри салуна (если заходите) — room reverb.

## Player spawn

Игрок респаунится после синематика у трапа «Serenity». Над трапом маркер «>» указывает в сторону городка.

- Первые 20 м: пустыня, одна дорожка вперёд.
- Справа 100 м — "Serenity" в dust settle state (partial Niagara).
- После первых 30 м — виден силуэт городка на холме.

## Performance

- **Bake** освещение где возможно (static lights для зданий).
- **HLOD** на дальние здания.
- **NavMesh** только на improve streets, не весь ландшафт.
- **Foliage** через `BP_InstancedFoliage` не в BP.
- 15-20 NPC будут держать 60fps на средней железке, 30+ NPC → просадка.

## Чек-лист фазы 7

- [ ] Модульный пак импортирован.
- [ ] 8 зданий на улице с правильными интервалами.
- [ ] Лошади стоят у коновязи, 1 движется по улице.
- [ ] 15 NPC ходят / стоят, разговаривают.
- [ ] Ambience звучит, без резких перепадов громкости.
- [ ] Кузнец анимированно бьёт молотом.
- [ ] Главная улица имеет NavMesh, игрок может пройти насквозь.
- [ ] FPS > 45 на RTX 3060 / 1080p.
