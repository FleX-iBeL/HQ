"""The bucketlist and the wishlist, checked on a throwaway folder: python3 tests/test_lists.py (no Claude, no network).

The engine (add, sub-items as deep as wanted, the totals, links, the time goal, done, let go, move, under, delete,
undo), an old wishlist in the to-do file moving over by itself, whole, with the old table gone after, what a call may and may not run,
and the rule the agents get."""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "app"  # the app's modules
tmp = Path(tempfile.mkdtemp(prefix="hq-lists-test-"))
(tmp / "HQ").mkdir()
(tmp / "challenges.md").write_text("""# Challenges

## 1. Important, not urgent

| Challenge | Type | Deadline | Status | In calendar | Added | Notes |
|---|---|---|---|---|---|---|
| Read a book | active | | open | | 2026-10-05 | |

## Log

- 2026-10-05 10:00: started.
""", encoding="utf8")
os.environ.update(HQ_FOLDER=str(tmp), HQ_WORKSPACE=str(tmp), HQ_ROLE_HERE="1", HQ_UNDER_TEST="1",
                  HQ_LISTS_UNDO=str(tmp / "lists-undo.json"), HQ_TODO_UNDO=str(tmp / "todo-undo.json"),
                  HQ_LISTS_TODAY="2026-11-26")
os.environ.pop("HQ_LISTS", None)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "routine"))
import lists  # noqa: E402

fails = []


