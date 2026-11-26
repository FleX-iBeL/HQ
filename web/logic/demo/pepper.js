// Pepper's made-up content, as the prototypes show it: the map, check-ins and the games.
// The shaping for the template is in ../pepper.js; swap these for real data there.

export const card = {
  kicker: 'Due today · 17:00', headline: 'Weekly check-in', sub: 'About 15 minutes, whenever you’re ready',
  line: 'Let’s look back at the week first. What went better than you expected?'
};

// The rows in her space: [label, value, screen or [screen, extra state]]
export const rows = [
  ['The map', 'This year 7 of 12', 'map'], ['The six-week game', 'Day 12, on track', 'games'], ['Check-ins', 'One due', 'checkin'],
  ['Coaching line', '1 new', ['chat', { chatAgent: 'pepper' }]], ['Her notes', '3', 'notes'], ['Past calls', 'Last Tuesday', 'pastCalls']
];
export const homeLines = [{ t: 'The game: day 12 of 42, on track', c: '#0f172a', w: '400' }, { t: 'The map: this year, 7 of 12 answered', c: '#0f172a', w: '400' }];

// The map's layers: [name, state, percent]
export const layers = [['The life you want', 'Done', 100], ['This year', '7 of 12', 58], ['The six-week game', 'In progress', 30], ['The ideal week', 'Not started', 0], ['This week', 'Not started', 0], ['Looking back', 'Not started', 0]];
// A layer's checklist: [question, mark, mark colour, note]
export const checklist = [['What does a great year look like, in one sentence?', 'Answered', '#15803d', 'Steady and healthy, with the Japan trip booked.'], ['Which three things matter most?', 'Answered', '#15803d', 'Health, the trip, HQ.'], ['What will you stop doing?', 'Parked', '#a16207', 'Come back to it after the game.'], ['What does a good month look like?', 'Later', '#475569', ''], ['Who do you want more time with?', 'Open', '#64748b', '']];
export const layerTitle = 'This year';

// The game: two weeks of marks (done, x, none, today, future) and their day letters
export const marks = ['done', 'done', 'x', 'done', 'done', 'none', 'none', 'done', 'done', 'done', 'x', 'done', 'today', 'future'];
export const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S', 'M', 'T', 'W', 'T', 'F', 'S', 'S'];
export const todayIndex = 12;
export const pages = 14;
export const pastGames = [{ id: 'autumn', name: 'Autumn reset', meta: 'September to October · won' }, { id: 'summer', name: 'Summer basics', meta: 'July to August · not won this time' }];
export const currentGame = 'current';
export const feelings = ['Great', 'Fine', 'Tired', 'Low'];
