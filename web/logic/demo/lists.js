// Made-up bucketlist and wishlist content: the items, an item's sub-items and links, as the prototypes show it.
// The shaping for the template is in ../lists.js; swap these for real data there.

export const rows = { lists: ['Lists', 'Groceries, bucket, wish', 'lists'] };

export const bucket = [
  { id: 'japan', name: 'Trip to Japan', meta: '€3,020 · spring 2027 · 3 inside' },
  { id: 'surf', name: 'Learn to surf', meta: '€450 · this summer · 40 hours' },
  { id: 'half', name: 'Run a half marathon', meta: 'Tap to give it a price, a goal, links, notes' }
];
export const wish = [{ id: 'espresso', name: 'Espresso machine', meta: '€699 once · score 3 of 5' }, { id: 'shoes', name: 'New running shoes', meta: '€160 once · score 4 of 5' }];
// What a new bucket or wish item says until it has more (the prototypes show the same example
// item for every bucket item; bucketId in state says which one is open).
export const newMeta = { bucket: 'Tap to give it a price, a goal, links, notes', wish: 'No price yet' };
export const subItems = [['flights', 'Flights', '€1,400 once'], ['ryokan', 'Ryokan, 3 nights', '€1,200 once'], ['jr', 'JR pass', '€420 once']];
export const links = ['japan-rail.example', 'ryokan-guide.example'];

export const titles = { bucketItem: 'Trip to Japan', subItem: 'Ryokan, 3 nights' };
