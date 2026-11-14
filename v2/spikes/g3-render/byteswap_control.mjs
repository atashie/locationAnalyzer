// Is the NAME comparison load-bearing, or does the bounds check do all the work?
//
// The big-endian mutation is reported caught, but the mutation runner stops at the first failing
// check -- which is the two-naming-layers group's init, where small ordinals byte-swap out of
// range and the BOUNDS check fires. That would mean the 300-entry byte-swap group, built for
// exactly this hazard, is never the thing that catches it, and the group is decoration.
//
// So: run the mutated worker against ONLY the byte-swap group. Ordinals 1 and 256 swap into each
// other and both index a real destination, so every structural check passes and the only
// observable difference is the shop name.
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
    });
  }
  return { label, got };
}

const base = run(src, 'baseline');
const mut = run(MUTATION(src), 'big-endian');
console.log(JSON.stringify(base, null, 1));
console.log(JSON.stringify(mut, null, 1));

if (mut.refusedAtInit) {
  console.log('\nThe byte-swap group refused at INIT, so a structural check caught it here too.');
  console.log('That is still not the name comparison. Reported honestly rather than claimed.');
  process.exit(1);
}
const wrongName = mut.got.some((r) => r.name !== r.expected);
const inRange = mut.got.every((r) => r.ordinal !== null);
console.log(wrongName && inRange
  ? '\nCONFIRMED: every ordinal stayed in range, every structural check passed, and the NAME is '
    + 'wrong.\nThe name comparison is the only thing that catches a big-endian read.'
  : '\nNOT CONFIRMED: the name comparison is not the thing doing the work here.');
process.exit(wrongName && inRange ? 0 : 1);
