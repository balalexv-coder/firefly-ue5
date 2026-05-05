"""Standalone тест UE Python Remote Execution discovery."""
import time
import remote_execution as re

config = re.RemoteExecutionConfig()
config.multicast_bind_address = "0.0.0.0"
config.multicast_ttl = 1

rc = re.RemoteExecution(config)
rc.start()
print("started, waiting up to 10s for UE nodes...")

for i in range(20):
    time.sleep(0.5)
    if rc.remote_nodes:
        print(f"  found {len(rc.remote_nodes)} node(s):")
        for n in rc.remote_nodes:
            print(f"    {n}")
        break
    else:
        print(f"  [{(i+1)*0.5:.1f}s] no nodes yet...")
else:
    print("TIMEOUT - no UE nodes discovered")

rc.stop()
