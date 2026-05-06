"""Dump everything: speakers + table (any large StaticMeshActor with 'table' or
whose AABB is bigger than typical character)."""
from __future__ import annotations
import json, logging, sys, time
import remote_execution as ue_re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

UE_SCRIPT = r"""
import unreal
import json

result = {"speakers": {}, "tables": [], "all_static_meshes": []}

es = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = es.get_editor_world()
all_actors = unreal.GameplayStatics.get_all_actors_of_class(
    world, unreal.Actor.static_class()
)

speaker_labels = {"Mal_MetaHuman", "BP_Zoe", "BP_Wash", "BP_Inara"}

for a in all_actors:
    try:
        label = a.get_actor_label()
        cls = a.get_class().get_name()
    except Exception:
        continue

    if label in speaker_labels:
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        scale = a.get_actor_scale3d()
        result["speakers"][label] = {
            "loc": (loc.x, loc.y, loc.z),
            "yaw": rot.yaw,
            "scale": (scale.x, scale.y, scale.z),
        }
        continue

    # Look for static mesh actors that might be the table.
    if isinstance(a, unreal.StaticMeshActor):
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        scale = a.get_actor_scale3d()
        # Try to get bounds:
        try:
            bb = a.get_actor_bounds(only_colliding_components=False)
            origin, extent = bb
            box_origin = (origin.x, origin.y, origin.z)
            box_extent = (extent.x, extent.y, extent.z)
        except Exception:
            box_origin, box_extent = None, None
        # SM mesh asset:
        sm_comp = a.static_mesh_component
        sm_path = None
        try:
            sm_asset = sm_comp.get_editor_property("static_mesh") if sm_comp else None
            if sm_asset:
                sm_path = sm_asset.get_path_name()
        except Exception:
            pass

        entry = {
            "label": label,
            "class": cls,
            "loc": (loc.x, loc.y, loc.z),
            "yaw": rot.yaw,
            "scale": (scale.x, scale.y, scale.z),
            "bounds_origin": box_origin,
            "bounds_extent": box_extent,
            "sm_asset": sm_path,
        }
        result["all_static_meshes"].append(entry)
        if "table" in label.lower() or "table" in (sm_path or "").lower():
            result["tables"].append(entry)

print("DUMP_FULL:" + json.dumps(result))
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
                if line.startswith("DUMP_FULL:"):
                    print(json.dumps(json.loads(line[len("DUMP_FULL:"):]), indent=2))
                    return 0
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
