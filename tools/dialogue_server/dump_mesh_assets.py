"""Dump skeletal mesh asset paths and component-relative rotations for each
speaker actor's Body, plus Live Retarget setup info if accessible."""
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

    target_labels = {"Mal_MetaHuman", "BP_Zoe", "BP_Wash", "BP_Inara"}

    for a in all_actors:
        try:
            label = a.get_actor_label()
        except Exception:
            continue
        if label not in target_labels:
            continue

        cls_obj = a.get_class()
        super_chain = []
        try:
            cur = cls_obj
            for _ in range(6):
                if not cur:
                    break
                super_chain.append(cur.get_name())
                cur = cur.get_super_class() if hasattr(cur, "get_super_class") else None
        except Exception:
            pass
        info = {"actor_class": cls_obj.get_name(), "super_chain": super_chain, "components": []}
        skel_comps = a.get_components_by_class(unreal.SkeletalMeshComponent)
        for c in skel_comps:
            comp_info = {
                "name": c.get_name(),
                "rel_loc": None,
                "rel_rot": None,
                "world_rot": None,
                "skel_mesh": None,
                "anim_class": None,
            }
            try:
                rel = c.get_relative_transform()
                comp_info["rel_loc"] = (rel.translation.x, rel.translation.y, rel.translation.z)
                rr = rel.rotation.rotator()
                comp_info["rel_rot"] = (rr.pitch, rr.yaw, rr.roll)
            except Exception as e:
                comp_info["rel_rot_err"] = repr(e)
            try:
                wr = c.get_world_rotation()
                comp_info["world_rot"] = (wr.pitch, wr.yaw, wr.roll)
            except Exception:
                pass
            try:
                sm = c.get_skeletal_mesh_asset()
                if sm:
                    comp_info["skel_mesh"] = sm.get_path_name()
            except Exception as e:
                comp_info["sk_err"] = repr(e)
            try:
                ac = c.get_anim_class()
                if ac:
                    comp_info["anim_class"] = ac.get_path_name()
            except Exception:
                pass
            info["components"].append(comp_info)
        result["speakers"][label] = info
except Exception as e:
    result["errors"].append("global: " + repr(e))
    result["errors"].append(traceback.format_exc())

print("DUMP_MESH:" + json.dumps(result))
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
                if line.startswith("DUMP_MESH:"):
                    print(json.dumps(json.loads(line[len("DUMP_MESH:"):]), indent=2))
                    return 0
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
