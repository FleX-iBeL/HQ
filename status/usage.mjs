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
 * F107: does the reading carry a 5-hour window? A plan without one (a verified Ultra) has no 5-hour limit, so nothing is shown or
 * gated on it; it all comes back with a reading that has one. No reading, or one that failed, isn't a plan without a limit.
 * A kept number is an old one. usagecost.five_on says the same.
 */
export function hasFive(reading) {
  if (!reading?.readable) return true;
  return (reading.limits ?? []).some((l) => lineKey(l.label) === 'five' && !l.kept);
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
 * F113: has this limit's window reset since the reading was taken? Only when its reset time parses and the reading was taken
 * before it: a reset time that can't be read is held, the same as one that's missing, so it never opens room by itself.
 */
export function windowPassed(l, reading, now = new Date()) {
  const reset = Date.parse(l?.resetsAt ?? '');
  const checked = Date.parse(reading?.checkedAt ?? '');
  return Number.isFinite(reset) && Number.isFinite(checked) && checked < reset && reset <= now.getTime();
}

/** Why a saved reading is too old to go by (over 30 minutes), in words, or null. */
export const STALE_MIN = 30;
export function staleWords(reading, now = new Date()) {
  if (!reading?.readable) return null;  // no reading at all has its own words in the verdict
  const at = Date.parse(reading.checkedAt ?? '');
  const min = Number.isFinite(at) ? Math.floor((now.getTime() - at) / 60000) : null;
  if (min !== null && min <= STALE_MIN) return null;
  const age = min === null ? 'of no known age' : min >= 2880 ? `${Math.floor(min / 1440)} days old` : min >= 120 ? `${Math.floor(min / 60)} hours old` : `${min} minutes old`;
  return `The usage reading is ${age}, older than ${STALE_MIN} minutes.`;
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
