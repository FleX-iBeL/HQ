# Data changes

A version that changes how something is stored in the user's folder ships that change here, one Python file each, with its undo.
The files run in the order of their names, so start each with a number: `002-move-the-notes.py`.

```python
WHAT = "The notes move to their own folder."   # plain words, for the changelog

def do(folder):      # folder: the workspace, a pathlib.Path
    ...

def undo(folder):    # puts everything back exactly as do found it
    ...
```

The main applies a new one within a minute (`routine/datachange.py`). `release.py main` lists them in the changelog and refuses a
release when an undo fails on a copy of the workspace. `update.py back` runs the undos of what it leaves behind, newest first.
