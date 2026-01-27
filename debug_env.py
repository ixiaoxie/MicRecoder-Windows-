import sys
import os
import subprocess

print(f"Python Executable: {sys.executable}")
print(f"Path: {os.environ.get('PATH')}")

try:
    print("Checking schtasks...")
    subprocess.run("schtasks /?", shell=True)
    print("schtasks check done.")
except Exception as e:
    print(f"schtasks check failed: {e}")
