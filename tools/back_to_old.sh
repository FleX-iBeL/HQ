#!/bin/bash
# The way back: puts this computer's HQ back on the code from before the new HQ took over (the tag before-hq2) and
# restarts it. Run it in the HQ folder of the computer to put back:  bash tools/back_to_old.sh
# On a Mac the call line and the status server are stopped with this HQ's own stop script (by their saved pids), the code
# goes to the local branch old-hq at before-hq2, the call line starts with the old start script, and the old routine
# (the HQ Routine helper keeps running tick.py every minute) starts the old status server within a minute. On Linux the
# same with stop-linux.sh, the status server by its saved pid, and the hq-start unit. The workspace (his data) is never
# touched: both versions read and write the same files. The other computer is left as it is.
set -u
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
TAG=before-hq2
if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  git fetch --quiet origin "refs/tags/$TAG:refs/tags/$TAG" || { echo "The tag $TAG isn't here and couldn't be fetched."; exit 1; }
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git stash push -m "before going back to $TAG" && echo "Changes to HQ's own files were stashed (git stash list)."
fi
stop_status() {  # the status server, only by the pid its start saved, and only when that process is HQ's status server
  local P=""
  [ -r scratch/status-server.pid ] && P=$(cat scratch/status-server.pid)
  if [ -n "$P" ] && kill -0 "$P" 2>/dev/null && ps -o command= -p "$P" | grep -q "status/server.mjs"; then
    kill "$P"; sleep 2; echo "Status server ($P) stopped."
  fi
}
if [ "$(uname)" = Darwin ]; then
  /bin/zsh app/stop.sh
  stop_status
  git checkout --quiet -B old-hq "$TAG" || exit 1
  /bin/zsh app/start.sh
  /bin/zsh status/phone.sh
else
  bash app/stop-linux.sh
  stop_status
  git checkout --quiet -B old-hq "$TAG" || exit 1
  systemctl --user restart hq-start.service
  SH=$(command -v zsh || command -v bash); "$SH" status/phone.sh
fi
echo "This computer's HQ is on $(git describe --tags --always) (branch old-hq). Back on the new one: git checkout dev, then start it again."
