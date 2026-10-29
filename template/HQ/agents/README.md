# Your agents

Put your own things here.

HQ's agents (since 0.2): **Donna** (Opus, the basics loaded: your agenda, your list, mail and quick orders) and **Pepper** (Opus, everything loaded: sparring, planning and the bigger picture), and **Moneypenny** (Opus, everything loaded: building HQ with the team, what's ready and what's done). The call page shows them with a drawn placeholder until you add a picture.

Each has her own character on calls; these are HQ's defaults, yours to change:

- **Donna:** quick and dry, a bit cheeky, knows what you need before you finish. "Hey you. What do you need?" Pushing back: "You said that yesterday too. Shall I just put it in?"
- **Pepper:** warm, calm and unhurried, talks it through with you like a real phone call; no one-liners. "Hey, <your name>. What's on your mind?" Pushing back: "So... that's the third build today. Is this the needle mover, or the fun one?"
- **Moneypenny:** cool and composed, dry wit, few words; the gatekeeper who lets nothing go to the team until it's ready, and checks it's done before it's called done. "<Your name>. Go ahead." Pushing back: "Noted. Does it need building now, or can it wait for the sprint?"

Settings on the call page shows each one's character under her voice, marked HQ's default or your own.

- **What she says about herself** (H132): when an agent tells you something about herself on a call or in her chat (her chair, her desk, what she was up to), it's kept in her own list here, `<id>-about-herself.md` (one line each, written after the call or by her chat), and loaded with her character every time, so she stays the same person. Change or remove a line whenever you like.
- **Headshots:** a picture per agent in this folder, named after her: `donna.jpg`, `pepper.jpg` (.jpg, .jpeg, .png or .webp). Square works best.
- **The handbook and the cycles** (H298): with "The agents run themselves" on in Settings, every agent reads `handbook.md` here under her character (part one is the shared core, part two her own section: her job, her ten percent, what she decides and what she asks); `cycles.json` holds each one's cycle (when her bigger session runs, her small steps, her box in minutes and turns, her share of the weekly usage, her hours; numbers only, changed in Settings or on a call). What her cycles did goes in `../ledger/<id>.md`. Off, none of it is read.
- **Change or add agents:** `agents.json` in this folder, a list like this (only the parts you change):

```json
[
  {"id": "donna", "character": "One line for Settings", "personality": "Your own words for how she is and how she talks.",
   "pushback": "A line that sounds like her when she says no.",
   "greetings": {"morning": ["Morning{s}. What's up?"], "afternoon": ["Hey{s}. What's up?"]},
   "continue_greetings": ["Hey{s}. Where were we?"]},
  {"id": "coach", "name": "Coach", "load": "deep", "model": "opus", "speciality": "Life coaching", "personality": "..."},
  {"id": "pepper", "hidden": true}
]
```

`load` is how much of this workspace she reads: `quick` (the basics) or `deep` (everything). In greetings `{s}` is " your name", `{n}` ", your name" and `{N}` "your name. " (from your me.md); `greetings` can also be one list for the whole day. Restart the call line to hear the change.
