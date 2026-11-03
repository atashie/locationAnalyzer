/* shared.js — G5a clickable prototypes (address-first vs describe-it).
 *
 * Plain JS, no build step. Shared by address-first.html and describe-it.html so the two
 * variants render IDENTICAL criteria cards, map, summary line and "why is this out?".
 * The pages differ only in their entry panel.
 *
 * EVERYTHING GEOGRAPHIC HERE IS FIXTURE OR SCRIPTED (see fixtures.js). Nothing is routed.
 * Travel-time text is always labelled "estimated, typical conditions". There are no
 * "rush hour" / "worst case" figures, no home counts, no neighborhood fit percentages.
 *
 * URL parameters (both variants):
 *   ?seed=1   seeded misparse: any airport criterion entered in minutes is shown in miles
 *   ?log=1    moderator log panel (timers, counters, event list)
 *   ?demo=1   pre-fills scenario S1 and computes (moderator demo / screenshots only)
 *   ?spot=id  after demo, runs "why is this out?" at a named check spot
 *
 * The pure logic (parser, gazetteer, estimates) is exported for Node tests at the bottom.
 */
(function (root, factory) {
  'use strict';
  var isNode = (typeof module === 'object' && module && module.exports);
  var F = isNode ? require('./fixtures.js') : root.G5A_FIXTURES;
  var REG = isNode ? require('./regions.js') : root.G5A_REGIONS;
  var api = factory(F, REG, root, isNode);
  if (isNode) { module.exports = api; }
  root.G5A = api;
})(typeof window !== 'undefined' ? window : globalThis, function (F, REG, root, isNode) {
  'use strict';

  // ---------------------------------------------------------------------------
  // Geometry helpers
  // ---------------------------------------------------------------------------
  function haversineMiles(a, b) {
    var R = 3958.8, toR = Math.PI / 180;
    var dLat = (b[1] - a[1]) * toR, dLng = (b[0] - a[0]) * toR;
    var s = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a[1] * toR) * Math.cos(b[1] * toR) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(s));
  }

  function pointInRing(pt, ring) {
    var x = pt[0], y = pt[1], inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      var intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
      if (intersect) { inside = !inside; }
    }
    return inside;
  }

  // A real region feature's geometry is Polygon or MultiPolygon, each polygon's first
  // ring an outer boundary and any further rings holes (standard GeoJSON winding is not
  // assumed; holes are handled by even-odd subtraction per polygon part).
  function polygonsOf(geometry) {
    if (!geometry) { return []; }
    if (geometry.type === 'Polygon') { return [geometry.coordinates]; }
    if (geometry.type === 'MultiPolygon') { return geometry.coordinates; }
    return [];
  }

  function pointInFeature(pt, feature) {
    var polys = polygonsOf(feature && feature.geometry);
    for (var i = 0; i < polys.length; i++) {
      var rings = polys[i];
      if (!pointInRing(pt, rings[0])) { continue; }
      var inHole = false;
      for (var h = 1; h < rings.length; h++) { if (pointInRing(pt, rings[h])) { inHole = true; break; } }
      if (!inHole) { return true; }
    }
    return false;
  }

  function featureBounds(feature) {
    var b = [Infinity, Infinity, -Infinity, -Infinity];
    polygonsOf(feature && feature.geometry).forEach(function (rings) {
      rings[0].forEach(function (p) {
        b[0] = Math.min(b[0], p[0]); b[1] = Math.min(b[1], p[1]);
        b[2] = Math.max(b[2], p[0]); b[3] = Math.max(b[3], p[1]);
      });
    });
    return b;
  }

  // properties.area_km2 is the real area computed by Gate G4 (see g4_generate_links.py);
  // reuse it rather than re-deriving area from simplified/generalised display geometry.
  function featureAreaSqMi(feature) {
    var km2 = feature && feature.properties && feature.properties.area_km2;
    return typeof km2 === 'number' ? km2 * 0.386102 : null;
  }

  function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  // ---------------------------------------------------------------------------
  // Real region index (built from regions.js / regions.geojson — Gate G4 output).
  // Picks a REAL precomputed feature for whatever anchors the user currently has
  // applied; never invents a shape. See fixtures.js header for provenance.
  // ---------------------------------------------------------------------------
  var REGION_PAIRS = {};   // "nameA|nameB" (sorted) -> feature
  var REGION_BY_ANCHOR = {}; // name -> [features]
  var REGION_LARGEST = null;
  (REG && REG.features || []).forEach(function (f) {
    var a = f.properties.a, b = f.properties.b;
    REGION_PAIRS[[a, b].sort().join('|')] = f;
    (REGION_BY_ANCHOR[a] = REGION_BY_ANCHOR[a] || []).push(f);
    (REGION_BY_ANCHOR[b] = REGION_BY_ANCHOR[b] || []).push(f);
    if (!REGION_LARGEST || f.properties.area_km2 > REGION_LARGEST.properties.area_km2) { REGION_LARGEST = f; }
  });

  function nearestG4Anchor(pt) {
    if (!pt) { return null; }
    var best = null;
    Object.keys(F.g4Anchors).forEach(function (name) {
      var d = haversineMiles(pt, F.g4Anchors[name]);
      if (!best || d < best.d) { best = { name: name, d: d }; }
    });
    return best ? best.name : null;
  }

  function featureForPair(nameA, nameB) {
    if (!nameA || !nameB || nameA === nameB) { return null; }
    return REGION_PAIRS[[nameA, nameB].sort().join('|')] || null;
  }

  function largestFeatureContaining(name) {
    var list = REGION_BY_ANCHOR[name];
    if (!list || !list.length) { return null; }
    return list.reduce(function (m, f) { return f.properties.area_km2 > m.properties.area_km2 ? f : m; }, list[0]);
  }

  function globalLargestFeature() { return REGION_LARGEST; }

  // anchors: applied cards that are people/places (not amenities). wantLarger: true when
  // the user has muted, deleted, or relaxed a criterion — always resolves to a bigger
  // real example than the tight pair would be, per Gate G5a spec.
  function pickFeature(anchors, wantLarger) {
    var names = [];
    anchors.forEach(function (c) {
      var n = nearestG4Anchor(cardAnchor(c));
      if (n && names.indexOf(n) === -1) { names.push(n); }
    });
    if (!names.length) { return globalLargestFeature(); }
    if (names.length === 1) { return largestFeatureContaining(names[0]) || globalLargestFeature(); }
    if (!wantLarger) {
      var exact = featureForPair(names[0], names[1]);
      if (exact) { return exact; }
    }
    var candidates = [];
    names.forEach(function (n) { (REGION_BY_ANCHOR[n] || []).forEach(function (f) { candidates.push(f); }); });
    if (!candidates.length) { return globalLargestFeature(); }
    var best = candidates.reduce(function (m, f) { return f.properties.area_km2 > m.properties.area_km2 ? f : m; }, candidates[0]);
    if (wantLarger) {
      var tight = featureForPair(names[0], names[1]);
      if (tight && best.properties.id === tight.properties.id) { return globalLargestFeature(); }
    }
    return best;
  }

  function regionAnchorLabel(feature) {
    if (!feature) { return ''; }
    return feature.properties.a + ' ↔ ' + feature.properties.b;
  }

  // ---------------------------------------------------------------------------
  // Scripted gazetteer
  // ---------------------------------------------------------------------------
  var PLACE_BY_ID = {};
  F.places.forEach(function (p) {
    PLACE_BY_ID[p.id] = p;
    if (p.options) {
      p.options.forEach(function (o) {
        PLACE_BY_ID[o.id] = { id: o.id, name: o.name, lng: o.lng, lat: o.lat, kind: p.kind, parent: p.id, aliases: [] };
      });
    }
  });
  function placeById(id) { return (id && PLACE_BY_ID[id]) || null; }

  var NUM_WORDS = [
    ['forty five', 45], ['forty-five', 45], ['thirty five', 35], ['thirty-five', 35], ['twenty five', 25], ['twenty-five', 25],
    ['half an hour', 30], ['an hour', 60], ['one hour', 60], ['sixty', 60], ['fifty', 50], ['forty', 40], ['thirty', 30],
    ['twenty', 20], ['fifteen', 15], ['twelve', 12], ['ten', 10], ['five', 5]
  ];

  function normalize(s) {
    s = String(s == null ? '' : s).toLowerCase();
    s = s.replace(/[’‘'`]/g, '');
    s = s.replace(/[–—]/g, '-');
    s = s.replace(/\s+/g, ' ').trim();
    NUM_WORDS.forEach(function (nw) {
      s = s.replace(new RegExp('\\b' + escapeRe(nw[0]) + '\\b', 'g'), String(nw[1]));
    });
    s = s.replace(/(\d)\s*-\s*(min)/g, '$1 $2');          // "10-minute" -> "10 minute"
    s = s.replace(/\bmins?\b/g, 'minutes').replace(/\bminute\b/g, 'minutes');
    s = s.replace(/,\s*(north carolina|nc)\b/g, '').replace(/\s+(north carolina|nc)$/, '');
    s = s.replace(/[.!?]+$/, '').trim();
    return s;
  }

  var ARTICLE_RE = /^(?:a|an|the|my|our|some|nearest|closest|good|nice|decent|great|big|small|local|any)\s+/;
  function stripArticles(s) {
    s = String(s || '').trim();
    for (var i = 0; i < 3 && ARTICLE_RE.test(s); i++) { s = s.replace(ARTICLE_RE, ''); }
    return s.trim();
  }

  function resolveCategory(text) {
    var t = stripArticles(normalize(text));
    if (!t) { return null; }
    var best = null;
    Object.keys(F.categories).forEach(function (key) {
      F.categories[key].aliases.forEach(function (al) {
        if (t === al || t.slice(-(al.length + 1)) === ' ' + al) {
          if (!best || al.length > best.len) { best = { key: key, len: al.length }; }
        }
      });
    });
    return best ? best.key : null;
  }

  // Returns {status: 'ok'|'ambiguous'|'outside'|'unknown', place?, options?, query}
  function resolvePlace(text) {
    var t = stripArticles(normalize(text));
    if (!t) { return { status: 'unknown', query: text }; }
    var exact = null, contained = null;
    F.places.forEach(function (p) {
      p.aliases.forEach(function (al) {
        if (t === al) {
          if (!exact || al.length > exact.len) { exact = { p: p, len: al.length }; }
        } else if ((al.length >= 6 || al.indexOf(' ') >= 0) &&
                   new RegExp('(^|\\s)' + escapeRe(al) + '(\\s|$)').test(t)) {
          if (!contained || al.length > contained.len) { contained = { p: p, len: al.length }; }
        }
      });
    });
    var hit = exact || contained;
    if (!hit) { return { status: 'unknown', query: text }; }
    var p = hit.p;
    if (p.options) { return { status: 'ambiguous', query: text, place: p, options: p.options }; }
    if (p.outside) { return { status: 'outside', query: text, place: p }; }
    return { status: 'ok', query: text, place: p };
  }

  // ---------------------------------------------------------------------------
  // Card model
  // ---------------------------------------------------------------------------
  var MODE_LABEL = { drive: 'Drive', bike: 'Bike', walk: 'Walk' };
  var seq = 0;

  function makeCard(o) {
    seq += 1;
    return {
      id: 'c' + seq,
      kind: o.kind,                        // 'person' | 'place' | 'amenity'
      who: o.who || null,
      placeQuery: o.placeQuery || '',
      placeId: o.placeId || null,
      options: o.options || null,          // ambiguous choices [{id,name,lng,lat}]
      optionsOf: o.optionsOf || null,
      category: o.category || null,
      mode: o.mode || 'drive',
      modeAssumed: !!o.modeAssumed,
      limit: Number(o.limit) || 0,
      limit0: Number(o.limit) || 0,
      unit: o.unit || 'min',
      off: false,
      relaxed: false,
      seeded: false,
      seededFixed: false,
      source: o.source || 'form'
    };
  }

  function cardFromPlaceQuery(card, query) {
    var r = resolvePlace(query);
    card.placeQuery = String(query || '').trim();
    card.placeId = null; card.options = null; card.optionsOf = null;
    if (r.status === 'ok' || r.status === 'outside') { card.placeId = r.place.id; }
    else if (r.status === 'ambiguous') { card.options = r.options; card.optionsOf = r.place.name; }
    return card;
  }

  // Seeded misparse: an airport criterion given in minutes is shown in miles.
  function applySeed(card, seed) {
    if (seed && card.placeId === 'rdu' && card.unit === 'min') { card.unit = 'mi'; card.seeded = true; }
    return card;
  }

  function cardStatus(c) {
    if (c.off) { return 'off'; }
    if (c.kind === 'amenity') { return F.categories[c.category] ? 'ok' : 'unknown'; }
    if (c.placeId) { var p = placeById(c.placeId); if (!p) { return 'unknown'; } return p.outside ? 'outside' : 'ok'; }
    if (c.options) { return 'ambiguous'; }
    return 'unknown';
  }
  function isApplied(c) { return cardStatus(c) === 'ok'; }
  function cardAnchor(c) { var p = placeById(c.placeId); return p ? [p.lng, p.lat] : null; }

  function cardPlaceName(c) {
    if (c.kind === 'amenity') { return F.categories[c.category] ? F.categories[c.category].label : (c.category || 'amenity'); }
    var p = placeById(c.placeId);
    if (p) { return p.name; }
    if (c.optionsOf) { return c.optionsOf; }
    return c.placeQuery || '(no place yet)';
  }
  function cardTitle(c) {
    if (c.kind === 'person') { return (c.who || 'Person') + ' → ' + cardPlaceName(c); }
    return cardPlaceName(c);
  }
  function cardLimitText(c) { return c.unit === 'mi' ? ('within ' + c.limit + ' mi') : ('≤ ' + c.limit + ' min'); }
  function cardDescription(c) {
    var parts = [];
    if (c.unit === 'min') { parts.push(MODE_LABEL[c.mode] + (c.modeAssumed ? ' (assumed)' : '')); }
    parts.push(cardLimitText(c));
    return parts.join(' · ');
  }
  function statusReason(c) {
    return { off: 'muted — removed from the region', ambiguous: 'needs a choice', unknown: 'place not recognised', outside: 'outside coverage', ok: '' }[cardStatus(c)];
  }

  // ---------------------------------------------------------------------------
  // Scripted estimates and region decision (fixture logic)
  // ---------------------------------------------------------------------------
  function reachMiles(c) { return c.unit === 'mi' ? c.limit : c.limit * F.speeds[c.mode]; }

  function estimateCard(c, pt) {
    var d;
    if (c.kind === 'amenity') {
      var pts = (F.categories[c.category] || { points: [] }).points;
      d = Infinity;
      pts.forEach(function (p) { var dd = haversineMiles(pt, p); if (dd < d) { d = dd; } });
      if (d === Infinity) { d = 5; }
    } else {
      var a = cardAnchor(c);
      d = a ? haversineMiles(pt, a) : 0;
    }
    var road = d * F.circuity;
    var value = c.unit === 'mi' ? Math.round(road * 10) / 10 : Math.max(1, Math.round(road / F.speeds[c.mode]));
    return { value: value, unit: c.unit, limit: c.limit, pass: value <= c.limit, ratio: value / Math.max(1, c.limit) };
  }

  function neededLimit(c, miles) {
    var m = Math.max(0, miles);
    return c.unit === 'mi' ? Math.ceil(m) + 1 : Math.ceil(m / F.speeds[c.mode]) + 1;
  }

  function decideRegion(cards, baselineCount) {
    var applied = cards.filter(isApplied);
    if (!applied.length) { return { key: 'none', applied: applied }; }
    var anchors = applied.filter(function (c) { return c.kind !== 'amenity'; });
    for (var i = 0; i < anchors.length; i++) {
      for (var j = i + 1; j < anchors.length; j++) {
        var a = anchors[i], b = anchors[j];
        var dist = haversineMiles(cardAnchor(a), cardAnchor(b)) * F.circuity;
        var ra = reachMiles(a), rb = reachMiles(b);
        if (ra + rb < dist) {
          return { key: 'impossible', applied: applied, pair: [a, b], roadMiles: Math.round(dist),
                   reach: Math.round(ra + rb), needA: neededLimit(a, dist - rb), needB: neededLimit(b, dist - ra) };
        }
      }
    }
    var relaxed = cards.some(function (c) { return c.off; }) ||
                  applied.some(function (c) { return c.relaxed; }) ||
                  cards.length < baselineCount;
    var feature = pickFeature(anchors, relaxed);
    return { key: relaxed ? 'relaxed' : 'tight', applied: applied, anchors: anchors, feature: feature };
  }

  function whyOut(pt, cards, feature) {
    var applied = cards.filter(isApplied);
    if (!applied.length) { return { kind: 'nocriteria', pt: pt }; }
    var inside = feature ? pointInFeature(pt, feature) : false;
    var items = applied.map(function (c) { return { card: c, est: estimateCard(c, pt) }; });
    if (inside) {
      items.forEach(function (it) {
        if (!it.est.pass) { it.est.value = Math.max(1, it.est.limit - 1); it.est.pass = true; it.est.capped = true; }
      });
      return { kind: 'in', pt: pt, items: items };
    }
    var failing = items.filter(function (it) { return !it.est.pass; });
    if (!failing.length) {
      var top = items.reduce(function (m, it) { return it.est.ratio > m.est.ratio ? it : m; }, items[0]);
      top.est.value = top.est.limit + Math.max(2, Math.round(top.est.limit * 0.2));
      top.est.pass = false; top.est.forced = true;
      failing = [top];
    }
    return { kind: 'out', pt: pt, items: items, failing: failing };
  }

  function nearestSpot(pt, maxMiles) {
    var best = null;
    F.checkSpots.forEach(function (s) {
      var d = haversineMiles(pt, [s.lng, s.lat]);
      if (d <= maxMiles && (!best || d < best.d)) { best = { spot: s, d: d }; }
    });
    return best ? best.spot : null;
  }

  // ---------------------------------------------------------------------------
  // Variant B parser: three scripted sentence families, deterministic, no LLM.
  //   1. "<who> drives|bikes|walks to <place> in under <N> minutes"
  //   2. "a <N>-minute walk|bike|drive to <amenity or place>"   (or "walk to <x> in <N> minutes")
  //   3. "<N> minutes to <place>"                               (mode assumed: drive)
  // ---------------------------------------------------------------------------
  var MODE_WORD = '(drives?|driving|drove|bikes?|biking|cycles?|cycling|bicycles?|walks?|walking|rides?)';
  var MODE_NOUN = '(walk|bike ride|bike|ride|drive|car ride|cycle)';
  var MINUTES = '(\\d{1,3}) minutes';
  var QUAL = '(?:(?:under|less than|at most|no more than|about|around|max|maximum|up to|roughly)\\s+)?';
  var SUBJ = '(i|me|we|my (?:partner|wife|husband|spouse|girlfriend|boyfriend|fiance|fiancee)|person 1|person 2|[a-z]+)';

  var RE_COMMUTE = new RegExp('^(?:' + SUBJ + '\\s+)?(?:(?:needs?|has|have|wants?|would like|will|can|could) to\\s+)?' +
    MODE_WORD + '\\s+to\\s+(?:work at\\s+|my (?:job|work|office) at\\s+|work in\\s+)?(.+?)\\s+(?:in|within)\\s+' + QUAL + MINUTES + '$');
  var RE_MIN_MODE_TO = new RegExp('^(?:(?:a|an|within a|within an|about a|be a|live a|have a)\\s+)?' + MINUTES + '\\s+' +
    MODE_NOUN + '\\s+(?:to|from|of|away from)\\s+(.+)$');
  var RE_MODE_TO_IN = new RegExp('^(?:(?:be )?(?:able to |can |could )?)(walk|bike|drive|cycle|walking|biking|driving|cycling|walkable|bikeable)\\s+' +
    '(?:distance\\s+)?(?:to|from)\\s+(.+?)\\s+(?:in|within)\\s+' + QUAL + MINUTES + '$');
  var RE_MIN_TO = new RegExp('^(?:(?:be|live|stay|are|is|am)\\s+)?(?:(?:within|under|about|no more than|at most|less than|max|maximum|up to|roughly)\\s+)?' +
    MINUTES + '\\s+(?:to|from|of|away from)\\s+(.+)$');

  var EXAMPLES = [
    'I drive to Downtown Durham in under 20 minutes and my partner bikes to Carrboro in under 15 minutes.',
    'A 10-minute walk to a library.',
    '30 minutes to Downtown Raleigh.'
  ];

  function modeFrom(word) {
    word = String(word || '').toLowerCase();
    if (/^(driv|drove|car)/.test(word)) { return 'drive'; }
    if (/^(bik|cycl|bicycl|rid)/.test(word)) { return 'bike'; }
    if (/^(walk|foot)/.test(word)) { return 'walk'; }
    return 'drive';
  }

  function whoLabel(subj) {
    subj = subj.trim();
    if (/^(i|me|myself)$/.test(subj)) { return 'Person 1'; }
    if (/^my /.test(subj)) { return 'Person 2'; }
    if (subj === 'we') { return 'Both of us'; }
    if (/^person [12]$/.test(subj)) { return 'Person ' + subj.slice(-1); }
    return subj.charAt(0).toUpperCase() + subj.slice(1);
  }

  var LEAD_RE = /^(?:and|also|then|plus|we want|we need|we would like|wed like|i want|i need|id like|i would like|we are looking for|im looking for|looking for|ideally|preferably|we)\s+/;
  function splitClauses(text) {
    var n = normalize(text);
    var parts = n.split(/\s*(?:[.;,\n]|\band\b|&|\bplus\b|\balso\b)\s*/);
    return parts.map(function (s) {
      s = s.trim();
      for (var i = 0; i < 2 && LEAD_RE.test(s); i++) { s = s.replace(LEAD_RE, ''); }
      s = s.replace(/^(?:to\s+)?(?:be\s+)?/, '').trim();
      return s;
    }).filter(Boolean);
  }

  // Returns { cards: [], unrecognised: [clause...], echo: [line...] }
  function parseDescription(text, opts) {
    opts = opts || {};
    var clauses = splitClauses(text);
    var cards = [], unrecognised = [], echo = [];

    function build(p) {
      var minutes = parseInt(p.minutes, 10);
      if (!(minutes > 0 && minutes <= 180)) { return null; }
      var subj = (p.subject || '').trim();
      if (/^(a|an|the|be|to|also|and|then|we)$/.test(subj) && subj !== 'we') { subj = ''; }
      if (/^(a|an|the|be|to|also|and|then)$/.test(subj)) { subj = ''; }
      var mode = p.modeWord ? modeFrom(p.modeWord) : 'drive';
      var modeAssumed = !p.modeWord;
      var obj = stripArticles(p.object.trim());
      if (!obj) { return null; }
      var placeRes = resolvePlace(obj);
      var cat = placeRes.status === 'unknown' ? resolveCategory(obj) : null;
      var who = subj ? whoLabel(subj) : null;
      var c;
      if (cat) {
        c = makeCard({ kind: 'amenity', category: cat, mode: mode, modeAssumed: modeAssumed, limit: minutes, unit: 'min', source: 'text' });
      } else {
        c = makeCard({ kind: who ? 'person' : 'place', who: who, mode: mode, modeAssumed: modeAssumed, limit: minutes, unit: 'min', source: 'text' });
        cardFromPlaceQuery(c, obj);
        applySeed(c, !!opts.seed);
      }
      return c;
    }

    clauses.forEach(function (cl) {
      var m, card = null;
      if ((m = RE_COMMUTE.exec(cl))) { card = build({ subject: m[1], modeWord: m[2], object: m[3], minutes: m[4] }); }
      else if ((m = RE_MIN_MODE_TO.exec(cl))) { card = build({ modeWord: m[2], object: m[3], minutes: m[1] }); }
      else if ((m = RE_MODE_TO_IN.exec(cl))) { card = build({ modeWord: m[1], object: m[2], minutes: m[3] }); }
      else if ((m = RE_MIN_TO.exec(cl))) { card = build({ object: m[2], minutes: m[1] }); }
      if (card) { cards.push(card); echo.push(echoLine(card)); }
      else { unrecognised.push(cl); }
    });
    return { cards: cards, unrecognised: unrecognised, echo: echo };
  }

  function echoLine(c) {
    var st = cardStatus(c);
    var tail = '';
    if (st === 'ambiguous') { tail = ' — ' + c.options.length + ' places match; pick one on the card'; }
    else if (st === 'outside') { tail = ' — outside the coverage area, not applied'; }
    else if (st === 'unknown') { tail = ' — place not recognised, not applied'; }
    else if (c.unit === 'min') { tail = ' (estimated, typical conditions)'; }
    return 'Added: ' + cardTitle(c) + ', ' + cardDescription(c) + tail;
  }

  // ---------------------------------------------------------------------------
  // UI (browser only)
  // ---------------------------------------------------------------------------
  var S = {
    variant: null, seed: false, logOn: false,
    cards: [], baselineCount: 0, computed: false,
    region: { key: 'none', applied: [] },
    editing: {},
    lastSpot: null, lastSpotName: null, whyOpen: false,
    map: null, mapReady: false, markers: [], spotMarker: null, fittedFeatureId: null,
    t0: Date.now(), tTask: null, tFirstRegion: null, tTrusted: null,
    events: [], counters: { corrections: 0, whyout: 0, relax: 0, choices: 0, seedFixed: false },
    onClear: null
  };

  function $(id) { return root.document.getElementById(id); }
  function param(name) {
    try { return new URL(root.location.href).searchParams.get(name); } catch (e) { return null; }
  }
  function secs(ms) { return (ms / 1000).toFixed(1) + ' s'; }

  function log(type, detail) {
    var now = Date.now();
    S.events.push({ t: now, sincePage: now - S.t0, sinceTask: S.tTask ? now - S.tTask : null, type: type, detail: detail || '' });
    if (S.logOn) { renderLog(); }
  }

  function countCorrection(type) {
    if (S.computed) { S.counters.corrections += 1; }
    log(type.type || type, type.detail);
  }

  // --- public card operations -------------------------------------------------
  function replaceCards(cards) {
    S.cards = cards.slice();
    S.baselineCount = S.cards.length;
    S.computed = true;
    S.editing = {};
    log('compute', S.cards.map(function (c) { return cardTitle(c) + ', ' + cardDescription(c); }).join(' | '));
    renderAll();
    focusCards();
  }

  function appendCards(cards) {
    cards.forEach(function (c) { S.cards.push(c); });
    S.baselineCount = S.cards.length;
    S.computed = true;
    log('compute', cards.map(function (c) { return cardTitle(c) + ', ' + cardDescription(c); }).join(' | '));
    renderAll();
    focusCards();
  }

  function clearAll(reason) {
    S.cards = []; S.baselineCount = 0; S.computed = false; S.editing = {};
    closeWhy();
    log('clear', reason || '');
    renderAll();
    if (typeof S.onClear === 'function') { S.onClear(); }
  }

  function findCard(id) { for (var i = 0; i < S.cards.length; i++) { if (S.cards[i].id === id) { return S.cards[i]; } } return null; }

  function relaxCard(id, n) {
    var c = findCard(id); if (!c) { return; }
    n = Number(n);
    if (!(n > 0)) { return; }
    c.limit = n;
    c.relaxed = n > c.limit0;
    S.counters.relax += 1;
    countCorrection({ type: 'relax', detail: cardTitle(c) + ' -> ' + cardLimitText(c) });
    renderAll();
    if (S.whyOpen && S.lastSpot) { runWhy(S.lastSpot, S.lastSpotName, true); }
  }

  function addCard(kind) {
    var c;
    if (kind === 'person') {
      var people = S.cards.filter(function (x) { return x.kind === 'person'; }).length;
      c = makeCard({ kind: 'person', who: 'Person ' + (people + 1), mode: 'drive', limit: 25, unit: 'min', source: 'add' });
    } else {
      c = makeCard({ kind: 'amenity', category: 'park', mode: 'walk', limit: 10, unit: 'min', source: 'add' });
    }
    S.cards.push(c);
    S.baselineCount = S.cards.length;
    S.computed = true;
    S.editing[c.id] = true;
    log('add', kind);
    renderAll();
    var el = root.document.querySelector('[data-id="' + c.id + '"] .card-editor input, [data-id="' + c.id + '"] .card-editor select');
    if (el) { el.focus(); }
  }

  // --- rendering ---------------------------------------------------------------
  function renderAll() {
    S.region = decideRegion(S.cards, S.baselineCount);
    if ((S.region.key === 'tight' || S.region.key === 'relaxed') && !S.tFirstRegion) {
      S.tFirstRegion = Date.now();
      log('first-region', S.region.key);
    }
    renderSummary();
    renderStatus();
    renderCards();
    renderMap();
    if (S.logOn) { renderLog(); }
  }

  function regionLabel(key) { return key === 'tight' ? 'both criteria' : 'relaxed (larger)'; }

  function renderSummary() {
    var el = $('summary'); if (!el) { return; }
    if (!S.cards.length) {
      el.innerHTML = '<strong>No criteria applied yet.</strong> ' + (S.variant === 'A'
        ? 'Fill in where you need to be, then press Compute.'
        : 'Describe where you need to be, then press Understand.');
      return;
    }
    var applied = S.cards.filter(isApplied);
    var notApplied = S.cards.filter(function (c) { return !isApplied(c); });
    var html = '<strong>Applied (' + applied.length + '):</strong> ' +
      (applied.length ? applied.map(function (c) { return escapeHtml(cardTitle(c) + ', ' + cardDescription(c)); }).join('; ') + '.' : 'none.');
    if (notApplied.length) {
      html += ' <strong>Not applied (' + notApplied.length + '):</strong> ' +
        notApplied.map(function (c) { return escapeHtml(cardTitle(c) + ' (' + statusReason(c) + ')'); }).join('; ') + '.';
    }
    if (S.region.key === 'none') { html += ' No region: nothing applied.'; }
    else if (S.region.key === 'impossible') { html += ' <strong>No area meets all criteria.</strong>'; }
    else if (S.region.feature) {
      var area = Math.round(featureAreaSqMi(S.region.feature));
      html += ' Region shown (' + regionLabel(S.region.key) + '): real example computed 2026-11-03 from self-hosted Valhalla, fixed example — ' +
        escapeHtml(regionAnchorLabel(S.region.feature)) + ', about ' + area + ' sq mi.';
    }
    el.innerHTML = html;
  }

  function renderStatus() {
    var el = $('status'); if (!el) { return; }
    var html = '';
    var r = S.region;
    if (r.key === 'impossible') {
      var a = r.pair[0], b = r.pair[1];
      html += '<div class="notice bad" role="alert"><p><strong>No area meets all criteria.</strong></p>' +
        '<p>' + escapeHtml(cardTitle(a)) + ' and ' + escapeHtml(cardTitle(b)) + ' are about ' + r.roadMiles +
        ' road-miles apart (estimated). ' + escapeHtml(cardLimitText(a)) + ' plus ' + escapeHtml(cardLimitText(b)) +
        ' reaches about ' + r.reach + ' miles in total under typical conditions.</p>' +
        '<div class="actions">' +
        '<button class="small" data-action="relax" data-id="' + a.id + '" data-n="' + r.needA + '">Relax ' + escapeHtml(a.who || cardPlaceName(a)) + ' to ' + r.needA + (a.unit === 'mi' ? ' mi' : ' min') + '</button>' +
        '<button class="small" data-action="relax" data-id="' + b.id + '" data-n="' + r.needB + '">Relax ' + escapeHtml(b.who || cardPlaceName(b)) + ' to ' + r.needB + (b.unit === 'mi' ? ' mi' : ' min') + '</button>' +
        '</div><p class="inline-note">Or turn one of them off, or change a workplace.</p></div>';
    }
    S.cards.forEach(function (c) {
      var st = cardStatus(c);
      if (st === 'outside') {
        html += '<div class="notice bad"><p><strong>' + escapeHtml(cardPlaceName(c)) + ' is outside the coverage area.</strong> This prototype covers the Research Triangle only (dashed box on the map). That criterion is not applied. Edit it, turn it off, or delete it.</p></div>';
      } else if (st === 'ambiguous') {
        html += '<div class="notice warn"><p><strong>' + escapeHtml(c.optionsOf) + ':</strong> ' + c.options.length + ' places match. Pick one on its card below; until then it is not applied.</p></div>';
      } else if (st === 'unknown') {
        html += '<div class="notice warn"><p><strong>Place not recognised:</strong> “' + escapeHtml(c.placeQuery || '(empty)') + '”. Edit the card and choose an employer, landmark, store or town from the list. Not applied until then.</p></div>';
      }
    });
    if (r.key === 'relaxed' && r.feature) {
      html += '<div class="notice"><p>Showing a larger real example region (' + escapeHtml(regionAnchorLabel(r.feature)) +
        ') because a criterion is off, deleted, or relaxed. This removes that criterion from the map, not just its visibility.</p></div>';
    }
    el.innerHTML = html;
  }

  function badgeFor(c) {
    var st = cardStatus(c);
    if (st === 'ok') { return c.relaxed ? ['relaxed', 'Relaxed to ' + c.limit + (c.unit === 'mi' ? ' mi' : ' min')] : ['ok', 'Applied']; }
    if (st === 'off') { return ['off', 'Muted — removed from the region (not just hidden)']; }
    if (st === 'ambiguous') { return ['warn', 'Needs a choice — not applied']; }
    if (st === 'outside') { return ['bad', 'Outside coverage — not applied']; }
    return ['warn', 'Place not recognised — not applied'];
  }

  function optionsHtml(list, selected, labeller) {
    return list.map(function (v) {
      var val = Array.isArray(v) ? v[0] : v, lab = Array.isArray(v) ? v[1] : labeller(v);
      return '<option value="' + escapeHtml(val) + '"' + (val === selected ? ' selected' : '') + '>' + escapeHtml(lab) + '</option>';
    }).join('');
  }

  function renderCards() {
    var ul = $('cards'); if (!ul) { return; }
    var count = $('card-count');
    if (count) { count.textContent = S.cards.length ? '(' + S.cards.filter(isApplied).length + ' applied of ' + S.cards.length + ')' : ''; }
    if (!S.cards.length) {
      ul.innerHTML = '<li class="inline-note">No criteria yet.</li>';
      return;
    }
    ul.innerHTML = S.cards.map(function (c) {
      var st = cardStatus(c);
      var badge = badgeFor(c);
      var cls = 'card state-' + st + (c.relaxed ? ' relaxed' : '') + (c.seededFixed ? ' seeded-fixed' : '');
      var body;
      if (c.unit === 'mi') {
        body = 'within <span class="unit-mi">' + c.limit + ' mi</span><span class="est">distance, not travel time</span>';
      } else {
        body = escapeHtml(cardDescription(c)) + '<span class="est">estimated, typical conditions</span>';
      }
      var chooser = '';
      if (st === 'ambiguous') {
        chooser = '<div class="chooser" role="group" aria-label="Which ' + escapeHtml(c.optionsOf) + '?"><p>' + c.options.length +
          ' places match “' + escapeHtml(c.optionsOf) + '”. Which one?</p>' +
          c.options.map(function (o) {
            return '<label><input type="radio" name="choose-' + c.id + '" data-action="choose" data-id="' + c.id + '" value="' + escapeHtml(o.id) + '"> ' + escapeHtml(o.name) + '</label>';
          }).join('') + '</div>';
      }
      var editing = !!S.editing[c.id];
      var editor = '<div class="card-editor"' + (editing ? '' : ' hidden') + '>';
      if (c.kind === 'person') {
        editor += '<div><label for="who-' + c.id + '">Who</label><input id="who-' + c.id + '" type="text" data-field="who" data-id="' + c.id + '" value="' + escapeHtml(c.who || '') + '"></div>';
      }
      if (c.kind !== 'amenity') {
        editor += '<div><label for="place-' + c.id + '">Place</label><input id="place-' + c.id + '" type="text" list="g5a-places" data-field="place" data-id="' + c.id + '" value="' + escapeHtml(c.placeQuery || cardPlaceName(c)) + '" placeholder="Employer, landmark, store or town"></div>';
      } else {
        editor += '<div><label for="cat-' + c.id + '">Amenity</label><select id="cat-' + c.id + '" data-field="category" data-id="' + c.id + '">' +
          optionsHtml(Object.keys(F.categories), c.category, function (k) { return F.categories[k].label; }) + '</select></div>';
      }
      editor += '<div class="row cols-3">' +
        '<div><label for="mode-' + c.id + '">How</label><select id="mode-' + c.id + '" data-field="mode" data-id="' + c.id + '"' + (c.unit === 'mi' ? ' disabled' : '') + '>' +
          optionsHtml([['drive', 'Drive'], ['bike', 'Bike'], ['walk', 'Walk']], c.mode) + '</select></div>' +
        '<div><label for="limit-' + c.id + '">Max</label><input id="limit-' + c.id + '" type="number" min="1" max="180" step="1" data-field="limit" data-id="' + c.id + '" value="' + c.limit + '"></div>' +
        '<div><label for="unit-' + c.id + '">Unit</label><select id="unit-' + c.id + '" data-field="unit" data-id="' + c.id + '">' +
          optionsHtml([['min', 'minutes'], ['mi', 'miles']], c.unit) + '</select></div>' +
        '</div>' +
        '<div class="actions"><button class="small" data-action="done" data-id="' + c.id + '">Done</button></div></div>';

      return '<li class="' + cls + '" data-id="' + c.id + '">' +
        '<div class="card-head"><span class="card-title">' + escapeHtml(cardTitle(c)) + '</span><span class="badge ' + badge[0] + '">' + escapeHtml(badge[1]) + '</span></div>' +
        '<div class="card-body">' + body + '</div>' + chooser +
        '<div class="card-actions">' +
        '<button class="small" data-action="edit" data-id="' + c.id + '" aria-expanded="' + (editing ? 'true' : 'false') + '">Edit</button>' +
        '<button class="small" data-action="toggle" data-id="' + c.id + '" aria-pressed="' + (c.off ? 'true' : 'false') + '">' +
          (c.off ? '👁️ Unmute (adds back)' : '👁️ Mute (removes from region)') + '</button>' +
        '<button class="small" data-action="delete" data-id="' + c.id + '">Delete</button>' +
        '</div>' + editor + '</li>';
    }).join('');
  }

  function focusCards() {
    var h = $('cards-heading');
    if (h && typeof h.focus === 'function') { h.focus(); }
  }

  // --- map --------------------------------------------------------------------
  function initMap() {
    var mapEl = $('map'); if (!mapEl) { return; }
    if (typeof root.maplibregl === 'undefined') {
      mapEl.innerHTML = '<p style="padding:16px">The map library did not load (this prototype needs internet access for MapLibre and OpenStreetMap tiles). Cards and explanations still work.</p>';
      return;
    }
    var map = new root.maplibregl.Map({
      container: 'map',
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            maxzoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          }
        },
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
      },
      center: F.center,
      zoom: F.zoom,
      attributionControl: true
    });
    map.addControl(new root.maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.on('load', function () {
      map.addSource('coverage', { type: 'geojson', data: F.coverage });
      map.addLayer({ id: 'coverage-line', type: 'line', source: 'coverage',
        paint: { 'line-color': '#7a3fbf', 'line-width': 1.5, 'line-dasharray': [3, 3] } });
      map.addSource('region', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'region-fill', type: 'fill', source: 'region', paint: { 'fill-color': '#1f5fbf', 'fill-opacity': 0.3 } });
      map.addLayer({ id: 'region-line', type: 'line', source: 'region', paint: { 'line-color': '#1f5fbf', 'line-width': 2 } });
      S.mapReady = true;
      renderMap();
    });
    map.on('click', function (e) {
      var pt = [e.lngLat.lng, e.lngLat.lat];
      var spot = nearestSpot(pt, 2);
      if (spot) { pt = [spot.lng, spot.lat]; }
      runWhy(pt, spot ? spot.name : null, false);
    });
    S.map = map;
  }

  function renderMapLabel() {
    var el = $('map-region-label'); if (!el) { return; }
    var r = S.region;
    if (r.key === 'tight' || r.key === 'relaxed') {
      el.hidden = false;
      el.textContent = (r.key === 'tight' ? 'Real example (both criteria): ' : 'Real example (relaxed — larger): ') +
        regionAnchorLabel(r.feature) + ' — computed 2026-11-03 from self-hosted Valhalla, fixed example';
    } else {
      el.hidden = true;
    }
  }

  function renderMap() {
    renderMapLabel();
    if (!S.map || !S.mapReady) { return; }
    var src = S.map.getSource('region');
    var feature = (S.region.key === 'tight' || S.region.key === 'relaxed') ? S.region.feature : null;
    src.setData({ type: 'FeatureCollection', features: feature ? [feature] : [] });
    var featureId = feature ? feature.properties.id + ':' + S.region.key : null;
    if (feature && featureId !== S.fittedFeatureId) {
      var b = featureBounds(feature);
      S.map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 40, duration: 600 });
      S.fittedFeatureId = featureId;
    }
    S.markers.forEach(function (m) { m.remove(); });
    S.markers = [];
    S.cards.forEach(function (c) {
      if (c.kind === 'amenity' || c.off) { return; }
      var st = cardStatus(c);
      if (st === 'ok') {
        var a = cardAnchor(c);
        var el = root.document.createElement('div');
        el.className = 'anchor' + (c.kind === 'place' ? ' place' : '');
        el.textContent = c.kind === 'person' ? (c.who || 'Person') + ': ' + cardPlaceName(c) : cardPlaceName(c);
        S.markers.push(new root.maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(a).addTo(S.map));
      } else if (st === 'ambiguous') {
        c.options.forEach(function (o) {
          var el2 = root.document.createElement('div');
          el2.className = 'anchor place';
          el2.textContent = '? ' + o.name;
          S.markers.push(new root.maplibregl.Marker({ element: el2, anchor: 'bottom' }).setLngLat([o.lng, o.lat]).addTo(S.map));
        });
      }
    });
  }

  // --- why is this out? ---------------------------------------------------------
  function runWhy(pt, spotName, rerun) {
    S.lastSpot = pt; S.lastSpotName = spotName || null;
    var res = whyOut(pt, S.cards, S.region.feature);
    if (!rerun) { S.counters.whyout += 1; log('whyout', (spotName || (pt[1].toFixed(3) + ', ' + pt[0].toFixed(3))) + ' -> ' + res.kind); }
    renderWhy(res);
    if (S.map && S.mapReady && typeof root.maplibregl !== 'undefined') {
      if (S.spotMarker) { S.spotMarker.remove(); }
      var el = root.document.createElement('div');
      el.className = 'spot-marker';
      el.setAttribute('aria-hidden', 'true');
      S.spotMarker = new root.maplibregl.Marker({ element: el }).setLngLat(pt).addTo(S.map);
    }
  }

  function renderWhy(res) {
    var el = $('whyout'); if (!el) { return; }
    var where = (S.lastSpotName ? 'Near ' + escapeHtml(S.lastSpotName) + ' · ' : '') + res.pt[1].toFixed(3) + ', ' + res.pt[0].toFixed(3);
    var html = '<h3><span id="whyout-title">Why is this spot ' + (res.kind === 'in' ? 'in' : 'out') + '?</span><button class="small" data-action="close-why">Close</button></h3>' +
      '<p class="spot">' + where + '</p>';
    if (res.kind === 'nocriteria') {
      html += '<p class="verdict">No criteria are applied yet, so there is no region to be in or out of.</p>';
    } else {
      var n = res.items.length;
      if (res.kind === 'in') {
        html += '<p class="verdict">This spot meets all ' + n + ' applied criteri' + (n === 1 ? 'on' : 'a') + '.</p>';
      } else {
        html += '<p class="verdict">' + res.failing.length + ' of ' + n + ' criteri' + (n === 1 ? 'on' : 'a') + ' fail' + (res.failing.length === 1 ? 's' : '') + ' here.</p>';
      }
      html += '<ul>' + res.items.map(function (it) {
        var c = it.card, e = it.est;
        var what = e.unit === 'mi'
          ? ('est. ' + e.value + ' mi (limit ' + e.limit + ' mi)')
          : ('est. ' + e.value + ' min ' + MODE_LABEL[c.mode].toLowerCase() + ' (limit ' + e.limit + ')');
        var btn = '';
        if (!e.pass) {
          btn = '<button class="small" data-action="relax" data-id="' + c.id + '" data-n="' + Math.ceil(e.value) + '">Relax to ' + Math.ceil(e.value) + (e.unit === 'mi' ? ' mi' : ' min') + '</button>';
        }
        return '<li class="' + (e.pass ? 'pass' : 'fail') + '"><span class="mark" aria-hidden="true">' + (e.pass ? '✓' : '✗') + '</span>' +
          '<span><span class="sr-only">' + (e.pass ? 'Passes: ' : 'Fails: ') + '</span>' + escapeHtml(cardTitle(c)) + ': ' + what + '</span>' + (btn || '<span></span>') + '</li>';
      }).join('') + '</ul>';
      if (res.kind === 'out' && res.failing.length > 1) {
        html += '<p class="note">More than one criterion fails here; relaxing one of them will not include this spot by itself.</p>';
      }
    }
    html += '<p class="note">Estimates are for typical conditions from a straight-line scripted approximation, not routed. The shaded region itself is a real precomputed example (Gate G4, computed 2026-11-03 from self-hosted Valhalla), not a live recomputation of this exact spot.</p>';
    el.innerHTML = html;
    el.hidden = false;
    S.whyOpen = true;
    var closeBtn = el.querySelector('[data-action="close-why"]');
    if (closeBtn) { closeBtn.focus(); }
  }

  function closeWhy() {
    var el = $('whyout'); if (el) { el.hidden = true; }
    S.whyOpen = false;
    if (S.spotMarker) { S.spotMarker.remove(); S.spotMarker = null; }
  }

  // --- variant B feedback (echo + "I did not understand" help) -------------------
  function renderDescribeFeedback(result) {
    var el = $('describe-feedback'); if (!el) { return; }
    var html = '';
    if (result.echo && result.echo.length) {
      html += '<ul class="echo">' + result.echo.map(function (line) { return '<li>' + escapeHtml(line) + '</li>'; }).join('') + '</ul>';
    }
    if (result.unrecognised && result.unrecognised.length) {
      html += '<div class="help" role="alert"><p><strong>I did not understand that yet — here is what I can read:</strong></p>' +
        '<ul>' + EXAMPLES.map(function (ex) { return '<li>' + escapeHtml(ex) + '</li>'; }).join('') + '</ul>' +
        '<p>Not understood: ' + result.unrecognised.map(function (u) { return '“' + escapeHtml(u) + '”'; }).join(', ') +
        '. Try rephrasing using one of the patterns above, or add/edit a card below instead.</p></div>';
      log('unrecognised', result.unrecognised.join(' | '));
    }
    if (!result.echo.length && !result.unrecognised.length) {
      html = '<p class="inline-note">Nothing to understand yet — type a sentence above.</p>';
    }
    el.innerHTML = html;
  }

  function checkSpotById(id) {
    var spot = null;
    F.checkSpots.forEach(function (s) { if (s.id === id) { spot = s; } });
    if (spot) { runWhy([spot.lng, spot.lat], spot.name, false); }
  }

  // --- moderator log ------------------------------------------------------------
  function fmtClock(ms) {
    var s = Math.floor(ms / 1000); var m = Math.floor(s / 60); s = s % 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function renderLog() {
    var el = $('modlog'); if (!el) { return; }
    if (!el.dataset.built) {
      el.dataset.built = '1';
      el.hidden = false;
      el.innerHTML = '<details class="modlog" open><summary>Moderator log (hidden unless ?log=1)</summary>' +
        '<div class="counters" id="log-counters"></div>' +
        '<div class="actions"><button class="small" id="log-task">Start task</button><button class="small" id="log-trust">Mark trusted</button><button class="small" id="log-copy">Copy log</button></div>' +
        '<ol id="log-list"></ol><textarea id="log-text" class="sr-only" aria-label="Log text" readonly></textarea></details>';
      $('log-task').addEventListener('click', function () {
        S.tTask = Date.now(); S.tTrusted = null;
        S.counters = { corrections: 0, whyout: 0, relax: 0, choices: 0, seedFixed: S.counters.seedFixed };
        log('task-start', '');
      });
      $('log-trust').addEventListener('click', function () { S.tTrusted = Date.now(); log('trusted', ''); renderLog(); });
      $('log-copy').addEventListener('click', function () {
        var text = logText();
        var ta = $('log-text'); ta.value = text;
        if (root.navigator.clipboard) { root.navigator.clipboard.writeText(text).catch(function () { ta.classList.remove('sr-only'); ta.select(); }); }
        else { ta.classList.remove('sr-only'); ta.select(); }
      });
      setInterval(renderLogCounters, 1000);
    }
    renderLogCounters();
    var list = $('log-list');
    list.innerHTML = S.events.slice(-80).map(function (e) {
      return '<li>' + fmtClock(e.sincePage) + (e.sinceTask != null ? ' (task +' + secs(e.sinceTask) + ')' : '') + ' — ' + escapeHtml(e.type) + (e.detail ? ': ' + escapeHtml(e.detail) : '') + '</li>';
    }).join('');
  }

  function renderLogCounters() {
    var el = $('log-counters'); if (!el) { return; }
    var now = Date.now();
    var rows = [
      ['Variant', S.variant + (S.seed ? ' · seed ON' : ' · seed off')],
      ['Elapsed', fmtClock(now - S.t0)],
      ['Task started', S.tTask ? fmtClock(S.tTask - S.t0) : '—'],
      ['First region', S.tFirstRegion ? (S.tTask && S.tFirstRegion >= S.tTask ? 'task +' + secs(S.tFirstRegion - S.tTask) : fmtClock(S.tFirstRegion - S.t0)) : '—'],
      ['Trusted', S.tTrusted ? (S.tTask ? 'task +' + secs(S.tTrusted - S.tTask) : fmtClock(S.tTrusted - S.t0)) : '—'],
      ['Corrections', String(S.counters.corrections)],
      ['Why-out opens', String(S.counters.whyout)],
      ['Relax clicks', String(S.counters.relax)],
      ['Choices made', String(S.counters.choices)],
      ['Seeded error fixed', S.counters.seedFixed ? 'yes' : 'no']
    ];
    el.innerHTML = rows.map(function (r) { return '<span>' + escapeHtml(r[0]) + '</span><strong>' + escapeHtml(r[1]) + '</strong>'; }).join('');
  }

  function logText() {
    return S.events.map(function (e) {
      return [fmtClock(e.sincePage), e.sinceTask != null ? secs(e.sinceTask) : '', e.type, e.detail].join('\t');
    }).join('\n');
  }

  // --- event binding --------------------------------------------------------------
  function bindRail() {
    var rail = root.document.querySelector('.rail'); if (!rail) { return; }
    rail.addEventListener('click', function (ev) {
      var btn = ev.target.closest('button[data-action]'); if (!btn) { return; }
      handleAction(btn);
    });
    rail.addEventListener('change', function (ev) {
      var t = ev.target;
      if (t.matches('input[data-action="choose"]')) {
        var c = findCard(t.dataset.id); if (!c) { return; }
        c.placeId = t.value; c.options = null;
        S.counters.choices += 1;
        log('choose', cardTitle(c));
        renderAll();
        return;
      }
      if (t.matches('[data-field]')) { handleField(t); }
    });
    var why = $('whyout');
    if (why) {
      why.addEventListener('click', function (ev) {
        var btn = ev.target.closest('button[data-action]'); if (!btn) { return; }
        handleAction(btn);
      });
      why.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { closeWhy(); var cb = $('check-btn'); if (cb) { cb.focus(); } } });
    }
    var addP = $('add-person'); if (addP) { addP.addEventListener('click', function () { addCard('person'); }); }
    var addA = $('add-amenity'); if (addA) { addA.addEventListener('click', function () { addCard('amenity'); }); }
    var clr = $('clear-all'); if (clr) { clr.addEventListener('click', function () { clearAll('clear-all'); }); }
    var chk = $('check-btn');
    if (chk) {
      chk.addEventListener('click', function () { var sel = $('check-spot'); if (sel && sel.value) { checkSpotById(sel.value); } });
    }
  }

  function handleAction(btn) {
    var action = btn.dataset.action, id = btn.dataset.id, c = id ? findCard(id) : null;
    if (action === 'close-why') { closeWhy(); return; }
    if (action === 'relax') { relaxCard(id, btn.dataset.n); return; }
    if (!c) { return; }
    if (action === 'edit') { S.editing[id] = !S.editing[id]; log('edit-open', cardTitle(c)); renderCards(); return; }
    if (action === 'done') { delete S.editing[id]; renderCards(); return; }
    if (action === 'toggle') {
      c.off = !c.off;
      countCorrection({ type: c.off ? 'turn-off' : 'turn-on', detail: cardTitle(c) });
      renderAll();
      return;
    }
    if (action === 'delete') {
      S.cards = S.cards.filter(function (x) { return x.id !== id; });
      delete S.editing[id];
      countCorrection({ type: 'delete', detail: cardTitle(c) + (c.seeded && !c.seededFixed ? ' (seeded card removed)' : '') });
      renderAll();
      return;
    }
  }

  function handleField(t) {
    var c = findCard(t.dataset.id); if (!c) { return; }
    var field = t.dataset.field, v = t.value;
    var before = cardTitle(c) + ', ' + cardDescription(c);
    if (field === 'who') { c.who = v.trim() || c.who; }
    else if (field === 'place') { cardFromPlaceQuery(c, v); }
    else if (field === 'category') { c.category = v; }
    else if (field === 'mode') { c.mode = v; c.modeAssumed = false; }
    else if (field === 'limit') {
      var n = parseInt(v, 10);
      if (n > 0 && n <= 180) {
        c.limit = n;
        if (n > c.limit0) { c.relaxed = true; } else { c.relaxed = false; c.limit0 = n; }
      }
    }
    else if (field === 'unit') {
      if (v !== c.unit) {
        c.unit = v; c.limit0 = c.limit; c.relaxed = false;
        if (c.seeded && v === 'min') { c.seededFixed = true; S.counters.seedFixed = true; log('seed-fixed', cardTitle(c)); }
      }
    }
    countCorrection({ type: 'edit', detail: before + ' -> ' + cardTitle(c) + ', ' + cardDescription(c) });
    renderAll();
    var again = root.document.getElementById(t.id);
    if (again) { again.focus(); }
  }

  function fillDatalist() {
    var dl = $('g5a-places'); if (!dl) { return; }
    dl.innerHTML = F.places.map(function (p) { return '<option value="' + escapeHtml(p.name) + '">'; }).join('');
    var sel = $('check-spot');
    if (sel) {
      sel.innerHTML = '<option value="">Choose a place…</option>' + F.checkSpots.map(function (s) {
        return '<option value="' + escapeHtml(s.id) + '">' + escapeHtml(s.name) + '</option>';
      }).join('');
    }
  }

  function init(opts) {
    opts = opts || {};
    S.variant = opts.variant || 'A';
    S.seed = param('seed') === '1';
    S.logOn = param('log') === '1';
    S.onClear = opts.onClear || null;
    if (root.document.body) { root.document.body.dataset.variant = S.variant; }
    fillDatalist();
    bindRail();
    initMap();
    log('init', 'variant ' + S.variant + (S.seed ? ' seed=1' : ''));
    renderAll();
    if (S.logOn) { renderLog(); }
    var demo = param('demo') === '1';
    var spot = param('spot');
    return { demo: demo, spot: spot, seed: S.seed };
  }

  // Scenario S1 used by ?demo=1 (moderator demo / screenshots only; not for participant tasks).
  var DEMO_S1 = {
    people: [
      { who: 'Person 1', place: 'UNC Hospitals', mode: 'drive', limit: 25 },
      { who: 'Person 2', place: 'Fidelity RTP', mode: 'drive', limit: 30 }
    ],
    amenities: [{ category: 'park', mode: 'walk', limit: 10 }],
    places: [{ place: 'RDU Airport', mode: 'drive', limit: 45 }],
    text: 'I drive to UNC Hospitals in under 25 minutes and my partner drives to Fidelity RTP in under 30 minutes. A 10-minute walk to a park. 45 minutes to the airport.'
  };

  return {
    fixtures: F,
    regions: REG,
    EXAMPLES: EXAMPLES,
    MODE_LABEL: MODE_LABEL,
    DEMO_S1: DEMO_S1,
    // pure
    normalize: normalize, stripArticles: stripArticles, resolvePlace: resolvePlace, resolveCategory: resolveCategory,
    parseDescription: parseDescription, splitClauses: splitClauses,
    makeCard: makeCard, cardFromPlaceQuery: cardFromPlaceQuery, applySeed: applySeed,
    cardStatus: cardStatus, isApplied: isApplied, cardTitle: cardTitle, cardDescription: cardDescription,
    estimateCard: estimateCard, decideRegion: decideRegion, whyOut: whyOut, nearestSpot: nearestSpot,
    nearestG4Anchor: nearestG4Anchor, featureForPair: featureForPair, pickFeature: pickFeature,
    regionAnchorLabel: regionAnchorLabel, featureAreaSqMi: featureAreaSqMi,
    util: { haversineMiles: haversineMiles, pointInRing: pointInRing, pointInFeature: pointInFeature,
            featureBounds: featureBounds, featureAreaSqMi: featureAreaSqMi, escapeHtml: escapeHtml },
    // ui
    init: init, replaceCards: replaceCards, appendCards: appendCards, clearAll: clearAll, addCard: addCard,
    relaxCard: relaxCard, checkSpotById: checkSpotById, closeWhy: closeWhy, log: log,
    renderDescribeFeedback: renderDescribeFeedback,
    state: function () { return S; }, isSeed: function () { return S.seed; }
  };
});
