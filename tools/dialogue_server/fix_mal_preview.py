"""Clear instance-level Body anim_class override on placed BP_Mal_v2 — let it
inherit BP class default like other actors. Fixes preview head detachment."""
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
    es = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = es.get_editor_world()
    all_actors = unreal.GameplayStatics.get_all_actors_of_class(
        world, unreal.Actor.static_class()
    )

    mal = None
    for a in all_actors:
        try:
            if a.get_actor_label() == "BP_Mal_v2":
                mal = a
                break
        except Exception:
            continue

    if not mal:
        result["errors"].append("BP_Mal_v2 not found")
    else:
        for c in mal.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "Body":
                # Clear anim_instance_class override.
                try:
                    c.set_anim_instance_class(None)
                    result["steps"].append("Cleared Body anim_class override")
                except Exception as e:
                    result["errors"].append("clear anim_class: " + repr(e))
                break

    # Save level
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = les.save_current_level()
        result["steps"].append("Save level: " + str(ok))
    except Exception as e:
        result["errors"].append("save: " + repr(e))

except Exception as e:
    result["errors"].append("global: " + repr(e))
    result["errors"].append(traceback.format_exc())

print("FIX_MAL:" + json.dumps(result))
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
                if line.startswith("FIX_MAL:"):
                    print(json.dumps(json.loads(line[len("FIX_MAL:"):]), indent=2))
                    return 0
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
