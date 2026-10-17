/**
 * The usage reading for the status page. A web page cannot ask Claude how much of the plan is
 * used; a session can (the usage tool). So a session saves what the tool said with
 * `node "status/save-usage.mjs"`, and the page shows that reading and how old it is.
 */

/**
 * What is kept of the usage tool's answer.
 * @param {any} tool the usage tool's output, as JSON
 * @param {{ now?: Date, by?: string }} [about]
 */
export function usageReading(tool, about = {}) {
  const plan = tool?.plan;
  const context = tool?.context;
  const ok = plan?.status === 'ok' && Array.isArray(plan.windows) && plan.windows.length > 0;
  return {
    checkedAt: (about.now ?? new Date()).toISOString(),
    by: about.by ?? '',
    readable: ok,
    plan: ok ? (plan.plan ?? '') : '',
    limits: ok
      ? plan.windows.map((w) => ({
          label: String(w.label),
          percent: Number(w.percentUsed),
          resetsAt: w.resetsAt ?? null,
        }))
      : [],
    context:
      context?.status === 'ok'
        ? {
            percent: Number(context.percentUsed),
            tokens: Number(context.tokensUsed),
            window: Number(context.contextWindow),
          }
        : null,
  };
}

/**
 * H91 (12 October 2026, call at 21:00): "So all three of them move each minute and then all three have a
 * fixed possibility." The three stop lines: the 5-hour line, the weekly all-models line and the weekly
 * Fable line. Each either moves (HQ's default) or stays at a fixed number of his choice; the settings sit
 * in the roadmap (lineSettings below), so the laptop and the server read the same ones.
 *
 * Moving: the line is the share of the limit's window that has gone by, recalculated every minute, so it
 * grows smoothly up to 100% in the window's last minute, the minute before its reset. It never stands below
 * its floor, so a fresh window is not a sudden cap: 10% for the 5-hour line (as H87 started), 20% for the
 * weekly lines (as F1 started). So the 5-hour line climbs 20% an hour after its first half hour; a weekly
 * line about 0.6% an hour (14% a day) after its first day and a half. The times follow from the reset time,
 * so nothing has to be kept anywhere. Without a reset time a moving line can't move: its fixed number counts.
 */
export const LINES = {
  five: { label: '5-hour', windowMs: 5 * 60 * 60 * 1000, floor: 10 },
  weekly: { label: 'Weekly · all models', windowMs: 7 * 24 * 60 * 60 * 1000, floor: 20 },
  fable: { label: 'Weekly · Fable', windowMs: 7 * 24 * 60 * 60 * 1000, floor: 20 },
};
/** A weekly line fixed without a number of its own (and no flat "**Weekly limit: N%**"): Claude's choice. */
export const WEEKLY_FIXED = 90;

/** Which of the three lines a plan limit's label belongs to. */
export function lineKey(label) {
  if (/5-hour/i.test(label ?? '')) return 'five';
  if (/^weekly/i.test(label ?? '')) return /fable/i.test(label) ? 'fable' : 'weekly';
  return null;
}

/**
 * The three lines' settings from the roadmap, or null when it names no usage limit (then nothing stops).
 *   - **Usage limit: 70%.**                 the 5-hour line's fixed number (also: there are stop lines at all)
 *   - **5-hour line: moving.** / fixed.     H87; moving when it isn't named
 *   - **Weekly line: moving; fixed at 90% when switched.** / **Weekly line: fixed at 90%.**
 *   - **Fable line: …**                     the same, for the weekly Fable limit
 * Older roadmaps: without a Weekly or Fable line, a flat "**Weekly limit: N%**" fixes both at N,
 * else both move.
 * @returns {{ five: {moving: boolean, fixed: number}, weekly: {moving: boolean, fixed: number}, fable: {moving: boolean, fixed: number} } | null}
 */
