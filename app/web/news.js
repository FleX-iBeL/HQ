// H236 (22 October 2026): your own news inside HQ. His words on the call: "it only gives you the news from specific
// sources about specific topics", "Maybe it's more of a session, just like life coaching ... way smaller", and "we can
// just read about it in the app so we don't have to go off-platform, right? I want to stay native in this app so we
// don't get any distractions. We do get sort of like our digital newspaper".
//
// The data is app/news.py's (/api/news): the items the routine on the main kept from their sources, newest first, and
// their setup (topics, what's left out, sources). This draws it in #newssheet, after the call page's own script, whose
// helpers it uses (histGet, histNote, sheetPull, backSwipe, showLayout, call and the other sheets' show functions).
// A tap reads an item inside HQ (/api/news?id=, the article's own text); the source's link only at the bottom. The
// setup is a short call of its own (about_news), with whoever they call. What's been seen is kept on this device: the
// dot on the button means new items since.
"use strict";
(function () {
  const $ = id => document.getElementById(id);
  const sheet = $("newssheet"), btn = $("newsbtn"), body = $("newsbody"), title = $("newstitle"), note = $("newsnote");
  if (!sheet || !btn) return;
  const css = document.createElement("style");
  css.textContent = `
  #newsbtn { display:flex; align-items:center; justify-content:center; cursor:pointer; position:relative; }
  #newsbtn .ndot { position:absolute; top:2px; right:calc(50% - 16px); width:9px; height:9px; border-radius:50%; background:var(--accent);
                   box-shadow:0 0 0 2px var(--bg); display:none; }
  #newsbtn.fresh .ndot { display:block; }
  #newssheet { position:fixed; left:0; right:0; bottom:0; height:82vh; z-index:10; background:var(--bg); border-top:1px solid var(--muted);
               border-radius:18px 18px 0 0; box-shadow:0 -8px 24px rgba(0,0,0,.2); display:none; flex-direction:column; gap:8px; text-align:left; }
  #newssheet.open { display:flex; }
  #newshead { position:relative; flex-shrink:0; }
  #newssheet h2 { margin:0; font-size:15px; font-weight:600; color:var(--muted); text-align:center; padding:0 74px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  #newsclose, #newsback { position:absolute; top:-8px; border:0; background:transparent; color:var(--fg); font:600 15px/1 -apple-system,sans-serif; padding:8px 10px; cursor:pointer; }
  #newsclose { right:-6px; } #newsback { left:-6px; display:none; }
  #newssheet:not([data-view="main"]) #newsback { display:block; }
  #newsbody { flex:1; min-height:60px; overflow-y:auto; -webkit-overflow-scrolling:touch; overscroll-behavior:contain; display:flex; flex-direction:column; gap:8px; padding:2px 2px 6px; }
  #newsbody > * { flex-shrink:0; }
  #newsbody .ncard { border:0; border-radius:14px; background:var(--soft); color:var(--fg); text-align:left; padding:11px 13px; font:15px/1.35 -apple-system,sans-serif; width:100%; box-sizing:border-box; }
  #newsbody button.ncard { cursor:pointer; }
  #newsbody .ncard > b { display:block; font-size:15px; font-weight:650; overflow-wrap:anywhere; }
  #newsbody .ncard.new > b::before { content:""; display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--accent); margin:0 7px 2px 0; }
  #newsbody .nsrc { color:var(--muted); font-size:12.5px; margin-top:4px; overflow-wrap:anywhere; }
  #newsbody .nsum { color:var(--fg); opacity:.82; font-size:14px; margin-top:4px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; overflow-wrap:anywhere; }
  #newsbody .nhead { color:var(--muted); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin:6px 2px -2px; }
  #newsbody .nchips { display:flex; gap:6px; flex-wrap:wrap; }
  #newsbody .nchip { border:1px solid color-mix(in srgb, var(--muted) 40%, transparent); background:var(--bg); color:var(--fg); border-radius:999px;
                     font:600 13px/1 -apple-system,sans-serif; padding:7px 12px; cursor:pointer; }
  #newsbody .nchip[aria-pressed="true"] { background:var(--accent); border-color:var(--accent); color:#04120f; }
  #newsbody .nrow { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:9px; }
  #newsbody .nbtn { border:1px solid color-mix(in srgb, var(--muted) 40%, transparent); background:var(--bg); color:var(--fg); border-radius:999px;
                    font:600 14px/1 -apple-system,sans-serif; padding:9px 14px; cursor:pointer; }
  #newsbody .nbtn.go { background:var(--accent); border-color:var(--accent); color:#04120f; }
  #newsbody .nbtn:disabled { opacity:.45; cursor:default; }
  #newsbody .nart h3 { margin:2px 0 6px; font:700 19px/1.3 -apple-system,sans-serif; overflow-wrap:anywhere; }
  #newsbody .nart p { margin:0 0 12px; font:16px/1.5 -apple-system,sans-serif; overflow-wrap:anywhere; }
  #newsbody .nart a { color:var(--muted); font-size:13px; }
  #newsbody .nline { padding:6px 0; border-top:1px solid color-mix(in srgb, var(--muted) 18%, transparent); overflow-wrap:anywhere; }
  #newsbody .nline:first-of-type { border-top:0; }
  #newsnote { min-height:0; font-size:13px; color:var(--muted); display:flex; gap:10px; align-items:center; justify-content:center; flex-wrap:wrap; flex-shrink:0; }
  html.m3 #newsbody .ncard { border-radius:20px; }
  `;
  document.head.appendChild(css);

  let data = null, view = { name: "main", id: null }, topic = "", ask = 0;
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const button = (text, cls, fn) => { const b = el("button", "nbtn" + (cls ? " " + cls : ""), text); b.type = "button"; b.addEventListener("click", fn); return b; };
  const SEEN = "hq-news-seen";
  const seenAt = () => { try { return parseFloat(localStorage.getItem(SEEN) || "0") || 0; } catch (e) { return 0; } };
  let openedAt = seenAt();  // what was new when the sheet opened stays marked while it's open
  const fresh = () => ((data && data.items) || []).filter(i => i.got > seenAt()).length;
  function say(text) { note.textContent = text || ""; }
  function ago(t) {
    const s = Math.max(0, Date.now() / 1000 - t);
    if (s < 3600) return Math.max(1, Math.round(s / 60)) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " h ago";
    try { return new Date(t * 1000).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }); } catch (e) { return ""; }
  }

  // The setup is its own short call, with whoever they call, straight into it (about_news).
  function start() {
    if (free || state !== "idle") return;
    window.aboutNewsNext = "setup"; showNews(false); call();
  }
  function startBtn(label) {
    const b = button(label, "go", start);
    b.disabled = free || state !== "idle";
    return b;
  }
  function heading(text) { body.appendChild(el("div", "nhead", text)); }

  function drawMain() {
    sheet.dataset.view = "main"; title.textContent = "News";
    body.innerHTML = "";
    if (!data.set) {
      histNote(body, "Your own newspaper: only the topics and sources you pick, nothing else. Set it up in a short call: what you want to hear about, what not, and where from.");
      const r = el("div", "nrow"); r.style.justifyContent = "center"; r.appendChild(startBtn("Set up your news")); body.appendChild(r);
      if (state !== "idle") body.appendChild(el("div", "nsrc", "You're on a call: just say what you'd like in your news."));
      return;
    }
    const named = [...(data.setup.topics || []).map(t => t.name), ...(data.setup.sources || []).map(x => x.topic).filter(Boolean)];
    const topics = [...new Set(named)].filter(n => (data.items || []).some(i => (i.topics || []).includes(n)));
    if (topics.length > 1) {
      const c = el("div", "nchips");
      for (const t of ["", ...topics]) {
        const b = el("button", "nchip", t || "All"); b.type = "button"; b.setAttribute("aria-pressed", String(t === topic));
        b.addEventListener("click", () => { topic = t; drawMain(); }); c.appendChild(b);
      }
      body.appendChild(c);
    }
    const items = (data.items || []).filter(i => !topic || (i.topics || []).includes(topic));
    if (!items.length) histNote(body, data.looked ? "Nothing in your news right now. Your sources are read about every hour." : "Your sources are read in a moment, and then about every hour.");
    for (const it of items.slice(0, 80)) {
      const b = el("button", "ncard" + (it.got > openedAt ? " new" : "")); b.type = "button";
      b.appendChild(el("b", "", it.title));
      if (it.summary) b.appendChild(el("div", "nsum", it.summary));
      b.appendChild(el("div", "nsrc", [it.source, ago(it.at), (it.topics || []).join(", ")].filter(Boolean).join(" · ")));
      b.addEventListener("click", () => go("item", it.id)); body.appendChild(b);
    }
    const s = el("button", "ncard"); s.type = "button";
    s.appendChild(el("b", "", "What's in your news"));
    s.appendChild(el("div", "nsrc", (data.setup.topics || []).length + " topics · " + (data.setup.sources || []).length + " sources"
                                     + (data.looked ? " · read " + ago(data.looked) : "")));
    s.addEventListener("click", () => go("setup")); body.appendChild(s);
  }
  async function drawItem(id) {
    const it = (data.items || []).find(i => i.id === id);
    if (!it) return drawMain();
    sheet.dataset.view = "item"; title.textContent = it.source;
    body.innerHTML = "";
    const a = el("div", "nart");
    a.appendChild(el("h3", "", it.title));
    a.appendChild(el("div", "nsrc", [it.source, ago(it.at)].filter(Boolean).join(" · ")));
    const txt = el("div"); txt.style.marginTop = "12px";
    if (it.summary) txt.appendChild(el("p", "", it.summary));
    const wait = el("div", "nsrc", "Getting the whole article…"); txt.appendChild(wait);
    a.appendChild(txt); body.appendChild(a);
    const link = el("a", "", "Read it at " + it.source); link.href = it.link; link.target = "_blank"; link.rel = "noopener";
    const foot = el("div", "nsrc"); foot.style.margin = "4px 0 10px"; foot.appendChild(link);
    const full = await histGet("api/news?id=" + encodeURIComponent(id));
    if (!(newsOpen() && view.name === "item" && view.id === id)) return;
    wait.remove();
    const paras = ((full && full.text) || "").split(/\n\n+/).filter(Boolean);
    if (paras.length) { txt.innerHTML = ""; for (const p of paras) txt.appendChild(el("p", "", p)); }
    else txt.appendChild(el("div", "nsrc", "This source doesn't share its whole article; this is what it gives."));
    a.appendChild(foot);
  }
  function drawSetup() {
    sheet.dataset.view = "setup"; title.textContent = "What's in your news";
    body.innerHTML = "";
    const s = data.setup || {};
    const top = el("div", "ncard");
    top.appendChild(el("b", "", "Change it in a short call"));
    top.appendChild(el("div", "nsrc", "Add or drop a topic, leave something out, or pick other sources."));
    const r = el("div", "nrow"); r.appendChild(startBtn("Change your news"));
    r.appendChild(button("Read them now", "", async (ev) => { ev.target.disabled = true; say("Reading your sources…"); await send({ fetch: true }); ev.target.disabled = false; }));
    top.appendChild(r); body.appendChild(top);
    heading("Topics");
    const t = el("div", "ncard");
    for (const x of s.topics || []) { const l = el("div", "nline"); l.appendChild(el("b", "", x.name)); l.appendChild(el("div", "nsrc", "Found by: " + (x.words || []).join(", "))); t.appendChild(l); }
    if (!(s.topics || []).length) t.appendChild(el("div", "nsrc", "No topics yet: only sources you take whole."));
    body.appendChild(t);
    heading("Left out");
    const o = el("div", "ncard", (s.leave_out || []).join(", ") || "Nothing yet.");
    const dr = data.dropped || {}, n = Object.values(dr).reduce((a, b) => a + b, 0);
    if (n) o.appendChild(el("div", "nsrc", n + " items left out at the last read."));
    body.appendChild(o);
    heading("Sources");
    const so = el("div", "ncard");
    for (const x of s.sources || []) {
      const st = (data.sources || {})[x.name] || null, l = el("div", "nline");
      l.appendChild(el("b", "", x.name));
      l.appendChild(el("div", "nsrc", (x.all ? "All of it" : "Only what's about your topics") + (x.topic ? " · " + x.topic : "")
                                      + (st ? (st.ok ? " · " + st.kept + " in your news" : " · didn't answer at the last read") : "")));
      so.appendChild(l);
    }
    body.appendChild(so);
  }
  async function send(b) {
    try {
      const r = await fetch("api/news", { method: "POST", cache: "no-store", headers: { "x-hq": "news", "content-type": "application/json" }, body: JSON.stringify(b) });
      const d = await r.json().catch(() => ({}));
      if (r.ok) { data = d; say(d.said || ""); mark(); draw(); return d; }
      say(d.error || "Couldn't do that. Try again.");
    } catch (e) { say("Couldn't reach HQ. Try again."); }
    return null;
  }
  function draw() {
    if (!data) { histNote(body, "Loading…"); return; }
    if (data.off === "Free") { title.textContent = "News"; histNote(body, "Free is on: none of your files. Turn it off in Settings to see your news."); return; }
    if (!data.on) { title.textContent = "News"; histNote(body, "News is off. Turn it on in Settings, under What HQ helps you with."); return; }
    if (view.name === "item") return drawItem(view.id);
    if (view.name === "setup") return drawSetup();
    drawMain();
  }
  function go(name, id) { view = { name, id: id || null }; say(""); draw(); body.scrollTop = 0; }
  function back() { go("main"); }
  function seen() {
    const at = Math.max(0, ...((data && data.items) || []).map(i => i.got || 0));
    try { if (at > seenAt()) localStorage.setItem(SEEN, String(at)); } catch (e) {}
    mark();
  }
  function mark() { btn.classList.toggle("fresh", !!(data && data.on && data.set && fresh() > 0)); }

  async function load() {
    const n = ++ask;
    const d = await histGet("api/news");
    if (n !== ask) return;
    if (d) { data = d; mark(); }
    if (newsOpen() && view.name !== "item") { const at = body.scrollTop; draw(); body.scrollTop = at; }
    if (newsOpen()) seen();
  }
  window.showNews = function (open) {
    if (open === newsOpen()) { if (open) load(); return; }
    if (open) {
      if (chatOpen()) { chatEl.classList.remove("open"); chatBtn.setAttribute("aria-expanded", "false"); showBadge(); }
      if (statOpen()) showStatus(false);
      if (histOpen()) showHistory(false);
      if (notesOpen()) showNotes(false);
      if (calOpen()) showCal(false);
      if (todoOpen()) showTodo(false);
      if (gameOpen()) showGame(false);
      if (coachOpen()) showCoach(false);
      showDirect(false);
      closeWx();
      if (setEl.classList.contains("open")) showSettings(false);
      view = { name: "main", id: null }; topic = ""; say(""); openedAt = seenAt();
    }
    sheet.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", String(open));
    if (open) { draw(); load(); } else ask++;
    showLayout();
  };
  btn.addEventListener("click", () => showNews(!newsOpen()));
  $("newsclose").addEventListener("click", () => showNews(false));
  $("newsback").addEventListener("click", back);
  backSwipe(sheet, body, () => sheet.dataset.view !== "main", back);
  sheetPull(sheet, () => showNews(false));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
  setInterval(() => { if (!document.hidden && !newsOpen()) load(); }, 10 * 60 * 1000);  // the dot keeps up while the app is open
  load();
})();
