# Lip-sync: варианты и выбор пайплайна

Цель — чтобы губы MetaHuman'а двигались в такт реплике. Рассматриваем 4 варианта от лучшего к самому простому.

---

## 1. NVIDIA Audio2Face (рекомендовано)

**Плюсы:** высочайшее качество, генерирует не только губы, но и полное выражение лица. Бесплатно.

**Минусы:** требует NVIDIA GPU, установки Omniverse (гигабайты), отдельного процесса.

**Пайплайн:**
```
TTS.mp3 → Audio2Face (standalone) → blendshape curves (.usd) → UE import → MetaHuman face
```

**Как подключить:**
1. Скачать **NVIDIA Omniverse Launcher**, установить Audio2Face приложение.
2. В Audio2Face сгенерировать **ARKit-совместимые blendshape curves** (52 стандартные формы лица Apple ARKit).
3. MetaHuman face rig уже поддерживает эти 52 кривые (face board или ARKit Pose Wrangler).
4. Экспорт кривых в **JSON или USD Animation Sequence**, импорт в UE как `Animation Sequence` на MetaHuman face skeleton.
5. Проигрывать как Montage на Face AnimBP.

**Автоматизация:** Omniverse поддерживает headless / python API — можно вызывать из dialogue server после TTS. Батч-режим.

**Лучше всего:** когда проект демо и вы снимаете трейлер. Качество на уровне кинематика.

---

## 2. MetaHuman Animator

**Плюсы:** встроен в UE, качество высокое, не нужен внешний GPU-сервер.

**Минусы:** ориентирован на **mocap видео** (iPhone + LiveLink Face), не на генерацию из аудио. Но есть Audio-driven режим в MH Animator с 5.4+.

**Пайплайн (audio-driven):**
1. В UE: Window → Animation → MetaHuman Animator.
2. Выбрать Audio → select WAV/MP3.
3. Нажать "Process" — получается `Animation Sequence` с ARKit кривыми.
4. Play on MetaHuman face.

**Качество:** хорошее, но слегка хуже A2F. Лучший компромисс «простота / результат».

**Лучше всего:** если не хотите ставить Omniverse.

---

## 3. Oculus Lipsync (OVRLipSync)

**Плюсы:** лёгкий, работает в реал-тайме, не нужен pre-process, open source.

**Минусы:** работает с 15 visemes (не ARKit 52), качество заметно проще. Нужно натягивать visemes на MetaHuman blendshapes через маппинг.

**Пайплайн:**
```
SoundWave → OVRLipSync plugin → viseme weights per frame → MetaHuman facial morphs
```

**Как подключить:**
1. Скачать **OVRLipSync UE plugin** с [oculus.com/developers](https://developer.oculus.com/downloads/package/oculus-lipsync-unreal/).
2. Положить в `Plugins/OVRLipSync/`, включить в Plugins.
3. На MetaHuman face BP добавить компонент `OVRLipSyncActorComponent`.
4. Виско-маппинг (JawOpen, LipFunneler и т.д.) настроить в проекте. Есть community-пресеты для MetaHuman.

**Лучше всего:** если хотите **реал-тайм** липсинк с минимальными задержками, без pre-processing.

---

## 4. Rhubarb Lip Sync

**Плюсы:** open source, CLI, работает на Windows, очень простой.

**Минусы:** 6 базовых форм рта (Hanna-Barbera стиль), качество скорее мультяшное.

**Пайплайн:**
```
audio.wav → rhubarb.exe → mouth shapes JSON → UE blendshapes
```

**Как подключить:** скачать release с GitHub (smacke/rhubarb-lip-sync), вызывать из Python (dialogue server) post-TTS, генерить JSON cue-points, в UE играть через AnimNotify.

**Лучше всего:** бюджетный прототип для проверки интеграции.

---

## Рекомендация

Для этого проекта:

- **v0.1 (прототип):** **MetaHuman Animator** с audio input. Меньше всего движущихся частей: всё в UE.
- **v1.0 (демо-трейлер):** **NVIDIA Audio2Face**. Качественный результат для записи кинематика.

---

## Voice mapping для TTS

Каждому персонажу — свой голос. Вот стартовый маппинг (ElevenLabs — примеры voice_id нужно получить в вашем аккаунте через API).

| Персонаж | Тип | Референс-тон | ElevenLabs (пример категории) | OpenAI fallback |
|---|---|---|---|---|
| Mal   | M / mid / baritone | Sam Elliott «light» | "Antoni" или кастом | `onyx` |
| Zoe   | F / mid / contralto | Spoken word jazz | "Domi" или кастом | `nova` |
| Wash  | M / young / tenor | Conan-lite, быстрый | "Adam" | `alloy` |
| Jayne | M / mid / bass | Bikers grumble | "Josh" | `onyx` |
| Kaylee| F / young / bright | Small town sweet | "Rachel" | `shimmer` |
| Inara | F / mid / warm | Jessica Rabbit calm | "Bella" | `nova` |
| Simon | M / young / baritone | Anglicized, чётко | "Ethan" | `echo` |
| River | F / young / fragile | Детский, тихий | "Emily" / quieter option | `shimmer` |
| Book  | M / older / bass | Morgan Freeman warm | "Paul" | `onyx` |

В `tools/dialogue_server/characters.py` эти значения пишутся как поле `voice_id_elevenlabs` и `voice_id_openai`. Заменяете на реальные id'ы из вашего аккаунта.

## FFmpeg пост-обработка (опционально)

Чтобы голоса были более «радио-Firefly» (корабельная связь):

```bash
ffmpeg -i input.mp3 \
  -af "highpass=f=300,lowpass=f=3400,volume=1.2,atempo=1.0" \
  -c:a libmp3lame -b:a 128k output.mp3
```

Это сужает частотный диапазон под «связь по интеркому». Применять только к тем репликам, которые должны звучать «через экран» — но большинство реплик в живой комнате должны быть чистыми.
