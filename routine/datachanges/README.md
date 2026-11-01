# Data changes

A version that changes how something is stored in the user's folder ships that change here, one Python file each, with its undo.
The files run in the order of their names, so start each with a number: `002-move-the-notes.py`. That number is what the change is: rename it if you
like, it won't run again, but it keeps its number. A release is refused when two changes share one or a change got a new one.

```python
WHAT = "The notes move to their own folder."   # plain words, for the changelog

def do(folder):      # folder: the workspace, a pathlib.Path
    ...

def undo(folder):    # puts everything back exactly as do found it
    ...
```

The main applies a new one within a minute (`routine/datachange.py`), once it's committed, unchanged from HEAD, and on GitHub's dev (on a
friend's copy: in the release she stands on); a file that's only in the folder is left alone and said once in the routine's log. `release.py main` lists them in the changelog and refuses a
release when an undo fails on a copy of the workspace. `update.py back` runs the undos of what it leaves behind, newest first.
