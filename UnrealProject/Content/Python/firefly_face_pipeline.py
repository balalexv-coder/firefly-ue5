"""
firefly_face_pipeline — авто-пайплайн "WAV → MetaHuman face AnimSequence + LS".

Что делает:
  1. Импортирует WAV файл (с диска) в `/Game/Audio/Dialogue/Generated/<character>/`
     как SoundWave.
  2. Создаёт MetaHuman Performance asset (`MHP_<stem>`) c Input Type = Audio,
     ссылается на этот SoundWave.
  3. Запускает блокирующий Process (start_pipeline) — генерация face curves.
  4. Экспортит Animation Sequence (`A_<character>_<stem>_Lipsync`) на
     Face_Archetype_Skeleton, без UI диалога.
  5. Программно генерирует Possessable Level Sequence (`LS_<character>_<stem>`):
     binding на character actor'а в L_SerenityCabin, sub-binding на Face,
     Audio track + Skeletal Animation track. См. create_level_sequence().
  6. Сохраняет все ассеты на диск.

Spawnable LS (через Epic's export_level_sequence) забракован — упирался в
memory limit (~4.5 GB MetaHuman текстур). Используем Possessable + ручной
поиск actor'а в loaded level через EditorActorSubsystem. См. docs/runbooks/
05_metahuman_audio_driven_face.md.

Идемпотентно: повторный запуск с тем же stem перезаписывает ассеты (если флаг
overwrite=True), либо пропускает если ассет существует.

Запускается headless'ом через scripts/process_face_audio.bat:

    scripts\\process_face_audio.bat <wav_path> <character_key> [line_id]

Аргументы скрипта:
  --wav        : абсолютный путь к WAV файлу (22050 Hz mono 16-bit рекомендовано)
  --character  : Mal | Zoe | Wash | Inara (используется в путях ассетов)
  --line-id    : опциональный ID реплики; если не задан — берётся stem WAV
  --overwrite  : перезаписать существующий Performance/AnimSequence (по умолчанию False)

Пример:
  python firefly_face_pipeline.py \\
      --wav  "C:/path/to/mal_demo_long.wav" \\
      --character Mal --line-id demo_long
"""

from __future__ import annotations

import argparse
import os
import sys

import unreal


# ---------- Константы ----------

# Куда складывать всё что генерится этим pipeline'ом (отдельно от ручных ассетов
# чтобы можно было безболезненно чистить или коммитить выборочно).
GENERATED_ROOT = "/Game/Audio/Dialogue/Generated"

# Стандартный MetaHuman Face Archetype Skeleton — target для AnimSequence экспорта.
FACE_ARCHETYPE_SKELETON = (
    "/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton.Face_Archetype_Skeleton"
)

VALID_CHARACTERS = ("Mal", "Zoe", "Wash", "Inara")

# Уровень с уже размещёнными crew member'ами — нужен для поиска actor'а при
# создании Possessable binding. Загружается headless'ом (load_map).
LEVEL_PATH = "/Game/Levels/L_SerenityCabin"

# Mapping character key → actor label (имя в Outliner) в L_SerenityCabin.
# Mal placeable отличается именем от других (BP_Mal был переименован в Mal_MetaHuman).
CHAR_TO_ACTOR_LABEL = {
    "Mal": "Mal_MetaHuman",
    "Zoe": "BP_Zoe",
    "Wash": "BP_Wash",
    "Inara": "BP_Inara",
}

# Имя SkeletalMeshComponent на MetaHuman BP, который проигрывает face anim.
# Для всех 4 MetaHuman'ов это "Face" (стандартное имя в MetaHuman BP template).
FACE_COMPONENT_NAME = "Face"


# ---------- Хелперы ----------

def _log(msg: str) -> None:
    unreal.log(f"[firefly-face] {msg}")


def _log_err(msg: str) -> None:
    unreal.log_error(f"[firefly-face] {msg}")


def _ensure_dir(content_path: str) -> None:
    asset_lib = unreal.EditorAssetLibrary
    if not asset_lib.does_directory_exist(content_path):
        asset_lib.make_directory(content_path)
        _log(f"created folder {content_path}")


def _save_asset(content_path: str) -> None:
    """Сохранить ассет по его /Game/... пути."""
    if unreal.EditorAssetLibrary.does_asset_exist(content_path):
        ok = unreal.EditorAssetLibrary.save_asset(content_path, only_if_is_dirty=False)
        if not ok:
            _log_err(f"save_asset failed for {content_path}")


