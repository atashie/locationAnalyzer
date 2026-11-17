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
    // Was 'the unknown hatch is dropped'. The hatch is gone -- it is the thing that was wrong --
    // so the mutation now drops the TINT, which is the same defect in its remaining form: an
    // unknown cell rendering with excluded's bytes.
    name: 'the unknown tint is dropped, so unknown renders as excluded',
    apply: (s) => s.replace(
      'px[p] = PX_NODATA;',
      'px[p] = PX_OUT;'),
  },
  {
    // The hatch marked a quarter of the unknown cells and this reintroduces it, because that is
    // the specific regression this change exists to prevent and nothing else would catch it: the
    // counts, the verdict plane and the mask are all unchanged by it. Only the per-pixel check
    // sees it.
    name: 'the diagonal hatch returns, so three quarters of unknown renders as excluded',
    apply: (s) => s.replace(
      'px[p] = PX_NODATA;',
      'px[p] = (((r + c) & 7) < 2) ? PX_NODATA : PX_OUT;'),
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
  // ------------------------------------------------------------------ pass 49 finding 5
  // Four defects that passed all 71 checks. Three of them are variations on the same hole: the
  // harness compared the ordinal, the count and the FIRST place's name, so anything that left
  // those three alone was invisible. The fourth is a missing refusal case.
  {
    // The count survives, the first name survives, and every other name is wrong. This is the
    // mutation that proves checking one member of a set is not checking the set.
    name: 'every place after the first is renamed',
    apply: (s) => s.replace('places: entry.places,',
                            "places: entry.places.map((p, i) => (i ? { ...p, name: 'WRONG' } : p)),"),
  },
  {
    // Collapsing the set while PRESERVING its length. `places.length === placeCount` holds, so
    // the shape check passes and the answer is three copies of one shop.
    name: 'the destination set is filled with copies of its first place',
    apply: (s) => s.replace('places: entry.places,',
                            'places: entry.places.map(() => entry.places[0]),'),
  },
  {
    // The node the journey was measured to, which nothing compared before pass 49.
    name: 'the destination node index is a constant',
    apply: (s) => s.replace('nodeIndex: entry.node_index,', 'nodeIndex: 999999,'),
  },
  {
    // The other half of the two-directional invariant. Its partner above had a refusal case and
    // this one did not, so deleting it was free.
    name: 'a destination named where no time is published is accepted',
    apply: (s) => s.replace('if (named && statuses[k][p] !== S_OK) {', 'if (false) {'),
  },
  {
    // Pass 49 finding 7: silence about the byte order read as little-endian by default.
    name: 'an undeclared destination byte order is read as little-endian',
    apply: (s) => s.replace("if (anyPlane && manifest.destination_plane_byte_order !== 'little') {",
                            "if (anyPlane && manifest.destination_plane_byte_order !== 'little'\n"
                            + '        && manifest.destination_plane_byte_order !== undefined) {'),
  },
  {
    // Pass 49 finding 11: allocation read as evaluation, so a zero-filled verdict plane answered
    // "included" for a cell no criterion had been applied to.
    name: 'a destination query before any compute answers from the zero-filled verdict plane',
    // Anchored on the reply that follows, not on the bare `if`. There are now three handlers
    // carrying `if (!state.computed) {` and `String.replace` with a string takes the FIRST, so a
    // bare anchor silently retargets whenever a handler is added above this one -- and would then
    // report "caught" for a mutation of a function it was not testing.
    apply: (s) => s.replace(
      /  if \(!state\.computed\) \{(\r?\n)    self\.postMessage\(\{ \.\.\.reply, notComputed: true, included: null,/,
      '  if (false) {$1    self.postMessage({ ...reply, notComputed: true, included: null,'),
  },
  {
    // Pass 49 finding 9: a byte count that omits the largest plane.
    name: 'the reported byte count omits the destination plane',
    apply: (s) => s.replace('+ (routeFlags[k] ? 1 : 0) + (destinations[k] ? 2 : 0)), 0),',
                            '+ (routeFlags[k] ? 1 : 0)), 0),'),
  },
  // ------------------------------------------------------------------ pass 50
  // Seven more that passed all 75 checks. Three of them existed because the harness compared the
  // reply against the very object the worker was handed, so a worker that rewrote its own input
  // in place agreed with itself.
  {
    // The whole-record comparison now runs against a frozen snapshot taken before init, so this
    // is caught. It passed before, every GERS id and licence corrupted.
    name: 'every returned place record has its gers_id and licence rewritten',
    apply: (s) => s.replace(
      'const entry = destTables[k].destinations[d];',
      'const entry = destTables[k].destinations[d];\n'
      + "    entry.places.forEach((pl) => { pl.gers_id = 'WRONG'; pl.licence = 'Proprietary'; });"),
  },
  {
    // There was no destination-length refusal case at all, so a plane of the wrong size was read
    // as if it were right and every ordinal after the first came from the wrong cell.
    name: 'the destination plane length check is removed',
    apply: (s) => s.replace('if (buf.byteLength !== n * 2) {', 'if (false) {'),
  },
  {
    // `| 0` before the bounds check: 4294967296 wraps to 0 and gets a confident answer.
    name: 'a destination coordinate is coerced instead of validated',
    apply: (s) => s.replace('if (!Number.isInteger(row) || !Number.isInteger(col)) {',
                            'if (false) {'),
  },
  {
    // The lifecycle class, not the one reader pass 49 fixed.
    name: 'verdicts are served from the zero-filled plane before any compute',
    apply: (s) => s.replace(
      "    throw new Error('verdicts requested before any compute has run; the plane is allocated and ",
      "    if (false) throw new Error('verdicts requested before any compute has run; the plane is allocated and "),
  },
  {
    name: 'the mask is served before any compute',
    apply: (s) => s.replace(
      "    throw new Error('mask requested before any compute has run; there is no region to report and ",
      "    if (false) throw new Error('mask requested before any compute has run; there is no region to report and "),
  },
  // NOT LISTED, deliberately: `state.lastInCount = 0` at init.
  //
  // Pass 50 finding D1 observed a fresh zero mask arriving with the previous bundle's count, and
  // the reset is in `worker.js` because that was a real contradiction. But the same finding's
  // other half -- refusing `mask` until a compute has run -- makes the stale value UNREACHABLE
  // through the message protocol: the only message that carries `inCount` cannot be obtained
  // between an init and a compute, and a compute recomputes it. So removing the reset changes no
  // observable behaviour, and a mutation for it SURVIVES every check. It is listed here as absent
  // rather than left to look like an oversight: the reset stays as defence in depth should the
  // lifecycle guard ever be relaxed, and nothing in this suite claims to be guarding it.
  {
    // A compute that throws part-way leaves the planes half rewritten, labelled with the
    // sequence number of the compute before it.
    name: 'a failed compute leaves its half-written plane readable',
    // Anchored on the blank line and the Hoist comment that follow, because the same two
    // statements appear in the init reset. Pass 49's lesson about identical statements.
    // Re-anchored 2026-11-14: `state.lastThresholds = null;` and its comment now sit between
    // these statements and the Hoist comment, so the old anchor matched nothing. It was reported
    // INERT on the first run after the change, which is what that distinction is for.
    apply: (s) => s.replace(
      /state\.computed = false;(\r?\n)  state\.lastSeq = -1;\1  \/\/ Cleared on the way IN/,
      '// the reset is gone$1  // Cleared on the way IN'),
  },

  // ------------------------------------------------------------------ explainAt, the card's data
  // `explainAt` RECOMPUTES the per-layer outcomes that `handleCompute` discards, so the whole
  // risk is that it recomputes something else and the card confidently explains a verdict nobody
  // reached. The fold check in the harness is the guard; these are what test the guard.
  {
    name: 'explainAt reports every criterion as a pass',
    apply: (s) => s.replace('const outcome = outcomeFor(status, raw, thresholdMin, horizons[k]);',
      'const outcome = O_PASS;'),
  },
  {
    name: 'explainAt softens a known failure into an unknown',
    apply: (s) => s.replace('const outcome = outcomeFor(status, raw, thresholdMin, horizons[k]);',
      'let outcome = outcomeFor(status, raw, thresholdMin, horizons[k]);'
      + ' if (outcome === O_FAIL) outcome = O_UNKNOWN;'),
  },
  {
    // `lastThresholds` is per ENABLED layer in enabled order. Indexing it by layer index hands
    // the wrong threshold to every layer after a disabled one, and the fold cannot see it
    // whenever the two thresholds happen to agree -- which they do in most of these fixtures.
    name: 'the threshold is read by layer index instead of enabled position',
    apply: (s) => s.replace('state.lastThresholds[enabledIndex]', 'state.lastThresholds[k]'),
  },
  {
    name: 'a layer that does not disclose reports no restriction instead of nothing',
    apply: (s) => s.replace('routeFlag: routeFlags[k] ? routeFlags[k][p] : null,',
      'routeFlag: routeFlags[k] ? routeFlags[k][p] : 0,'),
  },
  {
    name: 'VALUE_NONE reaches the card as the number 255',
    apply: (s) => s.replace(
      'value: (status === S_OK || bounded) && raw !== VALUE_NONE ? raw : null,',
      'value: raw,'),
  },
  {
    name: 'no enabled criteria reports an empty list instead of nothing',
    apply: (s) => s.replace('criteria: criteria.length ? criteria : null,', 'criteria,'),
  },
  {
    name: 'explainAt explains the zero-filled plane before any compute',
    // `verdict: null` is what makes this explainAt's guard and not destinationAt's. The first
    // version of this anchor stopped at `notComputed: true,` and matched destinationAt, which is
    // earlier in the file -- so it reported CAUGHT by failing the destination check while
    // explainAt's guard was never touched. A control that can pass on the wrong cause is not a
    // control (ledger 30), and this one did.
    apply: (s) => s.replace(
      /  if \(!state\.computed\) \{(\r?\n)    self\.postMessage\(\{ \.\.\.reply, notComputed: true, verdict: null,/,
      '  if (false) {$1    self.postMessage({ ...reply, notComputed: true, verdict: null,'),
  },
  {
    name: 'explainAt coerces a coordinate before checking its bounds',
    apply: (s) => s.replace(
      /const row = msg\.row;(\r?\n)  const col = msg\.col;(\r?\n)  const reply = \{ type: 'explainAt'/,
      "const row = msg.row | 0;$1  const col = msg.col | 0;$2"
      + "  const reply = { type: 'explainAt'"),
  },
  // REMOVED, not re-anchored: 'explainAt names a destination at a cell the region excludes'.
  // It tested the rule pass 51 finding B4 refuted. Suppressing a criterion's destination because
  // a DIFFERENT criterion failed made the card claim the layer does not disclose one, which is
  // false, so naming it is now the correct behaviour and the mutation inverted into
  // 'explainAt withholds a destination because another criterion failed' above. Recorded as
  // withdrawn rather than deleted silently: a mutation that disappears looks like coverage that
  // was never there.
  {
    // A reader that writes. Every per-cell assertion would still pass, because the explanation
    // and the plane would agree -- on the value the reader had just put there. Re-anchored after
    // B4 removed the `included` local; reported INERT on the first run after that.
    name: 'explainAt writes to the verdict plane while reading it',
    apply: (s) => s.replace(/  const criteria = \[\];(\r?\n)  \/\/ `lastThresholds` is per ENABLED/,
      '  const criteria = []; verdict[p] = V_INCLUDED;$1  // `lastThresholds` is per ENABLED'),
  },
  {
    // **The mutation the fold cannot see, which is why Python's own per-criterion planes are
    // recorded.** It softens an UNKNOWN into a PASS only at cells the region already excludes.
    // There, some other layer FAILs, so the fold still yields EXCLUDED and still equals the
    // verdict plane: every self-consistency check passes while the card tells a household its
    // walk criterion was satisfied at a cell whose stored status says we do not know.
    name: 'explainAt reports an unknown as a pass where another criterion already failed',
    apply: (s) => s.replace('const outcome = outcomeFor(status, raw, thresholdMin, horizons[k]);',
      'let outcome = outcomeFor(status, raw, thresholdMin, horizons[k]);'
      + ' if (verdict[p] === V_EXCLUDED && outcome === O_UNKNOWN) outcome = O_PASS;'),
  },
  // ------------------------------------------------------------------ pass 51 finding B2
  // **Five corruptions of the explanation that each passed all 79 conformance checks and all 16
  // card checks.** The fold check and the recorded per-layer outcomes bind the OUTCOME. They did
  // not bind the fields reported beside it, so an explanation could carry a fabricated minute, an
  // inverted route flag, a forced INCLUDED headline, invented place names or a wrong horizon, and
  // every advertised check still passed. Codex pass 51 executed all five.
  //
  // "Outcomes do not authenticate the accompanying explanation" is the lesson, and these stay as
  // controls on the repair rather than being deleted once the repair is in.
  {
    name: 'explainAt reports a fabricated minute beside a correct outcome',
    apply: (s) => s.replace(
      'value: (status === S_OK || bounded) && raw !== VALUE_NONE ? raw : null,',
      'value: (status === S_OK || bounded) && raw !== VALUE_NONE ? 42 : null,'),
  },
  {
    name: 'explainAt inverts the route flag it discloses',
    apply: (s) => s.replace('routeFlag: routeFlags[k] ? routeFlags[k][p] : null,',
      'routeFlag: routeFlags[k] ? 1 - routeFlags[k][p] : null,'),
  },
  {
    name: 'explainAt gives every cell the INCLUDED headline',
    apply: (s) => s.replace('    verdictName: VERDICT_NAMES[verdict[p]],',
      "    verdictName: 'INCLUDED',"),
  },
  {
    name: 'explainAt invents the place names after the first',
    apply: (s) => s.replace(
      /        named = \{ ordinal: d, nodeIndex: entry\.node_index, placeCount: entry\.place_count,(\r?\n)          places: entry\.places \};/,
      "        named = { ordinal: d, nodeIndex: entry.node_index, placeCount: entry.place_count,$1"
      + "          places: entry.places.map((pl, pi) => (pi ? { ...pl, name: 'Fabricated Shop' } "
      + ": pl)) };"),
  },
  {
    name: 'explainAt reports the wrong horizon',
    apply: (s) => s.replace('      horizonS: horizons[k],', '      horizonS: 1,'),
  },
  // ------------------------------------------------------------------ pass 53 finding F1
  // **Three MORE that passed all 87 worker checks and all 29 card checks**, after pass 52's five
  // were closed. Three distinct causes, all mine: an enumeration written from memory rather than
  // from the artifact omitted three envelope fields; an assertion compared against a constant the
  // harness itself supplied; and the fixture added to catch a criterion-index substitution
  // carried no destination planes, so the same defect one array along survived it.
  {
    name: 'explainAt stamps every reply with the first compute sequence',
    apply: (s) => s.replace("  const reply = { type: 'explainAt', reqId: msg.reqId, seq: state.lastSeq, row, col };",
      "  const reply = { type: 'explainAt', reqId: msg.reqId, seq: 1, row, col };"),
  },
  {
    name: 'explainAt marks a successful reply as outside the published area',
    apply: (s) => s.replace(/    verdict: verdict\[p\],(\r?\n)    verdictName: VERDICT_NAMES\[verdict\[p\]\],/,
      '    verdict: verdict[p], outside: true,$1    verdictName: VERDICT_NAMES[verdict[p]],'),
  },
  // **Both anchored with the preceding newline, which is not cosmetic.** `const d =
  // destinations[k][p];` occurs three times in worker.js at three indentations -- 8 spaces in
  // `handleInit`'s validation loop, 4 in `handleDestinationAt`, 6 here -- and a 6-space string
  // anchor matches INSIDE the 8-space line, which comes first in the file. The first version of
  // the plane mutation therefore mutated `handleInit`, failed its invariant, and reported CAUGHT
  // while `handleExplainAt` was never touched. That is pass 51's confirm-on-the-wrong-cause, in a
  // mutation written one pass after recording it, and it is why this runner now reports the
  // function each mutation landed in.
  {
    name: 'explainAt reads the previous enabled layer destination table',
    in: 'handleExplainAt',
    apply: (s) => s.replace(/\n        const entry = destTables\[k\]\.destinations\[d\];/,
      '\n        const entry = destTables[Math.max(0, k - 1)].destinations[d];'),
  },
  {
    name: 'explainAt reads the previous enabled layer destination plane',
    in: 'handleExplainAt',
    apply: (s) => s.replace(/\n      const d = destinations\[k\]\[p\];/,
      '\n      const d = destinations[Math.max(0, k - 1)] ? destinations[Math.max(0, k - 1)][p]'
      + ' : destinations[k][p];'),
  },

  // ------------------------------------------------------------------ pass 52 finding F1
  // **Five MORE corruptions that passed all 79 conformance checks and all 27 card checks**, after
  // pass 51's five were closed. Three are response-envelope fields no assertion mentioned; two
  // are criterion-index substitutions that no fixture could discriminate, because every
  // multi-layer group gave its layers the same threshold and the same horizon.
  //
  // The lesson underneath both halves: closing the instances a reviewer supplies is not closing
  // the class, and a fixture set that holds a dimension constant cannot see a defect along it.
  {
    name: 'explainAt labels every reply with a sequence no compute produced',
    apply: (s) => s.replace("  const reply = { type: 'explainAt', reqId: msg.reqId, seq: state.lastSeq, row, col };",
      "  const reply = { type: 'explainAt', reqId: msg.reqId, seq: -1, row, col };"),
  },
  {
    name: 'explainAt answers a request id nobody sent',
    apply: (s) => s.replace("  const reply = { type: 'explainAt', reqId: msg.reqId, seq: state.lastSeq, row, col };",
      "  const reply = { type: 'explainAt', reqId: 0, seq: state.lastSeq, row, col };"),
  },
  {
    name: 'explainAt labels every reply as cell (0, 0)',
    apply: (s) => s.replace("  const reply = { type: 'explainAt', reqId: msg.reqId, seq: state.lastSeq, row, col };",
      "  const reply = { type: 'explainAt', reqId: msg.reqId, seq: state.lastSeq, row: 0, col: 0 };"),
  },
  {
    name: 'every criterion is compared against the first enabled threshold',
    apply: (s) => s.replace('state.lastThresholds[enabledIndex]', 'state.lastThresholds[0]'),
  },
  {
    name: 'every criterion discloses the first layer horizon',
    apply: (s) => s.replace('      horizonS: horizons[k],', '      horizonS: horizons[0],'),
  },
  {
    // Pass 51 B4, restored as a mutation. Suppressing a criterion's destination because some
    // OTHER criterion failed made the card say the layer "does not say which destination" about
    // a layer whose plane and side table both name one -- a false non-disclosure.
    name: 'explainAt withholds a destination because another criterion failed',
    apply: (s) => s.replace('    if (destinations[k] && status === S_OK) {',
      '    if (verdict[p] === V_INCLUDED && destinations[k] && status === S_OK) {'),
  },
  {
    // Anchored past the shared `continue` line, which `destinationAt` has verbatim.
    name: 'explainAt explains criteria the compute did not use',
    apply: (s) => s.replace(
      /if \(state\.lastEnabled && !state\.lastEnabled\[k\]\) continue;(\r?\n)    const thresholdMin/,
      '// the enabled filter is gone$1    const thresholdMin'),
  },
];

const original = fs.readFileSync(WORKER, 'utf8');
let caught = 0;
const survived = [];
const inert = [];
const errored = [];
const misplaced = [];

/** Which top-level function contains this character offset, by scanning declarations before it. */
function functionAt(source, offset) {
  let name = '(top level)';
  const decl = /^function (\w+)\(/gm;
  let m;
  while ((m = decl.exec(source)) !== null) {
    if (m.index > offset) break;
    name = m[1];
  }
  return name;
}

/** The offset of the first character where two sources differ. */
function firstDifference(a, b) {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) if (a[i] !== b[i]) return i;
  return n;
}

// A mutation that does not change the source is a broken mutation, not a passing decoder.
for (const m of MUTATIONS) {
  const mutated = m.apply(original);
  if (mutated === original) {
    inert.push(m.name);
    console.error(`INERT    ${m.name}  (the edit matched nothing; the guard is not testing it)`);
    continue;
  }
  // **Where did it land?** A mutation that edits a function other than the one it names is caught
  // by a check about something else, and reports CAUGHT while the guard under test is untouched.
  // That has now happened twice -- pass 51 on a lifecycle guard, pass 53 on a destination read --
  // both times because a string anchor matched inside a more deeply indented line earlier in the
  // file. The landing site is printed for every mutation so a wrong one is visible, and asserted
  // where the mutation declares `in`.
  const landed = functionAt(original, firstDifference(original, mutated));
  if (m.in && landed !== m.in) {
    misplaced.push(`${m.name} (landed in ${landed}, declared ${m.in})`);
    console.error(`MISPLACED ${m.name}  (edited ${landed}, not ${m.in}: it would be caught by a `
      + 'check about something else)');
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
    console.log(`caught   ${m.name}  [${landed}]\n           ${failLine.trim()}`);
  }
}

console.log(`\n${caught} of ${MUTATIONS.length} mutations caught`
  + (inert.length ? `, ${inert.length} INERT` : '')
  + (survived.length ? `, ${survived.length} SURVIVED` : '')
  + (misplaced.length ? `, ${misplaced.length} MISPLACED` : '')
  + (errored.length ? `, ${errored.length} ERRORED` : ''));
if (fs.readFileSync(WORKER, 'utf8') !== original) {
  console.error('worker.js was left mutated');
  process.exit(2);
}
process.exit(survived.length === 0 && inert.length === 0 && errored.length === 0
  && misplaced.length === 0 && caught === MUTATIONS.length ? 0 : 1);
