import {localCardImage,scryfallImageUrl} from './cardImages';
test('cached cards respect the same-origin MTG subpath, remote artwork stays unchanged',()=>{
 window.history.replaceState({},'', '/mtg/');expect(localCardImage('/card-images/a.jpg')).toBe('/mtg/card-images/a.jpg');expect(scryfallImageUrl({imageSmall:'/card-images/a.jpg'})).toBe('/mtg/card-images/a.jpg');expect(localCardImage('https://cards.scryfall.io/art.jpg')).toBe('https://cards.scryfall.io/art.jpg');window.history.replaceState({},'', '/');expect(localCardImage('/card-images/a.jpg')).toBe('/card-images/a.jpg');
});
