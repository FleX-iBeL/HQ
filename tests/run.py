#!/usr/bin/env python3
"""Runs every test here (tests/test_*.py), each in its own process, and prints one line per test and the total.

    python3 tests/run.py            all of them
    python3 tests/run.py todo games only these
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
names = sorted(HERE.glob("test_*.py"))
if sys.argv[1:]:
    names = [n for n in names if n.stem[5:] in sys.argv[1:]]
bad = 0
for t in names:
    t0 = time.time()
    r = subprocess.run([sys.executable, str(t)], capture_output=True, text=True, timeout=900, cwd=str(HERE))
    last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    ok = r.returncode == 0
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {t.stem:22} {time.time() - t0:5.1f}s  {last[:160]}")
    if not ok:
        print("\n".join("      " + l for l in (r.stdout + r.stderr).strip().splitlines() if l.startswith(("FAIL", "Traceback", "  File", "    ")) or "Error" in l)[-2500:])
print(f"\n{len(names) - bad} of {len(names)} passed.")
sys.exit(1 if bad else 0)
