import subprocess, sys
def ping_parent():
    try:
        subprocess.run([sys.executable, '-c', 'import sys; sys.exit(0)'], timeout=1)
    except Exception:
        pass
    return False
