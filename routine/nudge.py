#!/usr/bin/env python3
"""H36: runs inside a job's own Terminal window, next to the chat, started by the window's script.

Every few seconds it looks for a nudge request for its job (routine/quiet.py writes it when the job has
gone quiet and the internet is there). Then it types the text (continue) into its own window, found by its
own tty, and writes the result. Only a window that still runs something counts: Terminal reuses tty
names, and an old finished window can have the same one (as in F8). A request from inside Terminal
needs no macOS permission (the same way the window closes itself, L7), and it never reaches another
window. It ends when the window's script ends.

    nudge.py N TTY PARENT_PID
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quiet

TYPE = """on run argv
	set t to item 1 of argv
	set s to item 2 of argv
	tell application "Terminal"
		with timeout of 15 seconds
			repeat with w in windows
				repeat with b in tabs of w
					if tty of b is t and (count of processes of b) > 0 then
						do script s in b
						return "typed"
					end if
				end repeat
			end repeat
		end timeout
	end tell
	return "window not found"
end run"""


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main():
    n, tty, parent = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    while alive(parent):
        req = quiet.pending(n)
        if req:
            quiet.clear_request()
            r = subprocess.run(["/usr/bin/osascript", "-e", TYPE, tty, req.get("text") or quiet.TEXT],
                               capture_output=True, text=True, timeout=30)
            said = (r.stdout + r.stderr).strip()
            tmp = quiet.RESULT + ".tmp"
            json.dump({"n": n, "at": time.time(), "ok": said == "typed", "said": said}, open(tmp, "w"))
            os.replace(tmp, quiet.RESULT)
        time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
