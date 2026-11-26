"""The to-do list on a throwaway workspace: add, move, done, a repeating item coming back, undo."""
from _kit import done, need, workspace

tmp = workspace("todo")
import todo  # noqa: E402

r = todo.add("2", "Call the dentist", "", "", "", "", "a test")
need(r.get("ok"), f"add to 2: {r.get('said')}")
items = {i["title"]: i for l in todo.read()["lists"] for i in l.get("items", [])}
need("Call the dentist" in items, "the new item is on the list")
r = todo.move("dentist", "1", "a test")
need(r.get("ok"), f"move it to 1: {r.get('said')}")
lists = {l["key"]: [i["title"] for i in l.get("items", [])] for l in todo.read()["lists"]}
need("Call the dentist" in lists.get("1", []) and "Call the dentist" not in lists.get("2", []), "it moved")
r = todo.done("dentist", "", "a test")
need(r.get("ok"), f"done: {r.get('said')}")
need("Call the dentist" in (tmp / "challenges.md").read_text().split("## 7. Done")[1], "it's under Done")
todo.add("3", "Pay the rent", "", "2026-12-24", "", "", "a test")
r = todo.repeat("rent", "every month", "a test")
need(r.get("ok"), f"repeat every month: {r.get('said')}")
todo.done("rent", "", "a test")
text = (tmp / "challenges.md").read_text()
need(text.count("Pay the rent") >= 2 and "2027-01-24" in text, "done brings a repeating item back with its next date")
before = text
r = todo.undo("a test")
need(r.get("ok") and (tmp / "challenges.md").read_text() != before, f"undo puts the last change back: {r.get('said')}")
need("## Log" in (tmp / "challenges.md").read_text(), "the file keeps its shape")
done()
