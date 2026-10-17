# Workflows

Guided workflows a user turns on (H202). Each folder is one: `workflow.json` (its name, what it is, who walks them through it, their file, how to start it), `guide.md` (the guide their agent follows on a call: one question at a time, sparring, writing their answers down as they go) and `blank.md` (their file before anything is filled in). Nothing personal ever goes in here: the answers live in the user's own workspace.

Turn one on: `python3 app/workflows.py on <id>` (list them with no arguments; `off <id>` turns one off, their file stays). Turning on copies the blank file into the workspace when there's none yet, never over an existing one, and adds its line to `where-things-go.md`. The call rules name the ones that are on from the next start of the call line.

- `map/`: the map, from the life you want three to five years out down to next week, in five layers: the vision, the year, the ideal week, the real week, looking back.
