"""
firefly_face_pipeline — авто-пайплайн "WAV → MetaHuman face AnimSequence".

Что делает:
  1. Импортирует WAV файл (с диска) в `/Game/Audio/Dialogue/Generated/<character>/`
     как SoundWave.
  2. Создаёт MetaHuman Performance asset (`MHP_<stem>`) c Input Type = Audio,
     ссылается на этот SoundWave.
  3. Запускает блокирующий Process (start_pipeline) — генерация face curves.
  4. Экспортит Animation Sequence (`A_<character>_<stem>_Lipsync`) на
     Face_Archetype_Skeleton, без UI диалога.
  5. Сохраняет все ассеты на диск.

Level Sequence НЕ генерится автоматически (попытка через Epic's
export_level_sequence создавала Spawnable Mal — упирался в memory limit на
runtime, текстуры MetaHuman ~4.5 GB). Per-line LS-ы создаём вручную в
редакторе на основе template'а LS_Test_Mal_Lipsync — копируем, swap'аем
audio + anim ссылки. См. docs/runbooks/05_metahuman_audio_driven_face.md.

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

    # 5. Save all
    for path in (
        f"{line_dir}/{sound_wave_name}",
        f"{line_dir}/{perf_name}",
        f"{line_dir}/{anim_name}",
    ):
        _save_asset(path)

    _log("=== pipeline done ===")

    return {
        "sound_wave": f"{line_dir}/{sound_wave_name}",
        "performance": f"{line_dir}/{perf_name}",
        "anim_sequence": f"{line_dir}/{anim_name}",
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
