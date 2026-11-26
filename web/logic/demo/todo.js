// Made-up to-do content: the four boxes, the lists behind them, an item, planning and repeating, groceries, as the prototypes show it.
// The shaping for the template is in ../todo.js; swap these for real data there.

export const rows = { todo: ['To-do', '12 open', 'todo'] };
export const homeLines = { todo: { t: '12 to-dos open', c: '#0f172a', w: '400' } };

// To-do: the four boxes on the to-do screen (count, colours, the first few items)
export const boxCards = [
  { name: 'Urgent and important', count: 2, cc: '#b42318', shadow: '0 0 0 1px #e2e8f0 inset', op: 1, items: ['Renew your passport', 'Pay the parking fine'] },
  { name: 'Important, not urgent', count: 28, cc: '#0f172a', shadow: '0 0 0 2px #0f172a inset', op: 1, items: ['Plan the Japan trip', 'Book the yearly check-up'] },
  { name: 'Urgent, not important', count: 3, cc: '#0f172a', shadow: '0 0 0 1px #e2e8f0 inset', op: 1, items: ['Reply to the building', 'Return the parcel'] },
  { name: 'Neither', count: 2, cc: '#0f172a', shadow: '0 0 0 1px #e2e8f0 inset', op: 0.6, items: ['Sort the photo library'] }
];
export const firstItem = { box: 'Urgent and important', title: 'Renew your passport' };
export const boxes = {
  'Urgent and important': ['Renew your passport', 'Pay the parking fine'],
  'Important, not urgent': ['Plan the Japan trip', 'Book the yearly check-up', 'Write the vision page', 'Sort the pension papers', 'Learn the surf basics', 'Call grandma on Sunday', 'Back up the photo library', 'Pick a new bank', 'Read Deep Work', 'Plan the garden', 'Fix the bike light', 'Update the CV', 'Book the boiler service', 'Choose a running plan', 'Clear out the attic', 'Meal-prep on Sundays', 'Set up the home office', 'Renew the gym card', 'Plan Sam’s surprise', 'Write to the old team', 'Price a new laptop', 'Try the climbing hall', 'Learn ten Japanese phrases', 'Frame the posters', 'Make a will', 'Plan the winter trip', 'Sell the old camera', 'Start a morning journal'],
  'Urgent, not important': ['Reply to the building', 'Return the parcel', 'Confirm the dentist'],
  'Neither': ['Sort the photo library', 'Unsubscribe from newsletters']
};
export const done = ['Book the dentist', 'Send the invoice', 'Buy a birthday card', 'Fix the doorbell', 'Renew the bike lock', 'Call the insurer'];
export const letGo = ['Learn the guitar', 'Redo the kitchen tiles'];
export const planned = { 'Plan the Japan trip': 'Planned Saturday 14:00 · CEO time', 'Book the yearly check-up': 'Planned tomorrow 10:00 · Admin', 'Write the vision page': 'Planned Monday 09:00 · CEO time', 'Call grandma on Sunday': 'Planned Sunday 11:00 · Cup fillers', 'Pick a new bank': 'Planned Tuesday 16:00 · Admin', 'Fix the bike light': 'Planned Wednesday 10:00 · gone by' };
export const deadlines = { 'Renew your passport': 'Friday', 'Pay the parking fine': 'Friday', 'Sort the pension papers': 'Monday', 'Return the parcel': 'Saturday' };
export const planBlocks = [['Today', '16:00 to 17:00', 'Admin essentials'], ['Tomorrow', '10:00 to 12:00', 'CEO time'], ['Tomorrow', '14:00 to 15:00', 'Money makers'], ['Monday', '09:00 to 11:00', 'CEO time']];
export const repeats = ['Doesn’t repeat', 'Every week', 'Every month', 'Every quarter', 'Every year'];
export const moveTo = ['Urgent and important', 'Important, not urgent', 'Urgent, not important', 'Neither', 'Commitments to others', 'Groceries', 'Wishlist'];

// Groceries (a tab of the lists screen)
export const groceries = ['Oat milk', 'Eggs', 'Spinach', 'Coffee beans', 'Lemons', 'Rice'];
export const groceriesTicked = [['Bread', 'last Tuesday'], ['Butter', '2 weeks ago'], ['Tomatoes', 'last week']];
