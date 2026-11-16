// mutate_card.mjs — does card_selftest.mjs actually catch a card that loses a disclosure?
//
// Same discipline as mutate_worker.mjs, on the layer a household actually reads. The failures
// worth guarding here are not arithmetic: they are a correct message rendered into a sentence
// that claims more than the data does. Each mutation below is one of those.
//
// INERT is reported separately from a catch, and fails the run: a mutation whose anchor matched
// nothing tested nothing, and counting it as a pass is how a guard goes quietly hollow.
//
// Run:  node spikes/g3-render/mutate_card.mjs

import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TARGET = path.join(__dirname, 'card.js');
const HARNESS = path.join(__dirname, 'card_selftest.mjs');

const MUTATIONS = [
  {
    // "We are not telling you" rendered as "there are none". The exact confusion the optional
    // plane exists to prevent, and the one a household cannot detect.
    name: 'a layer that does not disclose is rendered as having no restrictions',
    // A regex with `\r?\n`, not a string literal: this working copy is checked out CRLF, and an
    // LF anchor matches nothing while every single-line anchor still matches fine.
    apply: (s) => s.replace(
      /bits\.push\('<div class="silent">This criterion does not say whether the route uses a '\r?\n          \+ 'restricted way\.<\/div>'\);/,
      'bits.push(\'<div class="silent">No restrictions on this route.</div>\');'),
  },
  {
    name: 'a layer that does not disclose is rendered as nothing at all',
    apply: (s) => s.replace(/\} else if \(crit\.routeFlag === null \|\| crit\.routeFlag === undefined\) \{/,
      '} else if (false) {'),
  },
  {
    // A lower bound printed as a measurement. Re-anchored after pass 51 B3 split `minutesText`
    // into three branches; it was reported INERT on the first run after that change.
    name: 'a lower bound is printed as a measured time',
    apply: (s) => s.replace('    if (!crit.valueIsLowerBound) return `${crit.value} min`;',
      '    return `${crit.value} min`;'),
  },
  {
    name: 'the card picks one place from a node that carries several',
    apply: (s) => s.replace(/if \(d\.placeCount > 1 \|\| names\.length > 1\) \{/, 'if (false) {'),
  },
  {
    // `namesDestination: null` is "this layer does not say", and a card that reads it as an
    // object prints "measured to undefined" -- which the real-bundle pass catches.
    name: 'a layer that names no destination is read as naming one',
    apply: (s) => s.replace('    if (!d) return null;',
      '    if (!d) return `measured to ${d && d.places}`;'),
  },
  {
    name: 'a place name reaches the DOM unescaped',
    apply: (s) => s.replace(/    return String\(s\)\.replace\(\/\[&<>"'\]\/g/,
      '    return String(s); return String(s).replace(/[&<>"\']/g'),
  },
  {
    // Anchored on the UNKNOWN branch only, not the bound branch below it, which carries the same
    // lookup. A regex with `\r?\n` rather than a literal newline, and backticks where the source
    // has backticks: the first version of this anchor used a quote and matched nothing, which the
    // runner reported as INERT.
    name: 'an unknown cause is printed as its wire code',
    apply: (s) => s.replace(
      /`\$\{esc\(WHY_UNKNOWN\[crit\.statusName\] \|\| crit\.statusName\)\}\.<\/div>`\);(\r?\n)      \} else if \(crit\.valueIsLowerBound\) \{/,
      '`${esc(crit.statusName)}.</div>`);$1      } else if (crit.valueIsLowerBound) {'),
  },
  {
    name: 'a criterion with no published time is given one',
    apply: (s) => s.replace("    if (crit.value === null || crit.value === undefined) return null;",
      '    if (crit.value === null || crit.value === undefined) return `${crit.value} min`;'),
  },
  {
    // No criteria excludes nothing. Rendering that as "everything is satisfied" turns the empty
    // AND into a claim about the place.
    name: 'no criteria is rendered as everything being satisfied',
    apply: (s) => s.replace(
      /      return '<div class="verdict">No criteria are switched on, so nothing is being asked of '\r?\n        \+ 'this spot\.<\/div>';/,
      "      return '<div class=\"verdict\">The model estimates this cell meets your limits."
      + "</div>';"),
  },
  {
    name: 'the cell lookup rounds instead of taking the floor',
    apply: (s) => s.replace('const col = Math.floor(((lon - W) / (E - W)) * ncols);',
      'const col = Math.round(((lon - W) / (E - W)) * ncols);'),
  },
  {
    name: 'the cell lookup treats the closed edges as the other pair',
    apply: (s) => s.replace('if (!(lon >= W && lon < E && lat > S && lat <= N)) return null;',
      'if (!(lon > W && lon <= E && lat >= S && lat < N)) return null;'),
  },
  // ------------------------------------------------------------------ Codex pass 51
  {
    // B6. This passed all sixteen checks, because before pass 51 there was no multi-criterion
    // rendering test at all -- not even a hand-built one.
    name: 'the card renders only the first criterion',
    apply: (s) => s.replace('for (const crit of msg.criteria) {',
      'for (const crit of msg.criteria.slice(0, 1)) {'),
  },
  {
    // B3. The value byte is ceil(bound / 60), so "at least 11 min" excludes a 630-second journey
    // the evidence allows. The honest statement is "more than 10 min".
    name: 'a rounded-up bound is reported as "at least" that many minutes',
    apply: (s) => s.replace("    return `more than ${crit.value - 1} min`;",
      '    return `at least ${crit.value} min`;'),
  },
  {
    name: 'a zero bound becomes "more than -1 min"',
    apply: (s) => s.replace("    if (crit.value <= 0) return 'no lower bound published';", ''),
  },
  // ------------------------------------------------------------------ pass 53 findings
  {
    // F7: the headline. No assertion mentioned it, so every excluded cell could read "Every
    // criterion you have on is satisfied here" and all 29 checks passed.
    name: 'every card claims the affirmative headline',
    // A regex with `\r?\n`: this file's targets are CRLF and an LF literal matches nothing,
    // which the runner reported as INERT. Fifth time, and the reason every multi-line anchor in
    // these runners is a regex.
    apply: (s) => s.replace(
      /`<div class="verdict">\$\{esc\(VERDICT_TEXT\[msg\.verdictName\]\r?\n      \|\| msg\.verdictName\)\}<\/div>`/,
      '`<div class="verdict">${esc(VERDICT_TEXT.INCLUDED)}</div>`'),
  },
  {
    // F7's second half: expected content being present does not mean foreign content is absent.
    name: 'a criterion block carries the other criteria destinations too',
    apply: (s) => s.replace('      const dest = destinationText(crit);',
      '      const dest = (msg.criteria.map(destinationText).filter(Boolean)[0]) || null;'),
  },
  {
    // F8: a reply that names no compute at all was exempted from the freshness check.
    name: 'a reply with no compute sequence is rendered anyway',
    apply: (s) => s.replace('          && msg.seq === s.displayedSeq;',
      '          && (msg.seq === undefined || msg.seq === s.displayedSeq);'),
  },
  // ------------------------------------------------- the request lifecycle (pass 51 B1 and B5)
  {
    // B1 restored: without the seq check, an explanation from the previous criteria renders over
    // the new raster.
    name: 'a reply is rendered without checking which compute it describes',
    apply: (s) => s.replace('          && msg.seq === s.displayedSeq;', ';'),
  },
  {
    // B5 and F4 together. The generation counter that first covered B5 was removed once the
    // position check subsumed it: both of its mutations survived, and dead defensive code is a
    // permanent survivor. This is the check that now carries both -- a reply must be about the
    // cell being inspected, and after `pointerLeft` no cell is.
    name: 'a reply is rendered without checking which cell it is about',
    apply: (s) => s.replace('          && atInspected', ''),
  },
  {
    name: 'a reply is matched to the inspected cell by row alone',
    apply: (s) => s.replace('          && msg.row === s.inspected.row && msg.col === s.inspected.col;',
      '          && msg.row === s.inspected.row;'),
  },
  {
    // F5: the failed-request transition. Without it the inspector wedges for ever.
    name: 'a failed request is left outstanding for ever',
    // A regex with `\r?\n`: card.js is CRLF and an LF literal matched nothing, which the runner
    // reported as INERT. Fourth time this session.
    apply: (s) => s.replace(/      requestFailed\(\) \{(\r?\n)        if \(!s\.pending\) return null;/,
      '      requestFailed() {$1        if (true) return null;'),
  },
  {
    name: 'a compute in flight leaves the previous one marked as displayed',
    apply: (s) => s.replace(/      computeStarted\(\) \{(\r?\n)        s\.displayedSeq = null;/,
      '      computeStarted() {$1        // left displayed'),
  },
  {
    name: 'an older compute claims the screen after a newer one',
    apply: (s) => s.replace('        if (seq !== newestSeq) return null;', ''),
  },
  {
    name: 'the inspected cell is not re-asked when the new raster paints',
    apply: (s) => s.replace('        return sendNow(s.inspected.row, s.inspected.col);',
      '        return null;'),
  },
  {
    name: 'leaving the data does not forget the inspected cell',
    apply: (s) => s.replace(/      pointerLeft\(\) \{(\r?\n)        s\.queued = null;(\r?\n)        s\.inspected = null;/,
      '      pointerLeft() {$1        s.queued = null;$2        // inspected kept'),
  },
  // NOT LISTED, deliberately: the generation check on the QUEUED position in `reply`.
  //
  // `pointerLeft` already sets `s.queued = null`, and that is the only way a generation can
  // change, so by the time `reply` looks at the queue it is empty whenever the generation has
  // moved. A mutation removing `next.gen === s.pointerGen` therefore SURVIVES every check, which
  // it did on the first run. The comparison stays as defence in depth should a future path ever
  // queue a position without clearing it, and it is recorded here as unguarded rather than left
  // to look like coverage. Same decision, and the same reasoning, as `state.lastInCount` in
  // `mutate_worker.mjs`.
  // ------------------------------------------------------------------ pass 52 finding F6
  // Three rendering corruptions that passed all 27 card checks, because the fixture-driven
  // checks inspected the disclosure's presence and the FIRST destination name and nothing else.
  {
    name: 'every criterion is displayed as a pass whatever it decided',
    apply: (s) => s.replace('<span class="outcome ${esc(crit.outcomeName)}">'
      + '${esc(crit.outcomeName)}</span>',
    '<span class="outcome ${esc(crit.outcomeName)}">PASS</span>'),
  },
  {
    name: 'every criterion displays the same limit',
    apply: (s) => s.replace('`<div>${esc(mins)} &middot; your limit ${esc(crit.thresholdMin)} min</div>`',
      '`<div>${esc(mins)} &middot; your limit 15 min</div>`'),
  },
  {
    name: 'only the first place of a shared node is displayed',
    apply: (s) => s.replace("    const names = (d.places || []).map((p) => p && p.name).filter(Boolean);",
      '    const names = (d.places || []).slice(0, 1).map((p) => p && p.name).filter(Boolean);'),
  },
  {
    name: 'the outside and not-yet-computed states are collapsed into one sentence',
    apply: (s) => s.replace("    if (msg.notComputed) return '<em>Nothing has been computed yet.</em>';",
      "    if (msg.notComputed) return '<em>Outside the published area.</em>';"),
  },
  // ------------------------------------------------------------------ pass 54, 2026-11-16
  // The wording changes are one string and one block position, which is exactly the kind of edit
  // a suite comparing the rendering against the same string cannot see. These four are the ways
  // each could be undone without any other check noticing.
  {
    name: 'the estimate note is dropped from the card',
    apply: (s) => s.replace(
      /,(\r?\n)    `<div class="estimate">\$\{esc\(ESTIMATE_NOTE\)\}<\/div>`\];/, '];'),
  },
  {
    // The whole point of the word. `encode_minutes` is `ceil`, so "to the nearest" understates
    // our own overstatement by up to 60 s -- and it reads MORE accurate, not less.
    name: 'the rounding is described as to the nearest minute',
    apply: (s) => s.replace("'and are rounded up to the whole minute.'",
      "'and are rounded to the nearest whole minute.'"),
  },
  {
    name: 'the estimate is described as measured from the address',
    apply: (s) => s.replace(
      "'Times are model estimates for a nearby grid point, not your address, '",
      "'Times are model estimates for this address, '"),
  },
  {
    // **Pass 55 F1, restored.** The published cell's centre is not where the time was measured:
    // the seconds come from a UTM cell centre a median 39.9 m away. This is the exact sentence
    // that shipped for a day, and the check that catches it must stay able to.
    name: 'the estimate claims the displayed cell\'s own centre as the origin',
    apply: (s) => s.replace(
      "'Times are model estimates for a nearby grid point, not your address, '\r\n    + 'and are rounded up to the whole minute.'",
      "'Times are estimates: measured from the centre of this cell, and '\r\n    + 'rounded up to the whole minute.'"),
  },
  {
    // **Pass 55 F2, restored.** A mutation of the CONSTANT, not of the rendering: every check
    // that compares the card against `VERDICT_TEXT` reads the mutated value and still agrees,
    // so only the pinned-literal check can catch this one. That is what it is for.
    name: 'the exclusion headline is stated as a fact about the place',
    apply: (s) => s.replace(
      "    EXCLUDED: 'Our model rules this cell out for at least one of your limits.',",
      "    EXCLUDED: 'At least one criterion is not satisfied here.',"),
  },
  {
    // A true swap back to the order this had before pass 54: the warning below the status
    // explanation, so "the time above" can point past another line at a time it does not mean.
    // Not a deletion -- the warning is still rendered, in the wrong place, which is the defect
    // pass 54 described and the one a presence check cannot see.
    name: 'the restricted-route warning moves back below the status explanation',
    apply: (s) => s.replace(
      /(      \/\/ The restricted-route disclosure[\s\S]*?'restricted way\.<\/div>'\);\r?\n      \}\r?\n)(\r?\n)(      if \(crit\.outcomeName === 'UNKNOWN'\) \{[\s\S]*?\r?\n      \}\r?\n)/,
      '$3$2$1'),
  },
];

const original = fs.readFileSync(TARGET, 'utf8');
let caught = 0;
const survived = [];
const inert = [];
const errored = [];

function run() {
  return spawnSync(process.execPath, [HARNESS], { encoding: 'utf8', timeout: 300000 });
}

const base = run();
if (base.status !== 0) {
  console.error('BASELINE IS NOT CLEAN -- nothing below means anything');
  console.error(`${base.stdout || ''}\n${base.stderr || ''}`.slice(-3000));
  process.exit(2);
}
console.log('baseline clean\n');

for (const m of MUTATIONS) {
  const mutated = m.apply(original);
  if (mutated === original) {
    inert.push(m.name);
    console.error(`INERT    ${m.name}  (the edit matched nothing; the guard is not testing it)`);
    continue;
  }
  fs.writeFileSync(TARGET, mutated, 'utf8');
  let out;
  try {
    out = run();
  } finally {
    fs.writeFileSync(TARGET, original, 'utf8');
  }
  const text = `${out.stdout || ''}\n${out.stderr || ''}`;
  const failLine = text.split('\n').find((l) => l.trim().startsWith('FAIL')) || '';
  // Only a harness that RAN and rejected the mutant counts. A crash, a signal or a syntax error
  // is an ERROR: pass 44 F2 found this runner's ancestor reporting "9 of 9 caught" with zero
  // mutants ever executed, because every spawn had failed with EPERM.
  if (out.error || out.signal || out.status === null) {
    errored.push(m.name);
    console.error(`ERROR    ${m.name}  (the harness did not run: `
      + `${out.error ? out.error.code || out.error.message : `signal ${out.signal}`})`);
  } else if (out.status === 0) {
    survived.push(m.name);
    console.error(`SURVIVED ${m.name}`);
  } else if (!failLine) {
    errored.push(m.name);
    console.error(`ERROR    ${m.name}  (exit ${out.status} with no FAIL line: the harness `
      + 'crashed rather than rejecting the mutant)');
  } else {
    caught++;
    console.log(`caught   ${m.name}\n           ${failLine.trim()}`);
  }
}

console.log(`\n${caught} of ${MUTATIONS.length} card mutations caught`
  + (inert.length ? `, ${inert.length} INERT` : '')
  + (survived.length ? `, ${survived.length} SURVIVED` : '')
  + (errored.length ? `, ${errored.length} ERRORED` : ''));
if (fs.readFileSync(TARGET, 'utf8') !== original) {
  console.error('card.js was left mutated');
  process.exit(2);
}
process.exit(survived.length === 0 && inert.length === 0 && errored.length === 0
  && caught === MUTATIONS.length ? 0 : 1);
