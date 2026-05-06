"""Dump leader pose component setup for each speaker actor's skeletal mesh
components. Used to debug why BP_Mal_v2's Face is detached from Body."""
from __future__ import annotations
import json, logging, sys, time
import remote_execution as ue_re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

UE_SCRIPT = r"""
import unreal
import json
import traceback

result = {"speakers": {}, "errors": []}

try:
    es = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = es.get_editor_world()
    all_actors = unreal.GameplayStatics.get_all_actors_of_class(
        world, unreal.Actor.static_class()
    )

    target_labels = {"BP_Wash", "BP_Zoe", "BP_Inara", "BP_Mal_v2"}

    for a in all_actors:
        try:
            label = a.get_actor_label()
        except Exception:
            continue
        if label not in target_labels:
            continue

        info = {"components": []}
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            comp = {"name": c.get_name()}
            try:
                lpc = c.leader_pose_component
                comp["leader_pose"] = lpc.get_name() if lpc else None
            except Exception as e:
                comp["leader_pose_err"] = repr(e)
            try:
                ap = c.get_attach_parent()
                comp["attach_parent"] = ap.get_name() if ap else None
                comp["attach_socket"] = str(c.get_attach_socket_name())
            except Exception as e:
                comp["attach_err"] = repr(e)
            try:
                rt = c.get_relative_transform()
                comp["rel_loc"] = (rt.translation.x, rt.translation.y, rt.translation.z)
                rr = rt.rotation.rotator()
                comp["rel_rot"] = (rr.pitch, rr.yaw, rr.roll)
            except Exception:
                pass
            try:
                ac = c.get_anim_class()
                comp["anim_class"] = ac.get_path_name() if ac else None
            except Exception:
                pass
            try:
                am = c.get_editor_property("animation_mode")
                comp["animation_mode"] = str(am)
            except Exception:
                pass
            info["components"].append(comp)
        result["speakers"][label] = info

except Exception as e:
    result["errors"].append("global: " + repr(e))
    result["errors"].append(traceback.format_exc())

print("DUMP_LEADER:" + json.dumps(result))
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
                if line.startswith("DUMP_LEADER:"):
                    print(json.dumps(json.loads(line[len("DUMP_LEADER:"):]), indent=2))
                    return 0
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
