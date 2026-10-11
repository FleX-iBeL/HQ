# Your agents

Put your own things here.

HQ's agents (since 0.2): **Donna** (Sonnet, the basics loaded: your agenda, your list, mail and quick orders) and **Pepper** (Opus, everything loaded: sparring, planning and the bigger picture). The call page shows them with a drawn placeholder until you add a picture.

- **Headshots:** a picture per agent in this folder, named after her: `donna.jpg`, `pepper.jpg` (.jpg, .jpeg, .png or .webp). Square works best.
- **Change or add agents:** `agents.json` in this folder, a list like this (only the parts you change):

```json
[
  {"id": "donna", "personality": "Your own words for how she is."},
  {"id": "coach", "name": "Coach", "load": "deep", "model": "opus", "speciality": "Life coaching", "personality": "..."},
  {"id": "pepper", "hidden": true}
]
```

`load` is how much of this workspace she reads: `quick` (the basics) or `deep` (everything).
