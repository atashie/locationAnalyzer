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
    name: 'the counts no longer describe the plane',
    apply: (s) => s.replace('          excludedCount++;', '          if (p % 7) excludedCount++;'),
  },
];

const original = fs.readFileSync(WORKER, 'utf8');
let caught = 0;
const survived = [];
const inert = [];

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
  if (out.status === 0) {
    survived.push(m.name);
    console.error(`SURVIVED ${m.name}`);
  } else {
    caught++;
    const first = (out.stdout || '').split('\n').find((l) => l.startsWith('FAIL')) || '';
    console.log(`caught   ${m.name}\n           ${first.trim()}`);
  }
}

console.log(`\n${caught} of ${MUTATIONS.length} mutations caught`
  + (inert.length ? `, ${inert.length} INERT` : '')
  + (survived.length ? `, ${survived.length} SURVIVED` : ''));
if (fs.readFileSync(WORKER, 'utf8') !== original) {
  console.error('worker.js was left mutated');
  process.exit(2);
}
process.exit(survived.length === 0 && inert.length === 0 ? 0 : 1);
