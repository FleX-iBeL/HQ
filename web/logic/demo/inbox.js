// Made-up inbox content: mail on home, his quick notes, her notes per agent, nudges, what she keeps an eye out for, cleared notes, as the prototypes show it.
// The shaping for the template is in ../inbox.js; swap these for real data there.

export const rows = { mail: ['Mail', '1 very important', 'mail', '#b42318', '600'], notes: ['Notes', 'Yours and hers', 'notes'] };
// Her lines on home: the nudges line depends on which nudges are done (see ../inbox.js).
export const homeLines = { mail: { t: '1 very important mail', c: '#b42318', w: '600' } };
export const nudgeLines = { left: '2 nudges: passport, parking fine', none: 'No nudges left' };

export const nudges = [{ id: 'passport', title: 'Renew your passport', sub: 'She’s nudging you since Monday' }, { id: 'fine', title: 'Pay the parking fine', sub: 'Due Friday' }];
export const nudgeNotes = [['passport', 'Renew your passport', 'since Monday'], ['fine', 'Pay the parking fine', 'until Friday']];

// Notes: hers per agent (all three agents' notes live here), yours, and Donna's own kinds
export const notesBy = {
  donna: [{ t: 'You prefer appointments after 10:00', when: 'Noted 3 weeks ago' }, { t: 'Keeping an eye out: the parcel from the shoe shop, until Friday', when: 'Since Tuesday' }],
  pepper: [{ t: 'Mornings are when you feel best. Protect them.', when: 'From Tuesday’s call' }, { t: 'Your word for this year: steady', when: 'From the map' }],
  mp: [{ t: 'Birthdays show twice in two calendars', when: 'Today' }, { t: 'The Mac strip still follows the system’s dark mode', when: 'Last week' }]
};
export const myNotes = [{ t: 'Ask the landlord about the boiler', when: 'Today, 11:02' }, { t: 'Gift idea for Sam: a pasta machine', when: 'Yesterday' }];
export const eyeRows = [{ t: 'The parcel from the shoe shop', when: 'until Friday' }, { t: 'Rain on your bike rides', when: 'every day' }];
export const clearedRows = [{ t: 'Call the bike shop', when: 'Cleared Monday' }, { t: 'Buy a present for Sam', when: 'Cleared last week' }];
