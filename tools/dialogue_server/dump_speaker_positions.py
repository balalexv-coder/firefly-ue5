"""
Print world transforms (location + rotation) of all 4 speaker actors and
BP_DialogueManager from the running UE Editor. Used to debug LookAt geometry.
"""

from __future__ import annotations

import json
import logging
import sys
import time

import remote_execution as ue_re


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


UE_SCRIPT = r"""
import unreal
import json

result = {"speakers": {}, "dm_speakers_map_raw": []}

es = unreal.UnrealEditorSubsystem()
world = es.get_editor_world()
all_actors = unreal.GameplayStatics.get_all_actors_of_class(
    world, unreal.Actor.static_class()
)

speaker_labels = {"Mal_MetaHuman", "BP_Mal_v2", "BP_Zoe", "BP_Wash", "BP_Inara"}
dm_label = "BP_DialogueManager"

for a in all_actors:
    try:
        label = a.get_actor_label()
    except Exception:
        continue
    if label in speaker_labels:
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        # try head bone world location + Body component world transform
        head_loc = None
        body_world_loc = None
        body_world_rot = None
        try:
            comps = a.get_components_by_class(unreal.SkeletalMeshComponent)
            for c in comps:
                if c.get_name() == "Body":
                    hl = c.get_socket_location("head")
                    head_loc = (hl.x, hl.y, hl.z)
                    bwl = c.get_world_location()
                    body_world_loc = (bwl.x, bwl.y, bwl.z)
                    bwr = c.get_world_rotation()
                    body_world_rot = (bwr.pitch, bwr.yaw, bwr.roll)
                    break
        except Exception:
            pass
        result["speakers"][label] = {
            "actor_loc": (loc.x, loc.y, loc.z),
            "actor_rot": (rot.pitch, rot.yaw, rot.roll),
            "body_world_loc": body_world_loc,
            "body_world_rot": body_world_rot,
            "head_loc": head_loc,
            "class": a.get_class().get_name(),
        }
    elif label == dm_label:
        # show what's in Speakers map
        sp_map = a.get_editor_property("Speakers")
        try:
            for k, v in sp_map.items():
                vlabel = v.get_actor_label() if v else None
                result["dm_speakers_map_raw"].append((str(k), vlabel))
        except Exception as e:
            result["dm_speakers_map_raw"].append(("err", str(e)))

print("DUMP_RESULT:" + json.dumps(result))
"""


def main() -> int:
    config = ue_re.RemoteExecutionConfig()
    config.multicast_bind_address = "0.0.0.0"
    config.multicast_ttl = 1
    rc = ue_re.RemoteExecution(config)
    rc.start()
    try:
        deadline = time.time() + 15.0
        node = None
        while time.time() < deadline:
            if rc.remote_nodes:
                node = rc.remote_nodes[0]
                break
            time.sleep(0.5)
        if node is None:
            log.error("No UE node found.")
            return 1
        log.info("UE node: %s", node.get("node_id"))

        rc.open_command_connection(node["node_id"])
        try:
            response = rc.run_command(UE_SCRIPT, exec_mode=ue_re.MODE_EXEC_FILE,
                                       unattended=True)
            output = response.get("output", "")
            if isinstance(output, list):
                output_str = "\n".join(
                    item.get("output", "") if isinstance(item, dict) else str(item)
                    for item in output
                )
            else:
                output_str = str(output)

            for line in output_str.splitlines():
                if line.startswith("DUMP_RESULT:"):
                    payload = json.loads(line[len("DUMP_RESULT:"):])
                    print(json.dumps(payload, indent=2))
                    return 0
            log.error("No DUMP_RESULT marker. Output:\n%s", output_str)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()


if __name__ == "__main__":
    sys.exit(main())
