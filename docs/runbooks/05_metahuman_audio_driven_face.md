# 05. MetaHuman Audio-Driven Face Animation — pipeline и gotcha

**Дата:** 2026-05-03. **UE версия:** 5.7.4. **MetaHuman plugin:** включён через Edit → Plugins → "MetaHuman".

## Цель

Озвучка персонажа (WAV из dialogue server) → автоматический lipsync на лице MetaHuman без записи MoCap, без NVIDIA Audio2Face, без облачных сервисов. Использует встроенную в UE 5.5+ фичу **MetaHuman Performance: Audio Input**.

Pipeline:

```
TTS (edge-tts, 22050 Hz mono 16-bit WAV)
  → импорт в Content/Audio/Dialogue/Test/ как SoundWave
  → MetaHuman Performance asset (Input Type = Audio)
  → Process → 260 face curves (CTRL_expressions_*, jaw, mouth)
  → Export Animation → AnimSequence на Face_Archetype_Skeleton
  → проигрывание на Mal_MetaHuman.Face через Sequencer / runtime
```

## Статус (Step 6B)

| Этап | Статус |
|---|---|
| WAV генерация (`tts.py output_format=wav`) | ✅ closed |
| Импорт WAV в UE как SoundWave | ✅ closed |
| Создание MetaHuman Performance asset | ✅ closed |
| Process → curves сгенерированы | ✅ closed (260 curves подтверждено в Persona) |
| Export Animation Sequence | ✅ closed (`A_Mal_Demo_Lipsync` на Face_Archetype) |
| Воспроизведение в Persona standalone | ✅ closed (рот/брови двигаются) |
| **Воспроизведение на полном Mal'е (с телом) в уровне** | ⚠️ **частично** — см. ниже |

## Главный gotcha — Face_AnimBP swallows curves

**Симптом:** При помещении `A_Mal_Demo_Lipsync` в Sequencer на компонент `Face` MetaHuman'а — рот/лицо не двигаются. При этом ровно тот же AnimSequence в Persona на превью-меше работает.

**Причина:** MetaHuman `Face_AnimBP_C` спроектирован под **Live Link face capture** (поток curve-данных извне). Он не имеет Sequencer-aware slot и просто перетирает curves своими (которые в нашем случае пустые, потому что Live Link не подключён).

**Подтверждение workflow'a:** если у `Face` компонента переключить **Animation Mode → Use Animation Asset** и подставить `A_Mal_Demo_Lipsync`, рот двигается. Но при этом Face теряет привязку к head bone Body и **отделяется от тела** (голова "плавает" в air space на high Z). Это второй gotcha — Face SkeletalMeshComponent у MetaHuman'а зависит от runtime-логики Face_AnimBP для master-pose / follow-body, и override AnimMode эту логику отключает.

**Резюме:** оба варианта по отдельности не работают. Для финального решения нужно одно из:

| Вариант | Усилия | Минусы |
|---|---|---|
| **A. Custom Face_AnimBP slot** — модифицировать AnimBP добавив `DefaultSlot` ноду через которую инжектируется Sequencer-анимация. После — `A_Mal_Demo_Lipsync` течёт через AnimBP, post-process работает, тело не отделяется. | Средне (1-2 ч; нужен duplicate `Face_AnimBP` под наш проект) | Нужно поддерживать форк AnimBP при апдейтах MetaHuman |
| **B. Sequencer Attach Track + Override Mode** — оставить Face Animation Mode = Use Animation Asset (рот двигается, голова отделяется), и в Sequencer добавить **Attach Track** на Face компонент → пристегнуть к `Body` socket `head`. | Малые (30 мин на актора, повторяется в каждом Level Sequence) | Workaround, не runtime-решение — годится для cinematics, не для динамических dialogue реплик |
| **C. Anim Sub Instance / Linked AnimBP** — UE 5.x поддерживает `Linked Anim Graph` который позволяет подменять часть AnimBP на другой граф в runtime. Можно сделать `Face_AnimBP_Lipsync` который проигрывает curves из переменной AnimSequence. | Высокие (2-3 ч на освоение Linked AnimBP в контексте MetaHuman) | Сложно отлаживать, риск задеть LOD/streaming setup MetaHuman'а |

**Текущий план:** идти на **A (Custom Face_AnimBP slot)** для polish-итерации, потому что это единственный вариант, который позволит **runtime воспроизводить lipsync во время dialogue без preset Level Sequence'ов**. Без этого dialogue server бесполезен для face animation.

## Step-by-step (что закрыто)

### 1. Включить MetaHuman plugin
- **Edit → Plugins** → поиск `MetaHuman` → включить плагин **"MetaHuman"** (не "MetaHuman SDK", это legacy).
- Перезапустить редактор.