# ---------- Этап 1: импорт WAV → SoundWave ----------

def import_wav_to_soundwave(
    wav_path_disk: str,
    target_dir: str,
    *,
    asset_name: str | None = None,
    overwrite: bool = False,
) -> unreal.SoundWave:
    """
    Импортирует WAV с диска в указанную папку Content. Возвращает SoundWave ассет.
    """
    if not os.path.isfile(wav_path_disk):
        raise FileNotFoundError(f"WAV not found on disk: {wav_path_disk}")

    asset_name = asset_name or os.path.splitext(os.path.basename(wav_path_disk))[0]
    target_path = f"{target_dir}/{asset_name}"

    asset_lib = unreal.EditorAssetLibrary
    if asset_lib.does_asset_exist(target_path):
        if not overwrite:
            _log(f"SoundWave already exists at {target_path}, reusing")
            return unreal.load_asset(target_path)
        _log(f"overwrite: deleting existing {target_path}")
        asset_lib.delete_asset(target_path)

    _ensure_dir(target_dir)

    task = unreal.AssetImportTask()
    task.filename = wav_path_disk
    task.destination_path = target_dir
    task.destination_name = asset_name
    task.replace_existing = True
    task.automated = True
    task.save = True

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])

    sound_wave = unreal.load_asset(target_path)
    if sound_wave is None:
        raise RuntimeError(f"Failed to import WAV → SoundWave at {target_path}")
    _log(f"imported SoundWave {target_path}")
    return sound_wave


# ---------- Этап 2: MetaHumanPerformance asset ----------

def create_performance_asset(
    sound_wave: unreal.SoundWave,
    target_dir: str,
    asset_name: str,
    *,
    overwrite: bool = False,
) -> unreal.MetaHumanPerformance:
    """Создаёт пустой MetaHumanPerformance ассет, привязывает к SoundWave."""
    target_path = f"{target_dir}/{asset_name}"
    asset_lib = unreal.EditorAssetLibrary

    if asset_lib.does_asset_exist(target_path):
        if not overwrite:
            _log(f"Performance asset exists at {target_path}, loading")
            return unreal.load_asset(target_path)
        _log(f"overwrite: deleting existing {target_path}")
        asset_lib.delete_asset(target_path)

    _ensure_dir(target_dir)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    performance = asset_tools.create_asset(
        asset_name=asset_name,
        package_path=target_dir,
        asset_class=unreal.MetaHumanPerformance,
        factory=unreal.MetaHumanPerformanceFactoryNew(),
    )

    # Используем set_editor_property — это триггерит PostEditChangeProperty,
    # без которого Performance не подхватит audio source (см. Epic example
    # process_audio_performance.py).
    performance.set_editor_property("input_type", unreal.DataInputType.AUDIO)
    performance.set_editor_property("audio", sound_wave)

    # Дефолты: Auto mood + Full Face + Control Rig head movement.
    solve = unreal.AudioDrivenAnimationSolveOverrides()
    solve.mood = unreal.AudioDrivenAnimationMood.AUTO_DETECT
    solve.mood_intensity = 1.0
    performance.set_editor_property("audio_driven_animation_solve_overrides", solve)
    performance.set_editor_property(
        "audio_driven_animation_output_controls",
        unreal.AudioDrivenAnimationOutputControls.FULL_FACE,
    )
    performance.set_editor_property(
        "head_movement_mode", unreal.PerformanceHeadMovementMode.CONTROL_RIG
    )

    _log(f"created Performance {target_path}")
    return performance


# ---------- Этап 3: Process (start_pipeline blocking) ----------

def process_performance(performance: unreal.MetaHumanPerformance) -> None:
    """Блокирующий Process — генерирует face curves внутри Performance ассета."""
    _log(f"starting pipeline for {performance.get_name()}")
    performance.set_blocking_processing(True)
    err = performance.start_pipeline()
    if err is unreal.StartPipelineErrorType.NONE:
        _log(f"pipeline finished OK for {performance.get_name()}")
    else:
        raise RuntimeError(f"start_pipeline returned error: {err} for {performance.get_name()}")


# ---------- Этап 4: Export AnimSequence ----------

