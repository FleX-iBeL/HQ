// Moneypenny's made-up content, as the prototypes show it: hand-overs, status, the
// planning board, work sessions, health and updates.
// The shaping for the template is in ../mp.js; swap these for real data there.

export const card = {
  kicker: 'New hand-over', headline: 'Calendar clean-up', sub: 'Ready for you and Claude Code',
  line: 'Everything is running. One hand-over is waiting for you.'
};

// The rows in her space: [label, value, screen or [screen, extra state]]
export const rows = [['Hand-overs', '1 new', 'handovers'], ['Her notes', '2', 'notes'], ['Texts', 'Yesterday', ['chat', { chatAgent: 'mp' }]], ['Past calls', 'Last Monday', 'pastCalls']];
export const homeLines = [{ t: 'Everything is running', c: '#15803d', w: '600' }, { t: 'Usage: 34% now, 61% this week', c: '#0f172a', w: '400' }, { t: '2 things being worked on', c: '#0f172a', w: '400' }];

export const handovers = [{ name: 'Calendar clean-up', meta: 'New · today', mc: '#854d0e' }, { name: 'Bucketlist totals', meta: 'Being built', mc: '#475569' }, { name: 'Weather radar', meta: 'Built · last week', mc: '#475569' }];
export const working = [{ name: 'Calendar clean-up', state: 'Building', pct: 60 }, { name: 'Bucketlist totals', state: 'Testing', pct: 85 }];
export const planning = [
  { phase: 'Now', items: [{ t: 'Calendar clean-up', s: 'building', c: '#ca8a04' }, { t: 'Bucketlist totals', s: 'testing', c: '#ca8a04' }] },
  { phase: 'Next', items: [{ t: 'The new design', s: 'designing', c: '#94a3b8' }, { t: 'Pick a design in settings', s: 'planned', c: '#94a3b8' }] },
  { phase: 'Done', items: [{ t: 'Bucketlist sub-items', s: '26 Nov', c: '#16a34a' }, { t: 'Weather radar', s: '19 Nov', c: '#16a34a' }] }
];
export const sessions = [{ name: 'Bucketlist sub-items', state: 'Done', start: 0, w: 40, c: '#16a34a', border: 'none' }, { name: 'Bucketlist totals', state: 'Testing now', start: 35, w: 45, c: '#ca8a04', border: 'none' }, { name: 'Calendar clean-up', state: 'Next', start: 78, w: 22, c: 'transparent', border: '1.5px dashed #a16207' }];
export const routines = [{ n: 'Calendar sync', l: '2 min ago' }, { n: 'Mail check', l: '5 min ago' }, { n: 'Reminders', l: 'running' }, { n: 'Call line', l: 'ready' }, { n: 'Backups', l: '03:00 last night' }];

// Updates: the label for each step of an update (idle, busy, done), and the toast after reload
export const update = { labels: ['Update to v4.3', 'Updating: getting the new version…', 'Update done'], doneSay: 'You’re on v4.3', takesMs: 1800 };
