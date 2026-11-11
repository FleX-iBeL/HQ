#!/usr/bin/env python3
"""The front capped (11 November 2026, by hand in the laptop chat, behind the backend switch front_cap).

His words: "Ok so cap the front solution and move weight to the back solution". What the laptop chat told him: "Keep everything, but an
item gets at most two review rounds and then goes to the build as it is." Why (the numbers of 8 to 10 November): an item with 0 or 1 flag
before its build passed QA first time 9 of 9; with 2 to 4 flags 63%, with 5 or more 60%. Rounds three and up bought nothing, and
preparing cost more than building and QA together.

Each of the two front reviews, the item's (review.py, on its wording) and her QA tests' (qatests.py), gets at most CAP flagged rounds per
item, counted per road (qatests.cycle: a QA failure opens a new road and the count starts again, as the twenty did). After the second flag:

  - the item is not stuck and doesn't go to him for that: the review no longer holds the Ready mark, his now or the team's way (review.
    why_not_ready, now_door_why; qatests.why_not, flagged_why, fix_why), and no third round runs (review.tick, now_review, next_round;
    qatests.review). The line marks it and sends it as if the review had passed;
  - its open findings, of either review, are kept with the item as "Open points from the front (not settled)": `sprint.py show LABEL`
    prints them under exactly that heading (the back's reviewer reads it), and the build job's first prompt carries them with one
    sentence: these were raised and not settled before the build; settle each in the build or say why it doesn't apply (tick.start);
  - unchanged: a point only he can answer (her sit-down list, review.sitdown, or her no) still holds the item for him, exactly as before;
    and the hard checks that refuse a seal (a test that crashes in its own setup, doesn't fail first, misses his words) stay as they are.
    Only the reviewer's rounds are capped.

A flagged round is one verdict on one wording: the same words or the same tests reviewed again don't count twice. The item review keeps
its verdicts in each row's "history" (review._attempt, every route: the background review, `review.py now`, F80's pass); an item reviewed
before the history was kept counts its flagged `now` rounds of the road, or (road 0) the F86 loop's rounds, whichever is more.

With the switch off nothing here holds or opens anything: every function below says "not capped".
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CAP = 2  # flagged rounds an item, for each of the two reviews (the laptop chat's choice, from the table: rounds three and up bought nothing)
HEADING = "Open points from the front (not settled):"
BUILD_SENTENCE = ("These were raised and not settled before the build; settle each in the build or say why it doesn't apply.")


def cap_on() -> bool:
    """The backend switch front_cap (app/backend.py)."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
        import backend
        return backend.on("front_cap")
    except Exception:
        return False


def _road(label: str) -> int:
    try:
        import qatests
        return qatests.cycle(label)
    except Exception:
        return 0


def _distinct_flags(rounds, road):
    """The flagged rounds of ROAD, one per wording (fp), oldest first."""
    out, seen = [], set()
    for x in rounds or []:
        if not isinstance(x, dict) or x.get("verdict") != "flag" or int(x.get("cycle") or 0) != road:
            continue
        k = x.get("fp") or x.get("at")
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def _entry(label):
    try:
        import review
        return ((review._state()[1].get("rows") or {}).get(label)) or {}
    except Exception:
        return {}


def item_count(label: str, e: dict | None = None) -> int:
    """How many flagged rounds the item's review has had on this item in its road (one per wording)."""
    e = _entry(label) if e is None else e
    road = _road(label)
    flags = _distinct_flags(e.get("history"), road)
    try:
        import review
        nows = _distinct_flags(review.now_rounds(e), road)
    except Exception:
        nows = []
    return max(len(flags), len(nows), int((e.get("fix") or {}).get("n") or 0) if road == 0 else 0)


def item_capped(label: str, e: dict | None = None) -> dict | None:
    """{"round", "findings"} when the item's review has had its CAP flagged rounds in this road and the switch is on, else None. The
    findings are those of its last flagged round."""
    if not cap_on():
        return None
    e = _entry(label) if e is None else e
    n = item_count(label, e)
    if n < CAP:
        return None
    if e.get("verdict") == "flag":
        fs = list(e.get("findings") or [])
    else:
        last = (_distinct_flags(e.get("history"), _road(label)) or [{}])[-1]
        fs = list(last.get("findings") or [])
    return {"round": n, "findings": fs}


def tests_flags(label: str) -> list:
    """Her QA tests' review: the flagged rounds of the road, one per version of the tests, oldest first."""
    try:
        import qatests
        return _distinct_flags(qatests.state(label).get("reviews"), qatests.cycle(label))
    except Exception:
        return []


def tests_capped(label: str) -> dict | None:
    """{"round", "findings"} when her tests' review has had its CAP flagged rounds in this road and the switch is on, else None."""
    if not cap_on():
        return None
    flags = tests_flags(label)
    if len(flags) < CAP:
        return None
    return {"round": len(flags), "findings": list(flags[-1].get("findings") or [])}


def open_points(label: str) -> list:
    """The open points the front kept with the item: [{"from", "round", "finding"}]; [] when neither review is capped (or the switch is off)."""
    label = label.strip().upper()
    out = []
    ic = item_capped(label)
    if ic:
        out += [{"from": "the item's review", "round": ic["round"], "finding": f} for f in ic["findings"]]
    tc = tests_capped(label)
    if tc:
        out += [{"from": "the review of her QA tests", "round": tc["round"], "finding": f} for f in tc["findings"]]
    return out


def open_words(label: str) -> str:
    """The open points under their heading, one line each, or ""."""
    pts = open_points(label)
    if not pts:
        return ""
    return HEADING + "\n" + "\n".join(f"- {p['from']}, round {p['round']} of {CAP}: {p['finding']}" for p in pts)


def build_note(labels) -> str:
    """For a build job's first prompt: each item's open points from the front with the one sentence, or ""."""
    parts = []
    for lab in labels:
        w = open_words(lab)
        if w:
            parts.append(f"{lab}: " + w)
    if not parts:
        return ""
    return "\n\n" + "\n\n".join(parts) + "\n" + BUILD_SENTENCE


def capped_words(label: str, which: str) -> str:
    """What a review says once its cap is reached."""
    return (f"That was the last round under the cap ({CAP} flagged rounds an item, the front capped): {label} goes on as it is; these "
            f"open points stay with it ({which}), shown by sprint.py show {label} under \"{HEADING}\", and go to the build to settle.")
