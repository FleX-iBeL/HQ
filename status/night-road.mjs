// H339 (6 and 7 November 2026), his words: "when MP runs the team at night, she makes like we have our artifacts like (the fix
// road), but instead of artifact, its visible in HQ so we can open them and they are stored of each night." The night's road,
// built by the program from what HQ records (the queue's jobs, their times and states, the steps a job says it's doing, the saved
// usage readings), so the page is complete and true with no words from anyone. A night is one file in the workspace,
// HQ/night-road/YYYY-MM-DD.json: {title, updated, running, rows: [{name, kind, start, end}], log: [{at, text}], usage: [{at, week}]}.
// The night of a day runs from its noon to the next day's noon, so her 21:45 check-in and the team's stop in the morning fall in it.
// H307 (folded in): the same timeline on the status page any time, from the jobs and the planning.
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseRoadmap } from './parse.mjs';
import { ROADMAP } from './paths.mjs';
import { FOLDER } from './paths.mjs';
import { lineSettings } from './usage.mjs';

export const NIGHTS = join(FOLDER, 'HQ', 'night-road');
const KINDS = ['done', 'broken', 'running', 'expected', 'you'];
const KIND_WORDS = { done: 'done', broken: 'found broken', running: 'running now', expected: 'expected (between earliest start and latest end)', you: 'you (waits for you)' };
const STALE_MIN = 20;
const JOB_MIN = 30;  // a job's length when nothing better is known
const WEEK = 7 * 864e5;

