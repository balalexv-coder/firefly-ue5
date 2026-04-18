"""
Инициализация проекта: создаёт все папки Content/, 5 стартовых карт,
BP_FireflyGameMode и наследуемого BP_FireflyPlayer.

Запускается headless'ом через init_project.bat в корне репо.
Идемпотентно — повторные запуски ничего не ломают.
"""

import unreal


FOLDERS = [
    # Служебные
    "/Game/Prototype",
    "/Game/Prototype/Levels",
    "/Game/Prototype/Materials",

    # Core (GameMode, PlayerController, etc.)
    "/Game/Core",

    # Crew
    "/Game/Crew/MetaHumans/Mal",
    "/Game/Crew/MetaHumans/Zoe",
    "/Game/Crew/MetaHumans/Wash",
    "/Game/Crew/MetaHumans/Jayne",
    "/Game/Crew/MetaHumans/Kaylee",
    "/Game/Crew/MetaHumans/Inara",
    "/Game/Crew/MetaHumans/Simon",
    "/Game/Crew/MetaHumans/River",
    "/Game/Crew/MetaHumans/Book",
    "/Game/Crew/Animation/Raw/Mixamo",
    "/Game/Crew/Animation/Retargeted",
    "/Game/Crew/Animation/Montages",
    "/Game/Crew/Animation/AnimBP",
    "/Game/Crew/Animation/IK",
    "/Game/Crew/Blueprints",
    "/Game/Crew/DataAssets",

    # Ship
    "/Game/Ship/Mesh",
    "/Game/Ship/Materials",
    "/Game/Ship/Textures",
    "/Game/Ship/Blueprints",

    # Cabin
    "/Game/Cabin/Meshes",
    "/Game/Cabin/Materials",
    "/Game/Cabin/Lights",
    "/Game/Cabin/Blueprints",

    # Orbital
    "/Game/OrbitalScene/Meshes",
    "/Game/OrbitalScene/Materials",

    # Landing
    "/Game/Landing/Niagara",
    "/Game/Landing/Sounds",
    "/Game/Landing/Cinematics",

    # Town
    "/Game/Town/Buildings/Saloon",
    "/Game/Town/Buildings/Sheriff",
    "/Game/Town/Buildings/Stable",
    "/Game/Town/Buildings/Blacksmith",
    "/Game/Town/Buildings/GeneralStore",
    "/Game/Town/Buildings/Houses",
    "/Game/Town/Props/Barrels",
    "/Game/Town/Props/Crates",
    "/Game/Town/Props/Lanterns",
    "/Game/Town/Props/Signs",
    "/Game/Town/NPCs/Meshes",
    "/Game/Town/NPCs/Animation",
    "/Game/Town/NPCs/BehaviorTrees",
    "/Game/Town/Horses/Mesh",
    "/Game/Town/Horses/Animation",
    "/Game/Town/PCG",
    "/Game/Town/Landscape",

    # UI
    "/Game/UI",

    # Audio
    "/Game/Audio/Dialogue",
    "/Game/Audio/Music",
    "/Game/Audio/Ambient",
    "/Game/Audio/SFX",

    # Cinematics
    "/Game/Cinematics",

    # Levels (все карты в одной папке)
    "/Game/Levels",

    # Config-like DataAssets
    "/Game/Config",
]


LEVELS = [
    "/Game/Levels/L_Main",
    "/Game/Levels/L_SerenityCabin",
    "/Game/Levels/L_OrbitalScene",
    "/Game/Levels/L_Landing",
    "/Game/Levels/L_Town",
]


def ensure_folders() -> None:
    asset_lib = unreal.EditorAssetLibrary
    for folder in FOLDERS:
        if not asset_lib.does_directory_exist(folder):
            asset_lib.make_directory(folder)
            unreal.log(f"[init] created folder {folder}")


def ensure_levels() -> None:
    level_editor_sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    asset_lib = unreal.EditorAssetLibrary

    for lvl in LEVELS:
        if asset_lib.does_asset_exist(lvl):
            continue
        ok = level_editor_sub.new_level(lvl)
        if ok:
            unreal.log(f"[init] created level {lvl}")
        else:
            unreal.log_warning(f"[init] failed to create level {lvl}")


def ensure_game_mode_and_player() -> None:
    """Простейшие BP-заглушки: BP_FireflyGameMode (parent GameModeBase)
    и BP_FireflyPlayer (parent Character). Позже наполняем в редакторе."""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_lib = unreal.EditorAssetLibrary

    pairs = [
        ("/Game/Core", "BP_FireflyGameMode", unreal.GameModeBase),
        ("/Game/Core", "BP_FireflyPlayer",   unreal.Character),
    ]
    for folder, name, parent in pairs:
        path = f"{folder}/{name}"
        if asset_lib.does_asset_exist(path):
            continue
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)
        tools.create_asset(name, folder, unreal.Blueprint, factory)
        asset_lib.save_asset(path)
        unreal.log(f"[init] created blueprint {path}")


def main() -> None:
    unreal.log("=== Firefly UE5 project init ===")
    ensure_folders()
    ensure_levels()
    ensure_game_mode_and_player()
    unreal.EditorAssetLibrary.save_directory("/Game", only_if_is_dirty=True, recursive=True)
    unreal.log("=== init done ===")


if __name__ == "__main__":
    main()