def export_anim_sequence(
    performance: unreal.MetaHumanPerformance,
    target_dir: str,
    asset_name: str,
) -> unreal.AnimSequence:
    """Экспортит AnimSequence без UI диалога. Skeleton — Face_Archetype_Skeleton."""
    settings = unreal.MetaHumanPerformanceExportAnimationSettings()
    settings.show_export_dialog = False
    settings.package_path = target_dir
    settings.asset_name = asset_name

    skeleton = unreal.load_asset(FACE_ARCHETYPE_SKELETON)
    if skeleton is None:
        raise RuntimeError(
            f"Could not load target skeleton {FACE_ARCHETYPE_SKELETON} — "
            "is the MetaHuman plugin enabled and a MetaHuman in /Game/MetaHumans/?"
        )
    settings.target_skeleton_or_skeletal_mesh = skeleton

    # head_movement=False: не баковать head bone translations в curves —
    # для slot/montage playback это вызывает отрыв Face mesh от Body. Для
    # Sequencer-based воспроизведения это тоже безопаснее.
    settings.enable_head_movement = False
    settings.export_range = unreal.PerformanceExportRange.PROCESSING_RANGE

    anim_seq = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(
        performance, settings
    )
    if anim_seq is None:
        raise RuntimeError(f"export_animation_sequence returned None for {performance.get_name()}")

    _log(f"exported AnimSequence {target_dir}/{anim_seq.get_name()}")
    return anim_seq


# ---------- Этап 5: Auto-gen Possessable Level Sequence ----------

def _ensure_level_loaded(level_path: str) -> None:
    """
    Раньше эта функция вызывала load_map чтобы гарантировать что уровень
    с актёрами загружен. Это убивало PIE (load_map editor world'а во время
    PIE crashes the play session).

    Теперь — функция NO-OP: предполагаем что вызывающий уже открыл нужный
    уровень в editor (либо вручную, либо PIE копия из L_SerenityCabin).
    Если actors не найдутся — _find_actor_by_label выбросит понятную ошибку.

    Для headless-режима без открытого editor: pipeline всё равно работает
    через remote exec в открытом UE Editor (не UE-Cmd), так что актёры
    всегда доступны в editor's current world.
    """
    actor_subsys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = actor_subsys.get_all_level_actors()
    if actors:
        current_world = actors[0].get_world().get_path_name()
        _log(f"using current world (no load_map): {current_world}")
    else:
        _log("WARNING: no actors in current world — _find_actor_by_label will fail")


def _find_actor_by_label(label: str) -> unreal.Actor:
    """
    Найти actor по Outliner label в editor world.

    Используем UnrealEditorSubsystem.get_editor_world() + GameplayStatics
    вместо EditorActorSubsystem.get_all_level_actors() — последний во
    время PIE может возвращать empty list (current world становится
    PIE-копия которая может быть недоступна из remote exec context).
    """
    editor_subsys = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    editor_world = editor_subsys.get_editor_world()
    if editor_world is None:
        raise RuntimeError("UnrealEditorSubsystem.get_editor_world() returned None")

    all_actors = unreal.GameplayStatics.get_all_actors_of_class(
        editor_world, unreal.Actor.static_class()
    )

    for actor in all_actors:
        if actor.get_actor_label() == label:
            return actor

    available = [a.get_actor_label() for a in all_actors[:10]]
    raise RuntimeError(
        f"Actor with label '{label}' not found in editor world. "
        f"Available labels (first 10): {available} (total: {len(all_actors)})"
    )


def _find_face_component(actor: unreal.Actor) -> unreal.SkeletalMeshComponent:
    """Найти Face SkeletalMeshComponent на MetaHuman actor'е."""
    components = actor.get_components_by_class(unreal.SkeletalMeshComponent)
    for comp in components:
        if comp.get_name() == FACE_COMPONENT_NAME:
            return comp
    raise RuntimeError(
        f"'{FACE_COMPONENT_NAME}' SkeletalMeshComponent not found on "
        f"{actor.get_actor_label()}. Available components: "
        f"{[c.get_name() for c in components]}"
    )


