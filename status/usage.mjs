/**
 * The usage reading for the status page. A web page cannot ask Claude how much of the plan is
 * used; a session can (the usage tool). So a session saves what the tool said with
 * `node "Jarvis VA/status/save-usage.mjs"`, and the page shows that reading and how old it is.
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

/** A weekly limit's stop line goes up in steps: seven days, four steps a day. */
const STEPS = 28;
const STEP_MS = 6 * 60 * 60 * 1000;
/** A weekly line never stands below this, so the start of a week is not a sudden cap (copied from an earlier project, 2026-10-09). */
const FLOOR = 20;

/**
 * The stop line for one limit at a given moment, in percent. The 5-hour limit stops at the
 * roadmap's stop line. A weekly limit is spread over its week instead, all 100% of it: the week
 * before its reset is cut into 28 steps of six hours, and each step that has begun allows one
 * 28th (about 3.6%), but the line never stands below 20%. So it stands at 20% for the week's
 * first day and a half, at 21.4% from the sixth step, at 50% halfway, and at 100% in its last
 * six hours. The times follow from the reset time, so nothing has to be kept
 * anywhere.
 * @param {{ label: string, resetsAt: string | null }} l
 * @param {number | null} limit the stop line in percent; null means there is none
 * @param {Date} [now]
 * @returns {{ line: number, next: string | null } | null} next: when the line moves up again
 */
export function stopLine(l, limit, now = new Date(), weekly = null) {
  if (limit === null) return null;
  // A flat weekly stop line ("**Weekly limit: N%**" in the roadmap) wins over the spread.
  if (weekly !== null && /^weekly/i.test(l.label)) return { line: weekly, next: null };
  const reset = l.resetsAt ? new Date(l.resetsAt).getTime() : NaN;
  if (!/^weekly/i.test(l.label) || Number.isNaN(reset)) return { line: limit, next: null };
  // The reset time comes a fraction of a second early or late; the steps sit on the whole minute.
  const start = Math.round(reset / 60000) * 60000 - STEPS * STEP_MS;
  const begun = Math.min(STEPS, Math.max(1, Math.floor((now.getTime() - start) / STEP_MS) + 1));
  // The first step whose line is above the floor; until then the line stays at the floor.
  const rises = Math.max(begun + 1, Math.floor((FLOOR * STEPS) / 100) + 1);
  return {
    line: Math.max(FLOOR, Math.round(((100 * begun) / STEPS) * 10) / 10),
    next: rises <= STEPS ? new Date(start + (rises - 1) * STEP_MS).toISOString() : null,
  };
}

/**
 * Whether work may go on. It stops when any plan limit is at or above its stop line (see
 * stopLine), and when the usage could not be read. The context window is shown but never stops
 * the work.
 * @param {ReturnType<typeof usageReading> | null} reading
 * @param {number | null} limit the stop line in percent; null means there is none
 * @param {Date} [now]
 * @param {{ weeklyOnly?: boolean }} [opts] weeklyOnly: only the weekly limits count (F13: a job past the line)
 */
export function usageVerdict(reading, limit, now = new Date(), weekly = null, { weeklyOnly = false } = {}) {
  if (!reading?.readable) return { stop: true, reason: 'The usage could not be read.' };
  if (limit === null) return { stop: false, reason: '' };
  // A kept reading (F6) is old and from another session: shown, but never a stop.
  // F13: a job let past the line only skips the 5-hour line; the weekly lines always count.
  const over = reading.limits
    .filter((l) => !l.kept)
    .filter((l) => !weeklyOnly || /^weekly/i.test(l.label))
    .map((l) => ({ ...l, line: stopLine(l, limit, now, weekly).line }))
    .filter((l) => l.percent >= l.line);
  if (over.length === 0) return { stop: false, reason: '' };
  return {
    stop: true,
    reason: `${over.map((l) => `${l.label} is at ${l.percent}%, its stop line is ${l.line}%`).join('; ')}.`,
  };
}