export function lineSettings(markdown) {
  const limit = /\*\*Usage limit:\s*(\d{1,3})\s*%/.exec(markdown);
  if (!limit) return null;
  const flat = /\*\*Weekly limit:\s*(\d{1,3})\s*%/.exec(markdown);
  const read = (name) => {
    const m = new RegExp(`\\*\\*${name} line:\\s*(moving|fixed)\\b([^*]*)\\*\\*`, 'i').exec(markdown);
    if (!m) return null;
    const n = /(\d{1,3})\s*%/.exec(m[2]);
    return { moving: m[1].toLowerCase() === 'moving', fixed: n ? Number(n[1]) : null };
  };
  const five = read('5-hour');
  const old = { moving: !flat, fixed: flat ? Number(flat[1]) : WEEKLY_FIXED };
  const week = read('Weekly');
  const fable = read('Fable');
  return {
    five: { moving: five ? five.moving : true, fixed: Number(limit[1]) },
    weekly: week ? { moving: week.moving, fixed: week.fixed ?? old.fixed } : old,
    fable: fable ? { moving: fable.moving, fixed: fable.fixed ?? old.fixed } : old,
  };
}

/**
 * Where a moving line stands at a given moment, from its limit's reset time.
 * @returns {{ line: number, next: string | null, perHour: number } | null} next: when it leaves its floor
 *   (null once it moves every minute, or at 100%); perHour: how fast it climbs; null without a reset time
 */
export function movingLine(key, resetsAt, now = new Date()) {
  const reset = resetsAt ? new Date(resetsAt).getTime() : NaN;
  if (Number.isNaN(reset) || !LINES[key]) return null;
  const { windowMs, floor } = LINES[key];
  const minutes = windowMs / 60000;
  // The reset time comes a fraction of a second early or late; the line moves on the whole minute.
  const start = Math.round(reset / 60000) * 60000 - windowMs;
  const begun = Math.min(minutes, Math.max(1, Math.floor((now.getTime() - start) / 60000) + 1));
  const line = Math.max(floor, Math.round((1000 * begun) / minutes) / 10);
  // The first minute whose share, to one decimal, is above the floor.
  const rises = Math.ceil(((floor + 0.05) * minutes) / 100);
  return {
    line,
    next: begun < rises ? new Date(start + (rises - 1) * 60000).toISOString() : null,
    perHour: Math.round((100 * 36e5 * 10) / windowMs) / 10,
  };
}

/** H87's name for the 5-hour one, kept for whoever still calls it. */
export const movingFiveHour = (resetsAt, now = new Date()) => movingLine('five', resetsAt, now);

/**
 * The stop line for one plan limit at a given moment, in percent: its own line, moving or fixed
 * (lineSettings). A limit that is none of the three (none today) stops at the 5-hour line's fixed number.
 * @param {{ label: string, resetsAt: string | null }} l
 * @param {ReturnType<typeof lineSettings>} lines null: no stop lines at all
 * @returns {{ line: number, next: string | null, perHour?: number, moving: boolean } | null}
 */
export function stopLine(l, lines, now = new Date()) {
  if (!lines) return null;
  const key = lineKey(l.label);
  const s = key ? lines[key] : null;
  if (!s) return { line: lines.five.fixed, next: null, moving: false };
  if (s.moving) {
    const m = movingLine(key, l.resetsAt, now);
    if (m) return { ...m, moving: true };
  }
  return { line: s.fixed, next: null, moving: false };
}

/**
 * H141 (14 October 2026, call at 17:44), replacing H114's fixed buffer: "maybe based on the estimated time, we can
 * see dynamically how much space there should be between now and the usage limit cap?", "1 % for every 2 minutes of
 * estimated work?" and "so then its 0.2% for every 2 minutes for weekly?". A new job only starts when the room under
 * each stop line is bigger than its own estimate needs; a job already running still goes on until the line itself.
 * The two rates live here and only here: percent of room for every START_ROOM.per minutes of estimated work.
 * H172 (16 October 2026): the routine's start check now gets the job's estimated usage from the finished jobs like it
 * (routine/usagecost.py, save-usage.mjs --gate --need five=X,weekly=Y); these rates are only the fallback, for work with
 * too little history (usagecost.py's FALLBACK says the same per minute).
 */
export const START_ROOM = { per: 2, five: 1, weekly: 0.2, fable: 0.2 };

/** When the estimate isn't known: 10 minutes, the same room as H114's old buffer (5 and 1 points). */
export const START_MINUTES = 10;

