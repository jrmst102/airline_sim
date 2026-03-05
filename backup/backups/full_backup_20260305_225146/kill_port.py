#!/usr/bin/env python3
"""Kill any process using port 8080."""
import os
import subprocess

result = subprocess.run(["lsof", "-ti:8080"], capture_output=True, text=True)
pids = result.stdout.strip().split()
if pids:
    for pid in pids:
        os.kill(int(pid), 9)
    print(f"Killed {len(pids)} process(es) on port 8080.")
else:
    print("Port 8080 is free.")
