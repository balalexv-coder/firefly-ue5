"""
Одноразовая утилита: Duplicate Face_AnimBP -> ABP_FireflyFace.

Создаёт копию MetaHuman Face_AnimBP в Content/Crew/Animation/AnimBP/,
после чего на нём можно безопасно править AnimGraph (добавить DefaultSlot
для рантайм-инжекции lipsync AnimSequence без отрыва Face от Body).

Запуск из UE Editor:
    File -> Tools -> Execute Python Script... -> выбрать этот файл
ИЛИ
    Output Log -> переключить Cmd на Python -> py duplicate_face_animbp.py

Идемпотентно: если ABP_FireflyFace уже существует, ничего не делает.
"""

import unreal


SRC = "/Game/MetaHumans/Common/Face/Face_AnimBP"
DST_DIR = "/Game/Crew/Animation/AnimBP"
DST = f"{DST_DIR}/ABP_FireflyFace"


def main() -> None:
    asset_lib = unreal.EditorAssetLibrary

    if asset_lib.does_asset_exist(DST):
        unreal.log_warning(f"[firefly] {DST} already exists — skipping duplicate")
        return

    if not asset_lib.does_asset_exist(SRC):
        unreal.log_error(
            f"[firefly] source missing: {SRC}. "
            "MetaHuman plugin/content not installed?"
        )
        return

    if not asset_lib.does_directory_exist(DST_DIR):
        asset_lib.make_directory(DST_DIR)
        unreal.log(f"[firefly] created folder {DST_DIR}")

    result = asset_lib.duplicate_asset(SRC, DST)
    if result is None:
        unreal.log_error(f"[firefly] duplicate_asset returned None for {SRC} -> {DST}")
        return

    asset_lib.save_asset(DST)
    unreal.log(f"[firefly] duplicated {SRC} -> {DST}")


if __name__ == "__main__":
    main()
