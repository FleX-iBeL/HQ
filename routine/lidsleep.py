#!/usr/bin/env python3
"""H45: keep working with the lid closed, on or off, flipped from a call. 10 October 2026 (call at
19:46): "A little script that can switch it on and off for me the sleep setting. And then I can just ask you
and you just flip it."

The setting is macOS's `pmset -a disablesleep`: 1 keeps the laptop working with the lid closed, 0 is back to
normal (it sleeps when the lid closes). Reading it needs nothing (`pmset -g`, "SleepDisabled"). Changing it
needs root, so it runs `sudo -n` on exactly one of the two commands below, which the one-time setup
(routine/install-lidsleep.sh, with his password once) allows without a password, and nothing else. Without
the setup, sudo -n fails at once instead of asking, and this says how to do the setup.

Every minute the helper (tick.py) runs it without options, so the status page also shows a change made by
hand. It writes .status/lidsleep.json.

    python3 "routine/lidsleep.py"        which it is now (written and printed)
    python3 "routine/lidsleep.py" on     keep working with the lid closed
    python3 "routine/lidsleep.py" off    back to normal: it sleeps when the lid closes
    python3 "routine/lidsleep.py" --dry  which it is now, printed only
"""
import json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
NOW_FILE = os.path.join(JV, ".status", "lidsleep.json")
PMSET = "/usr/bin/pmset"
SUDO = "/usr/bin/sudo"
SUDOERS = "/etc/sudoers.d/hq-lidsleep"  # put there by the one-time setup
# Its name before H54 (11 October 2026), set up before then, works the same until it is renamed.
SUDOERS_OLD = "/etc/sudoers.d/jarvis-lidsleep"
SETUP_LINE = f'sudo sh "{os.path.join(HERE, "install-lidsleep.sh")}"'
COMMAND = {"on": [PMSET, "-a", "disablesleep", "1"], "off": [PMSET, "-a", "disablesleep", "0"]}


def read():
    """True: the laptop keeps working with the lid closed. False: it sleeps as normal."""
    out = subprocess.run([PMSET, "-g"], capture_output=True, text=True, timeout=20).stdout
    m = re.search(r"SleepDisabled\s+(\d)", out)
    return bool(m and m.group(1) == "1")  # no line at all means it was never turned on


def set_up():
    return os.path.exists(SUDOERS) or os.path.exists(SUDOERS_OLD)


def words(on):
    return ("On: the laptop keeps working with the lid closed" if on
            else "Off: the laptop sleeps when the lid closes, as normal")


def write(on):
    os.makedirs(os.path.dirname(NOW_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(NOW_FILE), prefix=".lidsleep")
    with os.fdopen(fd, "w") as f:
        json.dump({"t": int(time.time()), "on": on, "words": words(on), "setup": set_up(),
                   "setup_line": SETUP_LINE}, f)
    os.replace(tmp, NOW_FILE)


def flip(want):
    """Runs only the one exact command, without asking for a password. Returns (ok, message)."""
    before = read()
    if before == (want == "on"):
        return True, f"It was already {words(before)}."
    r = subprocess.run([SUDO, "-n"] + COMMAND[want], capture_output=True, text=True, timeout=20)
    after = read()
    if r.returncode != 0 or after != (want == "on"):
        why = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["no answer"]
        if not set_up() or "password" in why[0].lower():
            return False, ("Can't flip it yet: the one-time setup isn't done. Type this once in "
                           f"Terminal, with your laptop password: {SETUP_LINE}  (still {words(after)})")
        return False, f"Couldn't flip it: {why[0]} (still {words(after)})"
    return True, f"Done. {words(after)}."


def main(argv):
    dry = "--dry" in argv
    want = next((a for a in argv if a in ("on", "off")), None)
    bad = [a for a in argv if a not in ("on", "off", "--dry", "status")]
    if bad:
        print("Use: lidsleep.py [on|off]")
        return 2
    try:
        if want:
            ok, msg = flip(want)
            print(msg)
            write(read())
            return 0 if ok else 1
        on = read()
    except Exception as e:
        print(f"Can't read the sleep setting: {e}")
        return 1
    print(f"{words(on)}." + ("" if set_up() else f" (A call can't flip it until the one-time setup: {SETUP_LINE})"))
    if not dry:
        write(on)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
