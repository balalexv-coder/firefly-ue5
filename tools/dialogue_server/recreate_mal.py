"""
Re-create Mal as BP_Mal_v2 by duplicating BP_Cooper, applying BP_Wash's
Body component settings, placing in level, updating Speakers map.

Pre-requisites:
- UE Editor open with L_SerenityCabin loaded.
- PIE off.
- BP_Cooper exists (от MetaHuman import).
- BP_Wash exists in level и работает (sits correctly).
"""
from __future__ import annotations
import json, logging, sys, time
import remote_execution as ue_re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

UE_SCRIPT = r"""
import unreal
import json
import traceback

result = {"steps": [], "errors": []}

try:
    target_path = "/Game/Crew/Blueprints/BP_Mal_v2"

    # --- 0. Cleanup if BP_Mal_v2 already exists ---
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        ok = unreal.EditorAssetLibrary.delete_asset(target_path)
        result["steps"].append("Deleted existing " + target_path + ": " + str(ok))

    # --- 1. Find BP_Cooper via asset registry ---
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    cooper_path = None
    for try_path in [
        "/Game/MetaHumans/Cooper/BP_Cooper",
        "/Game/Crew/Blueprints/BP_Cooper",
        "/Game/Cooper/BP_Cooper",
    ]:
        if unreal.EditorAssetLibrary.does_asset_exist(try_path):
            cooper_path = try_path
            break

    if not cooper_path:
        # Search by name
        ar_filter = unreal.ARFilter(
            class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Blueprint")],
            recursive_paths=True,
        )
        try:
            ar_filter.package_paths = ["/Game"]
        except Exception:
            pass
        for ad in asset_registry.get_assets(ar_filter):
            if str(ad.asset_name) == "BP_Cooper":
                cooper_path = "/" + str(ad.package_name).lstrip("/")
                break

    if not cooper_path:
        result["errors"].append("BP_Cooper not found anywhere")
        print("RECREATE_RESULT:" + json.dumps(result))
    else:
        result["steps"].append("Found BP_Cooper at " + cooper_path)

        # --- 2. Duplicate to BP_Mal_v2 ---
        new_bp = unreal.EditorAssetLibrary.duplicate_asset(cooper_path, target_path)
        if not new_bp:
            result["errors"].append("Duplicate failed")
        else:
            result["steps"].append("Duplicated to " + target_path)

            # Save the new asset right away
            unreal.EditorAssetLibrary.save_asset(target_path)

            # --- 3. Find scene actors ---
            es = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = es.get_editor_world()
            all_actors = unreal.GameplayStatics.get_all_actors_of_class(
                world, unreal.Actor.static_class()
            )

            wash_actor = None
            old_mal_actor = None
            dm_actor = None

            for a in all_actors:
                try:
                    label = a.get_actor_label()
                except Exception:
                    continue
                if label == "BP_Wash":
                    wash_actor = a
                elif label == "Mal_MetaHuman":
                    old_mal_actor = a
                elif label == "BP_DialogueManager":
                    dm_actor = a

            result["steps"].append("Found Wash=%s OldMal=%s DM=%s" % (
                wash_actor is not None, old_mal_actor is not None, dm_actor is not None))

            # --- 4. Read Wash's Body anim_class ---
            wash_anim_class = None
            if wash_actor:
                for c in wash_actor.get_components_by_class(unreal.SkeletalMeshComponent):
                    if c.get_name() == "Body":
                        try:
                            wash_anim_class = c.get_anim_class()
                        except Exception:
                            pass
                        if not wash_anim_class:
                            try:
                                wash_anim_class = c.get_editor_property("anim_class")
                            except Exception:
                                pass
                        break

            anim_class_name = wash_anim_class.get_path_name() if wash_anim_class else "None"
            result["steps"].append("Wash Body anim_class = " + anim_class_name)

            # --- 5. Spawn BP_Mal_v2 in level ---
            new_bp_loaded = unreal.EditorAssetLibrary.load_asset(target_path)
            generated_class = new_bp_loaded.generated_class() if new_bp_loaded else None

            if not generated_class:
                result["errors"].append("Could not get generated class for BP_Mal_v2")
            else:
                spawn_loc = unreal.Vector(-220.0, 10.0, 0.0)
                spawn_rot = unreal.Rotator(0.0, 0.0, -90.0)
                eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
                new_mal = eas.spawn_actor_from_class(generated_class, spawn_loc, spawn_rot)

                if not new_mal:
                    result["errors"].append("Spawn failed")
                else:
                    new_mal.set_actor_label("BP_Mal_v2")
                    result["steps"].append("Spawned BP_Mal_v2 at (-220,10,0) Yaw=-90")

                    # --- 6. Apply Wash's anim class to new Mal's Body ---
                    if wash_anim_class:
                        for c in new_mal.get_components_by_class(unreal.SkeletalMeshComponent):
                            if c.get_name() == "Body":
                                try:
                                    c.set_anim_instance_class(wash_anim_class)
                                    result["steps"].append("set_anim_instance_class on Body OK")
                                except Exception as e:
                                    result["errors"].append("set_anim_instance_class: " + repr(e))
                                break

                    # --- 7. Update Speakers map ---
                    if dm_actor:
                        try:
                            speakers = dm_actor.get_editor_property("Speakers")
                            new_speakers = {}
                            for k, v in speakers.items():
                                if str(k) == "Mal":
                                    new_speakers[str(k)] = new_mal
                                else:
                                    new_speakers[str(k)] = v
                            # ensure Mal entry exists
                            new_speakers.setdefault("Mal", new_mal)
                            dm_actor.set_editor_property("Speakers", new_speakers)
                            result["steps"].append("Updated Speakers map (Mal->BP_Mal_v2)")
                        except Exception as e:
                            result["errors"].append("update speakers: " + repr(e))

                    # --- 8. Delete old Mal_MetaHuman ---
                    if old_mal_actor:
                        try:
                            eas.destroy_actor(old_mal_actor)
                            result["steps"].append("Deleted old Mal_MetaHuman")
                        except Exception as e:
                            result["errors"].append("delete old Mal: " + repr(e))

                    # --- 9. Save level ---
                    try:
                        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
                        ok = les.save_current_level()
                        result["steps"].append("Save level: " + str(ok))
                    except Exception as e:
                        result["errors"].append("save level: " + repr(e))

except Exception as e:
    result["errors"].append("global: " + repr(e))
    result["errors"].append(traceback.format_exc())

print("RECREATE_RESULT:" + json.dumps(result))
"""

def main() -> int:
    config = ue_re.RemoteExecutionConfig()
    config.multicast_bind_address = "0.0.0.0"
    config.multicast_ttl = 1
    rc = ue_re.RemoteExecution(config)
    rc.start()
    try:
        deadline = time.time() + 10.0
        node = None
        while time.time() < deadline:
            if rc.remote_nodes:
                node = rc.remote_nodes[0]
                break
            time.sleep(0.5)
        if node is None:
            log.error("No UE node")
            return 1
        rc.open_command_connection(node["node_id"])
        try:
            r = rc.run_command(UE_SCRIPT, exec_mode=ue_re.MODE_EXEC_FILE,
                               unattended=True)
            output = r.get("output", "")
            if isinstance(output, list):
                output = "\n".join(i.get("output", "") if isinstance(i, dict) else str(i) for i in output)
            for line in str(output).splitlines():
                if line.startswith("RECREATE_RESULT:"):
                    payload = json.loads(line[len("RECREATE_RESULT:"):])
                    print(json.dumps(payload, indent=2))
                    return 0 if not payload.get("errors") else 1
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
