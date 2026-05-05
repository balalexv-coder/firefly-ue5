"""
UE Python Remote Execution клиент — триггерит firefly_face_pipeline.py
в уже запущенном UE Editor'e.

Архитектура:
  dialogue_server (FastAPI) ──► ue_pipeline_client.run_pipeline_in_ue()
                                         │ socket / multicast UDP
                                         ▼
                                UE Editor (PythonScriptPlugin remote exec)
                                         │ выполняет в editor's Python interpreter
                                         ▼
                                firefly_face_pipeline.run_pipeline(...)
                                         │
                                         ▼
                                /Game/Audio/Dialogue/Generated/<Speaker>/<line_id>/
                                  ├── <line_id>           (SoundWave)
                                  ├── MHP_<line_id>       (MetaHumanPerformance)
                                  ├── A_<Speaker>_<line_id>_Lipsync (AnimSequence)
                                  └── LS_<Speaker>_<line_id>       (LevelSequence)

Pre-requisites в UE проекте:
  Plugins → Python Editor Script Plugin → Enable Remote Execution = True
  (см. DefaultEngine.ini, секция [/Script/PythonScriptPlugin.PythonScriptPluginSettings])

Usage:
    from ue_pipeline_client import run_pipeline_in_ue
    paths = run_pipeline_in_ue(
        wav_path="C:/path/to/line.wav",
        character="Mal",
        line_id="autogen_001",
        timeout_seconds=60,
    )
    # paths = {"sound_wave": "/Game/...", "performance": "/Game/...",
    #          "anim_sequence": "/Game/...", "level_sequence": "/Game/..."}
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import remote_execution as ue_re


log = logging.getLogger(__name__)


class UEPipelineError(RuntimeError):
    """UE remote-exec pipeline не сработал (нет nodes / timeout / pipeline failure)."""


def _wait_for_node(rc: ue_re.RemoteExecution, deadline_s: float) -> dict[str, Any]:
    """Ждать пока хотя бы один UE Editor node ответит на multicast discovery."""
    while time.time() < deadline_s:
        nodes = rc.remote_nodes
        if nodes:
            return nodes[0]
        time.sleep(0.2)
    raise UEPipelineError(
        "No UE Editor with Python Remote Execution found. "
        "Make sure UE is running and Project Settings → Python → "
        "Enable Remote Execution = True."
    )


def run_pipeline_in_ue(
    wav_path: str,
    character: str,
    line_id: str,
    *,
    overwrite: bool = True,
    discovery_timeout_seconds: float = 5.0,
    exec_timeout_seconds: float = 120.0,
) -> dict[str, str]:
    """
    Выполнить firefly_face_pipeline.run_pipeline в running UE Editor через
    Python Remote Execution. Блокирует до завершения pipeline'а.

    Возвращает dict с content-путями созданных ассетов:
      sound_wave, performance, anim_sequence, level_sequence

    Бросает UEPipelineError если: UE не найден / timeout / pipeline упал.
    """
    if not Path(wav_path).is_file():
        raise UEPipelineError(f"WAV not found on disk: {wav_path}")

    config = ue_re.RemoteExecutionConfig()
    # Defaults: multicast 239.0.0.1:6766. UE по дефолту биндится на 0.0.0.0 —
    # синхронизируем bind address на client side чтобы не зависеть от
    # конфига UE (Project Settings → Plugins → Python).
    config.multicast_bind_address = '0.0.0.0'
    # TTL=1 (subnet) надёжнее чем 0 (host) на Windows — некоторые network
    # stack'и в Windows не loopback'ают multicast при TTL=0 даже на одной машине.
    config.multicast_ttl = 1
    rc = ue_re.RemoteExecution(config)
    rc.start()
    try:
        deadline = time.time() + discovery_timeout_seconds
        node = _wait_for_node(rc, deadline)
        log.info("UE node found: %s (%s)", node.get("node_id"), node.get("user"))

        rc.open_command_connection(node["node_id"])
        try:
            # Выполняемый скрипт: импортит pipeline (он лежит в UE
            # Content/Python, автоматически на sys.path в editor'e), вызывает
            # run_pipeline, печатает результат RESULT_OK / RESULT_ERR префиксом.
            wav_escaped = wav_path.replace("\\", "/").replace("'", "\\'")
            line_id_escaped = line_id.replace("'", "\\'")
            char_escaped = character.replace("'", "\\'")

            # Cmd is pure ASCII — Cyrillic comments cause encoding issues
            # in UE remote exec protocol.
            # Force-eject cached module before import — UE Python caches
            # imported modules in sys.modules, importlib.reload не всегда
            # триггерит re-evaluate с новой .py версии.
            cmd = f"""
import sys, json, traceback
try:
    sys.modules.pop('firefly_face_pipeline', None)
    import firefly_face_pipeline as p
    paths = p.run_pipeline(
        wav_path_disk=r'{wav_escaped}',
        character_key='{char_escaped}',
        line_id='{line_id_escaped}',
        overwrite={bool(overwrite)},
    )
    print('FIREFLY_PIPELINE_OK:' + json.dumps(paths))
except Exception as e:
    print('FIREFLY_PIPELINE_ERR:' + str(e))
    traceback.print_exc()
"""

            response = rc.run_command(
                cmd,
                exec_mode=ue_re.MODE_EXEC_FILE,
                unattended=True,
            )
            output = response.get("output", "")
            success = response.get("success", False)

            # output может быть list of dicts или string — нормализуем.
            output_str = ""
            if isinstance(output, list):
                output_str = "\n".join(
                    item.get("output", "") if isinstance(item, dict) else str(item)
                    for item in output
                )
            else:
                output_str = str(output)

            log.debug("UE remote exec output:\n%s", output_str)

            if not success:
                raise UEPipelineError(
                    f"UE remote exec returned success=False. Output:\n{output_str}"
                )

            for line in output_str.splitlines():
                line = line.strip()
                if line.startswith("FIREFLY_PIPELINE_OK:"):
                    import json
                    return json.loads(line[len("FIREFLY_PIPELINE_OK:"):])
                if line.startswith("FIREFLY_PIPELINE_ERR:"):
                    raise UEPipelineError(
                        f"Pipeline failed in UE: {line[len('FIREFLY_PIPELINE_ERR:'):]}\n"
                        f"Full output:\n{output_str}"
                    )

            raise UEPipelineError(
                f"Pipeline ran but no FIREFLY_PIPELINE_OK marker found. Output:\n{output_str}"
            )

        finally:
            rc.close_command_connection()
    finally:
        rc.stop()


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description="Test UE remote pipeline invocation")
    parser.add_argument("--wav", required=True)
    parser.add_argument("--character", required=True, choices=["Mal", "Zoe", "Wash", "Inara"])
    parser.add_argument("--line-id", required=True)
    args = parser.parse_args()

    paths = run_pipeline_in_ue(args.wav, args.character, args.line_id)
    print("Generated assets:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
