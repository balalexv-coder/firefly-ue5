# Рендер синематика в видео

В UE 5.x **Movie Render Queue** (MRQ) — де-факто стандарт. Windows-билды, однако, из коробки **не умеют** MP4 — нужен workaround через FFmpeg. Ниже пошагово.

---

## Установка и включение

1. Edit → Plugins → найти `Movie Render Queue`, включить, перезапустить UE.
2. Убедиться, что включён `Apple ProRes Media` (на Windows тоже ставится, даёт возможность MOV+ProRes — без потерь).
3. Желательно: включить `Console Variables Editor`, пригодится для настройки качества через cvars.

## Базовый рендер PNG-последовательности

1. Откройте `LS_Landing` в Sequencer.
2. В тулбаре Sequencer → кнопка «Render Movie» с дропдауном → `Render (Movie Render Queue)` (не старый Matinee rendering!).
3. В открывшемся окне **Movie Render Queue**:
   - Left list: ваш sequence.
   - Right: Settings.
4. Config:
   - **Output**: `.png Sequence [8bit]` для превью; `.exr Sequence` для постобработки.
   - **Anti-aliasing**: Temporal Sample Count = 8 (низкое значение — быстрее, выше — меньше шума).
   - **Spatial Sample Count** = 4 (борется с motion blur noise).
   - **Game Overrides** → Cinematic: Shot → убирает LOD staircases.
   - **Deferred Passes** → Final Image only (на первом проходе).
5. Output directory: `<project>/Saved/MovieRenders/LS_Landing/`.
6. Accept → Render.

На 1920×1080, 30 fps, 28 секунд, с 8 TS + 4 SS = **~5-15 минут рендера** на RTX 4070.

## Конвертация в MP4 через FFmpeg

1. Установить FFmpeg: `winget install ffmpeg` или https://ffmpeg.org.
2. В папке с PNG последовательностью:

```bash
ffmpeg -framerate 30 -i "LS_Landing.%04d.png" \
       -c:v libx264 -crf 18 -pix_fmt yuv420p \
       -preset slow \
       LS_Landing_1080p.mp4
```

Для 4K (3840×2160):
```bash
ffmpeg -framerate 30 -i "LS_Landing.%04d.png" \
       -c:v libx264 -crf 20 -pix_fmt yuv420p -preset slow \
       -vf "scale=3840:2160:flags=lanczos" \
       LS_Landing_4k.mp4
```

CRF 18 = near-lossless, ~50-80 Mbps. CRF 23 = YouTube-quality, ~15 Mbps.

## Добавить звук

Если записывали аудио отдельно (MRQ exports PCM WAV):
```bash
ffmpeg -i LS_Landing_1080p.mp4 -i audio.wav \
       -c:v copy -c:a aac -b:a 192k -shortest \
       LS_Landing_final.mp4
```

Если в MRQ писался audio track в тот же .wav в Saved/MovieRenders/ — просто подмержите.

## Вариант «напрямую в ProRes MOV»

Вместо PNG → FFmpeg можно сразу в ProRes (поддерживается на Windows с плагином):
- Output: `.mov (Apple ProRes)`.
- Profile: ProRes 422 HQ.
- Плюс: всё в одном файле с аудио.
- Минус: большой размер (десятки GB).

ProRes MOV → H.264 MP4 потом так же через FFmpeg если нужно.

## Проблемы из практики

### «Рендер запустился, но картинка пустая / чёрная»

- Вероятно, Level Blueprint запускает Sequence только при нажатии какой-то кнопки.
- Решение: в MRQ settings найти **"Game Overrides" → "Start Game Mode" → "No Game Mode"** (или ваш кинематографический GameMode, где Sequence проигрывается сам).

### «Частота рендеринга хаотичная»

- `Lock to Display` в MRQ должно быть **выключено**.
- В Sequencer настройки → Display Rate = Output Framerate в MRQ (например, 30 fps везде).

### «Motion blur слабый / отсутствует»

- В проекте должен быть включён motion blur: Project Settings → Rendering → Motion Blur → Enable.
- В MRQ: Anti-aliasing → **Override Motion Blur** = 0.5 (стандарт).

### «Niagara отстаёт при высоком Temporal Sample Count»

- Niagara использует `deltaTime`, с множеством sub-samples она «взрывается».
- Решение: в Niagara asset → Emitter settings → `Determinism` = true; seed фиксировать.

### «Ошибка `Failed to write frame` — мало места / закрыт writable путь»

- Saved/ иногда на C: ограничен. Вывод в другое место через Output → Output Directory абсолютный путь на D:.

### «На рендере видны швы/лоды MetaHuman'ов»

- Project Settings → Rendering → Skinned Mesh LOD Bias = -1.
- Или в MRQ: Game Overrides → Cinematic LOD = true.

## Бюджет времени на рендер

| Конфиг | Кадр 1080p | Секвенция 28s (840 frames) |
|---|---|---|
| TS 1, SS 1 (preview) | 0.3 s | ~5 min |
| TS 8, SS 1 (draft) | 1.5 s | ~20 min |
| TS 8, SS 4 (final) | 4-8 s | 1–2 hours |
| TS 16, SS 8 (4K final) | 20 s | 3–6 hours |

На RTX 4070 примерно. На слабее железе — в 2-4 раза дольше.

## Альтернатива — OBS screen capture

Быстрее, грязнее:
1. В UE: запустить Sequence через Play In Editor (или уровень).
2. В OBS: записать экран при включённом v-sync.
3. Результат: немного дрожит, но 60 fps и сразу MP4.

Подходит для прототипа / «показать в Discord», не для портфолио.

## Чек-лист перед финальным рендером

- [ ] Все Landscape LOD'ы — на максимум.
- [ ] Niagara seeds зафиксированы.
- [ ] Post Process Volume в Unbound = true.
- [ ] Sequencer track по камере — cut-track (не blended без надобности).
- [ ] Виртуальные Lumens / Nanite проверены в Movie Render.
- [ ] Free disk > 20 GB на output drive.
- [ ] Отключён sleep/hibernate на время рендера.
- [ ] UE закрыл другие hungry плагины (Megascans Browser и т.д.).
