// H59: the version, a new one, and the changelog, on the status page and the call page (one file for both;
// both servers serve it at /update-ui.js and answer the same api/update... addresses).
//
// 11 October 2026, typed on the calls of 12:42 and 13:14, as asked: "is there some way we can build in
// that they see when they open the HQ that there is a new version, with a button to update?", "and also a
// message that if they are up to date that they are running the latest version, and also that if they click on
// update, a warning message that if it's not macos, that explained from above and that claude will get
// instructions to patch it up locally again" and "maybe we can put a mini text in more gray with version number,
// and if you click on it you can see the changelog what we've added/changed over the versions".
//
//   HQUpdate.mount({ line, banner, busy })   line: where the small grey version goes; banner: where the
//                                            "a new version" bar goes; busy(): true while on a call (the bar
//                                            hides then: an installed update ends a call, H187)
//   window.hqUpdate.open()                   the changelog
//   window.hqUpdate.ask()                    Update (on another computer than a Mac: the warning first)
//   window.hqUpdate.render()                 draw again (the call page calls it when a call starts or ends)
//   H235: after an update, when something they added themselves might clash with it (st.clash), the bar says so in
//   plain words with Talk it through (a text to their agent; opt.openTexts, else the texts button) and Send to the
//   team (a roadmap row and a job), and × for it's fine.
// [Claude's choices: a look every minute, every 3 seconds while updating; the bar can be put away until the
// next version; a finished update is shown for half an hour.]
(() => {
  const CSS = `
  .hqu { --u-ink: #1b1f24; --u-soft: #6b7785; --u-card: #fff; --u-rule: #d5d9df; --u-blue: #0b5fbf; --u-red: #b42318; --u-tint: #eef4fc;
    font: 14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-align: left; }
  @media (prefers-color-scheme: dark) {
    .hqu { --u-ink: #e8eaed; --u-soft: #8c97a8; --u-card: #1f2227; --u-rule: #3a3f47; --u-blue: #6aa9f0; --u-red: #f0766a; --u-tint: #1d2a3a; }
  }
  .hqu-ver { border: 0; background: transparent; color: var(--u-soft); opacity: .8; font: 12px/1.3 -apple-system, BlinkMacSystemFont, sans-serif;
    padding: 4px 6px; cursor: pointer; letter-spacing: .2px; }
  .hqu-ver:hover { opacity: 1; text-decoration: underline; }
  .hqu-bar { display: none; align-items: center; gap: 10px; flex-wrap: wrap; background: var(--u-tint); color: var(--u-ink);
    border: 1px solid var(--u-rule); border-radius: 12px; padding: 9px 12px; max-width: 560px; width: 100%; margin: 0 auto; }
  .hqu-bar.show { display: flex; }
  .hqu-bar .t { flex: 1 1 220px; min-width: 0; }
  .hqu-bar .t b { font-weight: 650; }
  .hqu-bar .t span { display: block; color: var(--u-soft); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hqu button.b { font: 600 14px/1 -apple-system, sans-serif; border-radius: 999px; padding: 8px 14px; cursor: pointer; border: 1px solid var(--u-rule);
    background: transparent; color: var(--u-ink); }
  .hqu button.b.go { background: var(--u-blue); border-color: var(--u-blue); color: #fff; }
  .hqu button.b[disabled] { opacity: .5; cursor: default; }
  .hqu button.x { border: 0; background: transparent; color: var(--u-soft); font-size: 18px; cursor: pointer; padding: 2px 6px; }
  .hqu-shade { position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 60; display: none; }
  .hqu-shade.open { display: block; }
  .hqu-sheet { position: fixed; z-index: 61; inset: 0; margin: auto; height: -webkit-fit-content; height: fit-content; width: min(560px, calc(100vw - 24px));
    max-height: calc(100vh - 48px); max-height: calc(100dvh - 48px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); overflow: auto; overscroll-behavior: contain; background: var(--u-card); color: var(--u-ink); border-radius: 16px;
    box-shadow: 0 12px 40px rgba(0,0,0,.35); padding: 18px 18px 14px; display: none; }
  .hqu-sheet.open { display: block; }
  .hqu-sheet h2 { margin: 0 0 4px; font-size: 18px; }
  .hqu-sheet .now { color: var(--u-soft); margin: 0 0 12px; }
  .hqu-sheet .row { display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px; flex-wrap: wrap; }
  .hqu-sheet h3 { font-size: 15px; margin: 16px 0 2px; }
  .hqu-sheet h3 small { font-weight: 500; color: var(--u-soft); margin-left: 6px; }
  .hqu-sheet h4 { font-size: 13px; margin: 8px 0 2px; color: var(--u-soft); font-weight: 600; text-transform: uppercase; letter-spacing: .4px; }
  .hqu-sheet ul { margin: 0; padding-left: 20px; }
  .hqu-sheet li { margin: 2px 0; }
  .hqu-sheet .warn { border-left: 3px solid var(--u-red); padding: 2px 0 2px 10px; }
  .hqu-sheet p { margin: 6px 0; }
  `;
  const $ = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const when = (t) => (t ? new Date(t * 1000).toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' }) : '');
  let opt = {}, st = null, timer = null, ver, bar, shade, sheet, mode = '';

  async function api(path, post) {
    const r = await fetch(path, post ? { method: 'POST', headers: { 'x-hq': 'update' } } : { cache: 'no-store' });
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }
  const running = () => st && st.run && ['waiting', 'updating'].includes(st.run.state);
  const recent = () => st && st.run && ['done', 'failed'].includes(st.run.state) && Date.now() / 1000 - (st.run.at || 0) < 1800;

  function verText() {
    if (!st || !st.version) return 'HQ';
    const v = 'v' + st.version;
    if (running()) return `${v} · updating…`;
    if (st.available) return `${v} · v${st.latest} is out`;
    if (st.latest && !st.offline) return `${v} · the latest version`;
    return v;
  }

  function render() {
    if (!ver) return;
    ver.textContent = verText();
    ver.title = 'What changed in each version';
    const away = (() => { try { return localStorage.getItem('hq-update-away') === st?.latest; } catch { return false; } })();
    const busy = opt.busy && opt.busy();
    bar.replaceChildren();
    let show = false;
    if (st && running()) {
      show = true;
      const t = $('div', 't');
      t.append($('b', '', `Updating to v${st.run.to || st.latest}`), $('span', '', [st.run.step, st.run.message].filter(Boolean).join(' · ')));
      bar.append(t);
    } else if (said && !busy) {
      show = true;
      const t = $('div', 't');
      t.append($('b', '', said));
      bar.append(t);
    } else if (st && st.clash && st.clash.state === 'new' && !busy) {
      // H235: after an update, something they added themselves might not work with it. In his words: "in nontechnical
      // terms it should give them a message that there might be possible conflicts. They could click on a button to
      // either have a chat or send it directly to the team to fix and make sure their HQ runs properly".
      show = true;
      const c = st.clash, t = $('div', 't');
      const names = c.items.map((x) => x.name);
      t.append($('b', '', 'Something you added might not fit this update'),
        $('span', '', `${names.join(', ')}: ${c.items[0].why[0]}${c.items.length > 1 || c.items[0].why.length > 1 ? ' (and more)' : ''}`));
      t.lastChild.style.whiteSpace = 'normal';
      t.lastChild.title = c.words || '';
      const chat = $('button', 'b', 'Talk it through');
      chat.id = 'hqu-clash-chat';
      chat.onclick = () => settle('chat', chat);
      const team = $('button', 'b go', 'Send to the team');
      team.id = 'hqu-clash-team';
      team.onclick = () => settle('team', team);
      const x = $('button', 'x', '×');
      x.title = 'It’s fine, leave it';
      x.id = 'hqu-clash-ok';
      x.onclick = () => settle('ok', x);
      bar.append(t, chat, team, x);
    } else if (st && recent() && !busy) {
      show = true;
      const t = $('div', 't');
      t.append($('b', '', st.run.state === 'done' ? 'Update done' : 'The update didn’t go through'), $('span', '', st.run.message || ''));
      t.lastChild.style.whiteSpace = 'normal';
      const again = $('button', 'b go', st.run.state === 'done' ? 'Reload' : 'Details');
      again.onclick = () => (st.run.state === 'done' ? location.reload() : open());
      bar.append(t, again);
    } else if (st && st.available && !away && !busy) {
      show = true;
      const t = $('div', 't');
      const items = (st.new || []).flatMap((s) => s.groups.flatMap((g) => g.items));
      t.append($('b', '', `HQ v${st.latest} is out`), $('span', '', items.slice(0, 2).join(' · ') || 'A new version'));
      const more = $('button', 'b', 'What’s new');
      more.onclick = open;
      const go = $('button', 'b go', 'Update');
      go.onclick = ask;
      const x = $('button', 'x', '×');
      x.title = 'Not now (until the next version)';
      x.onclick = () => { try { localStorage.setItem('hq-update-away', st.latest); } catch {} render(); };
      bar.append(t, more, go, x);
    }
    bar.classList.toggle('show', show);
    if (sheet.classList.contains('open') && mode === 'log') fillLog();
  }

  // H235: the clash buttons. What was done shows in the bar for a few seconds; Talk it through opens the texts.
  let said = '', saidTimer = null;
  async function settle(how, btn) {
    btn.disabled = true;
    let out = null;
    try { out = await api('api/update/clash-' + how, true); } catch {}
    if (out && out.version) st = out;
    said = (out && out.said) || 'That didn’t go through just now; try again in a minute.';
    clearTimeout(saidTimer);
    saidTimer = setTimeout(() => { said = ''; render(); }, 8000);
    render();
    if (out && out.open === 'texts') (opt.openTexts || (() => { const a = document.getElementById('directbtn'); if (a) a.click(); else location.href = 'direct'; }))();
  }

  async function poll() {
    try { st = await api('api/update'); } catch { /* the server may be restarting during an update */ }
    render();
    clearTimeout(timer);
    timer = setTimeout(poll, running() ? 3000 : 60000);
  }

  function close() { sheet.classList.remove('open'); shade.classList.remove('open'); mode = ''; }
  function openSheet(m) { mode = m; sheet.classList.add('open'); shade.classList.add('open'); }

  let log = null;
  async function fillLog() {
    sheet.replaceChildren();
    sheet.append($('h2', '', st && st.version ? `HQ v${st.version}` : 'HQ'));
    let now = '';
    if (!st) now = 'Looking…';
    else if (running()) now = `Updating to v${st.run.to || st.latest}: ${st.run.step || ''} ${st.run.message || ''}`;
    else if (st.available) now = `A newer version is out: v${st.latest}.`;
    else if (st.latest && !st.offline) now = `You’re running the latest version, v${st.version}. Last checked ${when(st.checked)}.`;
    else if (st.offline) now = `Couldn’t look for a newer version just now (offline?).${st.checked ? ' Last tried ' + when(st.checked) + '.' : ''}`;
    else now = 'Not checked for a newer version yet.';
    if (st && st.ahead) now += ` This copy has ${st.ahead} change${st.ahead === 1 ? '' : 's'} since v${st.version} that aren’t in a version yet.`;
    sheet.append($('p', 'now', now));
    const row = $('div', 'row');
    if (st && st.available && !running()) {
      const go = $('button', 'b go', `Update to v${st.latest}`);
      go.onclick = ask;
      row.append(go);
    }
    if (st && !running()) {
      const chk = $('button', 'b', 'Check now');
      chk.onclick = async () => { chk.disabled = true; chk.textContent = 'Checking…'; try { st = await api('api/update/check', true); } catch {} render(); fillLog(); };
      row.append(chk);
    }
    const cl = $('button', 'b', 'Close');
    cl.onclick = close;
    row.append(cl);
    sheet.append(row);
    if (!log) { try { log = await api('api/changelog'); } catch { log = { versions: [] }; } }
    const list = [...(st && st.available ? (st.new || []).map((s) => ({ ...s, coming: false, newer: true })) : []), ...(log.versions || [])];
    if (!list.length) sheet.append($('p', 'now', 'No changelog yet.'));
    const seen = new Set();
    for (const s of list) {
      const key = s.version || s.title;
      if (seen.has(key)) continue;
      seen.add(key);
      const h = $('h3', '', s.coming ? 'Coming next' : `v${s.version}`);
      const tag = s.newer ? 'new, not installed yet' : s.current ? 'you’re here' : s.coming ? 'not in a version yet' : (s.title.split('·')[1] || '').trim();
      if (tag) h.append($('small', '', tag));
      sheet.append(h);
      for (const g of s.groups || []) {
        if (g.name) sheet.append($('h4', '', g.name));
        const ul = $('ul');
        for (const it of g.items) ul.append($('li', '', it));
        sheet.append(ul);
      }
    }
  }
  function open() { log = null; openSheet('log'); fillLog(); }

  async function start() {
    close();
    try { st = await api('api/update/start', true); } catch { /* shown on the next look */ }
    render();
    clearTimeout(timer);
    timer = setTimeout(poll, 1500);
  }
  function ask() {
    if (!st || !st.available || running()) return open();
    if (st.mac) return start();
    // Not a Mac: their own parts, and what Claude gets afterwards. In his words: "a warning message that if it's
    // not macos, that explained from above and that claude will get instructions to patch it up locally again".
    sheet.replaceChildren();
    sheet.append($('h2', '', `Update to v${st.latest}?`));
    const w = $('div', 'warn');
    w.append(
      $('p', '', 'This computer isn’t a Mac, so some parts of HQ were built by your own Claude. Those are in the local folder, and the update never touches them.'),
      $('p', '', 'Anything else you changed in HQ is saved first, on a backup branch on this computer. Nothing is sent anywhere.'),
      $('p', '', 'After the update, your Claude finds instructions in the updates folder: what changed, and what to check or rebuild so everything works here again.'),
    );
    sheet.append(w);
    const row = $('div', 'row');
    const no = $('button', 'b', 'Cancel');
    no.onclick = close;
    const yes = $('button', 'b go', 'Update');
    yes.onclick = start;
    row.append(no, yes);
    sheet.append(row);
    openSheet('ask');
  }

  function mount(o) {
    opt = o || {};
    const style = $('style');
    style.textContent = CSS;
    document.head.append(style);
    ver = $('button', 'hqu hqu-ver', 'HQ');
    ver.type = 'button';
    ver.id = 'hqu-ver';
    ver.onclick = open;
    bar = $('div', 'hqu hqu-bar');
    bar.id = 'hqu-bar';
    bar.setAttribute('role', 'status');
    shade = $('div', 'hqu-shade');
    shade.onclick = close;
    sheet = $('div', 'hqu hqu-sheet');
    sheet.id = 'hqu-sheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-label', 'Versions');
    (opt.line || document.body).append(ver);
    if (opt.banner) opt.banner.append(bar); else document.body.prepend(bar);
    document.body.append(shade, sheet);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sheet.classList.contains('open')) close(); });
    // F39: on the iPhone a tap on its buttons only made them jump and the sheet stayed; a clean tap presses the button
    // itself at the end of the touch, and the touch's own late click is cancelled, so it's never pressed twice.
    let tap = null;
    const tapOn = (e) => (e.target instanceof Element ? e.target.closest('.hqu-sheet button, .hqu-ver, .hqu-bar button') : null);
    document.addEventListener('touchstart', (e) => { const b = e.touches.length === 1 ? tapOn(e) : null; tap = b ? { b, x: e.touches[0].clientX, y: e.touches[0].clientY, at: Date.now() } : null; }, { passive: true, capture: true });
    document.addEventListener('touchmove', (e) => { if (tap && (Math.abs(e.touches[0].clientX - tap.x) > 10 || Math.abs(e.touches[0].clientY - tap.y) > 10)) tap = null; }, { passive: true, capture: true });
    document.addEventListener('touchend', (e) => {
      const t = tap; tap = null;
      if (!t || e.defaultPrevented || Date.now() - t.at > 700 || t.b.disabled || !t.b.isConnected) return;
      const c = e.changedTouches[0], under = c && document.elementFromPoint(c.clientX, c.clientY);
      if (!under || !t.b.contains(under)) return;
      if (e.cancelable) e.preventDefault();
      t.b.click();
    }, { passive: false });
    // F39 (18 October 2026): a pull down closes it too, the way every sheet on the call page closes since Modern 3;
    // from anywhere while it's scrolled to its top. It follows the finger with translate, so the centring stays.
    // F48 (22 October 2026, his words: "Changelog in the app if you scroll it jumps to the bottom right and half is
    // unreadable"): it was centred with a transform; on the iPhone a scroll could lose it, leaving its top-left corner
    // in the middle of the screen. Now it's centred with inset and margin auto, no transform to lose.
    let p = null;
    const back = (go) => {
      const quick = matchMedia('(prefers-reduced-motion: reduce)').matches;
      sheet.style.transition = quick ? 'none' : 'translate .2s ease-out';
      sheet.style.translate = go ? `0 ${innerHeight}px` : '';
      setTimeout(() => { if (go) close(); sheet.style.transition = sheet.style.translate = ''; }, quick ? 0 : 200);
    };
    sheet.addEventListener('touchstart', (e) => {
      p = e.touches.length === 1 && sheet.scrollTop <= 0 ? { x: e.touches[0].clientX, y: e.touches[0].clientY, at: Date.now(), dir: '' } : null;
    }, { passive: true });
    sheet.addEventListener('touchmove', (e) => {
      if (!p || e.touches.length !== 1) return;
      const dx = e.touches[0].clientX - p.x, dy = e.touches[0].clientY - p.y;
      if (!p.dir) { if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return; p.dir = dy > 0 && Math.abs(dy) > Math.abs(dx) * 1.2 ? 'pull' : 'other'; }
      if (p.dir !== 'pull') return;
      if (e.cancelable) e.preventDefault();
      p.dy = Math.max(0, dy); sheet.style.transition = 'none'; sheet.style.translate = `0 ${p.dy}px`;
    }, { passive: false });
    sheet.addEventListener('touchend', () => {
      const s = p; p = null; if (!s || s.dir !== 'pull') return;
      const d = s.dy || 0; back(d >= 110 || (d > 40 && d / Math.max(1, Date.now() - s.at) > 0.5));
    });
    sheet.addEventListener('touchcancel', () => { if (p && p.dir === 'pull') back(false); p = null; });
    poll();
  }

  window.HQUpdate = { mount };
  window.hqUpdate = { open, ask, render, poll, state: () => st };
})();
