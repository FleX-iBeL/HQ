#!/bin/zsh
# A test instance of HQ that is safe to write to: a throwaway copy of the workspace and a second pair of servers on it.
#   tools/test_instance.sh start    copy the workspace (when there's no copy yet) and start the two servers:
#                                   the page and the API on http://127.0.0.1:7872, the status server on 127.0.0.1:4759
#   tools/test_instance.sh stop     stop those two, each only by the pid saved when it started
#   tools/test_instance.sh reset    stop, copy the workspace again, start
#   tools/test_instance.sh status   whether they run, and where the copy is
# The copy (scratch/test-workspace/) holds the data files HQ reads and writes: the top-level .md files, coaching/, and HQ/
# without call transcripts older than a week; never the other folders of the workspace, never .git. It runs as an HQ on its
# own: its own HQ memory (scratch/test-support/, no pairing, so it's main and hands nothing to the real main and syncs
# nothing), no git (the copy isn't a repo, so nothing is committed or pushed), no texts or pushes to the phone
# (HQ_DIRECT_DRY=1, and the copy's phone list is emptied), nothing changed outside HQ by a call or a text (HQ_NO_OUTSIDE=1:
# no mail, no calendar writes), no phone line, no routine (the every-minute routine is never started for it), and its
# status server writes no history (HQ_STATUS_TRIAL=1). A maps key saved there stays in its own file (HQ_MAPS_KEY_FILE), and
# Turn everything on only says what it would do (HQ_FIX_DRY=1).
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
WS="$ROOT/scratch/test-workspace"
SUP="$ROOT/scratch/test-support"
LIVE="$(cd "$ROOT/workspace" && pwd -P)"
PIDS="$ROOT/scratch/test-instance"
export HQ_PORT=7872 HQ_STATUS_PORT=4759 HQ_WORKSPACE="$WS" HQ_SUPPORT="$SUP" HQ_ROLE_READ="$SUP" HQ_DIRECT_DRY=1 \
  HQ_NO_OUTSIDE=1 HQ_STATUS_TRIAL=1 HQ_UPDATE_LOOK=0 HQ_PID_FILE="$PIDS/call.pid" HQ_LOG="$PIDS/call.log" \
  HQ_STATUS_PID_FILE="$PIDS/status.pid" HQ_STATUS_LOG="$PIDS/status.log" \
  HQ_TODO_UNDO="$PIDS/todo-undo.json" HQ_LISTS_UNDO="$PIDS/lists-undo.json" HQ_GAMES_UNDO="$PIDS/games-undo.json" \
  HQ_MAPS_KEY_FILE="$PIDS/maps-key" HQ_FIX_DRY=1
unset HQ_PHONE

copy() {
  [[ "$WS" == "$LIVE" || -z "$LIVE" ]] && { echo "Refused: the copy would be the live workspace."; exit 2; }
  rm -rf "$WS" "$SUP"
  mkdir -p "$WS" "$SUP" "$PIDS"
  # the top-level files and coaching/, then HQ/ without the call transcripts (put back below: only the last week's)
  rsync -a --exclude '/*/' --exclude '.git' "$LIVE/" "$WS/"
  rsync -a --exclude '.git' "$LIVE/coaching/" "$WS/coaching/"
  rsync -a --exclude '.git' --exclude '/calls/' --exclude '/chris/' --exclude '/dashboard-backup/' "$LIVE/HQ/" "$WS/HQ/"
  mkdir -p "$WS/HQ/calls"
  find "$LIVE/HQ/calls" -maxdepth 1 -name '*.md' -mtime -7 -exec cp -p {} "$WS/HQ/calls/" \;
  # no phone to push to from the copy
  find "$WS/HQ" -path '*line*' -name 'subscriptions*.json' -exec sh -c 'echo "[]" > "$1"' _ {} \;
  rm -rf "$WS/.git"
  echo "Copied the workspace to $WS ($(du -sh "$WS" | cut -f1))."
}

running() { [[ -r "$1" ]] && kill -0 "$(<"$1")" 2>/dev/null; }

case "$1" in
  start)
    [[ -d "$WS/HQ" ]] || copy
    mkdir -p "$PIDS" "$SUP"
    /bin/zsh "$ROOT/app/start.sh"
    echo "Test instance: http://127.0.0.1:7872 (status 127.0.0.1:4759). Pids: call $(cat "$PIDS/call.pid" 2>/dev/null), status $(cat "$PIDS/status.pid" 2>/dev/null)."
    ;;
  stop)
    /bin/zsh "$ROOT/app/stop.sh"
    ;;
  reset)
    /bin/zsh "$ROOT/app/stop.sh"
    copy
    /bin/zsh "$ROOT/app/start.sh"
    echo "Test instance: http://127.0.0.1:7872 (status 127.0.0.1:4759). Pids: call $(cat "$PIDS/call.pid" 2>/dev/null), status $(cat "$PIDS/status.pid" 2>/dev/null)."
    ;;
  status)
    running "$PIDS/call.pid" && echo "call line: pid $(<"$PIDS/call.pid") on 7872" || echo "call line: not running"
    running "$PIDS/status.pid" && echo "status server: pid $(<"$PIDS/status.pid") on 4759" || echo "status server: not running"
    echo "copy: $WS"
    ;;
  *)
    sed -n '2,7p' "$0"; exit 2 ;;
esac
