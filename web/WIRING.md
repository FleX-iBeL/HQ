# Wiring an area to real data

The app runs the design's templates on the prototypes' made-up data. You replace that data with real data, one area at a time. Each area has its own module, demo file and templates, so you only edit your own files.

## Your files

| Area | Module (yours) | Demo data (yours) | Screens | Template files (yours) |
|---|---|---|---|---|
| call | `logic/call.js` | `logic/demo/call.js` | call, transcript (the live transcript of a call), mini bar, incoming call, add someone | `templates/*/*/call.html`, `templates/phone/shared/transcript.html`, `templates/mac/thread/transcript.html` |
| texts | `logic/texts.js` | `logic/demo/texts.js` | chat (texts with an agent), past calls, one past call | `templates/phone/shared/chat.html`, `templates/mac/{desk,spotlight}/chat.html`, `*/shared/pastCalls.html`, `*/shared/callLog.html` |
| agenda | `logic/agenda.js` | `logic/demo/agenda.js` | agenda, appointment (travel, notes), kinds of time, calendar filter; Today on home; Donna's card | `*/shared/agenda.html`, `appt.html`, `agendaFilter.html`, `kinds.html` |
| todo | `logic/todo.js` | `logic/demo/todo.js` | to-do (four boxes), the list behind a box, an item, done and let go, groceries | `*/shared/todo.html`, `todoItem.html`, `todoList.html`, `groceries.html` |
| lists | `logic/lists.js` | `logic/demo/lists.js` | the lists screen and its tabs, bucketlist, wishlist, a bucket item, a sub-item | `*/shared/lists.html`, `templates/*/*/bucketItem.html`, `*/shared/subItem.html` |
| inbox | `logic/inbox.js` | `logic/demo/inbox.js` | mail, notes (his quick notes, her notes, nudges, eye-outs, cleared) | `*/shared/mail.html`, `notes.html` |
| pepper | `logic/pepper.js` | `logic/demo/pepper.js` | the map, a layer, check-ins, the game, your games | `*/shared/map.html`, `layer.html`, `checkin.html`, `game.html`, `games.html` |
| mp | `logic/mp.js` | `logic/demo/mp.js` | hand-overs, a hand-over, status, planning board, work sessions, health, updates | `*/shared/handovers.html`, `handover.html`, `status.html`, `planning.html`, `sessions.html`, `health.html`, `updates.html` |
| settings | `logic/settings.js` | `logic/demo/settings.js` | settings and the design switch, features, sound, voices, weather, tutorial and its tour, the states | `*/shared/settings.html`, `features.html`, `sound.html`, `voices.html`, `weather.html`, `tutorial.html` |

`*` means both `phone` and `mac`. Make a change in each device's copy, and in each design's copy when the file is per design.

The core owns these files, and nobody else edits them: `logic/core.js`, `logic/util.js`, `app.js`, `engine.js`, `api.js`, `boot.js`, and the per-design `shell.html`, `home.html` and `space.html`. Home, the spaces and the shells show values from every area. If you need a markup change there, ask whoever owns the core.

## How an area module works

- `NAME`, `start` (its state at the start), `vals(st, ctx, D)` returns `{ values, agent, sheets, titles, submit }`.
  - `values` are the template's holes.
  - `agent.donna.rows` / `homeLines` are its rows in Donna's space and its lines on her home card, keyed (core orders them).
  - `sheets` are the sheets it opens (`app.setState({ sheet: 'plan' })`).
  - `titles` are its screens' titles.
  - `submit` is what its text boxes do on Enter.
- `D` is where the data comes from:
  - The demo module, while `WIRED = false`, or in demo mode (`?demo=1`, or localStorage `hq-demo` = `1`).
  - `state.data.<NAME>` once you set `export const WIRED = true`.
- While `state.data.<NAME>` is missing, your `vals` isn't called. Your holes stay empty, so the template shows its own empty state or nothing. Export `LOADING_OK = true` if you'd rather handle `D == null` yourself (for example, to show "Loading").
- Read the real data from `D` and keep the shaping. The demo module shows the shape your shaping expects. Either make the server's answer fit that shape in `load`, or change your shaping.
- `export async function load(app)`: fetch and store. It is called once at mount, again when the server answers after being away, and on a return to the foreground only when that area's last load is over a minute old. A load asked while the area's own load still runs is dropped. A GET asked while the same GET is on its way gets that same answer (`api.js`), so two areas reading one endpoint cost one request. Any poll of your own stops while `document.hidden`.
  ```js
  export async function load(app) { app.setData('todo', await app.api.get('api/todo')); }
  ```
