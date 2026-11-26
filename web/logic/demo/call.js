// The made-up call, as the prototypes show it: what was said so far per agent, and the
// yes-or-no Donna asks. Lines are ['h' her, 'm' me, 'w' her while working, text].
// The shaping is in ../call.js; swap these for real data there.

// The call so far, per agent; Donna's asks a yes or no, with the line that follows each.
export const callLines = {
  donna: [['m', 'Can you move the gym to 20:00?'], ['w', 'Let me look…'], ['h', 'Twenty hundred is free, nothing else that evening.']],
  pepper: [['m', 'Can we do the check-in now?'], ['h', 'Of course. Let’s look back at the week first.'], ['h', 'What went better than you expected?']],
  mp: [['m', 'How’s everything running?'], ['h', 'Everything is running. One hand-over is waiting for you.']]
};
export const askOf = 'donna';
export const answers = { yes: [['m', 'Yes.'], ['h', 'Done. The gym is at 20:00 now.']], no: [['m', 'No.'], ['h', 'Fine, I’ll leave it at 19:00.']] };

