import sys
import os
import subprocess

# Add project dir to path
sys.path.append(r"d:\Python\recordVoice")

try:
    from mic_recorder import StartupHandler
    
    print("Attempting to set startup task...")
    StartupHandler.set_startup(True)
    
    # Check if task exists
    check_cmd = 'schtasks /Query /TN "MicRecorderAutoStart"'
    result = subprocess.run(check_cmd, capture_output=True, text=True, shell=True)
    
    if "MicRecorderAutoStart" in result.stdout:
        print("\n[SUCCESS] Task 'MicRecorderAutoStart' found in Task Scheduler.")
        print(result.stdout)
    else:
        print("\n[FAILURE] Task not found.")
        print(result.stderr)
        
except Exception as e:
    print(f"Verification Error: {e}")
