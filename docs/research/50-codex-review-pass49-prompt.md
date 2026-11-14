# Codex adversarial review, pass 49 — publishing the selected destination

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`4685158`. Python: `v2/.venv/Scripts/python.exe`.

## Runtime note — read this first, it changes what you can check

Your sandbox on this machine **cannot start processes at all**. Pass 48 established this: every
`exec_command` fails with `windows unelevated restricted-token sandbox cannot enforce split
writable root sets`, under `workspace-write`, with and without `--add-dir`, and with `--ephemeral`.
See `docs/engineering-notes/reference-codex-runtime-quirks.md`. So:

* You **cannot** run Python, pytest, `node` or `git`. Do not plan around them.
* You **can** read any file, and you **can** execute JavaScript through the `node_repl` MCP tool.
  Pass 48 used that to load `worker.js` into a `vm` context with a `self` shim and replay the whole
  conformance harness in memory, including mutations. That is the strongest tool you have here and
  the destination work is mostly JavaScript, so use it.
* For anything needing Python, reason from the source and **say what you could not execute**. An
  unexecuted argument clearly labelled as such is worth more to me than a guess dressed as a
  measurement.
* Write your report **to stdout as your final message**, not to a file.

## What shipped

`published-v4` adds an **optional fourth plane**: the selected destination — *which grocery* the
published time was measured to. `arrival_with_selected_destination` and `cell_selected_destination`
already computed it and nothing kept it, which is what made the owner's one walked journey
unscorable: `measure/e3.py` needs a reported and an observed time **for the same journey** and
nothing identified the journey.

**The owner's presentation rule, 2026-11-13: the node plus the set, and the card chooses.** The
plane names a destination **node** as a dense `uint16` ordinal; a side table carries every place on
that node; a card decides what to show. The claim is that **the set is the truthful answer rather
than a convenience**, because the selection is a cost-argmin over nodes, so two groceries on one
node are indistinguishable to the routing graph and choosing between them is a comparison nobody
ran.

## The claims to attack, hardest first

**A. The two-directional invariant, which is the main thing I claim is new.** Pass 48 F3 found that
a route-flag plane cannot be validated from its own contents — a *clear* flag asserts nothing, so
you flipped one down and one up on the shipped plane and every check accepted it. I claim
`DEST_NONE` beside a published time is different in kind: a **contradiction**, because a published
time is a time *to somewhere*. Both directions are enforced in `wire.encode_selected_destination`,
in the worker's init loop, and again in the exporter after reprojection.

* Find a case where `DEST_NONE` beside status `OK` is **legitimate** and the check therefore
  refuses a correct artifact. Horizon interactions, a destination node pruned between the sweep and
  the table, a cell whose journey exists but whose selected node fell out of `dest_idx` — anything.
  If such a case exists the invariant is too strong and will block a future build.
* I claim the check now **proves** what pass 48 could only measure: that value, status and
  destination come from one source cell, because the shipped status plane holds 258,684 OK cells
  and the destination plane names exactly 258,684 with zero disagreement. Is that a proof or a
  coincidence of this grid pair? Construct a mixed triple that still satisfies both directions.
* Does the same reasoning apply to the **route flag**, i.e. did I miss a checkable direction there
  and conclude too quickly that none exists?

**B. The byte order, and a guard I am suspicious of myself.**
`worker.js:196` reads `if (manifest.destination_plane_byte_order !== undefined && ... !== 'little')`.
So a v4 manifest that **omits** the field is read little-endian with no check at all.

* Is that defensible — the format specifies little-endian, so the field is redundant confirmation
  and its absence means the default — or is it a guard that does nothing in the case that matters?
* `byteswap_control.mjs` is my positive control: it runs the big-endian mutation against the
  300-entry `byte-swap survivors` group and requires that every ordinal stayed in range, every
  structural check passed, and the shop **name** is wrong. Attack the control. Does it prove the
  name comparison is load-bearing, or could it pass for a reason unrelated to endianness?
* `wire.destination_plane_bytes` writes through `np.dtype("<u2")`. Is every other path that touches
  this plane equally explicit, including `np.save`/`np.load` of the raster, the exporter's
  reprojection, and the vectors generator?

**C. "The plane, not run-length, because of the access pattern."** Measured, the plane costs
**38,505** deflated against column-major run-length's **28,027** — so it is 10,478 bytes dearer,
4.1% of the bundle. I shipped it anyway on the argument that a card reads **one** cell, where value
and status are read for every cell on every repaint, so expanding 330,502 run-length entries to
answer one lookup is backwards.

* Attack the argument. Is there any consumer that reads the destination plane **wholesale**, now or
  obviously soon — a legend, a "show me every shop in view", an export? If so the access-pattern
  claim is wrong about the access pattern.
