# HQ2's API, for the app's page

The page talks to one address: the call line, `http://127.0.0.1:7870` on this computer (HQ_PORT). It serves the page
itself (the folder `web/`, as it is on disk, every file with `Cache-Control: no-cache`), its own API under `/api/`, and
passes everything under `/status/...` on to the status server (`127.0.0.1:4758`, HQ_STATUS_PORT) unchanged: so
`/status/routines.json` on the page's address is the status server's `/routines.json`. The texts' old paths
(`/direct.json`, `/direct/send`, `/direct/subscribe`, `/direct/key`, `/direct/report`, `/direct-sw.js`) are passed on too.

Every change (POST) needs its own `x-hq` header, so a page from elsewhere can't press it (a plain form can't set one).
Answers are JSON. An error is `{"error": "plain words"}` with 400 (nothing asked), 403 (no header, or not on Free), 404
(no such thing), 409 (the main didn't take it) or 500. On a Free-only line (HQ_FREE_ONLY=1) the life endpoints answer
`{"off": "Free", ...}`. The examples below are made up.

**On the backup** (the laptop while the server is main) a change is handed to the main HQ, which writes it; the answer
then has `"handed": "main"` (or `"kept"` when the main can't be reached: it goes by itself later) and a `said` that
ends "It comes back here with the sync in a moment."; the list read right after may not show it yet.

## Trying things safely

Two instances can run at once:

- **The live one** on `127.0.0.1:7870` (page and API) and `127.0.0.1:4758` (status), started with `app/start.sh` and
  stopped with `app/stop.sh`. It reads the live workspace. Only read from it while testing (GET); on this laptop every
  write would be handed to the real main.
- **The test instance** on `127.0.0.1:7872` (page and API) and `127.0.0.1:4759` (status):
  `tools/test_instance.sh start | stop | reset | status`. It runs on a throwaway copy of the workspace in
  `scratch/test-workspace/` (the top-level files, `coaching/`, and `HQ/` with only the last week's call transcripts).
  Write to it freely: it is an HQ on its own (no hand-over to the real main, no sync, no git, so no commit or push), it
  pushes nothing to the phone (HQ_DIRECT_DRY=1: an agent's text answer is a canned line), a call or text changes nothing
  outside HQ (HQ_NO_OUTSIDE=1: no mail, no calendar writes), there's no phone line and no routine, and its status server
  writes no history. `reset` stops it, copies the workspace again and starts it. Its pids are in `scratch/test-instance/`.

Both serve `web/` as it is on disk at every request.

## The page, the agents, the call

| Method, path | Header | Body | Answer |
|---|---|---|---|
| GET `/`, `/call`, `/direct` | | | `web/index.html` (a placeholder when there's none). `/direct` is where a tapped text opens the page |
| GET `/<file>` | | | any file inside `web/` |
| GET `/tour.json` | | | the tutorial's pieces |
| GET `/favicon.ico`, `/apple-touch-icon.png`, `/icon-192.png`, `/icon-512.png` | | | HQ's icon (the night one on a server with HQ_LABEL) |
| GET `/api/agents` | | | `{"agents": [{"id": "donna", "name": "Donna", "full_name": "…", "voice": "af_bella", "load": "quick", "model": "opus", "colour": "#6d28d9", "speciality": "…", "character": "…", …}], "soon": [], "free_only": false}` |
| GET `/agents/{id}/picture` | | | her photo, or a drawn placeholder (SVG) |
| GET `/api/busy` | | | `{"calls": 0}` calls on now (an update waits for 0) |
| POST `/api/offer` | | see "A call" | the WebRTC answer `{"sdp": "…", "type": "answer", "pc_id": "…"}` |

### A call

The page opens the microphone, makes an `RTCPeerConnection({iceServers: []})`, adds the mic track, and makes one data
channel `pc.createDataChannel("chat", {ordered: true})`. It creates the offer, waits for ICE gathering to complete (or
3 s), then:

```
POST /api/offer   Content-Type: application/json
{"sdp": "<the offer>", "type": "offer", "request_data": {
   "agent": "donna",            // donna, pepper or moneypenny; her model and load go with her
   "mode": "quick",             // only for an old page; the agent's own load wins
   "free": false,               // Free: a plain Claude with the internet, nothing of his, nothing kept
   "voice": "af_bella",         // her voice (Settings); else her default
   "voices": {"donna": "af_bella", "pepper": "af_heart", "moneypenny": "bf_emma"},  // for a three-way
   "continue": "2026-11-26-1943",   // optional: go on from a saved call (its name from /api/calls)
   "handover": true,            // optional, with continue: she was put on by another agent
   "callback": true,            // optional, with continue: she's calling back after "hang up and call me back"
   "about": "e1d7…",            // optional: a call about an appointment (its id from /api/calendar)
   "about_todo": "69f2…",       // optional: about a to-do item (its id from /api/todo)
   "about_coaching": "layer-4", // optional: about a layer or check-in (its key from /api/coaching)
   "ring": "12",                // optional: he picked up the agent's call from the notification (?ring=12&agent=… on the page)
   "demo": true, "demo_topic": "calendar"   // optional: the tutorial's demo call (Free, Opus, no tools)
}}
```

The answer is `{"sdp", "type", "pc_id"}`; set it as the remote description. Her voice arrives as the remote audio
track. The page sends `"ping: <ms>"` as plain text on the channel every second (a keep-alive the server ignores).

Page → server, on the data channel (JSON strings):

| Message | What it does |
|---|---|
| `{"type": "hangup"}` | he hung up: the after-call work starts at once. Send it before closing the connection, and on `pagehide` |
| `{"type": "ptt", "held": true}` / `false` | hold-to-talk: while held the turn stays his; on release his turn ends |
| `{"type": "typed", "text": "…"}` | a line typed in the chat; she answers out loud as usual. The **Yes** button sends `{"type": "typed", "text": "Yes"}` |
| `{"type": "cancel"}` | take back what he just said (while `hq-cancellable` is on), or, too late for that, she stops and "Cancel last message" goes in as his turn |

Mute is the page's own: it turns the mic track off (`track.enabled = false`); nothing is sent.

Server → page, on the data channel:

| Message | Meaning |
|---|---|
| `{"type": "hq-state", "state": "listening"}` | listening, hearing (he talks), transcribing (after he let go), thinking, speaking |
| `{"type": "hq-chat", "who": "me", "text": "…"}` | a line for the chat: `who` is `me`, `hq` (her) or `filler`; on a three-way `agent` names who said it |
| `{"type": "hq-cancellable", "on": true}` | the Cancel button may show (or go) |
| `{"type": "hq-cancelled"}` | his last line was taken back: strike it through |
| `{"type": "hq-hangup"}` | she hung up after his goodbye: close the call as a hang-up |
| `{"type": "hq-callback", "agent": "pepper", "call": "2026-11-26-1943"}` | she'll call him right back: hang up, then call `agent` with `continue: call, callback: true` |
| `{"type": "hq-switch", "agent": "moneypenny", "call": "2026-11-26-1943"}` | she put another agent on: hang up, then call `agent` with `continue: call, handover: true` |
| `{"type": "hq-three-way", "agents": ["donna", "moneypenny"]}` | another agent joined this call |

An incoming ring: a push notification "Donna is calling" (from the texts' push) opens `/?ring=N&agent=ID`; the page
starts that call with `request_data.ring = "N"` and that agent. Nothing rings in the page itself.

### Past calls

| GET | Answer |
|---|---|
| `/api/calls` | `{"calls": [{"name": "2026-11-26-1943", "started": "26 November, 19:43", "date": "2026-11-26", "time": "19:43", "agent": "Donna", "continues": "", "said": 12}]}` newest first |
| `/api/calls/{name}` | `{"name", "started", "agent", "lines": [{"who": "me", "text": "…", "time": "19:43", "agent": "…", "cancelled": false}], …}` |
| `/api/last-call` | the newest call the same way, or `{"lines": []}` |

## Donna: the calendar, the to-do list, the lists, notes, mail

| Method, path | Header | Body | Answer |
|---|---|---|---|
| GET `/api/calendar[?fresh=1]` | | | `{"on": true, "looked": 1795716424.0, "looking": false, "error": "", "events": [{"id", "title", "start", "end", "all_day", "where", "notes", "calendar", "free", "link", "others", "gcolor", "mark_id", "mark": "done"\|"x"\|"", "appt_notes": [{"id", "text", "when"}], "ping": false, "color", "kind", "travel": {…}}], "calendars": [{"name", "color"}], "kinds": [{"id", "name", "colour", "color", "gcolor", "template", "own"}]}`. `fresh=1` reads Google again when the copy is over 15 minutes old (`looking` true; ask again a bit later) |
| POST `/api/calendar/mark` | `x-hq: calendar` | `{"id": "<event id>", "mark": "done"\|"x"\|""}` | the calendar as above |
| POST `/api/calendar/note` | `x-hq: calendar` | `{"id", "add": "text"}` or `{"id", "clear": "<note id>"}` | the calendar |
| POST `/api/calendar/ping` | `x-hq: calendar` | `{"id", "on": true, "before": 10}` | the calendar (Donna pings him when it starts) |
| POST `/api/calendar/travel` | `x-hq: calendar` | `{"id", "on": true, "mode": "car"\|"transit"}` | the calendar |
| POST `/api/calendar/kind` | `x-hq: calendar` | `{"id": "<kind id>", "name": "…"}`, `{"id", "colour": "banana"}` or `{"id", "reset": true}` | the calendar |
| GET `/api/todo` | | | `{"lists": [{"key": "1", "num": "1", "name": "Important, not urgent", "kind": "matrix", "items": [{"id", "title", "notes", "deadline", "status", "type", "added", "planned": {"short": "Wednesday 10:00", …}, "repeats": "every month"}]}], "log": ["…"], "mail": [{"when", "from", "subject", "what", "status"}], "blocks": [{"id", "title", "start", "end", "calendar", "short", "past"}], "how": "…", "file": "challenges.md", "changed": 1795716424}` |
| POST `/api/todo` | `x-hq: todo` | one of: `{"add": "text", "list": "1"}` (several lines: several items), `{"done": "<id or words>"}`, `{"letgo": "<id>", "why": "…"}`, `{"move": "<id>", "to": "2"}`, `{"tick": "<id>"}` / `{"untick": "<id>"}` (groceries), `{"order": "<id>", "place": 3}`, `{"rename": "<id>", "title": "…"}`, `{"plan": "<id>", "block": "<block id>"}`, `{"unplan": "<id>"}`, `{"repeat": "<id>", "rule": "every month"}` (`""` or `"off"` stops it), `{"undo": true}` | the list as above, plus `"said": "Added … to 1."`, `"undo": true` (an undo is possible now), `"id"` after a rename |
| GET `/api/lists` | | | `{"lists": [{"key": "bucket"\|"wish", "name": "Bucketlist", "items": [{"id": "L23", "name", "kind", "price", "every", "links", "goal", "hours", "score", "notes", "status", "subs": [ … the same, as deep as wanted ], "totals"}], "totals", "open"}], "kinds": [...], "every": ["once", "month", "year"], "moved": {…}}` |
| POST `/api/lists` | `x-hq: lists` | `{"do": "add", "name", "list": "bucket"\|"wish", "under": "L23"}`, `{"do": "set", "item": "L23", "field": "price", "value": "120"}` (fields: lists.FIELDS), `{"do": "link"\|"unlink", "item", "url"}`, `{"do": "done"\|"open"\|"drop"\|"delete", "item"}`, `{"do": "move", "item", "to": "wish"}`, `{"do": "under", "item", "parent"}`, `{"do": "undo"}` | the lists, plus `said` and `undo` |
| GET `/api/notes` | | | `{"items": [{"id", "when", "text"}], "hers": {"name": "Donna", "items": [{"id", "when", "text"}], "watches": [{"n", "kind", "text", "until", "matches"}], "nudges": [{"n", "text", "paused"}]}}` his quick notes and Donna's notes |
| POST `/api/notes` | `x-hq: notes` | `{"add": "text"}`, `{"clear": "<id>"}`, `{"restore": "<id>"}`, `{"clear_hers": "<id>"}`, `{"restore_hers": "<id>"}`, `{"nudge_done": 3}` | the notes as above |
| POST `/api/here` | `x-hq: here` | `{"lat": 52.37, "lon": 4.89}` (only when he allows his location) | `{"ok": true}` |

The mail list (what the hourly mail check found) comes with `/api/todo` as `mail`. Her past calls: `/api/calls`
(filter by `agent`).

## Pepper: the map, check-ins, the six-week game

| Method, path | Header | Body | Answer |
|---|---|---|---|
| GET `/api/coaching` | | | `{"on": true, "agent": {"id": "pepper", "name": "Pepper"}, "named": "", "map": true, "start": "let's go through my map", "layers": [{"n": 1, "name": "The vision", "status": "…", "word": "done", "counts": {"answered": 25, …}, "total": 32, "can_close": true, "items": [{"state", "key", "question", "note"}]}], "checkins": [{"key", "kind", "title", "due", "from", "next", "when", "line", "layer", "score"}], "due": 0, "thread": [{"at", "from": "me"\|"agent", "text", "why"}], "waiting": false}` (the coaching line is `thread`) |
| POST `/api/coaching` | `x-hq: coaching` | `{"send": "a text to her"}`, `{"done": "<check-in key>"}`, `{"later": "<key>"}` | the same, plus `said` |
| GET `/api/games` | | | `{"games": [{"id", "name", "for", "game", "rules", "win_text", "tracks": [{"id", "kind": "tick"\|"count"\|"diary", "name", "days": {"2026-11-03": "done"}, …}], "weeks": 8, "phase": "playing", "start", "end", "setup", "look_end", "length", "debrief", "best", "lean", "fears", "honest", "remind", "away"}], "kinds": {"tick": "…", "count": "…", "diary": "…"}}` |
| POST `/api/games` | `x-hq: games` | with `"game": "<id>"` and for tick, count and note `"day": "YYYY-MM-DD"` (default today): `{"tick": "done"\|"x"\|"clear", "track"}`, `{"count": "5", "track", "set": false}`, `{"note": "…"}`, `{"diary": "…", "feel": "good", "track"}`, `{"week": "2", "text": "…"}`, `{"debrief": "…"}`, `{"undo": true}` | the games, plus `said` and `undo` |
| GET `/api/workflows` | | | `{"items": [{"id": "map", "name": "Life coaching", "on": true, "what": "…"}]}` |
| POST `/api/workflows` | `x-hq: workflows` | `{"id": "map", "on": false}` | `{"items": […], "said"}` |

## Moneypenny: status, being worked on, planning, hand-overs, sessions, usage, updates, health

All of these are the status server's, read through `/status/` on the page's address. Read only, except the few POSTs named.

| GET | Answer |
|---|---|
| `/status/status.json` | being worked on, the roadmap's status block: `{"state": "BUILDING"\|"TESTING"\|"RELEASING"\|"WAITING"\|"DONE"\|"STOPPED", "title": "🔨 BUILDING", "headline": "Now: …", "notes": [{"label": "Just finished", "text": "…"}, {"label": "Next", …}], "current": {"phase": "Phase A", "steps": [{"name": "A1", "mark": "done"\|"doing"\|"todo"}]}, "log": [{"time": "19:52", "text": "…"}], "updated": "Updated 2026-11-26 19:52", "at": 1795718000, "problems": [], "usageLines": {"five": {"moving": true, "fixed": 70}, "weekly": {…}, "fable": {…}}}` |
| `/status/planning.json` | the planning board, to look at: `{"rows": [{"label": "H12", "title": "…", "phase": "H", "phase_title": "H · Features", "bug": false, "rank": 1, "moscow": "must"\|"should"\|"could"\|"wont"\|null}], "groups": [{"tag": "must", "name": "Must", "labels": ["H12"]}], "count": 40}` (sorted: MoSCoW, bugs first, rank) |
| `/status/handovers.json` | `{"handovers": [{"name": "2026-11-26-something.md", "title": "…", "date": "2026-11-26", "modified": 1795718000.0, "bytes": 4200}]}` newest first |
| `/status/handovers/{name}` | one: the same fields plus `"text"` (Markdown) |
| `/status/sessions.json` | work sessions as recorded: `{"sessions": [{"key": "2026-11-25", "title": "The night", "updated": null, "running": false, "rows": 12}]}` newest first |
| `/status/sessions/{YYYY-MM-DD}` | one: `{"key", "title", "running", "rows": [{"name", "kind", "start", "end"}], "log": [{"at", "text"}], "usage": [{"at", "week"}]}` |
| `/status/usage.json` | the newest reading (this HQ's or the paired one's): `{"checkedAt": "2026-11-26T19:01:08.000Z", "by": "usage check · from a call", "readable": true, "plan": "Max", "limits": [{"label": "5-hour limit", "percent": 31, "resetsAt": "…", "kept": false}, {"label": "Weekly · all models", …}, {"label": "Weekly · Fable", …}], "context": null, "from": "server"}` or `null`. The two bars: the 5-hour and the weekly. Each bar's stop line comes from `status.json`'s `usageLines` (moving lines move with the window; usage.mjs's `stopLine` works it out) |
| `/status/routines.json` | health: `{"broken": [{"store", "what", "file", "why", "say"}], "noLog": false, "forYou": [{"who", "question", "since", "box"}], "laptop": true, "where": "Local · macOS", "now": 1795720000.0, "routines": {"mail": {"state": "ok"\|"running"\|"waiting"\|"down"\|"off", "text": "…", "at", "last", "next", "every", "why", "detail"}, "call": {…}, "beat-laptop": {…}, …}, "incidents": [{"id", "key", "down", "why", "fixes": [{"at", "what"}], "back"}], "temperature": {…}, "battery": {…}, "stats": {…}, "lidsleep": {…}}` |
| `/status/routines-history.json?h=24` | `{"now", "samples": [{"t", "s": {"mail": "ok", …}}]}` one a minute |
| `/status/temperature-history.json?h=24`, `/status/battery-history.json?h=24`, `/status/stats-history.json?h=24` | `{"now", "samples": [...]}` |
| `/status/where.json` | `{"where": "Local · macOS", "role": {"text": "…"} \| null}` |
| `/status/hq.json` | the Mac app's summary (desktop/hq_control.py health) **[it still reads the old HQ's ports: see the report]** |
| `/status/install`, `/status/install.json` | the installer's checklist |
| `/status/api/role` | `{"name", "main", "acting": "main"\|"backup", …}` this HQ's role |

| POST | Header | Body | Answer |
|---|---|---|---|
| `/status/api/lidsleep` | `x-hq: lidsleep` | `{"want": "on"\|"off"}` | `{"ok", "said"}` (409 off a Mac) |
| `/status/api/handover` | `x-hq: handover` | `{"want": "on"\|"off"}` | `{"ok", "said"}` |
| `/status/hq/fix` | `x-hq: fix` | | turns on what's off (never stops anything) |

Updates (on the call line itself):

| Method, path | Header | Answer |
|---|---|---|
| GET `/api/update` | | `{"version": "1.0.3", "tag": "v1.0.3", "ahead": 0, "latest": "1.0.4", "available": true, "new_tag": "v1.0.4", "new": [{"title", "version", "groups": [{"name", "items": ["…"]}]}], "checked", "offline", "platform": "darwin", "mac": true, "run": {"state": "idle"\|"waiting"\|"updating"\|"done"\|"failed", "step", "message"}, "clash": {…}\|null}` |
| GET `/api/changelog` | | `{"version", "ahead", "versions": [{"title", "version", "groups"}]}` |
| POST `/api/update/start` | `x-hq: update` | starts the update; the status as above |
| POST `/api/update/check` | `x-hq: update` | looks on GitHub now; the status |
| POST `/api/update/clash-chat`, `/api/update/clash-ok` | `x-hq: update` | after an update, a possible clash with their own extensions: talk it through (a text to their agent) or it's fine; the status plus `said`, `open: "texts"` |

## Texts (Donna's line, Pepper's coaching line, Moneypenny's line)

| Method, path | Header | Body | Answer |
|---|---|---|---|
| GET `/direct.json` | | | Donna's line: `{"agent": {"id": "donna", "name": "Donna", "colour": "#6d28d9", "key": "<VAPID public key>", "phones": 1}, "line": "direct", "messages": [{"at": 1795718000.1, "from": "me"\|"agent", "text": "…", "why": "reply"\|"remind"\|"mail"\|…, "id": "…"}]}` (the last 200) |
| GET `/direct.json?line=team` | | | Moneypenny's line, the same shape, `"line": "team"` |
| POST `/direct/send` | `x-hq: direct` | `{"text": "…", "line": "team"` (optional; Donna's without), `"lat", "lon"` (optional)`}` | `{"ok": true}`; her answer lands in the thread a little later: poll `/direct.json` |
| GET `/direct/key` | | | `{"key": "<VAPID public key>"}` for `pushManager.subscribe` |
| POST `/direct/subscribe` | `x-hq: direct` | the browser's PushSubscription JSON | `{"ok": true, …}` |
| POST `/direct/report` | `x-hq: direct` | what the page or its worker saw (`{"shown": "…", "error": "…"}`) | `{"ok": true}` |
| GET `/direct-sw.js` | | | the service worker for pushed texts (register it at scope `/`). A tap opens the push's `url` (`/direct` or `/direct?line=team`), and a ring opens `/?ring=N&agent=ID` |

Pepper's coaching line is `/api/coaching` (`thread`, and `{"send": …}`).

## Settings

| Method, path | Header | Body | Answer |
|---|---|---|---|
| GET `/api/features` | | | What HQ helps you with: `{"items": [{"id": "calendar", "name": "Calendar", "line": "…", "buttons": ["calbtn"], "on": true, "needs": "texts", "needs_name": "Texts with Donna", "waiting": false, "fixed": "Off on this computer", "key": {"key": false, "kind": ""}}]}`. Ids: calendar, todo, texts, weather, travel, driving, mail, notes, team (the Status place), coaching |
| POST `/api/features` | `x-hq: features` | `{"id": "weather", "on": false}` | `{"items": […], "said"}` |
| POST `/api/drive/key` | `x-hq: features` | `{"key": "AIza…"}` keeps their maps key on this computer; `{"key": ""}` forgets it | `{"items": […]}` (the key itself never comes back) |
| GET `/api/weather[?fresh=1][&lat=..&lon=..]` | | | `{"for": "Amsterdam", "looked", "gps": false, "home": "Amsterdam", "now": {…}, "hours": [...], "days": [...], "alert": {"on": true, "n": 6}}` |
| POST `/api/weather/alert` | `x-hq: weather` | `{"on": true}` | the rain alert on or off |

Voices, sound, light and dark are the page's own (kept on the device); the voices an agent can have are
`config.VOICES` (`af_heart`, `af_bella`, `bf_emma`, …); the chosen one goes with each call's `voice`.

## Not sure / to check

- `/api/weather`'s fields beyond `for`, `looked`, `gps`, `home` and `alert` were not seen with real data (the copy had no
  fresh reading); they come from `app/weather.py view`.
- `/status/hq.json` comes from the Mac app's control script, copied unchanged; it still looks at the old HQ's ports.
- The `travel` object on an appointment and a game track's day fields are as `trips.py` and `games.py` write them; read
  `app/trips.py` (`page_view`) and `app/games.py` (`read`) for the exact keys.
