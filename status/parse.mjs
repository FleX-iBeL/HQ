/**
 * Reads the status out of HQ/roadmap.md. The roadmap is the only place the status is written;
 * the status page (tools/status/index.html) draws what this returns and stores nothing itself.
 *
 * The block at the top of HQ/roadmap.md, up to the first line with only "---":
 *   # <emoji> STATE IN CAPITALS
 *   ## Now: … (or Next: …)
 *   **Label:** one or two short lines
 *   | Phase X | step ✅ | step 🔨 | step ⬜ |
 *   - 14:05 what was done      (the log, newest first, at most eight lines)
 *   *Updated … *
 * Below it, each "## Phase X · title → version" has a table whose rows start with
 * "| ✅ | D1 Name | …"; the other columns (what you get, backlog, model) and the text under the
 * table are kept as they are written, for the page to show when a phase is opened.
 *
 * Anywhere in the file, "**Usage limit: 70%**" is the share of a plan limit at which work stops; the three
 * stop lines' settings (moving or fixed, H91) are read by lineSettings in usage.mjs.
 */

import { lineSettings } from './usage.mjs';

// H183: 🔁 marks the team's repeating work (Phase Maintenance): never open, never done.
const MARKS = { '✅': 'done', '🔨': 'doing', '⬜': 'todo', '❓': 'ask', '🔁': 'repeat' };
const STATES = ['BUILDING', 'TESTING', 'RELEASING', 'WAITING', 'DONE', 'STOPPED'];