* Is 4.1% of the bundle a fair way to state the cost, or does it hide something — the raw 661,004
  bytes, the memory the decoder holds, the `Uint16Array` allocation per layer?
* `readLittleEndianU16` loops byte by byte over 330,502 cells at init. Is that a real cost on a
  phone, and is there a correct faster form?

**D. The set, and whether anything can collapse it.** The claim is that where a node carries
several places the artifact names a set and no consumer may present one as *the* destination.

* Trace every path by which the set could be collapsed or reordered on the way to a reader:
  `handleDestinationAt`, the exporter's pass-through of the table, the vectors generator.
* The exporter copies the side table **unmodified**. The generator omits phones, emails, websites,
  socials, addresses and upstream record ids — but if the generator ever adds a field, does
  anything stop it shipping? Should the exporter filter rather than trust?
* 432 destinations are in the table and only **425** are named by a shipped cell, so 7 entries are
  unreferenced. Is that a defect, a payload waste, or a consumer hazard — a reader iterating the
  table would list shops no cell can reach.

**E. The licensing reasoning, which gates the whole feature.** The grocery rows carry
`CDLA-Permissive-2.0`, `Apache-2.0` and `CC0-1.0`. I concluded the names are publishable with
attribution, and that the side table must be a **separate artifact with its own licence block**
rather than merged into the travel-time layer, because that layer is ODbL-published and ODbL is
share-alike. See `docs/engineering-notes/project-phase1-s3-destination-identity.md` and decision 17
in the design record.

* Is "separate file, separate licence block" actually sufficient, or does shipping them in one
  manifest, fetched together and keyed to the same cells, make them one database for ODbL's
  purposes anyway?
* Does anything in the published bundle now carry a restricted source that decision 17 forbids?
  Check what the side table actually contains against what I claim it contains.
* Is the attribution adequate for CDLA-Permissive-2.0, which requires that recipients be told?

**F. The checks I added to stop myself repeating pass 48, as new code.**

* `test_the_javascript_encoding_lists_match_the_python_one` parses `worker.js` and `app.js` with a
  regex. Does it actually fail when the lists drift, or can it pass vacuously — a renamed constant,
  a reformatted array, a comment? The encoding set lived in five places and a bump missed three, so
  this test is the only thing standing between the next bump and the same defect.
* `test_the_vectors_carry_two_naming_layers_and_a_byte_swap_survivor` pins the fixture shape. One of
  its assertions is `assert two["dest_tables"][0] != two["dest_tables"][1] or True`, which I think
  is vacuous. Say so if it is, and say what it should assert.
* The destination mutations in `mutate_worker.mjs` — 30 of 30 are reported caught. Two of them are
  anchored with regexes because the init loop and the query hold the same statement. Does each
  mutation produce the defect its name claims, is any caught for an unrelated reason, and **what
  disclosure or naming defect does no mutation represent?** An unrepresented defect is worth more
  than a caught one.

**G. The figures.** Attack these as numbers and as method.

| quantity | value |
|---|---|
| grocery places, in category | 550 |
| within 300 m of a node | 549 |
| distinct destination nodes | 510 |
| nodes carrying more than one place | 36, holding 75 places |
| destinations selected by at least one cell | 432 |
| cells naming a destination (source grid) | 256,752 |
| answered cells ending at a shared node | 14,487 of 256,752 — 5.6% |
| shipped status OK / shipped named | 258,684 / 258,684 |
| distinct destinations in the shipped plane | 425 |
| ties: destinations moved under 3 relabellings | 0 |

The tie measurement reuses `measure_tie_flag.py`'s instrument via
`persist_selected_destination.py --ties`, and pass 48's positive control lives in the former. **Is
the control actually reached on the destination path, or did I reuse the instrument and leave its
control behind?** If so the zero is worthless and I want to know in those words.

Also: the decision report says "550 places snap to 510 nodes and 75 share one". I read that as 75
*places* on 36 shared nodes and corrected a note that had said 75 nodes. Check which reading is
right.

**H. Anything the change introduced.** `wire.py` gained `surface_fingerprint` usage,
`encode_selected_destination`, `destination_plane_bytes`, `decode_destination_plane` and
`named_destination`; the exporter gained a dtype-aware `reproject_plane`; `app.js` gained two
fetches and a widened init. Review them as new code, not as repairs.

## Output

For each finding: severity, the exact file and line, a **runnable reproducer** (JavaScript you
executed, or Python clearly marked unexecuted), and what it costs — a number that moves, or a claim
that must be withdrawn. Say which claims you checked and could not break. If the two-directional
invariant is unsound or too strong, say so first and in those words.
