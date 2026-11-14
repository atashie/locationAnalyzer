// mutate_worker.mjs — does the conformance harness actually catch a wrong decoder?
//
// Codex pass 43 F2 found that it did not. The harness reconstructed verdicts from the RGBA
// buffer, where EXCLUDED and UNKNOWN are only distinguishable on the hatch stripe, so three
// quarters of the cells were compared against nothing and the real-layer window — which carries
// no inline expected array — was compared against nothing at all. Two wrong implementations
// passed all 37 of its checks: one returning UNKNOWN for NO_PATH, and one rotating the entire
// raster by 10,007 cells.
//
// So the harness is now itself checked. Each mutation below is a decoder defect that has to be
// caught; a mutation that survives is reported as a hole, not as a pass. This is the same
// discipline as `scripts/mutate_exact_geometry.py` and `scripts/mutate_certify.py`, moved to the
// one layer that had a check nobody had tested.
//
// Run:  node spikes/g3-render/mutate_worker.mjs

import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER = path.join(__dirname, 'worker.js');
const HARNESS = path.join(__dirname, 'worker_conformance.mjs');

/** Each mutation: a name, and a (source -> source) edit that must change behaviour. */
const MUTATIONS = [
  {
    name: 'NO_PATH becomes unknown instead of a known failure',
    apply: (s) => s.replace(/case S_NO_PATH:\s*\n\s*return O_FAIL;/,
      'case S_NO_PATH:\n      return O_UNKNOWN;'),
  },
  {
    name: 'the whole raster is rotated by 10,007 cells',
    apply: (s) => s.replace('const tEnd = performance.now();',
      `{ const nn = state.nrows * state.ncols;
         if (nn > 20000) {
           const mv = state.mask.slice(), vv = state.verdict.slice();
           for (let i = 0; i < nn; i++) { state.mask[i] = mv[(i + 10007) % nn]; state.verdict[i] = vv[(i + 10007) % nn]; }
         } }
       const tEnd = performance.now();`),
  },
  {
    name: 'an off-network bound no longer proves a failure',
    apply: (s) => s.replace('return value > thresholdMin ? O_FAIL : O_UNKNOWN;',
      'return O_UNKNOWN;'),
  },
  {
    name: 'the beyond-horizon comparison is flipped',
    apply: (s) => s.replace('return horizonS >= 60 * thresholdMin ? O_FAIL : O_UNKNOWN;',
      'return horizonS < 60 * thresholdMin ? O_FAIL : O_UNKNOWN;'),
  },
  {
    name: 'an unknown beats a known failure (the pre-v2 break, restored)',
    // Multi-line anchors are regexes tolerant of CRLF. A literal newline matched nothing
    // in a CRLF working tree, and the INERT report caught that rather than banking it as
    // a pass -- which is the whole reason this file reports INERT separately.
    apply: (s) => s.replace(/if \(o === O_FAIL\) anyFail = 1;\r?\n\s*else if \(o === O_UNKNOWN\) anyUnknown = 1;/,
      'if (o === O_UNKNOWN) { anyUnknown = 1; break; }\n          else if (o === O_FAIL) anyFail = 1;'),
  },
  {
    name: 'the OK comparison is strict',
    apply: (s) => s.replace('return value <= thresholdMin ? O_PASS : O_FAIL;',
      'return value < thresholdMin ? O_PASS : O_FAIL;'),
  },
  {
    name: 'no criteria excludes everything instead of including it',
    apply: (s) => s.replace(/mask\.fill\(1\);\r?\n\s*verdict\.fill\(V_INCLUDED\);\r?\n\s*px\.fill\(PX_IN\);\r?\n\s*inCount = n;/,
      'mask.fill(0);\n    verdict.fill(V_EXCLUDED);\n    px.fill(PX_OUT);\n    inCount = 0;'),
  },
  {
    name: 'the mask disagrees with the verdict plane',
    apply: (s) => s.replace(/mask\[p\] = 1;\r?\n\s*verdict\[p\] = V_INCLUDED;/,
      'mask[p] = (p % 1000 === 0) ? 0 : 1;\n          verdict[p] = V_INCLUDED;'),
  },
  {
    // Pass 44 F1. The RGBA buffer is wiped AFTER every per-cell write, so the verdict plane, the
    // mask and the counts are all correct and the overlay shows nothing at all.
    name: 'the overlay is blanked just before it is posted',
    apply: (s) => s.replace('const tEnd = performance.now();',
      'px.fill(0); const tEnd = performance.now();'),
  },
  {
    // Pass 44 F1. `mask[p] = 2` satisfies `(mask[i] === 1) === (verdict === INCLUDED)` at an
    // excluded cell, and app.js polygonizes at 0.5 -- so 225,520 excluded pixels at 15 minutes
    // enter the polygon's included set. The mask is a consumer output, not a debug aid.
    name: 'excluded mask cells carry 2 instead of 0',
    apply: (s) => s.replace(/mask\[p\] = 0;\r?\n\s*verdict\[p\] = V_EXCLUDED;/,
      'mask[p] = 2;\n          verdict[p] = V_EXCLUDED;'),
  },
  {
    name: 'excluded cells are painted with the included colour',
    apply: (s) => s.replace(/verdict\[p\] = V_EXCLUDED;\r?\n\s*px\[p\] = PX_OUT;/,
      'verdict[p] = V_EXCLUDED;\n          px[p] = PX_IN;'),
  },
  {
    name: 'the unknown hatch is dropped, so unknown renders as excluded',
    apply: (s) => s.replace(
      "px[p] = (((r + c) & HATCH_PERIOD_MASK) < HATCH_WIDTH) ? PX_NODATA : PX_OUT;",
      'px[p] = PX_OUT;'),
  },
  {
    // The disclosure must never be an eligibility input. If the flag can move a verdict, the
    // flags-withheld control in the harness diverges from the same expectations.
    name: 'a restricted route is treated as an exclusion',
    apply: (s) => s.replace(
      'if (o === O_FAIL) anyFail = 1;',
      'if (o === O_FAIL || (F[k] && F[k][p] === ROUTE_RESTRICTED)) anyFail = 1;'),
  },
  {
    // The disclosure stops being counted at all, while every verdict stays correct -- which
    // is the shape of a silent disclosure failure: nothing looks broken.
    name: 'the disclosure is never counted',
    apply: (s) => s.replace(/if \(disclosingLayers\) \{\r?\n/, 'if (false) {\n'),
  },
  {
    // Counting the flag on EXCLUDED cells too, rather than only where the verdict is
    // INCLUDED. The verdicts stay correct and only the disclosure count is wrong.
    name: 'the disclosure counts cells that were not included',
    apply: (s) => s.replace(
      'verdict[p] = V_EXCLUDED;',
      'verdict[p] = V_EXCLUDED; if (F[0] && F[0][p] === 1) restrictedIncludedCount++;'),
  },
  {
    name: 'a missing flag plane reports zero instead of null',
    apply: (s) => s.replace(
      'restrictedIncludedCount: disclosingLayers ? restrictedIncludedCount : null,',
      'restrictedIncludedCount: restrictedIncludedCount,'),
  },
  {
    name: 'the flag-versus-status invariant is not checked at init',
    apply: (s) => s.replace(
      'if (v === ROUTE_RESTRICTED && statuses[k][p] !== S_OK) {',
      'if (false) {'),
  },
  {
    // Pass 48. Correct whenever a bundle has ONE disclosing layer, which every fixture had.
    name: 'every layer\'s flag is read from layer 0',
    apply: (s) => s.replace(
      'if (F[k] && F[k][p] === ROUTE_RESTRICTED) { restrictedIncludedCount++; break; }',
      'if (F[0] && F[0][p] === ROUTE_RESTRICTED) { restrictedIncludedCount++; break; }'),
  },
  {
    // Pass 48. Without the break a cell flagged in two enabled layers counts twice, so the
    // disclosure count exceeds the number of cells disclosed about.
    name: 'a cell flagged in two layers is counted twice',
    apply: (s) => s.replace(
      'if (F[k] && F[k][p] === ROUTE_RESTRICTED) { restrictedIncludedCount++; break; }',
      'if (F[k] && F[k][p] === ROUTE_RESTRICTED) { restrictedIncludedCount++; }'),
  },
  {
    // Pass 48, and the sharpest of the three: the guarantee that a disclosure cannot move a
    // verdict, defeated under exactly the condition no fixture created. `m` is the number of
    // ENABLED layers, so this is inert on every single-layer case.
    name: 'the flag excludes cells, but only when two layers are enabled',
    apply: (s) => s.replace(
      'if (o === O_FAIL) anyFail = 1;',
      'if (o === O_FAIL || (m > 1 && F[k] && F[k][p] === ROUTE_RESTRICTED)) anyFail = 1;'),
  },
  {
    // The plane's signature failure: read big-endian, ordinals 1 and 256 swap into each other,
    // both index a real destination, every structural check passes and the shop name is wrong.
    name: 'the destination plane is read big-endian',
    apply: (s) => s.replace(
      'out[i] = bytes[2 * i] | (bytes[2 * i + 1] << 8);',
      'out[i] = (bytes[2 * i] << 8) | bytes[2 * i + 1];'),
  },
  {
    // Correct whenever a bundle names destinations in ONE layer, which is why the two-layer
    // fixture exists.
    // Anchored on the line AFTER, because the init-invariant loop and the query hold the
    // same statement and an unanchored replace silently hits the first one.
    name: 'the destination QUERY reads every layer from layer 0',
    apply: (s) => s.replace(
      /const d = destinations\[k\]\[p\];(\r?\n\s*)if \(d === DEST_NONE\) continue;/,
      'const d = destinations[0][p];$1if (d === DEST_NONE) continue;'),
  },
  {
    name: 'the destination INVARIANT CHECK reads every layer from layer 0',
    apply: (s) => s.replace(
      /const d = destinations\[k\]\[p\];(\r?\n\s*)const named = d !== DEST_NONE;/,
      'const d = destinations[0][p];$1const named = d !== DEST_NONE;'),
  },
  {
    // A disabled criterion is not on screen, so naming its destination answers a question the
    // household did not ask.
    name: 'the destination query ignores which criteria are enabled',
    apply: (s) => s.replace(
      'if (state.lastEnabled && !state.lastEnabled[k]) continue;', ''),
  },
  {
    name: 'a destination is named for an excluded cell',
    apply: (s) => s.replace('if (verdict[p] !== 0) {', 'if (false) {'),
  },
  {
    // "this bundle does not say" rendered as "there is none" -- the UNKNOWN_CAUSE lesson again.
    name: 'naming nothing reports an empty list instead of null',
    apply: (s) => s.replace('namesDestination: named.length ? named : null });',
                            'namesDestination: named });'),
  },
  {
    // The direction the route flag cannot have. Disabling it lets a plane and a surface disagree
    // about whether a journey exists at all.
    name: 'a published time with no destination is accepted',
    apply: (s) => s.replace('if (!named && statuses[k][p] === S_OK) {', 'if (false) {'),
  },
  {
    name: 'a destination ordinal past the side table is accepted',
    apply: (s) => s.replace('if (named && d >= table.destinations.length) {', 'if (false) {'),
  },
  {
    // The set IS the answer, so collapsing it to its first member asserts a comparison the
    // routing never made: the cost-argmin is over NODES.
    name: 'the destination set is collapsed to its first place',
    apply: (s) => s.replace('places: entry.places,', 'places: entry.places.slice(0, 1),'),
  },
  {
    name: 'the counts no longer describe the plane',
    apply: (s) => s.replace('          excludedCount++;', '          if (p % 7) excludedCount++;'),
  },
];

const original = fs.readFileSync(WORKER, 'utf8');
let caught = 0;
const survived = [];
const inert = [];
const errored = [];

// A mutation that does not change the source is a broken mutation, not a passing decoder.
for (const m of MUTATIONS) {
  const mutated = m.apply(original);
  if (mutated === original) {
    inert.push(m.name);
    console.error(`INERT    ${m.name}  (the edit matched nothing; the guard is not testing it)`);
    continue;
  }
  fs.writeFileSync(WORKER, mutated, 'utf8');
  let out;
  try {
    out = spawnSync(process.execPath, [HARNESS], { encoding: 'utf8', timeout: 300000 });
  } finally {
    fs.writeFileSync(WORKER, original, 'utf8');
  }
  // Pass 44 F2: this used to count EVERY non-zero outcome as a catch, including `status: null`
  // from a spawn error. In the reviewer's session `spawnSync` returned EPERM and the runner
  // reported "9 of 9 mutations caught" with ZERO mutated decoders ever executed. A gate that is
  // green when it did not run is worse than no gate, so the only accepted catch is the harness
  // exiting 1 having printed a FAIL line -- a crash, a signal, a timeout or a syntax error is an
  // ERROR, and is reported as one.
  const text = `${out.stdout || ''}\n${out.stderr || ''}`;
  const failLine = text.split('\n').find((l) => l.trim().startsWith('FAIL')) || '';
  if (out.error || out.signal || out.status === null) {
    errored.push(`${m.name} (${out.error ? out.error.code || out.error.message : out.signal})`);
    console.error(`ERROR    ${m.name}  (the harness did not run: `
      + `${out.error ? out.error.code || out.error.message : `signal ${out.signal}`})`);
  } else if (out.status === 0) {
    survived.push(m.name);
    console.error(`SURVIVED ${m.name}`);
  } else if (out.status !== 1 || !failLine) {
    errored.push(`${m.name} (exit ${out.status}, no FAIL line)`);
    console.error(`ERROR    ${m.name}  (exit ${out.status} without a FAIL line: the harness `
      + 'crashed rather than rejecting the mutant)');
  } else {
    caught++;
    console.log(`caught   ${m.name}\n           ${failLine.trim()}`);
  }
}

console.log(`\n${caught} of ${MUTATIONS.length} mutations caught`
  + (inert.length ? `, ${inert.length} INERT` : '')
  + (survived.length ? `, ${survived.length} SURVIVED` : '')
  + (errored.length ? `, ${errored.length} ERRORED` : ''));
if (fs.readFileSync(WORKER, 'utf8') !== original) {
  console.error('worker.js was left mutated');
  process.exit(2);
}
process.exit(survived.length === 0 && inert.length === 0 && errored.length === 0
  && caught === MUTATIONS.length ? 0 : 1);