const plain = (text) =>
  text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*`]/g, '')
    .trim();

/** @param {string} markdown */
export function parseRoadmap(markdown) {
  const lines = markdown.split('\n');
  const end = lines.findIndex((l) => l.trim() === '---');
  const block = end < 0 ? [] : lines.slice(0, end);
  const problems = [];

  const h1 = block.find((l) => l.startsWith('# '));
  const title = h1 ? h1.slice(2).trim() : '';
  const words = title
    .replace(/[^A-Za-z ]/g, ' ')
    .trim()
    .toUpperCase();
  const state = STATES.find((s) => words.includes(s)) ?? null;
  if (!h1) problems.push('The first heading (the state) is missing.');
  else if (!state) problems.push(`The state "${title}" is not one of ${STATES.join(', ')}.`);

  const h2 = block.find((l) => l.startsWith('## '));
  if (!h2) problems.push('The second heading (the step) is missing.');

  const notes = block
    .filter((l) => /^\*\*[^*]+:\*\*/.test(l.trim()))
    .map((l) => {
      const m = /^\*\*([^*]+):\*\*\s*(.*)$/.exec(l.trim());
      return { label: m[1], text: plain(m[2]) };
    });

  const row = block.find((l) => /^\|\s*Phase /.test(l));
  let current = null;
  if (row) {
    const cells = row
      .split('|')
      .slice(1, -1)
      .map((c) => c.trim());
    current = {
      phase: cells[0].replace(/^Phase\s+/, ''),
      steps: cells.slice(1).map((c) => {
        const mark = Object.keys(MARKS).find((k) => c.includes(k));
        return { name: c.replace(mark ?? '', '').trim(), status: mark ? MARKS[mark] : 'todo' };
      }),
    };
  } else problems.push('The one-row table of the current phase is missing.');

  // The log: "- 14:05 what was done", newest first.
  const log = block
    .map((l) => /^-\s+(\d{1,2}:\d{2})\s+(.+)$/.exec(l.trim()))
    .filter(Boolean)
    .map((m) => ({ time: m[1], text: plain(m[2]) }));

  const updated = block.find((l) => /^\*Updated/.test(l.trim()));

  const phases = [];
  let phase = null;
  let columns = [];
  let underHeading = false;
  for (const line of lines.slice(Math.max(0, end))) {
    const head = /^## Phase (\S+) · (.+?)(?:\s+→\s+(.+))?$/.exec(line);
    if (head) {
      phase = {
        id: head[1],
        title: plain(head[2]),
        target: head[3] ? plain(head[3]) : '',
        steps: [],
        body: [],
      };
      columns = [];
      phases.push(phase);
      continue;
    }
    if (/^## /.test(line)) phase = null;
    if (!phase) continue;
    const cells = line.startsWith('|')
      ? line
          .split('|')
          .slice(1, -1)
          .map((c) => c.trim())
      : null;
    // The heading row of the steps table names the columns: "| | Step | What you get | … |".
    if (cells && cells[0] === '' && cells[1] === 'Step') {
      columns = cells;
      underHeading = true;
      continue;
    }
    // The rule under that heading row.
    if (underHeading) {
      underHeading = false;
      if (cells?.every((c) => /^-+$/.test(c))) continue;
    }
    if (cells && cells[0] in MARKS && cells.length > 1) {
      const details = [];
      for (let i = 2; i < cells.length; i++) {
        if (cells[i] && cells[i] !== '—') details.push({ label: columns[i] ?? '', text: cells[i] });
      }
      phase.steps.push({ name: plain(cells[1]), status: MARKS[cells[0]], details });
      continue;
    }
    phase.body.push(line);
  }
  for (const p of phases) {
    while (p.body.length && !p.body[0].trim()) p.body.shift();
    while (p.body.length && /^(-{3,})?\s*$/.test(p.body[p.body.length - 1])) p.body.pop();
  }
  if (phases.length === 0) problems.push('No "## Phase …" sections were found.');

  // Phase L: the queue of jobs agreed on a call, under "## The queue" (kept by routine/jobs.py).
  const queue = { on: true, jobs: [] };
  const qStart = lines.findIndex((l) => l.trim() === '## The queue');
  if (qStart >= 0) {
    for (const line of lines.slice(qStart + 1)) {
      if (/^#{1,2} /.test(line)) break;
      if (/^\*\*Routine:\*\*/.test(line)) queue.on = !/off/i.test(line);
      const m = /^- Job (\d+) · (.+?) · agreed (\S+ \S+) · (.*)$/.exec(line);
      if (m) {
        // H283: notes for a job while it runs or waits sit at the end of its line: " ⟪note DATE TIME[ · read HH:MM]⟫ TEXT".
        // H286: and what it says it's doing now, " ⟪now HH:MM⟫ TEXT", and its redone estimate, " ⟪redone HH:MM · N min · was M min⟫ WHY".
        const first = m[4].search(/ ⟪(?:note|now|redone) /);
        const notes = [];
        let now = null;
        let redone = null;
        if (first >= 0) {
          for (const x of m[4].slice(first).matchAll(/ ⟪(note|now|redone) ([^⟫]*)⟫ (.*?)(?= ⟪(?:note|now|redone) |$)/g)) {
            if (x[1] === 'note') {
              const h = /^(\S+ \S+?)(?: · read (\S+))?$/.exec(x[2]);
              if (h) notes.push({ at: h[1], read: h[2] ?? null, text: plain(x[3]) });
            } else if (x[1] === 'now') now = { at: x[2], text: plain(x[3]) };
            else {
              const r = /^(\d\d:\d\d) · (\d+) min · was (\d+) min$/.exec(x[2]);
              if (r) redone = { at: r[1], est: Number(r[2]), was: Number(r[3]), why: plain(x[3]) };
            }
          }
        }
        queue.jobs.push({ n: Number(m[1]), state: m[2], agreed: m[3], text: plain(first < 0 ? m[4] : m[4].slice(0, first)), notes, now, redone });
      }
    }
    // H39: the waiting jobs (ready or held) run in the order they stand on the list; number their place.
    let place = 0;
    for (const j of queue.jobs) if (/^(ready|held)/.test(j.state)) j.place = ++place;
  }

  // H43: the schedule, work planned ahead for a day and time, under "## The schedule" (kept by routine/schedule.py).
  const sStart = lines.findIndex((l) => l.trim() === '## The schedule');
  const schedule = sStart >= 0 ? { items: [] } : null;
  if (sStart >= 0) {
    for (const line of lines.slice(sStart + 1)) {
      if (/^#{1,2} /.test(line)) break;
      const m = /^- Item (\d+) · (.+?) · at (\S+ \S+) · added (\S+ \S+) · (.*)$/.exec(line);
      if (m) schedule.items.push({ n: Number(m[1]), state: m[2], at: m[3], added: m[4], text: plain(m[5]) });
    }
  }

  const limit = /\*\*Usage limit:\s*(\d{1,3})\s*%/.exec(markdown);
  // HQ: a flat stop line for the weekly limits, instead of spreading them over the week.
  const weekly = /\*\*Weekly limit:\s*(\d{1,3})\s*%/.exec(markdown);
  // H87: the 5-hour line moves through the session ("**5-hour line: moving**", also when the line is
  // missing: HQ's default) or stays at the usage limit's fixed number ("**5-hour line: fixed**").
  const five = /\*\*5-hour line:\s*(moving|fixed)\b/i.exec(markdown);

  return {
    usageLimit: limit ? Number(limit[1]) : null,
    weeklyLimit: weekly ? Number(weekly[1]) : null,
    usageMoving: five ? five[1].toLowerCase() === 'moving' : true,
    // H91: the three stop lines (5-hour, weekly all models, weekly Fable), each moving or fixed.
    usageLines: lineSettings(markdown),
    state,
    title,
    headline: h2 ? plain(h2.slice(3)) : '',
    notes,
    current,
    log,
    updated: updated ? plain(updated) : '',
    phases,
    queue,
    schedule,
    problems,
  };
}
