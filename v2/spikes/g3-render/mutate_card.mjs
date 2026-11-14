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
    // A lower bound printed as a measurement.
    name: 'a lower bound is printed as a measured time',
    apply: (s) => s.replace(
      'return crit.valueIsLowerBound ? `at least ${crit.value} min` : `${crit.value} min`;',
      'return `${crit.value} min`;'),
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
      "      return '<div class=\"verdict\">Every criterion you have on is satisfied here.</div>';"),
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
  {
    name: 'the outside and not-yet-computed states are collapsed into one sentence',
    apply: (s) => s.replace("    if (msg.notComputed) return '<em>Nothing has been computed yet.</em>';",
      "    if (msg.notComputed) return '<em>Outside the published area.</em>';"),
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
