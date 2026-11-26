// Made-up texts, as the prototypes show them: the chat with each agent, the list of the
// three chats, past calls and one past call's log, a failed text.
// Lines are ['h' her, 'm' me, text]. The shaping is in ../texts.js; swap these for real data there.

// Donna's space rows for this area: [label, value, screen or [screen, extra state]]
export const rows = { pastCalls: ['Past calls', 'Last today', 'pastCalls'], texts: ['Texts', '2 today', ['chat', { chatAgent: 'donna' }]] };

export const texts = {
  donna: [['h', 'Morning. Four things today and two I’m still nudging you on.'], ['m', 'Can you move the gym to 20:00?'], ['h', 'Done. The gym is at 20:00 now.'], ['h', 'Leave at 14:40 for the dentist. I’ll text you at 14:30.']],
  pepper: [['h', 'Your weekly check-in is ready whenever you are. Fifteen minutes.'], ['m', 'After the dentist?'], ['h', 'Perfect. I’ll keep 17:00 for us.']],
  mp: [['h', 'Hand-over ready: calendar clean-up. Everything’s running.'], ['m', 'Thanks, I’ll pick it up tonight.'], ['h', 'Noted.']]
};
export const lastText = { donna: '14:02', pepper: '09:00', mp: 'Yesterday' };
export const unread = { donna: 2, pepper: 1, mp: 0 };

// Past calls per agent: per day [time, about, lines]
export const pastCalls = {
  donna: [{ day: 'Today', items: [['09:12', 'Moving the gym', 14]] }, { day: 'Tuesday', items: [['08:05', 'The week ahead', 9]] }],
  pepper: [{ day: 'Tuesday', items: [['18:40', 'The year, part two', 52]] }, { day: 'Last week', items: [['19:10', 'Setting up the game', 61]] }],
  mp: [{ day: 'Monday', items: [['21:10', 'What’s next for HQ', 23]] }]
};
export const pastCallLog = [['m', 'Can you move the gym to 20:00?'], ['h', 'Sure. Twenty hundred works, nothing else that evening.'], ['m', 'And remind me to leave for the dentist.'], ['h', 'I’ll text you at 14:30. Leave at 14:40.']];

// One failed text in Donna's chat, until retried.
export const failedIn = 'donna';
