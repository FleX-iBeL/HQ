"""The privacy check over HQ's own tree (not its git history): nothing personal in HQ's files."""
import subprocess
import sys

from _kit import APP, HQ, done, need

r = subprocess.run([sys.executable, str(APP / "privacy.py")], cwd=str(HQ), capture_output=True, text=True, timeout=600)
print(r.stdout.strip()[-1500:])
need(r.returncode == 0, "the privacy check finds nothing personal in the files")
done()
