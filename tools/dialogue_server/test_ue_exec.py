"""Sanity test для UE remote exec command."""
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

print(f"Connecting to {nodes[0]['node_id']}")
rc.open_command_connection(nodes[0]['node_id'])

# Try simple print statement
cmd = "print('HELLO_FROM_REMOTE')"
print(f"Sending: {cmd}")
response = rc.run_command(cmd, exec_mode=re.MODE_EXEC_STATEMENT, unattended=True)
print(f"Response: {response}")

rc.close_command_connection()
rc.stop()