const pad = (n) => String(n).padStart(2, '0');
const day = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const hm = (t) => { const d = new Date(t); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const ms = (s) => { const t = Date.parse(s ?? ''); return Number.isNaN(t) ? null : t; };
const local = (d, t) => ms(`${d}T${t}`);  // YYYY-MM-DD and HH:MM, local time

/** Which night a moment belongs to: the day of the evening it started (noon to noon). */
export const nightOf = (t = Date.now()) => day(new Date(t - 12 * 36e5));
const windowOf = (key) => { const s = local(key, '12:00'); return [s, s + 864e5]; };

export async function nights() {
  try {
    return (await readdir(NIGHTS)).map((f) => /^(\d{4}-\d{2}-\d{2})\.json$/.exec(f)?.[1]).filter(Boolean).sort().reverse();
  } catch { return []; }
}

async function readNight(key) {
  try {
    const n = JSON.parse(await readFile(join(NIGHTS, `${key}.json`), 'utf8'));
    return n && typeof n === 'object' ? n : null;
  } catch { return null; }
}

/** The queue's jobs as timeline rows: done when they really ran, running from their start, coming from earliest to latest. */
export function jobRows(jobs, now = Date.now()) {
  const out = [];
  for (const j of jobs ?? []) {
    const name = String(j.text ?? '').replace(/\s+/g, ' ').trim().slice(0, 90);
    if (!name) continue;
    const [ad, at] = String(j.agreed ?? '').split(' ');
    const agreed = local(ad, at);
    let m;
    if ((m = /^done (\d\d:\d\d) on (\d{4}-\d{2}-\d{2})/.exec(j.state))) {
      const end = local(m[2], m[1]);
      if (end == null) continue;
      const start = agreed != null && agreed <= end && end - agreed < 12 * 36e5 ? agreed : end - JOB_MIN * 6e4;
      out.push({ name, kind: 'done', start, end });
    } else if ((m = /^(?:running|stop asked)(?: since)? (\d\d:\d\d)/.exec(j.state))) {
      let start = local(day(new Date(now)), m[1]);
      if (start > now) start -= 864e5;
      out.push({ name, kind: 'running', start, end: Math.max(start + JOB_MIN * 6e4, now + 5 * 6e4) });
    } else if (/^boxed/.test(j.state)) {
      // ran past its box: found broken, from its start to about where its box ran out (never past now)
      const start = agreed ?? now - JOB_MIN * 6e4;
      out.push({ name, kind: 'broken', start, end: Math.max(start + 6e4, Math.min(now, start + JOB_MIN * 6e4)) });
    } else if (/^held/.test(j.state)) {
      out.push({ name, kind: 'you', start: agreed ?? now, end: Math.max(now + 60 * 6e4, (agreed ?? now) + 6e4) });
    } else if (/^ready/.test(j.state)) {
      // the earliest a waiting job starts is the routine's next whole-minute tick after this one
      const start = Math.ceil(now / 6e4) * 6e4 + 6e4 + ((j.place ?? 1) - 1) * JOB_MIN * 6e4;
      out.push({ name, kind: 'expected', start, end: start + JOB_MIN * 6e4 });
    }
  }
  return out;
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const FACT_MIN = 5;  // a fact's bar (a verdict, a release, a round): from its own time, a few minutes wide
const fact = (name, kind, at) => ({ name: `${name} at ${hm(at)}`, kind, start: at, end: at + FACT_MIN * 6e4 });
const jobName = (j) => String(j?.text ?? '').replace(/\s+/g, ' ').trim().slice(0, 90);
const plainWhy = (s) => String(s ?? '').replace(/\b[Jj]ob \d+/g, 'a job').replace(/\s+/g, ' ').trim().slice(0, 80);

async function trailLines() {
  try {
    return (await readFile(join(dirname(ROADMAP), 'trail.jsonl'), 'utf8')).split('\n').map((l) => { try { return JSON.parse(l); } catch { return null; } })
      .filter((x) => x && typeof x.at === 'number');
  } catch { return []; }
}

/** Every other fact HQ records, each a row of its own at its real time (done example 1): each check's verdict (QA failed or
 * passed, from the item's row and from the record), each refusal and incident, each review round, the release, and a run that
 * ended at its box (found broken from its start to that end, so the run that's then done is the green row after it). */
export async function factRows(parsed, now = Date.now()) {
  const out = [], seen = new Set();
  for (const ph of parsed?.phases ?? []) for (const st of ph.steps ?? []) {
    const label = /^([A-Z]+\d+)\b/.exec(st.name ?? '')?.[1];
    if (!label) continue;
    for (const d of st.details ?? []) {
      for (const m of String(d.text ?? '').matchAll(/QA (failed|passed) \(job (\d+), (\d{1,2}) ([A-Z][a-z]+) (\d{4}) (\d\d):(\d\d)\)/g)) {
        const mo = MONTHS.indexOf(m[4]);
        if (mo < 0 || seen.has(m[2])) continue;
        seen.add(m[2]);
        const at = new Date(Number(m[5]), mo, Number(m[3]), Number(m[6]), Number(m[7])).getTime();
        out.push(fact(`${label} QA ${m[1]}`, m[1] === 'failed' ? 'broken' : 'done', at));
      }
    }
  }
  const lines = await trailLines();
  const labels = new Map(lines.filter((x) => x.label).map((x) => [x.id, x.label]));
  const jobs = new Map((parsed?.queue?.jobs ?? []).map((j) => [Number(j.n), j]));
  for (const x of lines) {
    const at = Math.round(x.at * 1000), label = labels.get(x.id) ?? '';
    if (at > now) continue;
    if (x.step === 'qa' && ['failed', 'passed'].includes(x.state) && !seen.has(String(x.job))) {
      seen.add(String(x.job));
      out.push(fact(`${label || 'An item'} QA ${x.state}`, x.state === 'failed' ? 'broken' : 'done', at));
    } else if (x.step === 'release') out.push(fact(`Release ${x.version ?? ''} out`.replace(/\s+/g, ' '), 'done', at));
    else if (x.step === 'round') out.push(fact(`${label || 'An item'} review round ${x.n ?? ''}`.trim(), 'done', at));
    else if (x.step === 'incident' || x.step === 'refused') out.push(fact(`Went wrong: ${plainWhy(x.why) || 'an incident'}`, 'broken', at));
    else if (x.step === 'job' && x.state === 'boxed' && jobs.has(Number(x.job))) {
      const j = jobs.get(Number(x.job)), [ad, t] = String(j.agreed ?? '').split(' ');
      const start = x.start ? Math.round(x.start * 1000) : local(ad, t);
      out.push({ name: jobName(j), kind: 'broken', start: start != null && start < at ? start : at - JOB_MIN * 6e4, end: at, boxed: true });
    }
  }
  return out;
}

const overlaps = (r, [s, e]) => r.end >= s && r.start <= e;
const fromFile = (r) => ({ name: String(r.name ?? ''), kind: KINDS.includes(r.kind) ? r.kind : 'done', start: ms(r.start), end: ms(r.end) });
const toFile = (r) => ({ name: r.name, kind: r.kind, start: new Date(r.start).toISOString(), end: new Date(r.end).toISOString() });

/** Takes one fresh row from HQ's records into a night's rows. What went wrong and then right keeps both: the found-broken row
 * stays with its real time and a new row follows it, never one row overwritten to green. Running and expected rows move on. */
export function takeRow(rows, r) {
  if (r.boxed) {
    if (rows.some((y) => y.name === r.name && y.kind === 'broken' && y.end === r.end)) return false;
    const { boxed, ...b } = r;
    const after = rows.findIndex((y) => y.name === r.name && y.kind !== 'broken' && y.end > b.end);
    if (after < 0) { rows.push(b); return true; }
    rows.splice(after, 0, b);
    rows[after + 1] = { ...rows[after + 1], start: Math.max(rows[after + 1].start, b.end) };
    return true;
  }
  let last = -1;
  rows.forEach((x, i) => { if (x.name === r.name) last = i; });
  if (last < 0) { rows.push(r); return true; }
  const x = rows[last];
  if (x.kind === 'broken' && r.kind !== 'broken') {
    rows.push({ ...r, start: Math.max(r.start, x.end), end: Math.max(r.end, x.end + 6e4) });
    return true;
  }
  const before = rows.slice(0, last).filter((y) => y.name === r.name && y.kind === 'broken').pop();
  if (before && r.kind !== 'broken') r = { ...r, start: Math.max(r.start, before.end), end: Math.max(r.end, before.end + 6e4) };
  if (x.kind === r.kind && x.end === r.end && x.start === r.start) return false;
  rows[last] = x.kind === 'broken' ? { ...x, end: r.end } : r;
  return true;
}

const readKept = (kept) => ({ title: kept?.title || 'The night', updated: ms(kept?.updated), running: kept ? kept.running !== false : true,
  rows: (Array.isArray(kept?.rows) ? kept.rows : []).map(fromFile).filter((r) => r.name && r.start != null && r.end != null),
  log: (Array.isArray(kept?.log) ? kept.log : []).filter((x) => x && x.text).map((x) => ({ at: ms(x.at), text: String(x.text) })),
  usage: (Array.isArray(kept?.usage) ? kept.usage : []).map((u) => ({ at: ms(u.at), week: Number(u.week) })).filter((u) => u.at != null && Number.isFinite(u.week)),
  reset: kept?.reset ?? null,
  parts: Array.isArray(kept?.parts) ? kept.parts : [] });

async function keep(key, kept, n) {
  try {
    await mkdir(NIGHTS, { recursive: true });
    await writeFile(join(NIGHTS, `${key}.json`), `${JSON.stringify({ ...(kept ?? {}), title: n.title, running: n.running,
      updated: kept?.updated ?? new Date().toISOString(), rows: n.rows.map(toFile), log: kept?.log ?? [], usage: kept?.usage ?? [] }, null, 1)}\n`);
  } catch { /* a page that can't keep it still shows it */ }
}

/** A kept night that's over: its still-running rows get their real end and colour once the job's own record has one. That close,
 * on the night the job started, is the only change a finished night ever gets; the night that runs now never writes onto it. */
async function closeKept(key, kept, n, records) {
  let changed = false;
  for (const r of n.rows) {
    if (r.kind !== 'running') continue;
    const end = records.find((x) => x.name === r.name && ['done', 'broken'].includes(x.kind) && x.end >= r.start);
    if (!end) continue;
    r.kind = end.kind;
    r.end = end.end;
    changed = true;
  }
  if (changed) await keep(key, kept, n);
  return n;
}

/** A night as the page shows it. The night that runs now takes in the queue's jobs and is kept with them, so it reads the same later. */
async function theNight(key, parsed, now) {
  const kept = await readNight(key);
  const n = readKept(kept);
  const facts = await factRows(parsed, now);
  const boxedNames = new Set(facts.filter((r) => r.boxed).map((r) => r.name));
  // a run ended at its box is its own found-broken row (the record's real end), so the job's own boxed state adds none
  const records = [...facts, ...jobRows(parsed?.queue?.jobs, now).filter((r) => !(r.kind === 'broken' && boxedNames.has(r.name)))];
  if (key !== nightOf(now)) return closeKept(key, kept, n, records.filter((r) => !r.boxed));
  // a job a kept night already holds stays on the night it started
  const older = new Set();
  for (const k of (await nights()).filter((d) => d < key)) for (const r of (await readNight(k))?.rows ?? []) older.add(r.name);
  let changed = false;
  for (const r of records.filter((x) => overlaps(x, windowOf(key)) && !older.has(x.name))) changed = takeRow(n.rows, r) || changed;
  if (changed || (!kept && n.rows.length)) await keep(key, kept, n);
  return n;
}

/** The routine's minute tick: the night that runs now written from HQ's records, and every kept night with a running row looked at. */
export async function tick(parsed, now = Date.now()) {
  const cur = nightOf(now);
  for (const k of await nights()) if (k !== cur) {
    const kept = await readNight(k);
    if (kept?.rows?.some((r) => r.kind === 'running')) await theNight(k, parsed, now);
  }
  return theNight(cur, parsed, now);
}

/** A usage reading HQ saves, written into the night that runs as it comes in (part 4b): {at, week}, and the week's reset. */
export async function addReading(week, at = Date.now(), reset = null) {
  if (!Number.isFinite(week)) return;
  const key = nightOf(at);
  const kept = (await readNight(key)) ?? { title: 'The night', running: true, rows: [], log: [], usage: [] };
  const usage = Array.isArray(kept.usage) ? kept.usage : [];
  const iso = new Date(at).toISOString();
  if (usage.some((u) => u.at === iso)) return;
  usage.push({ at: iso, week });
  try {
    await mkdir(NIGHTS, { recursive: true });
    await writeFile(join(NIGHTS, `${key}.json`), `${JSON.stringify({ ...kept, usage, ...(reset ? { reset } : {}) }, null, 1)}\n`);
  } catch { /* the graph waits for the next reading */ }
}

/** What a row shows as: never running after its end in a night that still runs (its end wasn't recorded: found broken). */
const shownKind = (r, n, now) => (r.kind === 'running' && r.end < now && n.running ? 'broken' : r.kind);

export function timelineHtml(rows, now = Date.now(), kindOf = (r) => r.kind) {
  if (!rows.length) return '<p class="soft">Nothing on the timeline yet.</p>';
  const list = [...rows].sort((a, b) => a.start - b.start);
  const t0 = Math.min(now, ...list.map((r) => r.start));
  const t1 = Math.max(now, ...list.map((r) => r.end));
  const span = Math.max(t1 - t0, 6e4);
  const at = (t) => Math.round((10000 * (t - t0)) / span) / 100;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => `<span class="nr-tick" style="left:${f * 100}%">${hm(t0 + f * span)}</span>`).join('');
  const body = list.map((r) => {
    const k = kindOf(r);
    const when = k === 'expected' ? `between ${hm(r.start)} and ${hm(r.end)}` : k === 'running' ? `${hm(r.start)}, until about ${hm(r.end)}`
      : r.kind === 'running' && k === 'broken' ? `${hm(r.start)}–${hm(r.end)}, its end never recorded` : `${hm(r.start)}–${hm(r.end)}`;
    return `<div class="nr-row"><div class="nr-name">${esc(r.name)} <span class="nr-when">${esc(when)}</span></div>`
      + `<div class="nr-lane"><div class="nr-bar k-${k}" tabindex="0" style="left:${at(r.start)}%;width:${Math.max(0.6, at(r.end) - at(r.start))}%" title="${esc(r.name)} · ${esc(when)}"></div></div></div>`;
  }).join('');
  const legend = KINDS.map((k) => `<span class="nr-key"><i class="nr-sw k-${k}"></i>${KIND_WORDS[k]}</span>`).join('');
  return `<div class="nr-timeline"><div class="nr-row nr-axis"><div class="nr-name"></div><div class="nr-lane">${ticks}`
    + `<div class="nr-now now" style="left:${at(now)}%" title="Now, ${hm(now)}"></div></div></div>${body}</div><div class="nr-legend">${legend}</div>`;
}

/** Part 4b: the week's usage graph: the real line from 0%, the moving line, the stop line, where it's heading. */
function usageHtml(n, now, markdown, reset0) {
  const reads = [...n.usage].sort((a, b) => a.at - b.at);
  if (!reads.length) return '<p class="soft">No usage reading yet this week: the graph starts empty at the week\'s start.</p>';
  const last = reads[reads.length - 1];
  let reset = ms(reset0) ?? ms(n.reset);
  if (reset == null) reset = reads[0].at + WEEK;
  while (reset <= last.at) reset += WEEK;
  while (reset - WEEK > last.at) reset -= WEEK;
  const ws = reset - WEEK;
  const week = reads.filter((r) => r.at >= ws);
  const set = lineSettings(markdown ?? '');
  const stop = set?.weekly && !set.weekly.moving ? set.weekly.fixed : 90;
  const W = 600, H = 200, x = (t) => Math.round((W * (t - ws)) / WEEK * 10) / 10, y = (p) => Math.round((H - 10 - (H - 20) * Math.min(100, Math.max(0, p)) / 100) * 10) / 10;
  const moving = (t) => Math.max(20, Math.round(100 * (t - ws) / WEEK));
  const real = [[ws, 0], ...week.map((r) => [r.at, r.week])].map(([t, p]) => `${x(t)},${y(p)}`).join(' ');
  const twelve = week.filter((r) => r.at >= last.at - 12 * 36e5);
  // the last twelve working hours' pace; with one reading in them, the week's own pace so far
  const pace = twelve.length > 1 && last.at > twelve[0].at ? (last.week - twelve[0].week) / (last.at - twelve[0].at)
    : last.at > ws ? last.week / (last.at - ws) : 0;
  const to = Math.min(reset, Math.max(now + 36e5, ...n.rows.map((r) => r.end)));
  const lands = Math.min(stop, last.week + pace * Math.max(0, to - last.at));
  const dots = week.map((r) => `<circle class="nr-reading" cx="${x(r.at)}" cy="${y(r.week)}" r="3"><title>${hm(r.at)}: the week at ${r.week}%, the moving line at ${moving(r.at)}%</title></circle>`).join('');
  return `<svg class="nr-usage" viewBox="0 0 ${W} ${H}" role="img" aria-label="The week's usage: now ${last.week}%, the stop line at ${stop}%">`
    + `<line class="nr-stop" x1="0" y1="${y(stop)}" x2="${W}" y2="${y(stop)}" stroke="#d33" stroke-dasharray="6 4"/>`
    + `<text x="4" y="${y(stop) - 4}" class="nr-stop-label">stop ${stop}%</text>`
    + `<polyline class="nr-moving" fill="none" stroke="#888" stroke-dasharray="2 4" points="${x(ws)},${y(20)} ${x(ws + 0.2 * WEEK)},${y(20)} ${x(reset)},${y(100)}"/>`
    + `<polyline class="nr-real" fill="none" stroke="#2a6" stroke-width="2" points="${real}"/>`
    + `<line class="nr-heading" x1="${x(last.at)}" y1="${y(last.week)}" x2="${x(to)}" y2="${y(lands)}" stroke="#2a6" stroke-dasharray="4 3"/>`
    + `${dots}<text x="${Math.min(W - 70, x(last.at) + 6)}" y="${y(last.week) - 6}">now ${last.week}%</text>`
    + `<text x="${Math.min(W - 110, x(to) - 100)}" y="${Math.max(12, y(lands) - 6)}" class="nr-heading-label">heading for ${Math.round(lands)}%</text></svg>`
    + `<div class="nr-legend"><span class="nr-key"><i class="nr-ln real"></i>the week used</span><span class="nr-key"><i class="nr-ln moving"></i>the moving line</span>`
    + `<span class="nr-key"><i class="nr-ln stop"></i>the stop line (${stop}%)</span><span class="nr-key"><i class="nr-ln heading"></i>where it's heading (${Math.round(lands)}% by ${hm(to)})</span></div>`;
}

export const CSS = `
.nr-timeline{margin:.6rem 0;font-size:.9rem}
.nr-row{display:grid;grid-template-columns:minmax(10rem,32%) 1fr;gap:.5rem;align-items:center;margin:.2rem 0}
.nr-name{overflow-wrap:anywhere}.nr-when{color:#777;font-size:.8rem}
.nr-lane{position:relative;height:1.1rem;background:rgba(127,127,127,.08);border-radius:3px}
.nr-axis .nr-lane{background:none;height:1.2rem}
.nr-tick{position:absolute;top:0;font-size:.7rem;color:#888;transform:translateX(-50%)}
.nr-now{position:absolute;top:0;width:2px;height:999px;background:#e33;z-index:2;pointer-events:none}
.nr-timeline{position:relative;overflow:hidden}
.nr-bar{position:absolute;top:2px;bottom:2px;border-radius:3px;min-width:4px}
.k-done{background:#2a6}.k-broken{background:#d33}.k-running{background:#38f}.k-you{background:#c8a000}
.k-expected{background:repeating-linear-gradient(45deg,#9ab 0 4px,transparent 4px 8px);border:1px solid #9ab}
.nr-legend{display:flex;flex-wrap:wrap;gap:.8rem;font-size:.8rem;margin:.3rem 0}
.nr-sw{display:inline-block;width:.9rem;height:.6rem;border-radius:2px;margin-right:.3rem}
.nr-ln{display:inline-block;width:1.2rem;border-top:2px solid #2a6;margin-right:.3rem;vertical-align:middle}
.nr-ln.moving{border-top:2px dotted #888}.nr-ln.stop{border-top:2px dashed #d33}.nr-ln.heading{border-top:2px dashed #2a6}
.nr-usage{width:100%;max-width:640px;height:auto;background:rgba(127,127,127,.05)}
.nr-usage text{font-size:11px;fill:#666}
@media (max-width:640px){.nr-row{display:block}.nr-name{margin-bottom:.15rem}}
`;

const PAGE_CSS = `body{font:15px/1.45 system-ui,sans-serif;max-width:960px;margin:1rem auto;padding:0 1rem;color:#222}
.soft{color:#777}.nr-facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:.6rem;margin:.8rem 0}
.nr-fact{background:rgba(127,127,127,.08);padding:.5rem;border-radius:6px}.nr-fact b{display:block;font-size:.75rem;color:#777;font-weight:600}
.nr-progress{display:block;width:100%;height:.5rem;accent-color:#678}
.nr-warn{color:#b30;font-weight:600}.nr-log li,.nr-parts li{margin:.2rem 0}.nr-pill{font-size:.75rem;border:1px solid #aaa;border-radius:9px;padding:0 .4rem;margin-left:.3rem}
@media (prefers-color-scheme:dark){body{background:#151515;color:#ddd}}` + CSS;

/** The night's page: /night-road (the night that's newest) and /night-road/YYYY-MM-DD (any kept night). */
export async function nightPage(key, parsed, { now = Date.now(), markdown = '', reset = null } = {}) {
  const list = await nights();
  const cur = nightOf(now);
  if (!key) key = list[0] && list[0] > cur ? list[0] : (list.includes(cur) || parsed?.queue?.jobs?.length ? cur : list[0] ?? cur);
  const n = await theNight(key, parsed, now);
  const all = [...new Set([key, ...(await nights())])].sort().reverse();
  const kind = (r) => shownKind(r, n, now);
  const ago = n.updated != null ? Math.max(0, Math.floor((now - n.updated) / 6e4)) : null;
  const stale = n.running && key === cur && ago != null && ago > STALE_MIN;
  const log = [...n.log].sort((a, b) => (b.at ?? 0) - (a.at ?? 0));
  const going = n.rows.filter((r) => kind(r) === 'running');
  const ahead = n.rows.filter((r) => ['running', 'expected'].includes(kind(r)));
  const step = log[0]?.text ?? (going[0] ? going[0].name : 'Nothing running');
  const usedNow = n.usage.length ? [...n.usage].sort((a, b) => b.at - a.at)[0].week : null;
  const finished = n.rows.filter((r) => ['done', 'broken'].includes(kind(r))).length;
  const pct = n.rows.length ? Math.round((100 * finished) / n.rows.length) : 0;
  const parts = n.parts.map((p) => `<li><span class="nr-dot">●</span> <b>${esc(p.title)}</b> ${esc(p.text ?? '')}${p.pill ? `<span class="nr-pill">${esc(p.pill)}</span>` : ''}</li>`).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The night's road · ${esc(key)}</title><style>${PAGE_CSS}</style></head><body>
<h1>${esc(n.title)} · ${esc(key)}</h1>
<p>The night's road: what the team did this night, kept as it happened.</p>
<p>Last updated <span id="nr-updated" data-at="${n.updated ?? ''}" data-live="${n.running && key === cur ? 1 : 0}">${n.updated != null ? `${hm(n.updated)} (${ago} min ago)` : 'not yet'}</span>${stale ? ` <span class="nr-warn">Not updated for ${ago} min</span>` : ''}</p>
<div class="nr-facts"><div class="nr-fact"><b>Current step</b>${esc(step)}</div>
<div class="nr-fact"><b>Expected end</b>${ahead.length ? hm(Math.max(...ahead.map((r) => r.end))) : n.running ? 'nothing more planned' : 'the night is over'}</div>
<div class="nr-fact"><b>The week used</b>${usedNow != null ? `${usedNow}%` : 'no reading yet'}</div>
<div class="nr-fact"><b>The team</b>${n.running && key === cur ? 'working the night' : 'finished for the night'}</div></div>
<progress class="nr-progress" max="100" value="${pct}" title="${finished} of ${n.rows.length} finished">${pct}%</progress>
<h2>The timeline</h2>${timelineHtml(n.rows, now, kind)}
<h2>The week's usage</h2>${usageHtml(n, now, markdown, reset)}
<h2>Now</h2><ul>${going.map((r) => `<li>${esc(r.name)}, since ${hm(r.start)}</li>`).join('') || '<li>Nothing running.</li>'}</ul>
${parts ? `<h2>The parts of the night</h2><ul class="nr-parts">${parts}</ul>` : ''}
<h2>The log</h2><ul class="nr-log">${log.map((x) => `<li>${x.at != null ? hm(x.at) : ''} ${esc(x.text)}</li>`).join('') || (n.rows.length ? '<li>No words logged yet: the timeline above is what ran.</li>' : '<li>A quiet night: nothing to do.</li>')}</ul>
<h2>The nights</h2><ul>${all.map((d) => `<li><a href="/night-road/${d}">${d}${d === key ? ' (this one)' : ''}</a></li>`).join('')}</ul>
<p><a href="/">Back to HQ</a></p>
<script>(function(){var u=document.getElementById('nr-updated');if(!u||!u.dataset.at)return;function f(){var t=Number(u.dataset.at),m=Math.max(0,Math.floor((Date.now()-t)/6e4)),d=new Date(t);u.textContent=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+' ('+m+' min ago)';if(u.dataset.live==='1'&&m>${STALE_MIN}&&!document.querySelector('.nr-warn')){var w=document.createElement('span');w.className='nr-warn';w.textContent=' Not updated for '+m+' min';u.after(w);}}setInterval(f,30000);if(u.dataset.live==='1')setInterval(function(){location.reload();},60000);})();</script>
</body></html>`;
}

/** H307: the timeline for the status page, any time: the night that runs now with the queue's jobs. */
export async function statusTimeline(parsed, now = Date.now()) {
  const n = await theNight(nightOf(now), parsed, now);
  const rows = n.rows.length ? n.rows : jobRows(parsed?.queue?.jobs, now).filter((r) => r.end >= now - 12 * 36e5);
  return `<style>${CSS}</style>${timelineHtml(rows, now, (r) => shownKind(r, n, now))}`;
}

// The routine's minute tick (routine/tick.py): node status/night-road.mjs --tick
if (process.argv[1] === fileURLToPath(import.meta.url) && process.argv.includes('--tick')) {
  let text = '';
  try { text = await readFile(ROADMAP, 'utf8'); } catch { /* no roadmap: the kept nights alone */ }
  await tick(text ? parseRoadmap(text) : null);
}
