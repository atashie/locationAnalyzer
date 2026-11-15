for(const o of COLA.options){cSelect(o.id); const all=['c-stop','c-stats','c-track','c-axis','c-map','c-cmp'].map(k=>els[k].innerHTML).join(''); if(/undefined|NaN|null/.test(all)) console.log('BAD',o.id, all.match(/.{40}(undefined|NaN|null).{20}/));}
for(const k of ['c-booked','c-drops-sat','c-drops-sun','c-morning','c-sunlede','c-sunchoices','c-calls','c-evening','c-standfirst','c-footer']) if(/undefined|NaN/.test(els[k].innerHTML)) console.log('BAD',k);
cSelect('trains');console.log(els['c-stats'].innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' '));
console.log(els['c-axis'].innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' '), '|', els['c-daysub'].textContent);
console.log(els['c-track'].innerHTML.replace(/\s+/g,' ').slice(0,900));
console.log('hidden cola/route', els['p-cola'].hidden, els['p-route'].hidden);
console.log(els['c-evening'].innerHTML.replace(/<[^>]+>/g,'').replace(/\s+/g,' '));

for(const r of COLA.sunday.routes){sSelect(r.id); const all=els['c-sunstats'].innerHTML+els['c-map'].innerHTML; if(/undefined|NaN/.test(all)) console.log('BAD sun',r.id); console.log('SUN',r.id,els['c-sunstats'].innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' '), (els['c-map'].innerHTML.match(/rt-sun2 on/g)||[]).length);}
console.log('DROPS', (els['c-drops-sat'].innerHTML.match(/<details/g)||[]).length, (els['c-drops-sun'].innerHTML.match(/<details/g)||[]).length);
console.log(els['c-drops-sun'].innerHTML.match(/class="dn">[^<]+/g).join('\n'));
console.log(els['c-morning'].innerHTML.replace(/\s+/g,' '));
console.log(els['c-sunlede'].innerHTML.replace(/\s+/g,' '));
