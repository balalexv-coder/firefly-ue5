"""Test multi-line pipeline statement via UE remote exec."""
import time
import remote_execution as re

config = re.RemoteExecutionConfig()
config.multicast_bind_address = "0.0.0.0"
config.multicast_ttl = 1

rc = re.RemoteExecution(config)
rc.start()
time.sleep(1)
nodes = rc.remote_nodes
if not nodes:
    print("No nodes")
    rc.stop()
    exit()

rc.open_command_connection(nodes[0]['node_id'])

# Multi-line stmt with imports
cmd = """
import sys
print('python version:', sys.version)
try:
    import firefly_face_pipeline as p
    print('IMPORT_OK', p.__file__)
except Exception as e:
    print('IMPORT_ERR:', e)
"""

print("Sending multi-line cmd via MODE_EXEC_FILE...")
response = rc.run_command(cmd, exec_mode=re.MODE_EXEC_FILE, unattended=True)
print(f"success: {response.get('success')}")
print(f"output: {response.get('output')}")

rc.close_command_connection()
rc.stop()
