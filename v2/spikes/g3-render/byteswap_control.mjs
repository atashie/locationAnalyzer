// What actually catches a big-endian read of the destination plane?
//
// Run the big-endian mutation against ONLY the byte-swap group. Ordinals 1 and 256 swap into each
// other and both index a real destination, so no STRUCTURAL check can notice -- which makes this
// a focused experiment on what the comparison against a recorded answer is doing.
//
// **The reason this file originally gave for existing was wrong (pass 50 finding G2).** It said
// the mutation runner "stops at the first failing check", so the byte-swap group would never be
// reached and was decoration. It is not: `check()` catches each failure and continues, and under
// the endian mutation the harness runs all its checks and the byte-swap group fails among them --
// 8 failures, including `(0, 0) ordinal 256, expected 1`. `mutate_worker.mjs` merely PRINTS the
// first failure. The group is reached and does its job. This control remains useful as an
// isolated experiment; the claim that it was load-bearing is withdrawn.
//
// **Pass 49 finding 6 corrected the conclusion this file used to draw.** It printed "the name
// comparison is the only thing that catches a big-endian read", and that is wrong twice over.
// The vectors record the expected ORDINAL beside the expected name, so in the harness
// `got.ordinal === want.ordinal` fires first and the name is never reached. What a swap survives
// is the bounds check; what catches it is comparing against a recorded expectation at all.
//
// The same finding showed this control could print CONFIRMED without performing an endian
// mutation. It never required the baseline to be right, never required its own replacement to
// have applied, and accepted "some name is wrong" as the evidence -- so reformatting the
// little-endian expression to make the replacement inert, plus any unrelated wrong-name defect,
// satisfied it. A positive control that passes on the wrong cause is not a control. All three
// conditions are now required, and the expected swapped ordinals are named explicitly.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const DIR = String.raw`C:\Users\arikt\documents\github\distanceFinder\v2\spikes\g3-render`;
const FIX = path.join(DIR, 'fixtures', 'conformance');
const src = fs.readFileSync(path.join(DIR, 'worker.js'), 'utf8');
const vectors = JSON.parse(fs.readFileSync(path.join(FIX, 'vectors.json'), 'utf8'));

const MUTATION = (s) => s.replace(
  'out[i] = bytes[2 * i] | (bytes[2 * i + 1] << 8);',
  'out[i] = (bytes[2 * i] << 8) | bytes[2 * i + 1];');

function load(source) {
  const outbox = [];
  const ctx = vm.createContext({
    performance, ArrayBuffer, Uint8Array, Uint16Array, Uint32Array, Int8Array,
    self: { postMessage: (m) => outbox.push(m), onmessage: null },
  });
  vm.runInContext(source, ctx);
  return {
    send(m) { outbox.length = 0; ctx.self.onmessage({ data: m }); return outbox.slice(); },
  };
}

const group = vectors.groups.find((g) => g.name === 'destination ordinals that survive a byte swap');
if (!group) throw new Error('the byte-swap group is missing from the vectors');
const planeBytes = (f) => {
  const b = fs.readFileSync(path.join(FIX, f));
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
};

function run(source, label) {
  const w = load(source);
  const init = {
    type: 'init',
    manifest: {
      nrows: group.nrows, ncols: group.ncols, encoding: vectors.encoding,
      destination_plane_byte_order: vectors.destination_plane_byte_order,
      layers: group.layers,
    },
    values: group.layers.map((l) => planeBytes(l.value_file)),
    statuses: group.layers.map((l) => planeBytes(l.status_file)),
    destinations: group.layers.map((l) => (l.dest_file ? planeBytes(l.dest_file) : null)),
    destTables: group.dest_tables,
  };
  const ready = w.send(init);
  const err = ready.find((m) => m.type === 'error');
  if (err) return { label, refusedAtInit: err.message };
  const c = group.cases[0];
  w.send({ type: 'compute', seq: 1, thresholds: c.thresholds, enabled: c.enabled });
  const got = [];
  for (const q of c.destination_at) {
    const d = w.send({ type: 'destinationAt', reqId: 1, row: q.row, col: q.col })
      .find((m) => m.type === 'destinationAt');
    got.push({
      cell: [q.row, q.col],
      ordinal: d.namesDestination ? d.namesDestination[0].ordinal : null,
      name: d.namesDestination ? d.namesDestination[0].places[0].name : null,
      expected: q.names ? q.names[0].first_place_name : null,
      expectedOrdinal: q.names ? q.names[0].ordinal : null,
      // The baseline requirement is "answers correctly", not "answers the two fields this file
      // happens to look at" -- which is the mistake pass 49 finding 5 found in the harness.
      nodeIndex: d.namesDestination ? d.namesDestination[0].nodeIndex : null,
      expectedNodeIndex: q.names ? q.names[0].node_index : null,
      names: d.namesDestination ? d.namesDestination[0].places.map((pl) => pl.name) : null,
      expectedNames: q.names ? q.names[0].place_names : null,
    });
  }
  return { label, got };
}

