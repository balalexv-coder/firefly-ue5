"""
Fill BP_DialogueManager.Speakers map automatically.

Discovers MetaHuman actors in the current editor level by their labels (or
simple name prefix) and assigns them to the Speakers map keys
"Mal" / "Zoe" / "Wash" / "Inara". Saves the level afterwards.

PIE must be OFF (we save the level).

Usage:
    cd tools/dialogue_server
    .venv\\Scripts\\python.exe fix_speakers_map.py
"""

from __future__ import annotations

import logging
import sys
import time

import remote_execution as ue_re


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# Python script that runs inside UE — pure ASCII, no Cyrillic.
UE_SCRIPT = r"""
import unreal
import json

result = {"actors": [], "dm": None, "matched": {}, "errors": [], "saved": False}

try:
    es = unreal.UnrealEditorSubsystem()
    world = es.get_editor_world()
    all_actors = unreal.GameplayStatics.get_all_actors_of_class(
        world, unreal.Actor.static_class()
    )

    dm_class_names = ("BP_DialogueManager_C", "DialogueManager", "DialogueManager_C")
    speaker_keys = ("Mal", "Zoe", "Wash", "Inara")
    matched = {}
    dm = None

    for a in all_actors:
        try:
            label = a.get_actor_label()
        except Exception:
            label = "<no-label>"
        cls = a.get_class().get_name()
        result["actors"].append({"label": label, "class": cls})

        # Identify DialogueManager.
        if dm is None and cls in dm_class_names:
            dm = a
            result["dm"] = {"label": label, "class": cls}

        # Match speaker by label prefix (case-sensitive). MetaHumans are
        # typically labelled "Mal_MetaHuman" / "BP_Mal" / "Mal" etc.
        for key in speaker_keys:
            if key in matched:
                continue
            if label == key or label.startswith(key + "_") or label.endswith("_" + key) \
               or ("_" + key + "_") in label or label.lower() == key.lower():
                matched[key] = a

    result["matched"] = {k: v.get_actor_label() for k, v in matched.items()}

    if dm is None:
        result["errors"].append("DialogueManager actor not found in level")
    elif len(matched) < 4:
        missing = [k for k in speaker_keys if k not in matched]
        result["errors"].append("Missing speakers: " + ",".join(missing))
    else:
        # Apply Speakers map: TMap<FString, AActor*>
        speakers_map = {k: v for k, v in matched.items()}
        dm.set_editor_property("Speakers", speakers_map)

        # Save current level — UE 5.7 API. LevelEditorSubsystem is the
        # canonical post-5.0 way; EditorLevelLibrary is the legacy fallback.
        saved = False
        try:
            les = unreal.LevelEditorSubsystem()
            saved = les.save_current_level()
        except Exception as e:
            try:
                saved = unreal.EditorLevelLibrary.save_current_level()
            except Exception as e2:
                result["errors"].append(
                    "save_current_level failed: " + repr(e) + " / " + repr(e2)
                )
        result["saved"] = bool(saved)

except Exception as e:
    result["errors"].append("Exception: " + repr(e))
    import traceback
    result["errors"].append(traceback.format_exc())

print("FIX_SPEAKERS_RESULT:" + json.dumps(result))
"""


def main() -> int:
    config = ue_re.RemoteExecutionConfig()
    config.multicast_bind_address = "0.0.0.0"
    config.multicast_ttl = 1

    rc = ue_re.RemoteExecution(config)
    rc.start()
    try:
        deadline = time.time() + 5.0
        node = None
        while time.time() < deadline:
            if rc.remote_nodes:
                node = rc.remote_nodes[0]
                break
            time.sleep(0.2)
        if node is None:
            log.error("No UE Editor with Python Remote Execution found.")
            return 1
        log.info("UE node: %s (%s)", node.get("node_id"), node.get("user"))

        rc.open_command_connection(node["node_id"])
        try:
            response = rc.run_command(
                UE_SCRIPT,
                exec_mode=ue_re.MODE_EXEC_FILE,
                unattended=True,
            )
            output = response.get("output", "")
            success = response.get("success", False)

            if isinstance(output, list):
                output_str = "\n".join(
                    item.get("output", "") if isinstance(item, dict) else str(item)
                    for item in output
                )
            else:
                output_str = str(output)

            log.info("success=%s", success)

            # Parse our marker line.
            import json
            payload = None
            for line in output_str.splitlines():
                line = line.strip()
                if line.startswith("FIX_SPEAKERS_RESULT:"):
                    payload = json.loads(line[len("FIX_SPEAKERS_RESULT:"):])
                    break

            if payload is None:
                log.error("No FIX_SPEAKERS_RESULT marker. Full output:\n%s", output_str)
                return 1

            # Report.
            log.info("Found %d actors in level", len(payload["actors"]))
            log.info("DialogueManager: %s", payload["dm"])
            log.info("Matched speakers: %s", payload["matched"])

            if payload["errors"]:
                log.warning("Errors: %s", payload["errors"])
                # Show interesting subset of actors to help diagnose label naming.
                for a in payload["actors"]:
                    if any(s.lower() in a["label"].lower() for s in ("mal", "zoe", "wash", "inara", "dialogue", "metahuman")):
                        log.info("  candidate: label=%r class=%s", a["label"], a["class"])
                return 1

            log.info("Saved: %s", payload["saved"])
            return 0
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()


if __name__ == "__main__":
    sys.exit(main())