def create_level_sequence(
    character_key: str,
    line_id: str,
    sound_wave: unreal.SoundWave,
    anim_sequence: unreal.AnimSequence,
    target_dir: str,
    *,
    overwrite: bool = False,
) -> unreal.LevelSequence:
    """
    Программно генерирует Possessable Level Sequence для одной dialogue line.

    Структура созданного LS:
      - Possessable binding на character actor'а (Mal_MetaHuman / BP_Zoe / ...)
        в L_SerenityCabin
      - Sub-binding на его Face SkeletalMeshComponent (set_parent → actor binding)
      - На root: MovieSceneAudioTrack с section, проигрывающим sound_wave
      - На Face binding: MovieSceneSkeletalAnimationTrack с section,
        проигрывающим anim_sequence
      - Playback range = длина anim_sequence

    Это эквивалент того, что делается вручную в Sequencer:
      1. + Track → Actor To Sequencer → Mal_MetaHuman
      2. На Mal_MetaHuman binding: + Track → Component → Face
      3. На Face binding: + Track → Animation → A_Mal_<line>_Lipsync
      4. На root: + Track → Audio → <sound_wave>
      5. AutoSize sections, set Playback Range
    """
    if character_key not in CHAR_TO_ACTOR_LABEL:
        raise ValueError(
            f"Unknown character_key={character_key!r}; "
            f"expected one of {list(CHAR_TO_ACTOR_LABEL)}"
        )

    ls_name = f"LS_{character_key}_{line_id}"
    ls_path = f"{target_dir}/{ls_name}"

    asset_lib = unreal.EditorAssetLibrary
    if asset_lib.does_asset_exist(ls_path):
        if not overwrite:
            _log(f"LevelSequence exists at {ls_path}, reusing")
            return unreal.load_asset(ls_path)
        _log(f"overwrite: deleting existing {ls_path}")
        asset_lib.delete_asset(ls_path)

    # Загружаем сцену чтобы actor был findable.
    _ensure_level_loaded(LEVEL_PATH)

    actor_label = CHAR_TO_ACTOR_LABEL[character_key]
    actor = _find_actor_by_label(actor_label)
    face_comp = _find_face_component(actor)
    _log(f"binding source: actor='{actor_label}' face='{face_comp.get_name()}'")

    _ensure_dir(target_dir)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    level_sequence = asset_tools.create_asset(
        asset_name=ls_name,
        package_path=target_dir,
        asset_class=unreal.LevelSequence,
        factory=unreal.LevelSequenceFactoryNew(),
    )

    # Display rate / tick resolution оставляем default (30 fps / 60000 ticks/sec).
    # Section ranges в UE 5.7 Python ставим через seconds-based API
    # (set_start_frame_seconds / set_end_frame_seconds), что избавляет от
    # ручного tick math и проблем с отсутствующим get_tick_resolution.

    # Possessable bindings: actor → Face.
    # Cosmetic операции (set_parent для иерархии, set_display_name) обёрнуты
    # в try/except — UE 5.7 Python API не всегда экспортит эти методы и
    # для воспроизведения LS они не нужны (Possessable bindings ссылаются
    # на objects напрямую).
    actor_binding = level_sequence.add_possessable(actor)
    face_binding = level_sequence.add_possessable(face_comp)

    try:
        face_binding.set_parent(actor_binding)
        actor_binding.set_display_name(actor_label)
        face_binding.set_display_name("Face")
        _log("binding hierarchy: face nested under actor")
    except AttributeError as e:
        _log(f"binding hierarchy methods unavailable ({e}); leaving flat — "
             "playback unaffected")

    # Длина из AnimSequence (надёжнее чем SoundWave — они одной длины, т.к.
    # оба сгенерены из того же Performance).
    duration_seconds = anim_sequence.get_play_length()
    _log(f"section length: {duration_seconds:.3f}s")

    # Skeletal Animation track + section на Face binding.
    anim_track = face_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    anim_section = anim_track.add_section()
    params = unreal.MovieSceneSkeletalAnimationParams()
    params.set_editor_property("Animation", anim_sequence)
    anim_section.set_editor_property("Params", params)
    anim_section.set_start_frame_seconds(0.0)
    anim_section.set_end_frame_seconds(duration_seconds)

    # Audio track + section на root sequence.
    audio_track = level_sequence.add_track(unreal.MovieSceneAudioTrack)
    audio_section = audio_track.add_section()
    audio_section.set_sound(sound_wave)
    audio_section.set_start_frame_seconds(0.0)
    audio_section.set_end_frame_seconds(duration_seconds)

    # Playback range = вся анимация.
    try:
        level_sequence.set_playback_start_seconds(0.0)
        level_sequence.set_playback_end_seconds(duration_seconds)
    except AttributeError as e:
        _log(f"set_playback_*_seconds unavailable ({e}); LS uses default range")

    _log(f"created LevelSequence {ls_path}")
    return level_sequence


# ---------- Pipeline orchestration ----------