### 2. Сгенерировать WAV (не MP3)
В `tools/dialogue_server/`:

```python
from tts import EdgeTTSBackend
backend = EdgeTTSBackend(output_format="wav")  # или TTS_OUTPUT_FORMAT=wav в env
wav = backend.synthesize(text="...", character_key="Mal", output_dir=Path("./out"))
# → 22050 Hz mono 16-bit PCM
```

### 3. Импортировать WAV в Content
Скопировать `.wav` в `UnrealProject/Content/Audio/Dialogue/Test/` (или drag&drop в Content Browser). UE auto-import создаёт `SoundWave` ассет.

### 4. Создать MetaHuman Performance asset
- Content Browser → правый клик в пустоте → **MetaHuman → MetaHuman Performance**.
- Имя: `MHP_<character>_<line>` (напр. `MHP_Mal_Demo`).
- Открывается редактор Performance (в окне сверху menu bar появляется **MetaHuman Animator**).

### 5. Настройки Performance
В Details панели:
- **Data → Input Type:** `Audio`
- **Audio:** drag `SoundWave` ассет в это поле.
- **Visualization → Control Rig:** опционально (для preview в редакторе; не нужно для генерации curves).

### 6. Process
Кнопка **Process** на верхней панели редактора Performance. Время: ~30 сек на 16-секундный WAV.

После — на тайм-лайне внизу появятся frames с данными.

### 7. Export Animation
Кнопка **Export Animation** на верхней панели. Сохранить как `A_<character>_<line>_Lipsync` рядом с Performance ассетом.

Skeleton автоматически выставляется в `Face_Archetype_Skeleton` (стандартный MetaHuman face skeleton).

### 8. Verify в Persona
Двойной клик на `A_*_Lipsync` → откроется Animation Editor. Жми Play. Должны:
- Двигаться кости/curves (видно на превью-меше: jaw, mouth, brow shapes).
- Внизу в Curves секции отображаться ~260 curves (CTRL_expressions_*, ...).
- Виден баннер: "Post process Animation Blueprint 'Face_PostProcess_AnimBP' is running" — это норма.

## Open question — на следующую сессию

Реализовать **вариант A (Custom Face_AnimBP slot)**:

1. Найти `Face_AnimBP` в `Content/MetaHumans/Common/Face/` (или похоже).
2. Сделать `Duplicate` → `Face_AnimBP_Lipsync` (или `ABP_FireflyFace`).
3. В AnimGraph после Live Link / Default flow добавить **Slot** ноду с именем `LipsyncSlot`.
4. На каждом MetaHuman BP (BP_Mal/Zoe/Wash/Inara) переключить Anim Class у компонента `Face` на новый AnimBP.
5. В Sequencer Animation track на Face → теперь curves инжектируются в `LipsyncSlot` и доходят до post-process AnimBP.

Альтернативно — runtime `Play Anim Slot` через C++ или Blueprint когда dialogue server возвращает audio_url + AnimSequence path.

## Артефакты в репо

- `UnrealProject/Content/Audio/Dialogue/Test/mal_demo_long.wav` — source WAV (16 sec, "Two hours to atmo, folks…")
- `UnrealProject/Content/Audio/Dialogue/Test/mal_demo_long.uasset` — SoundWave
- `UnrealProject/Content/Audio/Dialogue/Test/MHP_Mal_Demo.uasset` — MetaHuman Performance
- `UnrealProject/Content/Audio/Dialogue/Test/A_Mal_Demo_Lipsync.uasset` — exported AnimSequence (260 curves)
- `UnrealProject/Content/Cinematics/LS_Test_Mal_Lipsync.uasset` — тестовый Level Sequence (демонстрирует gotcha; не финальное решение)

## Ссылки

- [MetaHuman Audio-Driven Animation — official docs](https://dev.epicgames.com/documentation/en-us/metahuman/audio-driven-animation)
- [MetaHuman Performance Asset — official docs](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-performance-asset)
- [MetaHuman 5.7 Release — feature list](https://www.metahuman.com/releases/metahuman-5-7-is-now-available)
- [UE Forum — Can't create MetaHuman Performance asset (plugin enable)](https://forums.unrealengine.com/t/cant-create-metahuman-performance-asset-in-5-5-0/2132487/2)
- [Community tutorial — Adding Expressive Performance to MetaHuman Audio Face Animations UE 5.5](https://forums.unrealengine.com/t/community-tutorial-adding-expressive-performance-to-metahuman-audio-face-animations-in-unreal-engine-5-5/2296328)
