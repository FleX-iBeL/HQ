#!/bin/sh
# Commit and push inbox.md after the hourly mail check. One fixed command, so it can be pre-approved.
# Only when this workspace is a git repo. The commit goes through HQ's shared lock, so it takes turns
# with a running job, and only inbox.md is committed.
cd "$(dirname "$0")/.." || exit 1
git rev-parse --git-dir >/dev/null 2>&1 || exit 0
git diff --quiet -- inbox.md && exit 0
for lock in "../routine/gitlock.py" "../HQ/routine/gitlock.py"; do
  [ -f "$lock" ] && exec /usr/bin/python3 "$lock" commit "Mail check: $(date '+%Y-%m-%d %H:%M')" inbox.md
done
echo "HQ's routine/gitlock.py not found" >&2; exit 1