def need(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def run(*a):
    return lists.run(list(a))


# the engine
need(run()[1].count("nothing on it yet") == 2, "a fresh HQ has two empty lists and no file")
need(not (tmp / "HQ" / "lists.json").exists(), "reading makes no file")
need(run("add", "Road trip", "--kind", "experience", "--goal", "2028", "--score", "5", "--why", "freedom", "--by", "test")[0] == 0, "add with a kind, a time goal and a score")
run("add", "Licence", "--under", "road trip", "--price", "2.500", "--hours", "40", "--kind", "service")
run("add", "Flights", "--under", "L1", "--price", "1800")
run("add", "Car", "--under", "L1", "--price", "900", "--link", "example.com/cars")
run("add", "Insurance", "--under", "car", "--price", "30", "--every", "month")
run("add", "Deep one", "--under", "insurance", "--price", "12,50", "--every", "year")
run("done", "flights")
d = lists.read()
top = d["lists"][0]["items"][0]
need(top["totals"] == {"once": 5200, "month": 30, "year": 12.5, "left": 3400, "hours": 40, "subs": 5, "subs_done": 1},
     f"the main item adds up everything under it, four levels deep: {top['totals']}")
need(top["sub"][2]["sub"][0]["sub"][0]["name"] == "Deep one", "a sub-item of a sub-item of a sub-item")
need(top["sub"][2]["links"] == ["https://example.com/cars"], "a link without https gets it")
run("drop", "licence")
need(lists.read()["lists"][0]["items"][0]["totals"]["once"] == 2700, "a let-go sub-item no longer counts")
run("open", "licence")
need(run("set", "L1", "price", "abc")[0] == 1 and run("set", "L1", "goal", "next year")[0] == 1 and run("set", "L1", "score", "9")[0] == 1,
     "a price, a time goal and a score that make no sense are refused in plain words")
need(run("set", "L1", "goal", "2028-06")[0] == 0 and lists.read()["lists"][0]["items"][0]["by"] == "2028-06", "the time goal takes a month")
need(run("set", "L1", "notes", "West coast")[0] == 0 and run("set", "L1", "notes", "")[0] == 0, "notes set and cleared")
need(run("link", "L1", "https://a.example")[0] == 0 and run("unlink", "L1", "1")[0] == 0, "a link on and off")
run("add", "Gym", "--price", "35", "--every", "month")
need(lists.read()["lists"][0]["totals"]["month"] == 65, "the whole list adds up")
need("place 1 of 2" in run("move", "gym", "top")[1], "an item moves among its neighbours")
need(run("under", "insurance", "top")[0] == 0 and len(lists.read()["lists"][0]["items"]) == 3, "a sub-item becomes a main item")
need(run("under", "L1", "flights")[0] == 1, "an item can't go under its own sub-item")
need(run("under", "insurance", "car")[0] == 0, "and back under another")
code, said = run("delete", "L1")
need(code == 0 and "5 under it" in said and len(lists.read()["lists"][0]["items"]) == 1, "delete takes everything under it")
need(run("undo")[0] == 0 and len(lists.read()["lists"][0]["items"]) == 2, "undo brings it back")
need(run("undo")[0] == 1, "one undo, not two")
need(run("show", "L1")[1].count("\n") > 5 and "€5,200" in run("show", "L1")[1], "show says the item with its totals")
run("add", "Car", "--list", "wish")
need(run("show", "car")[0] == 1 and run("show", "car", "--list", "wish")[0] == 0, "a name on both lists asks which, --list answers")
run("delete", "car", "--list", "wish")

# an old wishlist in the to-do file: it moves over by itself, whole, and the old table goes
import todo  # noqa: E402
run("add", "Headphones", "--list", "wish", "--notes", "The old ones are worn out.")  # one already on the new list
todo_file = tmp / "challenges.md"
todo_file.write_text(todo_file.read_text(encoding="utf8").replace(
    "| Read a book | active | | open | | 2026-10-05 | |", "| Read a book | active | | open | | 2026-10-05 | |\n| Hang the lamp | active | | open | | 2026-10-06 | |").replace("## Log\n", """## Shopping wishlist

Things to buy.

| Item | Type | When | Status | Added | Notes |
|---|---|---|---|---|---|
| A lamp | | | open | 2026-10-09 | [Link](https://example.com/lamp) |
| Headphones | passive | when there's money | on hold | 2026-10-05 | The old ones are worn out. |

## Details in my own words

**Headphones.** They broke in March.

**Book.** A paragraph about reading, not about a lamp.

**Lamp.** Loosely about lamps.

## Log
"""), encoding="utf8")
need(todo.has_wish_table() and any(l["kind"] == "wish" for l in todo.read()["lists"]), "before: the to-do file has its own wishlist")
run("wish")  # any look at the lists
w = lists.read()["lists"][1]["items"]
need([i["name"] for i in w] == ["Headphones", "A lamp"], "every wish is on the wishlist, none twice")
need(w[1]["links"] == ["https://example.com/lamp"] and w[1]["notes"] == "" and w[1]["added"] == "2026-10-09",
     "a link in the notes becomes a link, the date is kept, and a paragraph that also names another item stays out")
h = w[0]["notes"]
need("reading" not in h and h.count("worn out") == 1 and "When: when there's money" in h and "Status: on hold" in h and "Type: passive" in h
     and "They broke in March" in h, "one already there is filled in with everything the old row had: " + h.replace("\n", " / "))
text = todo_file.read_text(encoding="utf8")
need("| A lamp |" not in text and "| Headphones |" not in text and "Things to buy." not in text and not todo.has_wish_table(),
     "the old table is gone from the to-do file")
need("## Shopping wishlist" in text and "Moved to the wishlist in HQ on" in text and "the wishlist moved to the wishlist in HQ (2 wishes)" in text,
     "the file says where the wishes went, and its log has the line")
need("They broke in March" in text and "| Read a book |" in text, "the rest of the file is as it was")
need(not any(l["kind"] == "wish" for l in todo.read()["lists"]), "the to-do list has no wishlist of its own any more")
need("Nothing to move" in run("import-wish")[1] and len(lists.read()["lists"][1]["items"]) == 2, "a second time moves nothing twice")
need(run("undo")[0] == 1 and len(lists.read()["lists"][1]["items"]) == 2, "the move can't be undone from the lists (the old table is gone)")
r = todo.add("wishlist", "A kettle", by="test")
need("wishlist" in r["said"].lower() and lists.read()["lists"][1]["items"][-1]["name"] == "A kettle"
     and "kettle" not in todo_file.read_text(encoding="utf8"), "a wish added through the to-do script lands on the wishlist")
need(lists.read()["moved"].get("wish") == "2026-11-26", "the app is told the wishlist moved")

# what a call may run, and what the agents are told
sys.path.insert(0, str(HERE.parent / "routine"))
import policy  # noqa: E402
pol = policy.Policy(folder=tmp)
script = HERE / "lists.py"


def may(cmd):
    return pol.decide("Bash", {"command": cmd}).verdict


ok = [may(f'python3 "{script}"'), may(f'python3 "{script}" add "A trip" --price 100'), may(f'python3 "{script}" done L1')]
no = [may(f'python3 "{script}" delete L1'), may(f'python3 "{script}" import-wish')]
need(all(x == policy.ALLOW for x in ok), f"a call reads, adds and ticks off without a yes: {ok}")
need(all(x == policy.DENY for x in no), f"a call never deletes for good or brings the old list over: {no}")
need(may(f"echo x > {tmp}/HQ/lists.json") != policy.ALLOW and pol.decide("Write", {"file_path": str(tmp / "HQ" / "lists.json"), "content": "x"}).verdict != policy.ALLOW,
     "the lists file isn't written past its script")
import config  # noqa: E402
need("lists.py" in config.GAMES_RULE and config.GAMES_RULE in config.VOICE_RULES and "{" not in config.LISTS_RULE.replace("{HQ}", "").replace("{user}", ""),
     "calls get the lists rule")
import role  # noqa: E402
need("delete" in role.WRITES["lists"] and role.SCRIPTS["lists"].endswith("app/lists.py") and "HQ/lists.json" in role.ONE_WRITER,
     "on the backup a change goes to the main, which is the only writer")
need(set(lists.WRITES) == set(role.WRITES["lists"]), "the script and the hand-over agree on what a change is")

print()
print("FAILED: " + "; ".join(fails) if fails else "All passed.")
sys.exit(1 if fails else 0)
