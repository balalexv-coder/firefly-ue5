# Session notes — 2026-04-20/21 (compact handoff)

Эта заметка — спасательный круг на случай очистки контекста через `/compact`. Ниже — текущее состояние, критические решения, и что делать дальше.

## Что сделано за сессию (6 коммитов)

```
2e0c5f9  Step 6 v1: TTS pipeline via edge-tts (2-voice placeholder)
a342b5a  ABP_Crew step 2 closed: head LookAt (workable, not perfect)
4a6f668  ABP_Crew step 2A: Look At scaffolding (axis tuning blocked)
747ba46  ABP_Crew step 1: Idle ↔ Talking state machine (IsSpeaking bool)
9dfcdc3  Smoke tests for dialogue server active-crew scope
7c8268a  4-character scene: Zoe/Wash/Inara MetaHumans + dialogue narrowed 9→4
bc9d8e3  Mal MetaHuman via Bridge + Live Retarget validated  (предыдущий день)
```

## Текущее состояние проекта

### UE scene (L_SerenityCabin)

4 MetaHuman'а на канонических позициях (см. `docs/SCENES.md`):
- **Mal_MetaHuman** (BP_Mal) at (-220, 10, 0), Yaw=-90°
- **BP_Zoe** at (-60, -90, 0), Yaw=0°
- **BP_Wash** at (-60, 110, 0), Yaw=180°
- **BP_Inara** at (100, 110, 0), Yaw=180°

Все используют общий `ABP_Crew` через MetaHuman Live Retarget (`Retarget Orig Anim Class`).

### ABP_Crew (Content/Crew/Animation/AnimBP/)

- **Variables:** `IsSpeaking` (Bool), `HeadTargetWorld` (Vector), `HeadTargetCS` (Vector)
- **State machine** `SM_CrewBody`: Idle ↔ Talking через IsSpeaking bool, 0.2s blend, Sitting_Idle_Manny / Sitting_Talking_Manny
- **Look At node** после state machine:
  - Bone: `head`
  - Axis: (0, 0, 1), In Local Space ON
  - Up Axis: (1, 0, 0), In Local Space ON
  - Clamp 70, Interp 0.25s (Ease in Out Exponent 2)
  - **Alpha = 1.0 LITERAL** (не Pin, не Dynamic — иначе UE silently ставит 0)
- **Event Graph:** world→CS конверсия HeadTargetWorld через Get Owning Component → Get World Transform → Inverse Transform Location

### Dialogue server (tools/dialogue_server/)

- **LLM**: Ollama + qwen3.5:9b (default), Anthropic backend доступен через env
- **Active crew**: 4 (Mal/Zoe/Wash/Inara) через `ACTIVE_KEYS` в `characters.py`
- **TTS**: edge-tts с 2-голосной заглушкой (en-US-GuyNeural для male, en-US-JennyNeural для female). Per-character voices — v2 задача.
- **Endpoints**:
  - `/start` → opener реплика Mal'а + TTS audio_url
  - `/turn` → 2-3 реплики + audio_urls + next player options
  - `/audio/<session>/<file>.mp3` — static serve
- **Tests**: `test_active_crew.py` (mock LLM, no TTS), `test_tts.py` (direct + e2e с Ollama), `test_real_ollama.py`

## Ключевые решения и гочи

### Head LookAt (cost: 3+ часа)

**Проблема:** UE Mannequin / MetaHuman head bone имеет нестандартные local axes (+Y = up-to-crown). Любой `Look At Axis` value даёт imperfect результат. Community issue без accepted solution: https://forums.unrealengine.com/t/ue-5-4-1-auto-retargeting-issue-mixamo-char-head-down/1864768

**Попытки:**
- Plan A (Look At node): axis не угадывается
- Plan B (Transform Modify Bone + FindLookAtRotation): работает для одной точки
- Plan C (yaw-only через Break Rotator): hardcoded Yaw=45 не повернул голову → нашёлся Alpha=Pin=0 silent-disable gotcha
- После фикса Alpha=1.0 литеральной — Look At заработал, хоть и не идеально

**Финальное решение:** Look At с axis (0, 0, 1) + Alpha=1.0. **"Workable for demo"** по user'у.

**AAA fix deferred**: Control Rig + Aim Constraint (iteration 2, отдельный runbook).

**Runbook**: `docs/runbooks/04_abp_crew_listener_look_at_ik.md` (содержит «подводные камни» секцию с Alpha-gotcha).

### Alpha=Pin silent-disable (cost: ~2 часа)

`Alpha` параметр в AnimGraph нодах по умолчанию exposed as Pin. Если pin не подключён к wire — UE считает Alpha=0 и **silently** отключает всю ноду. Выглядит как «нода не работает», никакого warning. Правильный способ: клик по dropdown справа от Alpha → снять «Expose As Pin» и «Dynamic Value» → вручную ввести 1.0.

### TTS через edge-tts

