#!/bin/sh
# H45 (HQ): the one-time setup, run once by the user with their password:
#   sudo sh routine/install-lidsleep.sh   (from HQ)
# Lets only "pmset -a disablesleep 1" and "pmset -a disablesleep 0" run without a password, so a call
# can flip the lid-closed sleep. The file is checked with visudo before it goes in, so a mistake can't
# break sudo. To undo: sudo rm /etc/sudoers.d/hq-lidsleep
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
if [ "$(id -u)" != "0" ]; then
  echo "Run it with sudo in front, like this:"
  echo "  sudo sh \"$HERE/install-lidsleep.sh\""
  exit 1
fi
SRC="$HERE/hq-lidsleep.sudoers"
TMP=$(mktemp /tmp/hq-lidsleep.XXXXXX)
if [ -z "$SUDO_USER" ] || [ "$SUDO_USER" = "root" ]; then
  echo "Run it from your own account, with sudo in front."
  exit 1
fi
sed "s/^YOUR_USER /$SUDO_USER /" "$SRC" > "$TMP"
chown root:wheel "$TMP"
chmod 440 "$TMP"
if ! /usr/sbin/visudo -cf "$TMP" >/dev/null; then
  rm -f "$TMP"
  echo "The rule didn't pass the check, so nothing was changed."
  exit 1
fi
mv "$TMP" /etc/sudoers.d/hq-lidsleep
rm -f /etc/sudoers.d/jarvis-lidsleep  # H54: the same rule under its name from before
/usr/sbin/visudo -c >/dev/null
echo "Done. From now on a call can flip the lid-closed sleep; nothing else runs without your password."
[ -n "$SUDO_USER" ] && sudo -u "$SUDO_USER" python3 "$HERE/lidsleep.py" >/dev/null 2>&1 || true
