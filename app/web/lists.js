// The bucketlist and the wishlist in the app (25 November 2026). His words: "i want to build a new feature called
// bucketlist. this way i can set sort of mini goals that i want to achieve. can be experiences, products or services to
// buy (single or recurring), i want to be able to store links, time goals and costs. also an unlimited amount of
// subitems should be able to be added and the total numbers on the main item should also be visible. also notes
// should be possible." and "i want to improve wishlist. i want just like the bucketlist subitems added as an option and
// add price and link and notes". The data is app/lists.py's (/api/lists). This draws both lists inside the To-do sheet,
// after the call page's own script, whose helpers it uses (histGet, todoView, todoBody, todoTitle, todoEl, todoNote,
// todoDraw, todoGo, todoOpen, TODO_TICK). The page calls in at four places: HQLists.load() when To-do opens,
// HQLists.chips(row) on To-do's first screen, HQLists.draw() and HQLists.back() while one of the lists is open.
"use strict";
(function () {
  if (!document.getElementById("todosheet")) return;
  let data = null, closedOpen = false, armed = "";
  const css = document.createElement("style");
  css.textContent = `
  #todobody .bltot { border-radius:14px; background:var(--soft); padding:10px 13px; font:15px/1.35 -apple-system,sans-serif; }
  #todobody .bltot b { display:block; font-size:12px; color:var(--muted); font-weight:700; margin-bottom:3px; }
  #todobody .bltot .big { font-size:18px; font-weight:700; }
  #todobody .bltot small { display:block; color:var(--muted); font-size:13px; margin-top:2px; }
  #todobody .bladd { display:flex; gap:8px; }
  #todobody .bladd input, #todobody .blf input, #todobody .blf textarea, #todobody .blf select { flex:1; min-width:0; box-sizing:border-box; border-radius:12px;
      border:1px solid color-mix(in srgb, var(--muted) 40%, transparent); background:var(--bg); color:var(--fg); font:15px/1.35 -apple-system,sans-serif; padding:10px 12px; }
  #todobody .bladd button { flex-shrink:0; border:0; border-radius:12px; background:var(--accent); color:#04120f; font:600 15px/1 -apple-system,sans-serif; padding:0 16px; cursor:pointer; min-height:44px; }
  #todobody .blf { display:flex; flex-direction:column; gap:5px; }
  #todobody .blf > label, #todobody .blhead { color:var(--muted); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; margin:4px 2px 0; }
  #todobody .blf > input, #todobody .blf > textarea { width:100%; flex:none; }
  #todobody .blf .two { display:flex; gap:8px; }
  #todobody .blf .two select { flex:0 0 42%; }
  #todobody .blf textarea { min-height:90px; resize:vertical; width:100%; }
  #todobody .blchips { display:flex; flex-wrap:wrap; gap:6px; }
  #todobody .blchips button { min-height:38px; min-width:44px; padding:4px 14px; border-radius:19px; border:1px solid color-mix(in srgb, var(--muted) 45%, transparent);
      background:transparent; color:var(--fg); font:600 14px/1 -apple-system,sans-serif; cursor:pointer; }
  #todobody .blchips button[aria-pressed="true"] { background:var(--accent); border-color:var(--accent); color:#04120f; }
  #todobody .bllink { display:flex; align-items:center; gap:8px; border-radius:12px; background:var(--soft); padding:4px 4px 4px 12px; }
  #todobody .bllink a { flex:1; min-width:0; color:var(--accent); font-size:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  #todobody .bllink button { flex-shrink:0; border:0; background:transparent; color:var(--muted); font:600 18px/1 -apple-system,sans-serif; width:40px; height:40px; cursor:pointer; }
  #todobody .blcrumb { color:var(--muted); font-size:13px; margin:-2px 2px 0; overflow-wrap:anywhere; }
  #todobody .tdrow .ck.on { background:var(--accent); border-color:var(--accent); color:#04120f; }
  #todobody .tdrow.dropped .it { color:var(--muted); text-decoration:line-through; }
  #todobody .blfold { border:0; background:transparent; color:var(--muted); font:600 13px/1 -apple-system,sans-serif; padding:10px 2px; text-align:left; cursor:pointer; }
  #todobody .tdacts .warn { color:var(--stop); }
  #todobody .tdacts .warn.armed { background:var(--stop); color:#fff; }`;
  document.head.appendChild(css);

  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const num = n => Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });
  function money(t) {
    const p = [];
    if (t.once) p.push("€" + num(t.once));
    if (t.month) p.push("€" + num(t.month) + " a month");
    if (t.year) p.push("€" + num(t.year) + " a year");
    return p.join(" + ");
  }
  function meta(it) {
    const t = it.totals, p = [money(t)];
    if (t.hours) p.push(num(t.hours) + " h");
    if (it.by) p.push("by " + it.by);
    if (t.subs) p.push(t.subs_done + " of " + t.subs + " done");
    if (it.score) p.push("score " + it.score);
    if (it.links.length) p.push(it.links.length === 1 ? "1 link" : it.links.length + " links");
    return p.filter(Boolean).join(" · ");
  }
  function listOf(key) { return ((data && data.lists) || []).find(l => l.key === key) || null; }
  function trail(key, path) {  // the items along a path of ids, from the main item down
    const out = []; let items = (listOf(key) || { items: [] }).items;
    for (const id of path) { const it = items.find(x => x.id === id); if (!it) return null; out.push(it); items = it.sub; }
    return out;
  }
  function say(text, undo) {
    todoNote.innerHTML = "";
    if (!text) return;
    todoNote.appendChild(el("span", "", text));
    if (undo) {
      const u = el("button", "", "Undo"); u.type = "button";
      u.addEventListener("click", async () => { u.disabled = true; if (await send({ do: "undo" })) todoDraw(); });
      todoNote.appendChild(u);
    }
  }
  async function send(body) {
    try {
      const r = await fetch("api/lists", { method: "POST", cache: "no-store", headers: { "x-hq": "lists", "content-type": "application/json" }, body: JSON.stringify(body) });
      const d = await r.json().catch(() => ({}));
      if (r.ok) { data = d; say(d.said || "", d.undo); return d; }
      say(d.error || "Couldn't change the list. Try again.");
    } catch (e) { say("Couldn't reach HQ. Try again."); }
    return null;
  }
  async function change(body) { const at = todoBody.scrollTop; if (await send(body)) { todoDraw(); todoBody.scrollTop = at; } }
  function go(key, path) { todoGo({ list: null, item: null, from: "main", lists: { key, path: path || [] } }); }

  function row(it, key, path) {
    const r = el("div", "tdrow" + (it.state === "done" ? " gone" : it.state === "dropped" ? " dropped" : ""));
    const ck = el("button", "ck" + (it.state === "done" ? " on" : "")); ck.type = "button"; ck.innerHTML = TODO_TICK;
    ck.setAttribute("aria-label", (it.state === "done" ? "Open again: " : "Done: ") + it.name);
    ck.addEventListener("click", () => change({ do: it.state === "open" ? "done" : "open", item: it.id }));
    const b = el("button", "it"); b.type = "button"; b.appendChild(el("span", "", it.name));
    const m = meta(it); if (m) b.appendChild(el("small", "", m));
    b.addEventListener("click", () => go(key, path.concat(it.id)));
    r.append(ck, b);
    return r;
  }
  function addBox(placeholder, body) {
    const f = el("form", "bladd"), i = el("input"); i.type = "text"; i.placeholder = placeholder; i.maxLength = 200; i.setAttribute("aria-label", placeholder);
    const b = el("button", "", "Add"); b.type = "submit";
    f.append(i, b);
    f.addEventListener("submit", e => { e.preventDefault(); const v = i.value.trim(); if (v) change(Object.assign({ do: "add", name: v }, body)); });
    return f;
  }
  function rows(items, key, path) {
    const open = items.filter(x => x.state === "open"), closed = items.filter(x => x.state !== "open");
    for (const it of open) todoBody.appendChild(row(it, key, path));
    if (closed.length) {
      const f = el("button", "blfold", (closedOpen ? "▾ " : "▸ ") + "Done or let go · " + closed.length); f.type = "button";
      f.addEventListener("click", () => { closedOpen = !closedOpen; const at = todoBody.scrollTop; todoDraw(); todoBody.scrollTop = at; });
      todoBody.appendChild(f);
      if (closedOpen) for (const it of closed) todoBody.appendChild(row(it, key, path));
    }
  }
  function totalsCard(title, t, extra) {
    const c = el("div", "bltot"); c.appendChild(el("b", "", title));
    c.appendChild(el("div", "big", money(t) || "No prices yet"));
    const p = [];
    if (t.left && t.left !== t.once) p.push("€" + num(t.left) + " of the one-off still to spend");
    if (t.hours) p.push(num(t.hours) + " hours");
    if (t.subs) p.push(t.subs_done + " of " + t.subs + " done");
    if (extra) p.push(extra);
    if (p.length) c.appendChild(el("small", "", p.join(" · ")));
    return c;
  }

  function drawList(l) {
    todoTitle.textContent = l.name;
    todoBody.appendChild(totalsCard("Everything on it", l.totals));
    todoBody.appendChild(addBox(l.key === "wish" ? "Add a wish" : "Add to your bucketlist", { list: l.key }));
    const old = l.key === "wish" && !(data.moved && data.moved.wish) ? ((typeof todoLists === "function" && todoLists("wish")[0]) || null) : null;
    if (old && old.items.length) {
      const c = el("button", "card"); c.type = "button";
      c.appendChild(el("b", "", "Your wishlist so far · " + old.items.length));
      c.appendChild(el("div", "few", "Bring them over, so each can have a price, links, notes and sub-items."));
      c.addEventListener("click", async () => { c.disabled = true; if (await send({ do: "import-wish" })) { if (typeof loadTodo === "function") loadTodo(); todoDraw(); } });
      todoBody.appendChild(c);
    }
    if (!l.items.length && !(old && old.items.length)) todoBody.appendChild(el("div", "empty", l.key === "wish" ? "Nothing on your wishlist yet." : "Nothing on your bucketlist yet. Things to live, get or do: add the first one above."));
    rows(l.items, l.key, []);
  }
  function field(label, node) { const f = el("div", "blf"); f.appendChild(el("label", "", label)); f.appendChild(node); return f; }
  function input(it, name, type, placeholder) {
    const i = el("input"); i.type = type || "text"; i.value = it[name] == null ? "" : String(it[name]); if (placeholder) i.placeholder = placeholder;
    if (type === "number") { i.min = "0"; i.step = "any"; i.inputMode = "decimal"; }
    i.addEventListener("change", () => { if (i.value.trim() !== (it[name] == null ? "" : String(it[name]))) change({ do: "set", item: it.id, field: name, value: i.value.trim() }); });
    return i;
  }
  function chips(it, name, options) {
    const c = el("div", "blchips");
    for (const [v, w] of options) {
      const b = el("button", "", w); b.type = "button"; b.setAttribute("aria-pressed", String((it[name] || "") === v || it[name] === v));
      b.addEventListener("click", () => change({ do: "set", item: it.id, field: name, value: (it[name] || "") === v || it[name] === v ? "" : String(v) }));
      c.appendChild(b);
    }
    return c;
  }
  function drawItem(l, path, chain) {
    const it = chain[chain.length - 1];
    todoTitle.textContent = l.name;
    if (chain.length > 1) todoBody.appendChild(el("div", "blcrumb", chain.slice(0, -1).map(x => x.name).join(" › ")));
    todoBody.appendChild(field("Name", input(it, "name")));
    if (it.sub.length) todoBody.appendChild(totalsCard("With everything under it", it.totals));
    todoBody.appendChild(field("Kind", chips(it, "kind", [["experience", "Experience"], ["product", "Product"], ["service", "Service"]])));
    const two = el("div", "two"), sel = el("select");
    for (const [v, w] of [["once", "once"], ["month", "a month"], ["year", "a year"]]) { const o = el("option", "", w); o.value = v; o.selected = (it.every || "once") === v; sel.appendChild(o); }
    sel.setAttribute("aria-label", "How often");
    sel.addEventListener("change", () => change({ do: "set", item: it.id, field: "every", value: sel.value }));
    two.append(input(it, "price", "number", "0"), sel);
    todoBody.appendChild(field("Price (€)", two));
    todoBody.appendChild(field("Time goal", input(it, "by", "text", "2027, 2027-06 or 2027-06-14")));
    todoBody.appendChild(field("Time it takes (hours)", input(it, "hours", "number", "0")));
    todoBody.appendChild(field("How much it brings your vision closer", chips(it, "score", [[1, "1"], [2, "2"], [3, "3"], [4, "4"], [5, "5"]])));
    if (it.score) todoBody.appendChild(field("Why that score", input(it, "why", "text", "In a few words")));
    todoBody.appendChild(el("div", "blhead", "Links"));
    it.links.forEach((u, n) => {
      const r = el("div", "bllink"), a = el("a", "", u.replace(/^https?:\/\/(www\.)?/, "")); a.href = u; a.target = "_blank"; a.rel = "noopener noreferrer";
      const x = el("button", "", "×"); x.type = "button"; x.setAttribute("aria-label", "Take this link off");
      x.addEventListener("click", () => change({ do: "unlink", item: it.id, url: String(n + 1) }));
      r.append(a, x); todoBody.appendChild(r);
    });
    const lf = el("form", "bladd"), li = el("input"); li.type = "text"; li.autocapitalize = "off"; li.placeholder = "Paste a link"; li.setAttribute("aria-label", "Paste a link"); li.inputMode = "url";
    const lb = el("button", "", "Add"); lb.type = "submit"; lf.append(li, lb);
    lf.addEventListener("submit", e => { e.preventDefault(); const v = li.value.trim(); if (v) change({ do: "link", item: it.id, url: v }); });
    todoBody.appendChild(lf);
    const ta = el("textarea"); ta.value = it.notes || ""; ta.placeholder = "Anything you want to remember about it";
    ta.addEventListener("change", () => { if (ta.value.trim() !== (it.notes || "")) change({ do: "set", item: it.id, field: "notes", value: ta.value.trim() }); });
    todoBody.appendChild(field("Notes", ta));
    todoBody.appendChild(el("div", "blhead", "Sub-items" + (it.totals.subs ? " · " + it.totals.subs_done + " of " + it.totals.subs + " done" : "")));
    rows(it.sub, l.key, path);
    todoBody.appendChild(addBox("Add a sub-item", { under: it.id }));
    const acts = el("div", "tdacts");
    const act = (text, body, cls) => { const b = el("button", cls || "", text); b.type = "button"; b.addEventListener("click", () => change(body)); acts.appendChild(b); return b; };
    if (it.state === "open") act("Done", { do: "done", item: it.id }, "ok"); else act("Open again", { do: "open", item: it.id }, "ok");
    if (it.state !== "dropped") act("Let go", { do: "drop", item: it.id });
    act("Move up", { do: "move", item: it.id, to: "up" }); act("Move down", { do: "move", item: it.id, to: "down" });
    const del = el("button", "warn" + (armed === it.id ? " armed" : ""), armed === it.id ? "Tap again to delete" : "Delete"); del.type = "button";
    del.addEventListener("click", async () => {
      if (armed !== it.id) { armed = it.id; todoDraw(); setTimeout(() => { if (armed === it.id) { armed = ""; if (todoView.lists) todoDraw(); } }, 5000); return; }
      armed = "";
      if (await send({ do: "delete", item: it.id })) go(l.key, path.slice(0, -1));
    });
    acts.appendChild(del);
    todoBody.appendChild(acts);
  }

  window.HQLists = {
    async load() { const d = await histGet("api/lists"); if (d && Array.isArray(d.lists)) { data = d; if (todoOpen()) todoDraw(); } },
    chips(rowEl) {  // the two lists on To-do's first screen
      if (!data || data.off || data.error) return;
      for (const l of data.lists) {
        const b = el("button", "", l.name); b.type = "button"; b.dataset.hqList = l.key;
        b.appendChild(el("span", "", String(l.open))); b.setAttribute("aria-label", l.name + ": " + l.open);
        b.addEventListener("click", () => go(l.key, []));
        rowEl.appendChild(b);
      }
    },
    ready() { return !!(data && !data.off && !data.error); },
    draw() {
      const v = todoView.lists, l = v && listOf(v.key);
      todoBody.innerHTML = "";
      if (!l) { todoView = { list: null, item: null, from: "main" }; return todoDraw(); }
      if (!v.path.length) return drawList(l);
      const chain = trail(v.key, v.path);
      if (!chain) { todoView = { list: null, item: null, from: "main", lists: { key: v.key, path: [] } }; return todoDraw(); }
      drawItem(l, v.path, chain);
    },
    back() {
      const v = todoView.lists;
      if (v && v.path.length) go(v.key, v.path.slice(0, -1)); else todoGo({ list: null, item: null, from: "main" });
    },
  };
})();
