"""
Restore original speaker orientations (или any target yaw set per actor).

Usage:
    .venv\\Scripts\\python.exe reorient_speakers.py
"""

from __future__ import annotations

import json
import logging
import sys
import time

import remote_execution as ue_re


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# label → desired yaw (degrees)
TARGET_YAWS: dict[str, float] = {
    "Mal_MetaHuman": -90.0,   # original
    "BP_Zoe":          0.0,   # original
    "BP_Wash":       180.0,   # original
    "BP_Inara":      170.0,   # 10° от исходных 180° к северу (к Mal'у)
}


UE_SCRIPT_TMPL = r"""
import unreal
import json

target_yaws = {targets_json}

result = {{"applied": [], "errors": []}}
es = unreal.UnrealEditorSubsystem()
world = es.get_editor_world()
all_actors = unreal.GameplayStatics.get_all_actors_of_class(
    world, unreal.Actor.static_class()
)

found = {{}}
for a in all_actors:
    try:
        label = a.get_actor_label()
    except Exception:
        continue
    if label in target_yaws:
        found[label] = a

for label, target_yaw in target_yaws.items():
    a = found.get(label)
    if a is None:
        result["errors"].append("missing actor: " + label)
        continue
    new_rot = unreal.Rotator(0.0, 0.0, target_yaw)
    a.set_actor_rotation(new_rot, False)
    loc = a.get_actor_location()
    result["applied"].append({{"label": label, "loc": (loc.x, loc.y, loc.z),
                               "new_yaw": target_yaw}})

try:
    les = unreal.LevelEditorSubsystem()
    result["saved"] = bool(les.save_current_level())
except Exception as e:
    result["errors"].append("save failed: " + repr(e))

print("REORIENT_RESULT:" + json.dumps(result))
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
            log.error("No UE node found")
            return 1
        log.info("UE node: %s", node.get("node_id"))

        rc.open_command_connection(node["node_id"])
        try:
            cmd = UE_SCRIPT_TMPL.format(targets_json=json.dumps(TARGET_YAWS))
            response = rc.run_command(cmd, exec_mode=ue_re.MODE_EXEC_FILE,
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
                if line.startswith("REORIENT_RESULT:"):
                    payload = json.loads(line[len("REORIENT_RESULT:"):])
                    print(json.dumps(payload, indent=2))
                    return 0 if not payload.get("errors") else 1
            log.error("No marker. Output:\n%s", output_str)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()


if __name__ == "__main__":
    sys.exit(main())
