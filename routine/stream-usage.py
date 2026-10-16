#!/usr/bin/env python3
"""The hourly mail check's output, read as it streams (L10). The mail check runs claude -p with
--output-format stream-json; its own run already brings the plan limits back (the stream's
rate_limit_event). This saves them to usage-live.json, in the status line's shape, for the usage
check, so the status page gets fresh numbers every hour for free. It prints the mail check's final
answer, as the log always had it. 9 October 2026: "I think the hourly one on that routine
is also free because it automatically checks. If there's new emails, right? So it should also get
that information back."
"""
import json, sys

import usagelive  # H51: the saving is shared with the call (app/brain.py)


windows, answer = None, None
for line in sys.stdin:
    try:
        d = json.loads(line)
    except ValueError:
        print(line, end="")  # not the stream (an error message): keep it in the log
        continue
    if d.get("type") == "rate_limit_event":
        windows = (d.get("rate_limit_info") or {}).get("unifiedWindows") or windows
    elif d.get("type") == "result":
        answer = d.get("result") or d.get("subtype")
        if d.get("is_error"):  # H42: say so, so the reason can be read afterwards
            kind = d.get("subtype")  # H162: a hit limit comes back as subtype "success"; say the result instead
            print(f"(the run ended with an error: {kind if kind and kind != 'success' else (d.get('result') or 'error')})")

if answer:
    print(answer)
out = usagelive.save(windows, "mail check")
if out:
    print("(usage saved from the mail check's own run: " + usagelive.summary(out) + ")")
else:
    print("(the mail check's run brought no usage back)")
