"""
Compute and print head bone bind-pose rotation в Component Space for Manny
skeleton (used by ABP_Crew). Result is used as Default Value of HeadRotationCS
variable so editor preview shows head в естественной позиции.
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

result = {"actors": [], "errors": []}
try:
    es = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = es.get_editor_world()
    all_actors = unreal.GameplayStatics.get_all_actors_of_class(
        world, unreal.Actor.static_class()
    )

    target_labels = {"Mal_MetaHuman", "BP_Zoe", "BP_Wash", "BP_Inara"}

    for a in all_actors:
        try:
            label = a.get_actor_label()
        except Exception:
            continue
        if label not in target_labels:
            continue

        comps = a.get_components_by_class(unreal.SkeletalMeshComponent)
        for c in comps:
            if c.get_name() != "Body":
                continue
            try:
                cs_xform = c.get_bone_transform(
                    "head",
                    unreal.RelativeTransformSpace.RTS_COMPONENT)
                cs_rot = cs_xform.rotation.rotator()
                result["actors"].append({
                    "label": label,
                    "head_cs_pitch": cs_rot.pitch,
                    "head_cs_yaw": cs_rot.yaw,
                    "head_cs_roll": cs_rot.roll,
                })
            except Exception as e:
                result["errors"].append(label + ": " + repr(e))
            break
except Exception as e:
    result["errors"].append("global: " + repr(e))
    result["errors"].append(traceback.format_exc())

print("DUMP_BIND:" + json.dumps(result))
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
            r = rc.run_command(UE_SCRIPT, exec_mode=ue_re.MODE_EXEC_FILE, unattended=True)
            output = r.get("output", "")
            if isinstance(output, list):
                output = "\n".join(i.get("output", "") if isinstance(i, dict) else str(i) for i in output)
            for line in str(output).splitlines():
                if line.startswith("DUMP_BIND:"):
                    print(json.dumps(json.loads(line[len("DUMP_BIND:"):]), indent=2))
                    return 0
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
