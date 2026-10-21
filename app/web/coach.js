// H225 (21 October 2026): Life coaching as its own place in the app, with check-ins. His words on the call: "maybe we
// can just make it sort of like a [life] coaching module where you can click on the button. You can see this checklist
// as well ... which layers you've checked off with the sessions ... We can actually make it separate sessions so also
// it won't drift off ... a speed dial line to you where we just talk about life coaching, where the weekly checkups
// come there", and earlier: "it changes colour or whatever, or you get the red dot ... I click there and then we can
// dive deep right into it immediately."
//
// The data is app/coaching.py's (/api/coaching): the layers of their map with the checklist (H224), the check-ins and
// which are due, and the coaching line (a thread with the workflow's agent). This draws it in #coachsheet, after the
// call page's own script, whose helpers it uses (histGet, histNote, sheetPull, backSwipe, showLayout, call and the
// other sheets' show functions). Start on a layer or a check-in starts its own call about only that (about_coaching).
// What's been read on the coaching line is kept on this device. No push notification: only the dot.
"use strict";
(function () {
  const $ = id => document.getElementById(id);
  const sheet = $("coachsheet"), btn = $("coachbtn"), body = $("coachbody"), title = $("coachtitle"), note = $("coachnote");
  if (!sheet || !btn) return;
  const css = document.createElement("style");
  css.textContent = `
  #coachbtn { display:flex; align-items:center; justify-content:center; cursor:pointer; position:relative; }
  #coachbtn .cdot { position:absolute; top:2px; right:calc(50% - 16px); width:9px; height:9px; border-radius:50%; background:var(--stop);
                    box-shadow:0 0 0 2px var(--bg); display:none; }
  #coachbtn.due .cdot { display:block; }
  #coachsheet { position:fixed; left:0; right:0; bottom:0; height:82vh; z-index:10; background:var(--bg); border-top:1px solid var(--muted);
                border-radius:18px 18px 0 0; box-shadow:0 -8px 24px rgba(0,0,0,.2); display:none; flex-direction:column; gap:8px;
                padding:14px 16px calc(220px + env(safe-area-inset-bottom)); text-align:left; }
  #coachsheet.open { display:flex; }
  #coachhead { position:relative; flex-shrink:0; }
  #coachsheet h2 { margin:0; font-size:15px; font-weight:600; color:var(--muted); text-align:center; padding:0 74px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  #coachclose, #coachback { position:absolute; top:-8px; border:0; background:transparent; color:var(--fg); font:600 15px/1 -apple-system,sans-serif; padding:8px 10px; cursor:pointer; }
  #coachclose { right:-6px; } #coachback { left:-6px; display:none; }
  #coachsheet:not([data-view="main"]) #coachback { display:block; }
  #coachbody { flex:1; min-height:60px; overflow-y:auto; -webkit-overflow-scrolling:touch; overscroll-behavior:contain; display:flex; flex-direction:column; gap:10px; padding:2px 2px 6px; }
  #coachbody > * { flex-shrink:0; }
  #coachbody .empty { color:var(--muted); text-align:center; margin:auto; padding:16px; line-height:1.4; }
  #coachbody .ccard { border:0; border-radius:14px; background:var(--soft); color:var(--fg); text-align:left; padding:11px 13px; font:15px/1.35 -apple-system,sans-serif; width:100%; box-sizing:border-box; }
  #coachbody button.ccard { cursor:pointer; }
  #coachbody .ccard > b { display:block; font-size:15px; font-weight:650; }
  #coachbody .ccard.due { background:color-mix(in srgb, var(--stop) 11%, var(--soft)); box-shadow:0 0 0 1px color-mix(in srgb, var(--stop) 30%, transparent); }
  #coachbody .csub { color:var(--muted); font-size:13px; margin-top:3px; overflow-wrap:anywhere; }
  #coachbody .chead { color:var(--muted); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin:6px 2px -2px; }
  #coachbody .cword { float:right; font-size:12px; font-weight:700; border-radius:99px; padding:2px 8px; margin-left:8px; background:color-mix(in srgb, var(--muted) 18%, transparent); color:var(--fg); }
  #coachbody .cword.done { background:var(--accent); color:#04120f; }
  #coachbody .cword.prog { background:color-mix(in srgb, var(--accent) 25%, transparent); }
  #coachbody .cbar { height:6px; border-radius:99px; background:color-mix(in srgb, var(--muted) 22%, transparent); margin:8px 0 2px; overflow:hidden; display:flex; }
  #coachbody .cbar i { display:block; height:100%; background:var(--accent); }
  #coachbody .cbar i.p { background:color-mix(in srgb, var(--accent) 45%, transparent); }
  #coachbody .crow { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:9px; }
  #coachbody .cbtn { border:1px solid color-mix(in srgb, var(--muted) 40%, transparent); background:var(--bg); color:var(--fg); border-radius:999px;
                     font:600 14px/1 -apple-system,sans-serif; padding:9px 14px; cursor:pointer; }
  #coachbody .cbtn.go { background:var(--accent); border-color:var(--accent); color:#04120f; }
  #coachbody .cbtn:disabled { opacity:.45; cursor:default; }
  #coachbody .citem { display:flex; gap:9px; align-items:flex-start; padding:7px 0; border-top:1px solid color-mix(in srgb, var(--muted) 18%, transparent); }
  #coachbody .citem:first-of-type { border-top:0; }
  #coachbody .cmark { flex:0 0 auto; font-size:11px; font-weight:700; border-radius:99px; padding:3px 7px; min-width:58px; text-align:center;
                      background:color-mix(in srgb, var(--muted) 18%, transparent); }
  #coachbody .cmark.answered { background:var(--accent); color:#04120f; }
  #coachbody .cmark.parked, #coachbody .cmark.later { background:color-mix(in srgb, var(--accent) 22%, transparent); }
  #coachbody .cmark.open { background:transparent; box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--muted) 50%, transparent); }
  #coachbody .cq { flex:1; min-width:0; overflow-wrap:anywhere; }
  #coachbody .cmsgs { display:flex; flex-direction:column; gap:6px; }
  #coachbody .cmsg { max-width:85%; padding:8px 11px; border-radius:16px; background:var(--soft); white-space:pre-wrap; overflow-wrap:anywhere; font:15px/1.35 -apple-system,sans-serif; }
  #coachbody .cmsg.me { align-self:flex-end; background:var(--accent); color:#04120f; }
  #coachbody .cmsg small { display:block; font-size:11px; opacity:.6; margin-top:3px; }
  #coachbody .ctype { color:var(--muted); font-size:13px; padding:2px 4px; }
  #coachsend { display:flex; gap:8px; align-items:flex-end; }
  #coachsend textarea { flex:1; min-width:0; box-sizing:border-box; border-radius:14px; border:1px solid color-mix(in srgb, var(--muted) 40%, transparent);
                        background:var(--bg); color:var(--fg); font:16px/1.35 -apple-system,sans-serif; padding:9px 11px; resize:none; max-height:140px; }
  #coachnote { min-height:0; font-size:13px; color:var(--muted); display:flex; gap:10px; align-items:center; justify-content:center; flex-wrap:wrap; flex-shrink:0; }
  html.m3 #coachbody .ccard { border-radius:20px; }
  `;
  document.head.appendChild(css);

  let data = null, view = { name: "main", layer: null }, ask = 0, poll = 0;
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const button = (text, cls, fn) => { const b = el("button", "cbtn" + (cls ? " " + cls : ""), text); b.type = "button"; b.addEventListener("click", fn); return b; };
  const who = () => (data && data.agent && data.agent.name) || "Pepper";
  const READ = "hq-coach-read";
  const readAt = () => { try { return parseFloat(localStorage.getItem(READ) || "0") || 0; } catch (e) { return 0; } };
  const unread = () => ((data && data.thread) || []).filter(m => m.from === "agent" && m.at > readAt()).length;
  function say(text) { note.textContent = text || ""; }

  async function send(b) {
    try {
      const r = await fetch("api/coaching", { method: "POST", cache: "no-store", headers: { "x-hq": "coaching", "content-type": "application/json" },
                                              body: JSON.stringify(b) });
      const d = await r.json().catch(() => ({}));
      if (r.ok) { data = d; say(d.said || ""); mark(); return d; }
      say(d.error || "Couldn't do that. Try again.");
    } catch (e) { say("Couldn't reach HQ. Try again."); }
    return null;
  }
  // One layer or one check-in is its own call, with the workflow's agent, straight into it (H225).
  function start(ref) {
    if (free || state !== "idle") return;
    const id = data && data.agent && data.agent.id;
    if (id && AGENTS[id] && id !== agent) { agent = id; mode = AGENTS[id].load; showMode(); }
    window.aboutCoachNext = ref; showCoach(false); call();
  }
  function startBtn(ref, label) {
    const b = button(label || "Start with " + who(), "go", () => start(ref));
    b.disabled = free || state !== "idle";
    return b;
  }
  function heading(text) { body.appendChild(el("div", "chead", text)); }
  function card(cls, parent) { const c = el("div", "ccard" + (cls ? " " + cls : "")); (parent || body).appendChild(c); return c; }

  function drawMain() {
    sheet.dataset.view = "main"; title.textContent = data.named || "Life coaching";
    body.innerHTML = "";
    if (!data.map) {
      histNote(body, "Your map isn't started yet. Go through it with " + who() + ", one layer per session, and it shows up here.");
      const r = el("div", "crow"); r.style.justifyContent = "center"; r.appendChild(startBtn("layer:1", "Start the first session")); body.appendChild(r);
      return;
    }
    const due = data.checkins.filter(c => c.due);
    if (due.length) heading("Time for");
    for (const c of due) {
      const k = card("due"); k.appendChild(el("b", "", c.title)); k.appendChild(el("div", "csub", c.line));
      const r = el("div", "crow"); r.appendChild(startBtn(c.key));
      r.appendChild(button("Done", "", () => send({ done: c.key }).then(d => d && draw())));
      r.appendChild(button("Not now", "", () => send({ later: c.key }).then(d => d && draw())));
      k.appendChild(r);
    }
    const t = el("button", "ccard"); t.type = "button";
    const n = unread(), last = (data.thread || []).slice(-1)[0];
    t.appendChild(el("b", "", "Text " + who() + (n ? " · " + n + " new" : "")));
    t.appendChild(el("div", "csub", last ? (last.from === "me" ? "You: " : "") + last.text.slice(0, 110) : "Talk life coaching any time: the check-ins land here too."));
    t.addEventListener("click", () => go("thread")); body.appendChild(t);
    heading("Your map");
    for (const L of data.layers) {
      const b = el("button", "ccard"); b.type = "button";
      const w = el("span", "cword" + (L.word === "done" ? " done" : L.word === "in progress" ? " prog" : ""), L.word);
      const h = el("b", "", L.n + ". " + L.name.replace(/\s*\(.*?\)\s*/g, " ").trim()); h.prepend(w); b.appendChild(h);
      const c = L.counts || {}, tot = L.total || 1;
      const bar = el("div", "cbar"); const a = el("i"); a.style.width = (100 * (c.answered || 0) / tot) + "%";
      const p = el("i", "p"); p.style.width = (100 * ((c.parked || 0) + (c.later || 0)) / tot) + "%"; bar.append(a, p); b.appendChild(bar);
      b.appendChild(el("div", "csub", (c.answered || 0) + " of " + L.total + " answered" + ((c.parked || 0) + (c.later || 0) ? ", " + ((c.parked || 0) + (c.later || 0)) + " parked or for later" : "") + ((c.open || 0) ? ", " + c.open + " open" : "")));
      b.addEventListener("click", () => go("layer", L.n)); body.appendChild(b);
    }
    heading("Check-ins");
    const rest = data.checkins.filter(c => !c.due);
    if (!data.checkins.some(c => c.kind === "week"))
      { const k = card(); k.appendChild(el("b", "", "The weekly look back")); k.appendChild(el("div", "csub", "Not set yet: its moment comes from your ideal week, in a session.")); }
    for (const c of rest) {
      const k = card(); k.appendChild(el("b", "", c.title));
      k.appendChild(el("div", "csub", [c.when, c.line].filter(Boolean).join(" · ")));
    }
    if (!data.kept) { const k = card(); k.appendChild(el("div", "csub", "HQ starts keeping your check-ins in a moment.")); }
  }
  function drawLayer(n) {
    const L = (data.layers || []).find(x => x.n === n);
    if (!L) return drawMain();
    sheet.dataset.view = "layer"; title.textContent = L.n + ". " + L.name.replace(/\s*\(.*?\)\s*/g, " ").trim();
    body.innerHTML = "";
    const top = card(); top.appendChild(el("b", "", L.word.charAt(0).toUpperCase() + L.word.slice(1)));
    if (L.status) top.appendChild(el("div", "csub", L.status.length > 260 ? L.status.slice(0, 257) + "…" : L.status));
    const r = el("div", "crow"); r.appendChild(startBtn("layer:" + L.n, L.word === "done" ? "Go back over it with " + who() : "Start a session with " + who()));
    top.appendChild(r);
    if (state !== "idle") top.appendChild(el("div", "csub", "You're on a call: just say what you'd like to work on."));
    heading("The checklist");
    const list = card();
    for (const it of L.items) {
      const row = el("div", "citem"); row.appendChild(el("span", "cmark " + it.mark, it.mark));
      const q = el("div", "cq", it.q); if (it.note) q.appendChild(el("div", "csub", it.note)); row.appendChild(q); list.appendChild(row);
    }
    if (!L.items.length) list.appendChild(el("div", "csub", "No questions in this layer."));
  }
  function drawThread() {
    sheet.dataset.view = "thread"; title.textContent = who();
    body.innerHTML = "";
    const msgs = el("div", "cmsgs");
    const th = data.thread || [];
    if (!th.length) msgs.appendChild(el("div", "empty", "Text " + who() + " about life coaching any time. The check-ins land here too, with the dot."));
    for (const m of th) {
      const b = el("div", "cmsg" + (m.from === "me" ? " me" : ""), m.text);
      try { b.appendChild(el("small", "", new Date(m.at * 1000).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" }))); } catch (e) {}
      msgs.appendChild(b);
    }
    if (data.waiting) msgs.appendChild(el("div", "ctype", who() + " is typing…"));
    body.appendChild(msgs);
    const f = el("div"); f.id = "coachsend";
    const ta = el("textarea"); ta.rows = 1; ta.placeholder = "Text " + who(); ta.setAttribute("aria-label", "Text " + who());
    ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = Math.min(140, ta.scrollHeight) + "px"; });
    const go = async () => {
      const text = ta.value.trim(); if (!text) return;
      ta.value = ""; sendB.disabled = true;
      if (await send({ send: text })) { drawThread(); waitReply(); }
      sendB.disabled = false;
    };
    ta.addEventListener("keydown", ev => { if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); go(); } });
    const sendB = button("Send", "go", go);
    f.append(ta, sendB); body.appendChild(f);
    seen();
    requestAnimationFrame(() => { body.scrollTop = body.scrollHeight; });
  }
  function seen() {
    const th = (data && data.thread) || [];
    const at = th.length ? th[th.length - 1].at : 0;
    try { if (at > readAt()) localStorage.setItem(READ, String(at)); } catch (e) {}
    mark();
  }
  function waitReply() {
    clearTimeout(poll);
    let tries = 0;
    const look = async () => {
      if (!coachOpen()) return;
      await load();
      if (data && data.waiting && ++tries < 90) poll = setTimeout(look, 3000);
    };
    poll = setTimeout(look, 2500);
  }
  function draw() {
    if (!data) { histNote(body, "Loading…"); return; }
    if (data.off === "Free") { title.textContent = "Life coaching"; histNote(body, "Free is on: none of your files. Turn it off in Settings to see your coaching."); return; }
    if (!data.on) { title.textContent = "Life coaching"; histNote(body, "Life coaching is off. Turn it on in Settings, under What HQ helps you with."); return; }
    if (view.name === "layer") return drawLayer(view.layer);
    if (view.name === "thread") return drawThread();
    drawMain();
  }
  function go(name, layer) { view = { name, layer: layer || null }; say(""); draw(); if (name !== "thread") body.scrollTop = 0; }
  function back() { go("main"); }
  function mark() { btn.classList.toggle("due", !!(data && data.on && ((data.due || 0) > 0 || unread() > 0))); }

  async function load() {
    const n = ++ask;
    const d = await histGet("api/coaching");
    if (n !== ask) return;
    if (d) { data = d; mark(); }
    if (coachOpen()) {
      const typing = document.activeElement && document.activeElement.closest && document.activeElement.closest("#coachsend");
      if (view.name === "thread" && typing) {  // never redraw under his fingers: only the messages
        const ta = document.querySelector("#coachsend textarea"), keep = ta ? ta.value : "";
        drawThread(); const t2 = document.querySelector("#coachsend textarea"); if (t2) { t2.value = keep; t2.focus(); }
      } else { const at = body.scrollTop; draw(); if (view.name !== "thread") body.scrollTop = at; }
    }
  }
  window.showCoach = function (open, where) {
    if (open === coachOpen()) { if (open) load(); return; }
    if (open) {
      if (chatOpen()) { chatEl.classList.remove("open"); chatBtn.setAttribute("aria-expanded", "false"); showBadge(); }
      if (statOpen()) showStatus(false);
      if (histOpen()) showHistory(false);
      if (notesOpen()) showNotes(false);
      if (calOpen()) showCal(false);
      if (todoOpen()) showTodo(false);
      if (gameOpen()) showGame(false);
      showDirect(false);
      closeWx();
      if (setEl.classList.contains("open")) showSettings(false);
      view = { name: where || "main", layer: null }; say("");
    } else clearTimeout(poll);
    sheet.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", String(open));
    if (open) { draw(); load(); } else ask++;
    showLayout();
  };
  btn.addEventListener("click", () => showCoach(!coachOpen()));
  $("coachclose").addEventListener("click", () => showCoach(false));
  $("coachback").addEventListener("click", back);
  backSwipe(sheet, body, () => sheet.dataset.view !== "main", back);
  sheetPull(sheet, () => showCoach(false));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
  setInterval(() => { if (!document.hidden && !coachOpen()) load(); }, 5 * 60 * 1000);  // the dot keeps up while the app is open
  load();
})();