Выбрали edge-tts поверх ElevenLabs/OpenAI/Piper потому что:
- Бесплатно (Microsoft public endpoint)
- Quality хорошая (neural voices)
- No API key, один `pip install`
- Для прогона-заглушки достаточно

Качество подтверждено user'ом: «Для демо просто отлично».

### MetaHuman Audio Driven Animation (следующий шаг)

В UE 5.5+ есть встроенная фича **Audio-Driven Animation для MetaHuman Animator**:
- Free, part of MetaHuman plugin
- Offline (no cloud, no Nvidia GPU)
- Input: WAV SoundWave → Output: Animation Sequence с facial curves
- Работает с Bridge-MetaHumans
- Docs: https://dev.epicgames.com/documentation/en-us/metahuman/audio-driven-animation-for-metahuman

**Workflow:** Enable MetaHuman plugin → import WAV → create **MetaHuman Performance** asset → Input Type = Audio → pick SoundWave → Process → export as Animation Sequence.

Это предпочтительнее NVIDIA Audio2Face для нашего случая (pre-recorded WAV, всё в UE).

## Следующий шаг (in_progress)

**Step 6 integration**: UE plays audio from `/audio` endpoint during Play mode.

Планируемые три шага:

### A. tts.py → WAV output (5 мин)

edge-tts может сохранять не только MP3 но и WAV напрямую через `audio-format` параметр. Добавить option в EdgeTTSBackend (например `output_format: "mp3" | "wav"`) чтобы MetaHuman Animator мог напрямую импортировать без конверсии.

Имплементация:
```python
# в EdgeTTSBackend.__init__:
self.output_format = output_format  # "mp3" or "wav"
# в synthesize:
ext = ".wav" if self.output_format == "wav" else ".mp3"
out_path = output_dir / f"{stem}{ext}"
# edge-tts не умеет native WAV, нужен pydub для конверсии MP3 → WAV
```

Или проще: использовать `pydub` (ffmpeg wrapper) для конверсии MP3 → WAV после edge-tts. Одна строка: `AudioSegment.from_mp3(mp3_path).export(wav_path, format="wav")`.

### B. Manual MetaHuman Performance workflow в UE (30 мин)

На одном WAV файле (например озвучка Mal'а "Two hours to atmo"):
1. Import WAV как SoundWave в `Content/Sounds/Test/`
2. Правый клик в Content Browser → MetaHuman → Create Performance Asset (или похожее по смыслу)
3. В Performance editor: Input Type = Audio, выбрать SoundWave
4. Process (подождать 10-30 сек)
5. Export Animation Sequence targeting Face skeleton (or standard MetaHuman face archetype)
6. Apply к `Mal_MetaHuman` в scene → Play → видим как губы и micro-gestures двигаются под аудио

Runbook 05 нужно написать после того как один раз прошли.

### C. Automation (later, после того как шаг B работает)

Python scripting в UE (Editor Utility Blueprint или Python script):
- Batch: импорт всех WAV из `audio/<session_id>/` как SoundWaves
- Для каждого — MetaHuman Performance → Animation Sequence
- Runtime: dialogue flow actor получает `/turn` response, подгружает соответствующий Animation Sequence на face mesh нужного character'а, запускает + toggle IsSpeaking

## Open questions

1. **UE audio playback для MP3 в runtime:** стандартный UE SoundWave ожидает импорт на этапе cook. Для runtime-скачивания MP3 с `/audio/...` нужен плагин `RuntimeAudioImporter` (бесплатный, популярный) или альтернативы. Пока не решено.

2. **WAV vs MP3 для MetaHuman Animator:** WAV точно работает (docs), MP3 — не подтверждено. Безопаснее конвертить в WAV.

3. **Control Rig для head tracking** — отложено на iteration 2 полировки.

## Полезные ссылки

- [MetaHuman Audio-Driven Animation — UE 5.7 docs](https://dev.epicgames.com/documentation/en-us/metahuman/audio-driven-animation-for-metahuman)
- [MetaHuman 5.7 Release Notes](https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-5-7-release-notes)
- [Community tutorial: Animate Metahuman Using Audio Files](https://forums.unrealengine.com/t/community-tutorial-animate-metahuman-using-audio-files/2177490)
- [UE 5.4.1 head down after retargeting (our pain point)](https://forums.unrealengine.com/t/ue-5-4-1-auto-retargeting-issue-mixamo-char-head-down/1864768)

## Технические доки репо

- `docs/SCENES.md` — рассадка + координаты + camera map
- `docs/CHARACTERS.md` — 9 персонажей + note про scope (4 active)
- `docs/runbooks/01_mixamo_to_ue_mannequin_retarget.md` — Mixamo pipeline
- `docs/runbooks/02_metahuman_creator_via_bridge.md` — MetaHuman через Bridge
- `docs/runbooks/03_abp_crew_idle_talking_state_machine.md` — state machine
- `docs/runbooks/04_abp_crew_listener_look_at_ik.md` — head tracking saga + Alpha gotcha
- `tools/dialogue_server/README.md` — dialogue server architecture