- `export const enter = { todoList: (app) => … }` runs when that screen opens. Use it for data that must be fresh on entry.
- Both `load` and `enter` only run for a wired area outside demo mode. The made-up app stays available with `?demo=1`.
- Talk to the server only through `app.api` (`api.js`):
  - `api.get(path)` and `api.post(path, body, tag)`. `tag` is the `x-hq` header the server asks for on changes: `todo`, `calendar`, `notes`, `features`, `weather`, `games`, …
  - A failed answer throws `ApiError { status, path, message, body }`.
  - A request that can't reach the server sets the app offline, and HQ shows its offline banner. Outside demo mode that banner is driven by real failures, not by the review switch.
- After a change: post it, then `load(app)` again, or patch `state.data` with `app.setData(NAME, (old) => …)`.
- Say what happened with `app.say(text, undoFn)`. With a function the toast shows Undo (for 8 seconds), which runs it and clears the toast; without one there's no Undo. In demo mode the prototypes' own rule decides.
- The time: `state.clockNow` changes once a minute, on the minute, while the page is shown, so anything that shows the time renders again.
- To-do item ids: the prototypes open the same example for every bucket item and every past game. `bucketId` (lists) and `gameId` (pepper) in state already say which one is open. Use them to pick the real item.

## What the core shows from several areas

Home, the spaces and the shells show words that come from several areas or the clock: they are under `hv` (core.js, `shellWords`), with the design's own words in demo mode. Each area feeds them through what it already gives:

- An agent's card (`card(st, D)`: kicker, headline, sub, line) for Donna (agenda), Pepper and Moneypenny. A card may say `actionOn: false` to hide the button under it in her space, and `act: (app) => …` for what that button does.
- Space rows and home lines, keyed or as a list. A keyed row from another area takes the place of a list's row with the same label, else it comes after it (so texts and past calls fill Pepper's and Moneypenny's rows).
- `nudges` and `nudgeCount` (inbox), `wxChip` and `setv.weather` (settings), `mpv.banner` and `mpv.usage.bars` (mp), the call's state (`cRing`, `cStarted`), and the texts' lines (Thread's labels).
- The agents' names, colours and what each is for come from `/api/agents` (read by the call area); the design's values stay where the server says nothing.

## Adding a hole

Write `{{ name }}` or `{{ a.b.c }}` in your template and return `name` from your `values`. Holes are paths only, never expressions. Compute the value in `vals` and give it a name.

- `x="{{ fn }}"` passes the raw value (a function, a number).
- `x="a {{ p }} b"` is a string.
- `<sc-if value="{{ c }}">` shows its content when `c` is truthy.
- `<sc-for list="{{ xs }}" as="x">` repeats its content, with `{{ x.… }}` and `{{ $index }}` available.
- Events are `onClick`, `onInput`, `onChange`, `onKeyDown`, `onSubmit` (camelCase), each bound to a function you return. The function gets the event.

## A text box

In the template:

```html
<input value="{{ drafts.NAME }}" onInput="{{ typed.NAME }}" onKeyDown="{{ enter.NAME }}">
```

In your module, return `submit: { NAME: (text) => … }`. The core keeps the draft in `state.drafts.NAME` without a render per keystroke (the box already shows the text), so read a draft from `app.state.drafts` in a handler. A box of your own that keeps what is typed in state uses `app.keepDraft(NAME, e.target)` (or `app.quietState(patch, e.target)`), never a `setState` per keystroke. Enter hands your function the trimmed text and clears the box. NAME must be unique across the app, so start it with your area (`todoAdd`, `inboxNote`). The bucketlist and wishlist boxes (`bucket`, `wish`) are the examples.

## Lists that change: the key rule

Put `key="{{ item.id }}"` on the first element inside an `sc-for` whose items can be added, removed or re-ordered. The nodes then follow the items, and nothing jumps or loses focus. Without a key, an item's place in the list is its identity.

## Checks (run all three before you hand over)

1. `node tests/web/logic_equivalence.mjs` (from HQ2). It compares every render value with the prototypes' own logic over thousands of taps, and checks the wiring switch.
   - It is the guard that the demo still behaves as designed. It runs the app in demo mode, so it still holds once your area is wired: keep your shaping working on the demo module.
   - Differences you make on purpose go in its `IGNORE` list, with a comment saying why.
2. Serve the app (`python3 tools/serve_web.py`, http://127.0.0.1:7871).
   - Requests that aren't a file under `web/` go to the backend: `HQ_DEV_BACKENDS`, by default 7870, then 7860, then 4748.
   - Writes are refused unless `HQ_DEV_WRITE_BACKENDS` names a backend. Never point it at live data.
   - Open `tests.html`: the engine tests must say 0 failed.
3. Open `tests.html?smoke`. It visits every screen of all six combinations and clicks every button. It must say 0 errors.

`python3 tools/split_design.py --check` shows which templates were changed by hand since the split. Run without `--check`, it never writes over them unless you pass `--force`.
