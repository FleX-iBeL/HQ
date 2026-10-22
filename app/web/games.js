// H222 (21 October 2026): the six-week game in the app, part 1: the template every game gets, and its kinds of tracks.
// His words on the call: "Same thing as with the calendar: I can just check whether I did it or I didn't do it, or
// write a note. Then we know at the end of the week we need to discuss it." and "They can always open their past
// history one." The data is app/games.py's (/api/games); this draws it in #gamesheet, after the call page's own script,
// whose helpers it uses (histGet, histNote, sheetPull, backSwipe, showLayout and the other sheets' show functions).
//
// Every game gets the same frame: where it is (setup, day N of 42, looking back, past), what it's for, the win line
// and how far along, today, the days, the diary, a look back per week and the debrief. What a game keeps track of is
// its tracks, each drawn by its kind from GAME_KINDS below. A team adding a kind for a game adds an entry here with the
// same name as in games.py's KINDS: today(game, track, el) for what can be done today, days(game, track, el) for the
// whole game (a grid, a graph), and line(game, track) for a few words.
"use strict";
(function () {
  const $ = id => document.getElementById(id);
  const gameEl = $("gamesheet"), gameBtn = $("gamebtn"), gameBody = $("gamebody"), gameTitle = $("gametitle"), gameNote = $("gamenote");
  if (!gameEl || !gameBtn) return;
  const css = document.createElement("style");
  css.textContent = `
  #gamesheet { position:fixed; left:0; right:0; bottom:0; height:82vh; z-index:10; background:var(--bg); border-top:1px solid var(--muted);
               border-radius:18px 18px 0 0; box-shadow:0 -8px 24px rgba(0,0,0,.2); display:none; flex-direction:column; gap:8px; text-align:left; }
  #gamesheet.open { display:flex; }
  #gamehead { position:relative; flex-shrink:0; }
  #gamesheet h2 { margin:0; font-size:15px; font-weight:600; color:var(--muted); text-align:center; padding:0 74px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  #gameclose, #gameback { position:absolute; top:-8px; border:0; background:transparent; color:var(--fg); font:600 15px/1 -apple-system,sans-serif; padding:8px 10px; cursor:pointer; }
  #gameclose { right:-6px; } #gameback { left:-6px; display:none; }
  #gamesheet[data-view="game"].many #gameback { display:block; }
  #gamebody { flex:1; min-height:60px; overflow-y:auto; -webkit-overflow-scrolling:touch; overscroll-behavior:contain; display:flex; flex-direction:column; gap:10px; padding:2px 2px 6px; }
  #gamebody > * { flex-shrink:0; }
  #gamebody .empty { color:var(--muted); text-align:center; margin:auto; padding:16px; line-height:1.4; }
  #gamebody .gcard { border:0; border-radius:14px; background:var(--soft); color:var(--fg); text-align:left; padding:11px 13px; font:15px/1.35 -apple-system,sans-serif; width:100%; box-sizing:border-box; }
  #gamebody button.gcard { cursor:pointer; }
  #gamebody .gcard > b { display:block; font-size:13px; color:var(--muted); font-weight:600; margin-bottom:5px; }
  #gamebody .gsub { color:var(--muted); font-size:13px; margin-top:3px; overflow-wrap:anywhere; }
  #gamebody .ghead { color:var(--muted); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin:6px 2px -2px; }
  #gamebody .gbar { height:8px; border-radius:99px; background:color-mix(in srgb, var(--muted) 22%, transparent); margin:8px 0 2px; position:relative; overflow:hidden; }
  #gamebody .gbar i { position:absolute; left:0; top:0; bottom:0; border-radius:99px; background:var(--accent); }
  #gamebody .gbar s { position:absolute; top:-2px; bottom:-2px; width:2px; background:var(--fg); opacity:.55; }
  #gamebody .grow { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:6px; }
  #gamebody .grow > span { flex:1 1 120px; min-width:0; }
  #gamebody .gbtn { border:1px solid color-mix(in srgb, var(--muted) 40%, transparent); background:var(--bg); color:var(--fg); border-radius:999px;
                    font:600 14px/1 -apple-system,sans-serif; padding:9px 14px; cursor:pointer; min-width:44px; }
  #gamebody .gbtn.on { background:var(--accent); border-color:var(--accent); color:#04120f; }
  #gamebody .gbtn.x.on { background:var(--stop); border-color:var(--stop); color:#fff; }
  #gamebody .gnum { font:700 20px/1 -apple-system,sans-serif; min-width:44px; text-align:center; }
  #gamebody textarea, #gamebody input[type=number] { width:100%; box-sizing:border-box; border-radius:10px; border:1px solid color-mix(in srgb, var(--muted) 40%, transparent);
                    background:var(--bg); color:var(--fg); font:15px/1.35 -apple-system,sans-serif; padding:8px 10px; resize:vertical; }
  #gamebody .ggrid { display:grid; grid-template-columns:auto repeat(7, 1fr); gap:4px; margin-top:6px; font-size:11px; color:var(--muted); align-items:center; }
  #gamebody .ggrid .c { aspect-ratio:1; border-radius:6px; background:color-mix(in srgb, var(--muted) 16%, transparent); border:0; padding:0; cursor:pointer;
                        font:600 11px/1 -apple-system,sans-serif; color:var(--fg); min-width:0; }
  #gamebody .ggrid .c.done { background:var(--accent); color:#04120f; }
  #gamebody .ggrid .c.x { background:color-mix(in srgb, var(--stop) 70%, transparent); color:#fff; }
  #gamebody .ggrid .c.later { opacity:.35; cursor:default; }
  #gamebody .ggrid .c.today { outline:2px solid var(--fg); outline-offset:1px; }
  #gamebody .ggrid .c.noted::after { content:"•"; }
  #gamebody svg.ggraph { width:100%; height:120px; display:block; margin-top:6px; }
  #gamebody .gentry { border-top:1px solid color-mix(in srgb, var(--muted) 22%, transparent); padding:7px 0 2px; overflow-wrap:anywhere; }
  #gamebody .gentry:first-of-type { border-top:0; }
  #gamebody .gfeel { display:inline-block; font-size:12px; font-weight:700; border-radius:99px; padding:2px 8px; margin-left:6px; background:color-mix(in srgb, var(--accent) 18%, transparent); }
  #gamenote { min-height:0; font-size:13px; color:var(--muted); display:flex; gap:10px; align-items:center; justify-content:center; flex-wrap:wrap; flex-shrink:0; }
  #gamenote button { border:0; background:transparent; color:var(--accent); font:600 13px/1 -apple-system,sans-serif; padding:6px; cursor:pointer; }
  html.m3 #gamebody .gcard { border-radius:20px; }
  `;
  document.head.appendChild(css);

  let data = null, cur = null, ask = 0;
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const btn = (text, cls, fn) => { const b = el("button", "gbtn" + (cls ? " " + cls : ""), text); b.type = "button"; b.addEventListener("click", fn); return b; };
  const fmt = iso => { try { return new Date(iso + "T12:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" }); } catch (e) { return iso; } };
  const pct = x => x == null ? "" : Math.round(x * 100) + "%";
  const addDays = (iso, n) => { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
  const label = t => t.label || t.id;
  const game = id => ((data && data.games) || []).find(g => g.id === id) || null;

  function say(text, undo) {
    gameNote.innerHTML = "";
    if (!text) return;
    gameNote.appendChild(el("span", "", text));
    if (undo) gameNote.appendChild(btn("Undo", "", async ev => { ev.target.disabled = true; if (await send({ undo: true })) draw(); }));
  }
  async function send(body) {
    try {
      const r = await fetch("api/games", { method: "POST", cache: "no-store", headers: { "x-hq": "games", "content-type": "application/json" },
                                           body: JSON.stringify(body) });
      const d = await r.json().catch(() => ({}));
      if (r.ok) { data = d; say(d.said || "", d.undo); mark(); return d; }
      say(d.error || "Couldn't change the game. Try again.");
    } catch (e) { say("Couldn't reach HQ. Try again."); }
    return null;
  }
  const change = (g, body) => send({ game: g.id, ...body }).then(d => { if (d) draw(); });

  // ---- the kinds of tracks: one drawer each, the same names as games.py's KINDS -----------------------------------
  const KINDS = window.GAME_KINDS = window.GAME_KINDS || {};
  KINDS.tick = KINDS.tick || {
    line: (g, t) => { const s = g.sums[t.id]; return s.played ? `${s.done} of ${s.played} days done (${pct(s.share)})` : "Not started yet"; },
    today(g, t, box) {
      const v = (g.days[g.today] || {})[t.id];
      const r = el("div", "grow"); r.appendChild(el("span", "", label(t)));
      r.appendChild(btn("Done", v === "done" ? "on" : "", () => change(g, { tick: v === "done" ? "clear" : "done", track: t.id })));
      r.appendChild(btn("X", "x" + (v === "x" ? " on" : ""), () => change(g, { tick: v === "x" ? "clear" : "x", track: t.id })));
      box.appendChild(r);
    },
    days(g, t, box) {
      const grid = el("div", "ggrid"); grid.setAttribute("role", "group"); grid.setAttribute("aria-label", label(t) + ", day by day");
      for (let w = 0; w < g.weeks; w++) {
        grid.appendChild(el("span", "", "W" + (w + 1)));
        for (let i = 0; i < 7; i++) {
          const day = addDays(g.start, w * 7 + i), v = (g.days[day] || {})[t.id], later = day > g.today;
          const c = el("button", "c" + (v ? " " + v : "") + (later ? " later" : "") + (day === g.today ? " today" : "") + ((g.days[day] || {}).note ? " noted" : ""));
          c.type = "button"; c.title = fmt(day) + (v ? ": " + (v === "done" ? "done" : "X") : "") + ((g.days[day] || {}).note ? " · " + g.days[day].note : "");
          c.setAttribute("aria-label", c.title);
          if (!later) c.addEventListener("click", () => change(g, { tick: v === "done" ? "x" : v === "x" ? "clear" : "done", track: t.id, day }));
          else c.disabled = true;
          grid.appendChild(c);
        }
      }
      box.appendChild(grid);
    }
  };
  KINDS.count = KINDS.count || {
    line: (g, t) => { const s = g.sums[t.id]; return s.total + (t.target ? " of " + t.target : "") + (t.per_day ? " · " + s.days_hit + " days with " + t.per_day : ""); },
    today(g, t, box) {
      const v = (g.days[g.today] || {})[t.id] || 0;
      const r = el("div", "grow"); r.appendChild(el("span", "", label(t) + (t.per_day ? " (" + t.per_day + " a day)" : "")));
      r.appendChild(btn("−", "", () => v > 0 && change(g, { count: -1, track: t.id })));
      r.appendChild(el("span", "gnum", String(v)));
      r.appendChild(btn("+", "", () => change(g, { count: 1, track: t.id })));
      box.appendChild(r);
    },
    days(g, t, box) { if (t.graph) box.appendChild(graph(g, [t])); }
  };
  KINDS.diary = KINDS.diary || {
    line: (g, t) => { const n = g.sums[t.id].entries; return n + (n === 1 ? " entry" : " entries"); },
    today(g, t, box) {
      const r = el("div"); r.appendChild(el("span", "", label(t)));
      const ta = el("textarea"); ta.rows = 2; ta.maxLength = 2000; ta.placeholder = "What happened, what you noticed"; ta.setAttribute("aria-label", label(t));
      r.appendChild(ta);
      const feels = el("div", "grow"); let feel = "";
      for (const f of t.feel || []) {
        const b = btn(f, "", () => { feel = feel === f ? "" : f; [...feels.querySelectorAll(".gbtn")].forEach(x => x.classList.toggle("on", x.textContent === feel)); });
        feels.appendChild(b);
      }
      feels.appendChild(btn("Add", "on", () => { if (ta.value.trim()) change(g, { diary: ta.value.trim(), feel, track: t.id }); }));
      r.appendChild(feels); box.appendChild(r);
    },
    days(g, t, box) {
      const list = (g.diary || []).filter(e => e.track === t.id);
      if (!list.length) { box.appendChild(el("div", "gsub", "Nothing written yet.")); return; }
      for (const e of list.slice(0, 60)) {
        const d = el("div", "gentry"); d.appendChild(el("span", "gsub", e.at));
        if (e.feel) d.appendChild(el("span", "gfeel", e.feel));
        d.appendChild(el("div", "", e.text)); box.appendChild(d);
      }
    }
  };

  // A graph of one or more counts over the six weeks: bars a day for one, lines adding up for several, the target dashed.
  function graph(g, tracks) {
    const NS = "http://www.w3.org/2000/svg", W = 300, H = 110, n = g.length, svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("class", "ggraph"); svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("role", "img");
    const days = [...Array(n)].map((_, i) => addDays(g.start, i)).filter(d => d <= g.today);
    const per = tracks.map(t => days.map(d => +((g.days[d] || {})[t.id] || 0)));
    const runs = per.map(a => a.reduce((o, v) => (o.push((o.length ? o[o.length - 1] : 0) + v), o), []));
    const one = tracks.length === 1;
    const top = Math.max(1, ...(one ? per[0] : runs.flat()), ...(one ? [tracks[0].per_day || 0] : tracks.map(t => t.target || 0)));
    const x = i => (i + .5) * W / n, y = v => H - 4 - v / top * (H - 10);
    const shape = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); svg.appendChild(e); return e; };
    const colors = ["var(--accent)", "var(--wait)", "var(--stop)", "var(--me)", "var(--muted)"];
    if (one) {
      per[0].forEach((v, i) => v && shape("rect", { x: x(i) - W / n * .35, y: y(v), width: W / n * .7, height: Math.max(1, H - 4 - y(v)), rx: 1.5, fill: colors[0] }));
      if (tracks[0].per_day) shape("line", { x1: 0, x2: W, y1: y(tracks[0].per_day), y2: y(tracks[0].per_day), stroke: "var(--fg)", "stroke-dasharray": "3 3", "stroke-width": 1, opacity: .5 });
    } else {
      runs.forEach((r, k) => {
        if (r.length) shape("polyline", { points: r.map((v, i) => `${x(i)},${y(v)}`).join(" "), fill: "none", stroke: colors[k % colors.length], "stroke-width": 2, "vector-effect": "non-scaling-stroke" });
        if (tracks[k].target) shape("line", { x1: 0, x2: W, y1: y(tracks[k].target), y2: y(tracks[k].target), stroke: colors[k % colors.length], "stroke-dasharray": "3 3", "stroke-width": 1, opacity: .7 });
      });
    }
    shape("line", { x1: 0, x2: W, y1: H - 4, y2: H - 4, stroke: "var(--muted)", "stroke-width": 1, opacity: .4 });
    svg.setAttribute("aria-label", tracks.map((t, k) => label(t) + ": " + (runs[k].length ? runs[k][runs[k].length - 1] : 0) + (t.target ? " of " + t.target : "")).join(", "));
    const wrap = el("div"); wrap.appendChild(svg);
    if (!one) wrap.appendChild(el("div", "gsub", tracks.map(t => label(t)).join(" · ") + " · adding up"));
    else wrap.appendChild(el("div", "gsub", "A day at a time" + (tracks[0].per_day ? ", the dashed line " + tracks[0].per_day + " a day" : "")));
    return wrap;
  }

  // ---- the sheet ---------------------------------------------------------------------------------------------------
  const PHASE = { coming: "Coming", setup: "Setup week", playing: "Playing", "looking back": "Looking back", past: "Past" };
  function where(g) {
    if (g.phase === "playing") return `Day ${g.day} of ${g.length} · until ${fmt(g.end)}`;
    if (g.phase === "coming" || g.phase === "setup") return `${PHASE[g.phase]} · starts ${fmt(g.start)}`;
    if (g.phase === "looking back") return `Looking back · until ${fmt(g.look_end)}`;
    return `${fmt(g.start)} to ${fmt(g.end)}`;
  }
  function card(title, parent) { const c = el("div", "gcard"); if (title) c.appendChild(el("b", "", title)); (parent || gameBody).appendChild(c); return c; }
  function kind(t) { return KINDS[t.kind] || { line: () => "", today() {}, days(g, t, box) { box.appendChild(el("div", "gsub", "This kind (" + t.kind + ") isn't drawn here yet.")); } }; }

  function drawList() {
    gameEl.dataset.view = "list"; gameTitle.textContent = "Six-week games";
    gameBody.innerHTML = "";
    const games = data.games, now = games.filter(g => g.phase !== "past"), past = games.filter(g => g.phase === "past");
    const row = g => {
      const c = el("button", "gcard"); c.type = "button";
      c.appendChild(el("b", "", PHASE[g.phase] + " · " + where(g))); c.appendChild(el("div", "", g.name));
      const first = g.tracks[0]; if (first) c.appendChild(el("div", "gsub", label(first) + ": " + kind(first).line(g, first)));
      c.addEventListener("click", () => go(g.id)); return c;
    };
    if (now.length) now.forEach(g => gameBody.appendChild(row(g)));
    if (past.length) { gameBody.appendChild(el("div", "ghead", "Past games")); past.forEach(g => gameBody.appendChild(row(g))); }
  }
  function drawGame(g) {
    gameEl.dataset.view = "game"; gameTitle.textContent = g.name;
    gameEl.classList.toggle("many", data.games.length > 1);
    gameBody.innerHTML = "";
    const top = card(PHASE[g.phase] + " · " + where(g));
    if (g.game) top.appendChild(el("div", "", g.game));
    if (g.for) top.appendChild(el("div", "gsub", "For: " + g.for));
    if (g.rules) top.appendChild(el("div", "gsub", "Rules: " + g.rules));
    // H239: the rest of the game's design, in their words
    [["best", "At my best"], ["lean", "What comes easily"], ["fears", "What could get in the way"],
     ["honest", "Keeps me honest"]].forEach(([k, say]) => { if (g[k]) top.appendChild(el("div", "gsub", say + ": " + g[k])); });
    if (g.phase === "setup" || g.phase === "coming") top.appendChild(el("div", "gsub", `Setup week from ${fmt(g.setup)}, six weeks from ${fmt(g.start)}, look back until ${fmt(g.look_end)}.`));
    const w = g.win || {};
    if (w.text) {
      const c = card("Win line"); c.appendChild(el("div", "", w.text));
      const full = w.need != null ? g.length : w.total;
      if (full) {
        const bar = el("div", "gbar"), fill = el("i"); fill.style.width = Math.min(100, (w.have || 0) / full * 100) + "%"; bar.appendChild(fill);
        if (w.need != null) { const m = el("s"); m.style.left = Math.min(100, w.need / full * 100) + "%"; bar.appendChild(m); }
        c.appendChild(bar);
        c.appendChild(el("div", "gsub", w.need != null ? `${w.have} of the ${w.need} days it takes` : `${w.have} of ${w.total}`));
      }
      const how = g.phase === "past" && w.won != null ? (w.won ? "Won." : "Not won this time.")
        : g.phase === "playing" && w.on_track != null ? (w.on_track ? "On track." : w.reachable === false ? "Out of reach now; still worth playing for what it teaches." : "Behind, still within reach.") : "";
      if (how) c.appendChild(el("div", "gsub", how));
    }
    if (g.phase === "playing") {
      const c = card("Today · " + fmt(g.today));
      for (const t of g.tracks) kind(t).today(g, t, c);
      const note = (g.days[g.today] || {}).note;
      if (note) c.appendChild(el("div", "gsub", "Noted: " + note));
      const ta = el("textarea"); ta.rows = 2; ta.maxLength = 2000; ta.placeholder = "A note for today"; ta.setAttribute("aria-label", "A note for today");
      const r = el("div", "grow"); r.appendChild(btn("Save note", "", () => { if (ta.value.trim()) change(g, { note: ta.value.trim() }); }));
      c.appendChild(ta); c.appendChild(r);
    } else if (g.phase === "setup" || g.phase === "coming") {
      card("").appendChild(el("div", "gsub", "Nothing to tick yet: the first day is " + fmt(g.start) + ". The setup week is for getting ready."));
    }
    for (const t of g.tracks) {
      const c = card(label(t) + " · " + kind(t).line(g, t));
      kind(t).days(g, t, c);
    }
    for (const gr of g.graphs || []) {
      const ts = gr.tracks.map(id => g.tracks.find(t => t.id === id)).filter(Boolean);
      if (ts.length) card(gr.label || ts.map(label).join(" and ")).appendChild(graph(g, ts));
    }
    const notes = Object.keys(g.days).filter(d => g.days[d].note).sort().reverse();
    if (notes.length) {
      const c = card("Notes");
      for (const d of notes) { const e = el("div", "gentry"); e.appendChild(el("span", "gsub", fmt(d))); e.appendChild(el("div", "", g.days[d].note)); c.appendChild(e); }
    }
    const ended = g.looks.filter(x => x.ended || x.look);
    if (ended.length) {
      gameBody.appendChild(el("div", "ghead", "Each week, looking back"));
      for (const x of ended) {
        const c = card(`Week ${x.n} · ${fmt(x.from)} to ${fmt(x.to)}`);
        if (x.look) c.appendChild(el("div", "", x.look));
        else if (g.phase !== "past") {
          c.appendChild(el("div", "gsub", "How did it go: what worked, what got in the way, what changes next week?"));
          const ta = el("textarea"); ta.rows = 3; ta.maxLength = 4000; ta.setAttribute("aria-label", "Week " + x.n + ", looking back");
          c.appendChild(ta); const r = el("div", "grow"); r.appendChild(btn("Keep it", "", () => { if (ta.value.trim()) change(g, { week: x.n, text: ta.value.trim() }); })); c.appendChild(r);
        } else c.appendChild(el("div", "gsub", "Not looked back on."));
      }
    }
    if (g.phase === "looking back" || g.phase === "past" || g.debrief) {
      const c = card("The debrief");
      if (g.debrief) c.appendChild(el("div", "", g.debrief));
      else {
        c.appendChild(el("div", "gsub", "Was it fun, was it useful, what did you learn? What do you keep, change or drop for the next game?"));
        const ta = el("textarea"); ta.rows = 3; ta.maxLength = 6000; ta.setAttribute("aria-label", "The debrief");
        c.appendChild(ta); const r = el("div", "grow"); r.appendChild(btn("Keep it", "", () => { if (ta.value.trim()) change(g, { debrief: ta.value.trim() }); })); c.appendChild(r);
      }
    }
  }
  function draw() {
    if (!data) { histNote(gameBody, "Loading…"); return; }
    if (data.off === "Free") { gameTitle.textContent = "Six-week game"; histNote(gameBody, "Free is on: none of your files. Turn it off in Settings to see your games."); return; }
    if (data.error) { gameTitle.textContent = "Six-week game"; histNote(gameBody, data.error); return; }
    if (!data.games.length) { gameTitle.textContent = "Six-week game"; histNote(gameBody, "No six-week game yet. Design one on a call, and the team sets it up here."); return; }
    const g = cur && game(cur);
    if (g) return drawGame(g);
    const live = data.games.filter(x => x.phase !== "past");
    if (live.length === 1 && data.games.length === 1) return drawGame(live[0]);
    drawList();
  }
  function go(id) { cur = id; say(""); draw(); gameBody.scrollTop = 0; }
  function back() { cur = null; say(""); drawList(); gameBody.scrollTop = 0; }
  function mark() { gameBtn.classList.toggle("on", !!(data && data.games && data.games.length)); }

  async function load() {
    const n = ++ask;
    const d = await histGet("api/games");
    if (n !== ask) return;
    if (d) { data = d; mark(); }
    if (gameOpen()) { const at = gameBody.scrollTop; draw(); gameBody.scrollTop = at; }
  }
  window.showGame = function (open) {
    if (open === gameOpen()) { if (open) load(); return; }
    if (open) {
      if (chatOpen()) { chatEl.classList.remove("open"); chatBtn.setAttribute("aria-expanded", "false"); showBadge(); }
      if (statOpen()) showStatus(false);
      if (histOpen()) showHistory(false);
      if (notesOpen()) showNotes(false);
      if (calOpen()) showCal(false);
      if (todoOpen()) showTodo(false);
      if (typeof coachOpen === "function" && coachOpen()) showCoach(false);  // H225
      if (typeof newsOpen === "function" && newsOpen()) showNews(false);  // H236
      showDirect(false);
      closeWx();
      if (setEl.classList.contains("open")) showSettings(false);
      const live = ((data && data.games) || []).filter(x => x.phase !== "past");
      cur = live.length === 1 ? live[0].id : null; say("");
    }
    gameEl.classList.toggle("open", open);
    gameBtn.setAttribute("aria-expanded", String(open));
    if (open) { draw(); load(); } else ask++;
    showLayout();
  };
  gameBtn.addEventListener("click", () => showGame(!gameOpen()));
  $("gameclose").addEventListener("click", () => showGame(false));
  $("gameback").addEventListener("click", back);
  backSwipe(gameEl, gameBody, () => gameEl.dataset.view === "game" && data && data.games.length > 1, back);
  sheetPull(gameEl, () => showGame(false));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
  load();
})();
