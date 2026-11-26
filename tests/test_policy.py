"""What a call may run: a handful of allowed and refused commands, and the guards around his files."""
from _kit import APP, HQ, ROUTINE, done, need, workspace

tmp = workspace("policy")
import policy  # noqa: E402

pol = policy.Policy(folder=tmp)


def may(cmd):
    return pol.decide("Bash", {"command": cmd}).verdict


A, D = policy.ALLOW, policy.DENY
need(may(f'python3 "{APP}/todo.py" add 1 "Buy milk"') == A, "the to-do list's script runs without a yes")
need(may(f'python3 "{ROUTINE}/planning_board.py" --words') == A, "the planning board reads without a yes")
need(may(f'python3 "{ROUTINE}/handovers.py"') == A, "the hand-overs read without a yes")
need(may(f'python3 "{ROUTINE}/jobs.py" mail-fast "tonight"') == A, "the mail check more often for a while")
need(may(f'python3 "{ROUTINE}/jobs.py" add "build something"') == D, "there's no team to give work to")
need(may(f'python3 "{ROUTINE}/jobs.py" mail-off') == D, "the mail switch itself is his own hand's")
need(may(f"grep -n Phase {tmp}/HQ/roadmap.md") == A, "a look is free")
need(may(f"echo x > {tmp}/challenges.md") == D, "the to-do file is never written through the shell")
need(pol.decide("Write", {"file_path": str(tmp / "HQ" / "roadmap.md"), "content": "x"}).verdict == D, "the planning file is never written whole")
need(may("claude -p hello") == D, "no other Claude through the shell")
need(pol.decide("mcp__claude_ai_Gmail__send_message", {}).verdict == D, "mail is never sent")
need(pol.decide("Agent", {}).verdict == D, "Claude's own helper isn't used on a call")
import os  # noqa: E402
os.environ["HQ_NO_OUTSIDE"] = "1"
need(pol.decide("mcp__claude_ai_Google_Calendar__create_event", {"summary": "x"}).verdict == D, "a test instance changes nothing outside")
need(pol.decide("mcp__claude_ai_Google_Calendar__list_events", {}).verdict == A, "a test instance may still look")
done()
