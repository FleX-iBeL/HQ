// The made-up content of settings, weather and the tutorial, as the prototypes show it.
// The shaping for the template is in ../settings.js; swap these for real data there.

// What HQ helps you with: [id, name, line, needs]
export const features = [['calendar', 'Calendar', 'Your days, two weeks ahead', null], ['todo', 'To-do', 'Your lists, the Eisenhower way', null], ['texts', 'Texts', 'The three can text you', null], ['weather', 'Weather', 'The chip on home and rain alerts', null], ['travel', 'Travel', 'When to leave, by bike or public transport', 'calendar'], ['driving', 'Driving', 'Drive times too, with a maps key', 'travel'], ['mail', 'Mail check', 'Donna flags the very important ones', null], ['notes', 'Notes', 'Quick notes the next call can read', null], ['coaching', 'Life coaching', 'Pepper’s map, check-ins and the game', null], ['team', 'The team’s work', 'Moneypenny’s hand-overs and Status', null]];
export const featuresOn = { calendar: true, todo: true, texts: true, weather: true, travel: true, driving: false, mail: true, notes: true, coaching: true, team: true };

export const voices = { donna: ['Warm, quick', 'Bright, clear', 'Low, steady'], pepper: ['Calm, unhurried', 'Soft, close', 'Warm, low'], mp: ['Cool, few words', 'Crisp, dry', 'Even, quiet'] };
export const voicesPicked = { donna: 'Warm, quick', pepper: 'Calm, unhurried', mp: 'Cool, few words' };

// Weather: the coming hours [time, degrees, chance of rain]
export const hours = [['15:00', '8°', ''], ['16:00', '7°', '70%'], ['17:00', '6°', '80%'], ['18:00', '6°', '40%'], ['19:00', '5°', '']];
export const weatherTitle = 'Weather · Amsterdam';

// The tutorial: its pieces [number, title, done] and the steps of the home tour [title, text]
export const pieces = [['1', 'Calling one of the three', 'Done'], ['2', 'Texting', ''], ['3', 'Today on home', ''], ['4', 'Donna’s space', ''], ['5', 'Pepper’s map', ''], ['6', 'Moneypenny and Status', '']];
export const tour = [['These are your three', 'Tap one to go into her space. Hold a card to call her straight away.'], ['Today, in order', 'Everything with a time, from all three. Tap one to open it.'], ['Text or call from here', 'Pick who first, then type, or tap the phone to call.']];
