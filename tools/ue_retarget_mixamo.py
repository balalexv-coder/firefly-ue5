"""
Batch-ретаргет Mixamo анимаций на MetaHuman скелет.

ЗАПУСКАТЬ ИЗ UE: Window → Python Editor → Execute File.
(Требует плагин "Python Editor Script Plugin" и Experimental: `Sequencer Scripting`.)

Предусловия (всё вручную один раз в редакторе):
  1. Импортированы Mixamo FBX в /Game/Crew/Animation/Raw/Mixamo/
     с общим скелетом SK_MixamoYBot_Skeleton.
  2. Создан IK Rig /Game/Crew/Animation/IK/IK_MixamoYBot.
  3. Создан IK Rig /Game/Crew/Animation/IK/IK_MetaHuman
     (или используется встроенный из плагина MetaHuman).
  4. Создан IK Retargeter /Game/Crew/Animation/IK/RTG_MixamoToMetaHuman
     с source=IK_MixamoYBot, target=IK_MetaHuman, chain mapping готов.

Что делает скрипт:
  - находит все Animation Sequence под /Game/Crew/Animation/Raw/Mixamo/
  - батчем ретаргетит через RTG_MixamoToMetaHuman на MetaHuman скелет
  - сохраняет в /Game/Crew/Animation/Retargeted/
  - суффикс "_MH" добавляется к именам
"""

import unreal

SOURCE_DIR = "/Game/Crew/Animation/Raw/Mixamo"
OUTPUT_DIR = "/Game/Crew/Animation/Retargeted"
RETARGETER_PATH = "/Game/Crew/Animation/IK/RTG_MixamoToMetaHuman"
SUFFIX = "_MH"


def _find_animations(source_dir: str) -> list[str]:
    """Возвращает список package paths всех AnimSequence в папке."""
    asset_lib = unreal.EditorAssetLibrary
    if not asset_lib.does_directory_exist(source_dir):
        unreal.log_error(f"Source directory does not exist: {source_dir}")
        return []

    asset_paths = asset_lib.list_assets(source_dir, recursive=True, include_folder=False)
    anims = []
    for path in asset_paths:
        asset = asset_lib.load_asset(path)
        if isinstance(asset, unreal.AnimSequence):
            anims.append(path)
    return anims


def retarget_all() -> None:
    asset_lib = unreal.EditorAssetLibrary
    if not asset_lib.does_asset_exist(RETARGETER_PATH):
        unreal.log_error(f"Retargeter not found: {RETARGETER_PATH}")
        return

    retargeter = asset_lib.load_asset(RETARGETER_PATH)
    if not isinstance(retargeter, unreal.IKRetargeter):
        unreal.log_error(f"{RETARGETER_PATH} is not an IKRetargeter")
        return

    if not asset_lib.does_directory_exist(OUTPUT_DIR):
        asset_lib.make_directory(OUTPUT_DIR)

    animations = _find_animations(SOURCE_DIR)
    if not animations:
        unreal.log_warning(f"No animations found in {SOURCE_DIR}")
        return

    unreal.log(f"Found {len(animations)} animations, retargeting...")

    batch = unreal.IKRetargetBatchOperation()
    settings = unreal.IKRetargetBatchOperationContext()
    settings.ik_retarget_asset = retargeter
    settings.folder_path = OUTPUT_DIR
    settings.name_rule.suffix = SUFFIX
    settings.replace_existing = True
    settings.use_sockets = True

    asset_objs = [asset_lib.load_asset(p) for p in animations]
    settings.assets_to_retarget = asset_objs

    batch.run_retarget(settings)

    unreal.EditorAssetLibrary.save_directory(OUTPUT_DIR, only_if_is_dirty=True, recursive=True)
    unreal.log(f"Done. Retargeted assets in: {OUTPUT_DIR}")


if __name__ == "__main__":
    retarget_all()