// The mutation must actually have been applied. Without this, an edit to the formatting of the
// little-endian expression makes `replace` a no-op and everything below runs on the real worker.
const mutatedSrc = MUTATION(src);
if (mutatedSrc === src) {
  console.log('NOT CONFIRMED: the endian replacement did not apply, so nothing was mutated. The '
    + 'anchor in MUTATION no longer matches worker.js.');
  process.exit(1);
}

// What a byte swap does to these two ordinals, written down rather than inferred: 1 -> 256 and
// 256 -> 1. "In range" is not the claim; these exact values are.
//
// Pass 50 finding G1: comparing the mutated ordinals against the BASELINE's byte-swaps is a
// RELATIVE test, and a worker whose baseline already returns 256 where 1 is expected satisfies it
// -- its mutated run returns 1, which is the swap of its own wrong baseline. So the expectation
// has to be absolute: the ordinals the VECTORS record, and their swaps.
const EXPECTED_ORDINALS = [1, 256];
const SWAPPED = new Map([[1, 256], [256, 1]]);

const base = run(src, 'baseline');
const mut = run(mutatedSrc, 'big-endian');
console.log(JSON.stringify(base, null, 1));
console.log(JSON.stringify(mut, null, 1));

if (base.refusedAtInit) {
  console.log('\nNOT CONFIRMED: the UNMUTATED worker refused this group, so the fixture or the '
    + 'worker is broken and the experiment below would measure that instead.');
  process.exit(1);
}
// The baseline must be exactly right, or a wrong answer under the mutation proves nothing about
// the mutation.
const baseOk = base.got.every((r) => r.name === r.expected)
  // The ordinal against what the VECTORS say it is, not merely against "not null". Without this
  // the whole experiment is relative to a baseline that may already be wrong.
  && base.got.every((r) => r.ordinal === r.expectedOrdinal)
  && base.got.every((r) => r.nodeIndex === r.expectedNodeIndex)
  && base.got.every((r) => JSON.stringify(r.names) === JSON.stringify(r.expectedNames));
// And the group really is the one built for this hazard, with the two ordinals named above.
const rightGroup = JSON.stringify(base.got.map((r) => r.expectedOrdinal))
  === JSON.stringify(EXPECTED_ORDINALS);
if (!rightGroup) {
  console.log('\nNOT CONFIRMED: the byte-swap group no longer expects ordinals '
    + `${JSON.stringify(EXPECTED_ORDINALS)}, so this file is testing a different fixture than the `
    + 'one it reasons about.');
  process.exit(1);
}
if (!baseOk) {
  console.log('\nNOT CONFIRMED: the baseline does not already answer correctly, so this cannot '
    + 'attribute a wrong answer to the byte order.');
  process.exit(1);
}

if (mut.refusedAtInit) {
  console.log('\nThe byte-swap group refused at INIT, so a structural check caught it here too.');
  console.log('That is still not a comparison against a recorded answer. Reported honestly.');
  process.exit(1);
}

// The ordinals must be the swaps of the RECORDED expectations -- absolute, not relative to a
// baseline that could itself be wrong.
const swappedOrdinals = mut.got.length === base.got.length
  && mut.got.every((r, i) => r.ordinal === SWAPPED.get(base.got[i].expectedOrdinal));
const wrongName = mut.got.some((r) => r.name !== r.expected);
const inRange = mut.got.every((r) => r.ordinal !== null);
const confirmed = swappedOrdinals && wrongName && inRange;
console.log(confirmed
  ? '\nCONFIRMED: every ordinal stayed in range, became exactly its byte-swap, and resolved to '
    + 'the wrong shop.\nNo structural check can see this. What catches it is comparing against a '
    + 'recorded expectation --\nthe ordinal first, since the vectors record that too, and the '
    + 'name behind it.'
  : '\nNOT CONFIRMED: '
    + (!swappedOrdinals ? 'the ordinals are not the byte-swaps of the baseline\'s, so whatever '
      + 'went wrong here is not the byte order.'
      : 'the swapped ordinals did not produce a wrong resolved name.'));
process.exit(confirmed ? 0 : 1);
