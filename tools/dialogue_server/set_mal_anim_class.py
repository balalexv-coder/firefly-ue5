"""Set Body component's anim_class to ABP_Crew_C in BP_Mal_v2 class defaults."""
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
    bp_path = "/Game/Crew/Blueprints/BP_Mal_v2"
    abp_path = "/Game/Crew/Animation/AnimBP/ABP_Crew"

    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        result["errors"].append("BP_Mal_v2 not loaded")
    else:
        gen_class = bp.generated_class()
        cdo = unreal.get_default_object(gen_class)
        result["steps"].append("CDO obtained: " + cdo.get_name())

        # Find Body component on CDO. CDO exposes components as attributes.
        body = None
        for attr_name in ("body", "Body"):
            try:
                candidate = getattr(cdo, attr_name, None)
                if candidate and isinstance(candidate, unreal.SkeletalMeshComponent):
                    body = candidate
                    break
            except Exception:
                continue

        if not body:
            # Try via get_editor_property
            for attr_name in ("Body", "body"):
                try:
                    candidate = cdo.get_editor_property(attr_name)
                    if candidate and isinstance(candidate, unreal.SkeletalMeshComponent):
                        body = candidate
                        break
                except Exception:
                    continue

        if not body:
            # Try SubobjectDataSubsystem
            try:
                sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
                handles = sds.gather_subobject_data_for_blueprint(bp)
                result["steps"].append("subobject handles: " + str(len(handles)))
                for h in handles:
                    data = sds.get_data(h)
                    obj = data.get_object()
                    if obj and obj.get_name() == "Body" and isinstance(obj, unreal.SkeletalMeshComponent):
                        body = obj
                        break
            except Exception as e:
                result["errors"].append("subobject lookup: " + repr(e))

        if not body:
            result["errors"].append("Body component not found on CDO")
        else:
            # Load ABP_Crew generated class
            abp_class = unreal.EditorAssetLibrary.load_blueprint_class(abp_path)
            if not abp_class:
                result["errors"].append("ABP_Crew class not loaded")
            else:
                result["steps"].append("ABP_Crew class loaded: " + abp_class.get_name())
                try:
                    body.set_editor_property("anim_class", abp_class)
                    result["steps"].append("set anim_class on Body CDO")
                except Exception as e:
                    result["errors"].append("set anim_class failed: " + repr(e))

                # Mark asset dirty + save
                try:
                    unreal.EditorAssetLibrary.set_metadata_tag(bp, "dirty", "true")
                except Exception:
                    pass
                saved = unreal.EditorAssetLibrary.save_asset(bp_path)
                result["steps"].append("save_asset: " + str(saved))

except Exception as e:
    result["errors"].append("global: " + repr(e))
    result["errors"].append(traceback.format_exc())

print("SET_ANIM_CLASS_RESULT:" + json.dumps(result))
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
                if line.startswith("SET_ANIM_CLASS_RESULT:"):
                    print(json.dumps(json.loads(line[len("SET_ANIM_CLASS_RESULT:"):]), indent=2))
                    return 0
            log.error("No marker. Output:\n%s", output)
            return 1
        finally:
            rc.close_command_connection()
    finally:
        rc.stop()

if __name__ == "__main__":
    sys.exit(main())
