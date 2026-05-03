"""
Одноразовая утилита: re-export существующего MetaHumanPerformance в
AnimSequence БЕЗ head movement (enable_head_movement = False).

Зачем: при slot playback (PlaySlotAnimationAsDynamicMontage) AnimSequence
с head_movement=True приводит к "отрыванию" Face mesh от Body — head bone
получает absolute translations из baked-кривых.

Запуск из UE Editor:
    File -> Execute Python Script... -> выбрать этот файл

Создаёт `A_Mal_Demo_Lipsync_NoHead` рядом с оригинальным A_Mal_Demo_Lipsync.
"""

import unreal


PERFORMANCE_PATH = "/Game/Audio/Dialogue/Test/MHP_Mal_Demo"
EXPORT_DIR = "/Game/Audio/Dialogue/Test"
EXPORT_NAME = "A_Mal_Demo_Lipsync_NoHead"

FACE_ARCHETYPE_SKELETON = (
    "/Game/MetaHumans/Common/Face/Face_Archetype_Skeleton.Face_Archetype_Skeleton"
)


def main() -> None:
    perf = unreal.load_asset(PERFORMANCE_PATH)
    if perf is None:
        unreal.log_error(f"[firefly] Performance not found: {PERFORMANCE_PATH}")
        return

    skeleton = unreal.load_asset(FACE_ARCHETYPE_SKELETON)
    if skeleton is None:
        unreal.log_error(f"[firefly] Skeleton not found: {FACE_ARCHETYPE_SKELETON}")
        return

    settings = unreal.MetaHumanPerformanceExportAnimationSettings()
    settings.show_export_dialog = False
    settings.package_path = EXPORT_DIR
    settings.asset_name = EXPORT_NAME
    settings.target_skeleton_or_skeletal_mesh = skeleton

    # КЛЮЧЕВОЙ параметр — отключаем head movement curves в экспортируемой
    # AnimSequence. Без этого slot playback тащит head bone абсолютно.
    settings.enable_head_movement = False
    settings.export_range = unreal.PerformanceExportRange.PROCESSING_RANGE

    anim = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(perf, settings)
    if anim is None:
        unreal.log_error("[firefly] export_animation_sequence returned None")
        return

    full_path = f"{EXPORT_DIR}/{EXPORT_NAME}"
    unreal.EditorAssetLibrary.save_asset(full_path)
    unreal.log(f"[firefly] re-exported (no head movement): {full_path}")


if __name__ == "__main__":
    main()
