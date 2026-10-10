"""Where HQ is, and where the user's own files are (phase M, M1, 10 October 2026).

HQ is the app: the same for everyone, its code in this folder. The user's own data lives in one
folder at the top of HQ called workspace, which the HQ repo ignores completely (it may be a link
to a folder elsewhere). Runtime state (scratch/, .status/) stays in HQ, also
ignored by the repo.

    HQ         this app's folder (the parent of routine/)
    WORKSPACE  HQ/workspace, or HQ_WORKSPACE
    FOLDER     the workspace with the link resolved: where Claude works, git runs and jobs start
               (the same path a chat in that folder has, so its settings and memory are found)
    DATA       FOLDER/Jarvis VA: the roadmap with its status block and queue, and the call transcripts
    ROADMAP    DATA/roadmap.md, or JARVIS_ROADMAP
"""
import os

HQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WORKSPACE = os.environ.get("HQ_WORKSPACE") or os.path.join(HQ, "workspace")
FOLDER = os.path.realpath(WORKSPACE)
DATA = os.path.join(FOLDER, "Jarvis VA")
ROADMAP = os.environ.get("JARVIS_ROADMAP") or os.path.join(DATA, "roadmap.md")


def agent_label(name: str, default_prefix: str = "com.hq") -> str:
    """The id of an installed LaunchAgent, e.g. agent_label("jarvis-watchdog"): the one in
    ~/Library/LaunchAgents ending in .<name>.plist (an older install may use another prefix),
    else com.hq.<name>, as this HQ installs it."""
    folder = os.path.expanduser("~/Library/LaunchAgents")
    try:
        found = sorted(f for f in os.listdir(folder) if f.endswith(f".{name}.plist"))
    except OSError:
        found = []
    return found[0][:-len(".plist")] if found else f"{default_prefix}.{name}"