/** The room (in points) a job of so many minutes needs under one stop line ('five', 'weekly' or 'fable'). */
export function roomNeeded(key, minutes = START_MINUTES) {
  const m = Number.isFinite(minutes) && minutes > 0 ? minutes : START_MINUTES;
  return Math.round((10 * (START_ROOM[key] ?? START_ROOM.five) * m) / START_ROOM.per) / 10;
}

/**
 * Whether work may go on. It stops when any plan limit is at or above its stop line (see
 * stopLine), and when the usage could not be read. The context window is shown but never stops
 * the work.
 * @param {ReturnType<typeof usageReading> | null} reading
 * @param {ReturnType<typeof lineSettings>} lines null: the roadmap names no usage limit, nothing stops
 * @param {Date} [now]
 * @param {{ weeklyOnly?: boolean, start?: boolean, minutes?: number, need?: { five?: number, weekly?: number, fable?: number } }} [opts]
 *   weeklyOnly: only the weekly limits count (F13: a job past the line); start: the check before a new job starts, which
 *   needs room under each line for the job's estimated usage `need` in points (H172; Weekly Fable takes the weekly
 *   one), else for its estimate of `minutes` at START_ROOM's rates (H141, roomNeeded)
 */
export function usageVerdict(reading, lines, now = new Date(), { weeklyOnly = false, start = false, minutes, need } = {}) {
  if (!reading?.readable) return { stop: true, reason: 'The usage could not be read.' };
  if (!lines) return { stop: false, reason: '' };
  // A kept reading (F6) is old and from another session: shown, but never a stop.
  // F13: a job let past the line only skips the 5-hour line; the weekly lines always count.
  const over = reading.limits
    .filter((l) => !l.kept)
    .filter((l) => !weeklyOnly || /^weekly/i.test(l.label))
    .map((l) => {
      const line = stopLine(l, lines, now).line;
      const key = lineKey(l.label) ?? 'five';
      const est = need ? Number(need[key] ?? need.weekly ?? 0) : null;
      const room = Math.round(10 * (line - l.percent)) / 10;
      return { ...l, line, est, need: !start ? 0 : est !== null && Number.isFinite(est) ? est : roomNeeded(key, minutes), room };
    })
    .filter((l) => l.room <= l.need);
  if (over.length === 0) return { stop: false, reason: '' };
  return {
    stop: true,
    reason: `${over
      .map((l) =>
        l.percent >= l.line
          ? `${l.label} is at ${l.percent}%, its stop line is ${l.line}%`
          : l.est !== null && Number.isFinite(l.est)
            ? `${l.label}: about ${Number.isFinite(minutes) && minutes > 0 ? `${Math.round(minutes)} min of work, estimated to use ` : ''}${l.need}% of it, doesn't fit under its stop line of ${l.line}%: there's ${l.room}% of room (at ${l.percent}%)`
            : `${l.label}: about ${Number.isFinite(minutes) && minutes > 0 ? Math.round(minutes) : START_MINUTES} min of work needs ${l.need}% of room under its stop line of ${l.line}%, there's ${l.room}% (at ${l.percent}%)`,
      )
      .join('; ')}.`,
  };
}

/**
 * H176 (16 October 2026, call at 13:37): "Maybe we can make that a yellow bar so we can visually see where it's going
 * to end up and know, if things go as estimated, where it would land and in what time." Where one plan limit's use
 * should land if the work goes as estimated, from the same estimates as the totals (routine/estimate.py plan): a piece
 * per job and planned item, in the order they'd run (a priority item where it cuts in). Kinds: 'team' (what's still to
 * come of the running job, and the waiting jobs), 'planned' (a one-time planned item), 'repeat' (a repeating one, its
 * next time). Work that runs past the limit's reset counts, by its minutes, for the next window (`next`). Work without a
 * time (the routine off, a line it never fits under) isn't placed; `untimed` counts it. `cross`: the first piece that
 * would take it past the stop line as it stands when that piece is done.
 * @returns {null | { key: string, now: number, to: number, lands: number | null, reset: number | null, line: number | null,
 *   pieces: Array<{ kind: string, what: string, add: number, from: number, to: number, start: number, lands: number, priority: boolean }>,
 *   kinds: Record<string, number>, next: number, untimed: number, cross: null | { what: string, at: number, pct: number, line: number },
 *   lineThen, thenAt, thenLands: the moving line when the one-off work lands (H177, H181); lineAll, allAt, allLands: when everything does }}
 */
export const LAND_KINDS = { team: "the team's work", planned: 'planned once', repeat: 'repeating' };
export function landing(l, lines, E, now = new Date(), { from = null } = {}) {
  const key = lineKey(l?.label);
  if (!key || key === 'fable' || !E || !Number.isFinite(Number(l.percent))) return null;
  const t = now.getTime() / 1000;
  const reset = l.resetsAt ? new Date(l.resetsAt).getTime() / 1000 : null;
  // H199: a later window (`from`, epoch seconds) counts only the work from its start; the current one counts all of it.
  const lo = from ?? -Infinity;
  const work = [];
  let untimed = 0;
  const put = (w) => (w.end && w.start !== null ? work.push(w) : (untimed += w.add > 0 ? 1 : 0));
  for (const [n, e] of Object.entries(E.jobs ?? {})) {
    if (e.finished || !e.cost) continue;
    const running = 'left' in e;
    const add = Math.max(0, Number(e.cost[key] ?? 0) - (running ? Number(e.used?.[key] ?? 0) : 0));
    const end = e.eta ?? null;
    const start = running ? t : (e.start ?? (end ? end - (e.est ?? 0) * 60 : null));
    put({ kind: 'team', what: `Job ${n}`, add, start, end, priority: false, running, waits: e.waits === 'usage' && !running });
  }
  for (const [n, e] of Object.entries(E.items ?? {})) {
    if (!e.cost) continue;
    put({ kind: e.every ? 'repeat' : 'planned', what: e.what ?? `Planned item ${n}`, add: Math.max(0, Number(e.cost[key] ?? 0)), start: e.start ?? null, end: e.eta ?? null, priority: !!e.priority, waits: !!e.usage_wait });
  }
  // The order they'd run: the running job first, then by when each starts.
  work.sort((a, b) => (b.running ? 1 : 0) - (a.running ? 1 : 0) || a.start - b.start || a.end - b.end);
  const r1 = (x) => Math.round(x * 10) / 10;
  let at = Number(l.percent);
  let next = 0;
  let nextSoon = 0;
  let cross = null;
  const pieces = [];
  const kinds = { team: 0, planned: 0, repeat: 0 };
  for (const w of work) {
    if (!(w.add > 0)) continue;
    // The part of it that runs before the reset, by its minutes; the rest is the next window's (H199: and what ran
    // before a later window's start was an earlier window's).
    const span = Math.max(1, w.end - w.start);
    const part = (a, b) => Math.max(0, Math.min(b, w.end) - Math.max(a, w.start)) / span;
    const frac = w.end <= lo ? 0 : reset === null || w.end <= reset ? (w.start >= lo ? 1 : part(lo, w.end)) : part(lo, reset);
    const here = w.add * frac;
    next += reset === null ? 0 : w.add * (w.start >= reset ? 1 : part(reset, w.end));
    // H199: of that, what falls in the 5-hour window right after the reset (the rest lands later still).
    if (key === 'five' && reset !== null) nextSoon += w.add * part(reset, reset + LINES.five.windowMs / 1000);
    if (here < 0.05) continue;
    const start = at;
    at += here;
    const lands = reset === null ? w.end : Math.min(w.end, reset);
    pieces.push({ kind: w.kind, what: w.what, add: r1(here), from: r1(start), to: r1(at), start: w.start, lands, priority: w.priority, waits: !!w.waits });
    kinds[w.kind] += here;
    const sl = stopLine(l, lines, new Date(1000 * (reset === null ? lands : Math.min(lands, reset - 60))));
    if (!cross && sl && r1(at) > sl.line) cross = { what: w.what, at: lands, pct: r1(at), line: sl.line };
  }
  const line = stopLine(l, lines, from !== null && from * 1000 > now.getTime() ? new Date(from * 1000) : now);
  // Where a moving line will stand when the last piece lands (before the reset), so the bar shows whether it fits then.
  // H177: the time it's read at is a landing (the 5-hour bar: before its reset); a fixed line gets none.
  const readAt = (last) => (last ? (reset === null ? last : Math.min(last, reset - 60)) : null);
  const lineAt = (when) => (when && line?.moving ? stopLine(l, lines, new Date(1000 * when)) : null);
  // H181: the purple line counts only the one-off work (the team's and planned once), so a repeating item every
  // night doesn't push it to the end; the green one counts everything, repeating included, and only when it's later.
  const oneOff = pieces.filter((p) => p.kind !== 'repeat');
  const thenLands = oneOff.length ? oneOff[oneOff.length - 1].lands : null;
  const thenAt = readAt(thenLands);
  const then = lineAt(thenAt);
  const allLands = pieces.length ? pieces[pieces.length - 1].lands : null;
  const allAt = readAt(allLands);
  const all = allAt !== thenAt ? lineAt(allAt) : null;
  const moves = (x) => !!x && x.line !== line.line;
  for (const k of Object.keys(kinds)) kinds[k] = r1(kinds[k]);
  return {
    key, now: Number(l.percent), to: r1(at), lands: allLands, reset,
    line: line ? line.line : null, moving: !!line?.moving,
    lineThen: moves(then) ? then.line : null, thenAt: moves(then) ? thenAt : null, thenLands: moves(then) ? thenLands : null,
    lineAll: moves(all) ? all.line : null, allAt: moves(all) ? allAt : null, allLands: moves(all) ? allLands : null,
    pieces, kinds, next: r1(next), nextSoon: r1(nextSoon), untimed, cross,
  };
}

/** H176: the landing in plain words, under its bar. `clock` turns epoch seconds into a time (with the day when it isn't today). */
export function landingWords(L, clock) {
  if (!L || (!L.pieces.length && !L.next && !L.untimed)) return '';
  const five = L.key === 'five';
  const s = [];
  if (L.pieces.length) {
    const parts = Object.entries(L.kinds).filter(([, v]) => v > 0).map(([k, v]) => `${LAND_KINDS[k]} ${v}%`);
    s.push(`If the work goes as estimated, it lands at ${L.to}% around ${clock(L.lands)} (${parts.join(', ')})${five && L.reset ? `, before its reset at ${clock(L.reset)}` : ''}.`);
    // H177: where the moving stop line will be by then, the dotted line on the bar; H181: by when the one-off work lands
    // (the green line, with the repeating work, says nothing here: a tap or the mouse on it shows it).
    if (L.lineThen !== null && L.lineThen !== undefined) {
      s.push(L.thenLands && L.thenLands !== L.lands
        ? `The one-off work lands around ${clock(L.thenLands)}; by then the stop line will be at ${L.lineThen}% (the dotted line).`
        : `By then the stop line will be at ${L.lineThen}% (the dotted line).`);
    }
    if (L.cross) s.push(`That goes past the stop line: around ${clock(L.cross.at)}, ${L.cross.what} takes it to ${L.cross.pct}% while the line is at ${L.cross.line}%.`);
    else if (L.line !== null) s.push(L.moving ? 'It stays under the stop line as the line climbs.' : 'It stays under the stop line.');
  } else if (five && L.next) s.push('Nothing lands before its reset.');
  // H199: the 5-hour bar says which part lands in the very next window and which part only later (the unfolded windows show where).
  const soon = L.nextSoon ?? L.next;
  if (L.next && five && soon < L.next - 0.05) {
    const later = Math.round((L.next - soon) * 10) / 10;
    s.push(soon >= 0.05
      ? `${soon}% more lands after the reset, in the next 5-hour window, and ${later}% later than that.`
      : `${L.next}% more lands later, after the next 5-hour window.`);
  } else if (L.next) s.push(`${L.next}% more lands after ${five ? 'the reset, in the next 5-hour window' : 'the weekly reset, in the next week'}.`);
  if (L.untimed) s.push(`${L.untimed === 1 ? 'One more piece of work has' : `${L.untimed} more pieces of work have`} no time yet, so ${L.untimed === 1 ? "it isn't" : "they aren't"} on the bar.`);
  return s.join(' ');
}

/**
 * H199 (17 October 2026, call at 14:45): "maybe we can have for fun the 5 hour session have an unfolding button so you
 * can see 4 more (making it 25 hours aka 1 day), and then you can see when we have things scheduled out and how much of
 * the estimated usage it will take", and on the same day: "because i am confused why it would be stuck tonight". The
 * 5-hour windows after the current one, back to back from its reset, each with the work landing in it the same way as
 * the current bar (landing, from 0%), its reset, its moving stop line and what waits for that line in it. A repeating
 * item every day is counted again a day later when that still falls inside. (A real window starts with the first use
 * after a reset, so with nothing running the times can shift.)
 * @returns {Array<{ n: number, from: number, reset: number, L: ReturnType<typeof landing>, lineFrom: number | null,
 *   lineTo: number | null, waits: Array<{ what: string, start: number }> }>}
 */
export const WINDOWS_AHEAD = 4;
export function windowsAhead(l, lines, E, now = new Date(), count = WINDOWS_AHEAD) {
  if (lineKey(l?.label) !== 'five' || !l.resetsAt || !E) return [];
  const win = LINES.five.windowMs / 1000;
  const first = Math.round(new Date(l.resetsAt).getTime() / 60000) * 60;
  if (!Number.isFinite(first)) return [];
  const end = first + count * win;
  const items = { ...(E.items ?? {}) };
  for (const [n, e] of Object.entries(E.items ?? {})) {
    if (e.every === 'day' && e.start && e.eta && e.start + 86400 < end) {
      items[`${n}+1`] = { ...e, what: `Planned item ${n} (the day after)`, start: e.start + 86400, eta: e.eta + 86400, usage_wait: false };
    }
  }
  const E2 = { ...E, items };
  const out = [];
  for (let k = 0; k < count; k++) {
    const from = first + k * win;
    const reset = from + win;
    const lw = { label: l.label, percent: 0, resetsAt: new Date(reset * 1000).toISOString() };
    const L = landing(lw, lines, E2, now, { from });
    const a = stopLine(lw, lines, new Date(from * 1000));
    const b = stopLine(lw, lines, new Date((reset - 60) * 1000));
    const waits = L ? L.pieces.filter((p) => p.waits && p.start >= from && p.start < reset).map((p) => ({ what: p.what, start: p.start })) : [];
    out.push({ n: k + 1, from, reset, L, lineFrom: a ? a.line : null, lineTo: b ? b.line : null, moving: !!a?.moving, waits });
  }
  return out;
}

/** H199: one later window in plain words, under its bar. */
export function windowWords(w, clock) {
  const L = w.L;
  const s = [];
  if (w.moving && w.lineFrom !== null) s.push(`The stop line climbs from ${w.lineFrom}% at ${clock(w.from)} to ${w.lineTo}% at ${clock(w.reset)}.`);
  else if (w.lineFrom !== null) s.push(`The stop line stays at ${w.lineFrom}%.`);
  if (!L || !L.pieces.length) {
    s.push('Nothing lands in this window.');
    return s.join(' ');
  }
  const parts = Object.entries(L.kinds).filter(([, v]) => v > 0).map(([k, v]) => `${LAND_KINDS[k]} ${v}%`);
  s.push(`If the work goes as estimated, it uses about ${L.to}% here, done around ${clock(L.lands)} (${parts.join(', ')}).`);
  if (L.lineThen !== null && L.lineThen !== undefined) s.push(`By then the stop line will be at ${L.lineThen}% (the dotted line).`);
  if (w.waits.length) {
    const names = w.waits.map((x) => `${x.what} around ${clock(x.start)}`);
    s.push(`Waits for the stop line to climb, so it starts later than it could: ${names.join(', ')}.`);
  }
  if (L.cross) s.push(`That goes past the stop line: around ${clock(L.cross.at)}, ${L.cross.what} takes it to ${L.cross.pct}% while the line is at ${L.cross.line}%.`);
  return s.join(' ');
}