def run_pipeline(
    wav_path_disk: str,
    character_key: str,
    line_id: str | None = None,
    overwrite: bool = False,
) -> dict[str, str]:
    """
    Полный pipeline: WAV → SoundWave → Performance → Process → AnimSequence.

    Возвращает словарь с content-путями к созданным ассетам.
    """
    if character_key not in VALID_CHARACTERS:
        raise ValueError(
            f"character_key={character_key!r} invalid; must be one of {VALID_CHARACTERS}"
        )

    stem = line_id or os.path.splitext(os.path.basename(wav_path_disk))[0]
    char_dir = f"{GENERATED_ROOT}/{character_key}"
    line_dir = f"{char_dir}/{stem}"

    _log(f"=== pipeline start: char={character_key} stem={stem} ===")
    _log(f"WAV source: {wav_path_disk}")
    _log(f"target dir: {line_dir}")

    # 1. WAV → SoundWave
    sound_wave_name = stem  # используем stem напрямую как имя SoundWave
    sound_wave = import_wav_to_soundwave(
        wav_path_disk, line_dir, asset_name=sound_wave_name, overwrite=overwrite
    )

    # 2. Performance (MHP_<stem>)
    perf_name = f"MHP_{stem}"
    performance = create_performance_asset(
        sound_wave, line_dir, perf_name, overwrite=overwrite
    )

    # 3. Process
    process_performance(performance)

    # 4. AnimSequence (A_<character>_<stem>_Lipsync)
    anim_name = f"A_{character_key}_{stem}_Lipsync"
    anim_seq = export_anim_sequence(performance, line_dir, anim_name)

    # 5. Possessable Level Sequence (LS_<character>_<stem>)
    ls_name = f"LS_{character_key}_{stem}"
    create_level_sequence(
        character_key=character_key,
        line_id=stem,
        sound_wave=sound_wave,
        anim_sequence=anim_seq,
        target_dir=line_dir,
        overwrite=overwrite,
    )

    # 6. Save all
    for path in (
        f"{line_dir}/{sound_wave_name}",
        f"{line_dir}/{perf_name}",
        f"{line_dir}/{anim_name}",
        f"{line_dir}/{ls_name}",
    ):
        _save_asset(path)

    _log("=== pipeline done ===")

    return {
        "sound_wave": f"{line_dir}/{sound_wave_name}",
        "performance": f"{line_dir}/{perf_name}",
        "anim_sequence": f"{line_dir}/{anim_name}",
        "level_sequence": f"{line_dir}/{ls_name}",
    }


# ---------- CLI ----------

def _read_args_from_env_or_argv() -> dict:
    """
    UE-Cmd под Windows криво форвардит quoted args через `-script="..."` —
    поэтому основной путь — env vars (FIREFLY_*). Если env не выставлены,
    fallback на argparse (удобно для интерактивного запуска из UE Editor:
    py firefly_face_pipeline.py --wav ... --character ...).
    """
    env_wav = os.environ.get("FIREFLY_WAV")
    env_char = os.environ.get("FIREFLY_CHAR")
    if env_wav and env_char:
        return {
            "wav": env_wav,
            "character": env_char,
            "line_id": os.environ.get("FIREFLY_LINE_ID") or None,
            "overwrite": os.environ.get("FIREFLY_OVERWRITE", "").lower() in ("1", "true", "yes"),
        }

    parser = argparse.ArgumentParser(
        description="Firefly: WAV → MetaHuman face AnimSequence pipeline (UE Python)"
    )
    parser.add_argument("--wav", required=True, help="Absolute path to WAV file on disk")
    parser.add_argument(
        "--character",
        required=True,
        choices=VALID_CHARACTERS,
        help="Crew character (used for asset path namespacing)",
    )
    parser.add_argument(
        "--line-id",
        default=None,
        help="Optional unique line ID (defaults to WAV file stem)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing assets (default: skip and reuse)",
    )
    args, _unknown = parser.parse_known_args()
    return {
        "wav": args.wav,
        "character": args.character,
        "line_id": args.line_id,
        "overwrite": args.overwrite,
    }


def main() -> int:
    a = _read_args_from_env_or_argv()
    if a["character"] not in VALID_CHARACTERS:
        _log_err(f"character must be one of {VALID_CHARACTERS}, got {a['character']!r}")
        return 2
    try:
        paths = run_pipeline(
            wav_path_disk=os.path.abspath(a["wav"]),
            character_key=a["character"],
            line_id=a["line_id"],
            overwrite=a["overwrite"],
        )
        unreal.log("[firefly-face] paths:")
        for k, v in paths.items():
            unreal.log(f"  {k}: {v}")
        return 0
    except Exception as e:  # noqa: BLE001
        _log_err(f"pipeline failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
