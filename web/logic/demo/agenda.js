// Made-up agenda content: today across the three, the agenda, an appointment, travel, the kinds of time, the calendars, as the prototypes show it.
// The shaping for the template is in ../agenda.js; swap these for real data there.

// Donna's card on home and in her space (her next appointment).
export const card = {
  kicker: 'Next · in 40 minutes', headline: 'Dentist at 15:00', sub: 'Leave at 14:40 · 18 minutes by bike',
  line: 'Sure. I moved the gym to 20:00 and I’ll text you at 14:30 to leave.'
};

// Her space's row for this area: [label, value, screen or [screen, extra state], value colour, value weight]
export const rows = { agenda: ['Agenda', '4 today', 'agenda'] };

export const dentist = { title: 'Dentist', when: 'Today · 15:00 to 15:45', where: 'Dental practice · Personal calendar · Admin essentials' };

// Today, across the three: who is the agent it belongs to.
export const today = [
  { isItem: true, time: '12:30', title: 'Lunch', past: true },
  { isNow: true },
  { isItem: true, time: '14:40', title: 'Leave', who: 'donna' },
  { isItem: true, time: '15:00', title: 'Dentist', who: 'donna' },
  { isItem: true, time: '17:00', title: 'Check-in', who: 'pepper' },
  { isItem: true, time: '20:00', title: 'Gym', who: 'donna' }
];
export const longTitles = { Lunch: 'Lunch with Alex', Leave: 'Leave for the dentist', 'Check-in': 'Weekly check-in' };

// The kinds of time and their colours.
export const kinds = { admin: '#dc2626', ceo: '#0d9488', money: '#eab308', client: '#16a34a', cup: '#9333ea', none: '#cbd5e1' };
export const kindNames = [['money', 'Money makers'], ['client', 'Client delivery'], ['admin', 'Admin essentials'], ['ceo', 'CEO time'], ['cup', 'Cup fillers'], ['none', 'Not set yet']];

// The agenda: per day [time, title, kind, past, where]
export const agenda = [
  { day: 'Today', items: [['09:30', 'Team standup', 'client', true], ['12:30', 'Lunch with Alex', 'cup', true], ['15:00', 'Dentist', 'admin', false, dentist.where], ['20:00', 'Gym', 'cup']] },
  { day: 'Tomorrow', items: [['10:00', 'Call with the accountant', 'admin'], ['Day', 'Sam’s birthday', 'none']] },
  { day: 'Saturday 28', items: [['11:00', 'Market with Alex', 'cup'], ['14:00', 'Plan the Japan trip', 'ceo']] }
];
export const calendars = [['personal', 'Personal'], ['work', 'Work'], ['birthdays', 'Birthdays']];
export const travel = { bike: 'Leave at 14:40 · 18 minutes by bike', transit: 'Tram 5 at 14:31 from the stop around the corner · 22 minutes', car: 'Leave at 14:45 · 12 minutes · parking nearby' };
export const travelWays = [['bike', 'Bike'], ['transit', 'Public transport'], ['car', 'Car']];
export const apptNotes = ['Ask about the night guard', 'Bring the insurance card'];
