"""Write the s3-12 record: what the page actually says at the walked cell.

The browser observations are literals -- a reading cannot be recomputed. Everything that CAN be
rechecked against the shipped bundle is rechecked here before the file is written, so the record
cannot be committed while disagreeing with the artifact it describes.
"""
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(r"C:\Users\arikt\documents\github\distanceFinder")
PUB = ROOT / "v2" / "spikes" / "g3-render" / "fixtures" / "published"
OUT = ROOT / "docs" / "experiments" / "s3-12-what-the-page-says-at-the-walked-cell.json"

#: `query_lon`/`query_lat` of band15min_pass-03: the centre of the UTM cell the journey was
#: computed for. **Not a door** -- Codex pass 55, F4. That row's `start_lon` and `start_lat` are
#: blank. No door has ever been recorded for this journey; recording one is what the re-walk is
#: for, and calling this a door would let the next walk claim a provenance it does not have.
QUERY_LON, QUERY_LAT = -79.062476, 35.902334
WALKED = (282, 126)          # the published cell containing that query coordinate
SHEET_INDEX = (286, 129)     # the same numbers, in the UTM grid the sheet uses

CARD_AT_15 = ("The model estimates this cell meets your limits."
              "Times are estimates: measured from the centre of this cell, and rounded up to the "
              "whole minute."
              "own_triangle_grocery_walkPASS14 min \u00b7 your limit 15 min"
              "This route uses a way that is not clearly public \u2014 a private drive, a track, "
              "or a path with restricted access. Your walk may be longer than the time above."
              "measured to Hill's Family Asian Markets")
CARD_AT_20 = CARD_AT_15.replace("your limit 15 min", "your limit 20 min")


def published(bounds, nrows, ncols, lon, lat):
    W, S, E, N = bounds
    return (int((N - lat) / (N - S) * nrows), int((lon - W) / (E - W) * ncols))


def main() -> None:
    man = json.loads((PUB / "manifest.json").read_text(encoding="utf-8"))
    entry = next(l for l in man["layers"] if l["id"] == "own_triangle_grocery_walk")
    nrows, ncols, bounds = man["nrows"], man["ncols"], man["bounds_wgs84"]

    def plane(key, dtype):
        return np.frombuffer((PUB / entry[key]).read_bytes(),
                             dtype=dtype).reshape(nrows, ncols)

    value, status = plane("value_file", np.uint8), plane("status_file", np.uint8)
    flag, dest = plane("flag_file", np.uint8), plane("dest_file", np.dtype("<u2"))
    table = json.loads((PUB / entry["dest_table"]).read_text(encoding="utf-8"))["destinations"]

    assert published(bounds, nrows, ncols, QUERY_LON, QUERY_LAT) == WALKED, (
        "the query coordinate no longer falls in the cell this record is about")

    def describe(cell):
        r, c = cell
        di = int(dest[r, c])
        rec = table[di] if di != 65535 else None
        return {
            "published_cell": {"row": r, "col": c},
            "value_byte_minutes": int(value[r, c]),
            "status_byte": int(status[r, c]),
            "route_flag_byte": int(flag[r, c]),
            "destination_index": None if di == 65535 else di,
            "place_names": [p.get("name") for p in (rec or {}).get("places", []) if p.get("name")],
            "outcome_at_15_min": "PASS" if int(value[r, c]) <= 15 else "FAIL",
            "outcome_at_20_min": "PASS" if int(value[r, c]) <= 20 else "FAIL",
        }

    walked, lookalike = describe(WALKED), describe(SHEET_INDEX)
    assert walked["value_byte_minutes"] == 14 and walked["route_flag_byte"] == 1
    assert walked["place_names"] == ["Hill's Family Asian Markets"]
    assert lookalike["outcome_at_15_min"] == "FAIL" and lookalike["route_flag_byte"] == 0

    doc = {
        "what_this_is":
            "The reading Codex pass 54 asked for before the re-walk: what the PAGE says at the "
            "cell band15min_pass-03 was walked from, read in a browser rather than inferred from "
            "the sheet. The sheet's encoded 14 minutes is evidence about the sheet. This is the "
            "answer the page gives for that cell. CORRECTED 2026-11-16, Codex pass 55 F4: this "
            "said 'the answer a household standing at that door would actually be shown'. There "
            "is no door. The coordinate is the journey's QUERY point -- the UTM cell centre -- "
            "and the sheet's start_lon/start_lat are blank.",
        "when": "2026-11-16",
        "where": {
            "browser": "Chrome 157.0.0.0 on Windows, devicePixelRatio 1",
            "page": "spikes/g3-render served on 127.0.0.1:8099 from the working tree",
            "bundle": "the shipped published-v4 fixtures, layer own_triangle_grocery_walk",
        },
        "how_to_reproduce": [
            "serve spikes/g3-render on loopback and open it",
            "set the walk threshold to 15, which is the band this journey is in",
            "hover the centre of published cell (282, 126): "
            f"lon {-79.0622862}, lat {35.9026751}",
            "note that this is the published cell's centre, which is about 41.5 m from the UTM "
            "cell centre the 810.8 s was computed at. They are different points and neither is "
            "a door",
            "the card's own heading states the cell it is describing, so the reading can be "
            "checked without trusting the pointer arithmetic",
        ],

        "the_defect_this_reading_found":
            {
                "summary":
                    "The probe in s3-10 called `the_walked_cell` was not the walked cell. It read "
                    "the audit sheet's (286, 129) as an index into the PUBLISHED raster. Those "
                    "numbers index the UTM GridSpec the pipeline computes on. The published "
                    "raster is a WGS84 lon/lat grid with its own indexing and also has a cell "
                    "(286, 129), about 400 m away, and the sheet's own lon/lat columns were "
                    "unused. Codex pass 55 confirmed the cause by rebuilding the UTM grid: the "
                    "sheet coordinate is the rounded centre of UTM cell (286, 129) and falls in "
                    "published cell (282, 126).",
                "why_it_mattered":
                    "The probe's own text called its card 'the one a person can check against a "
                    "walk'. The two cells do not agree about anything a walker would check.",
                "the_cell_the_index_pointed_at": lookalike,
                "the_cell_the_door_is_in": walked,
                "the_sheets_own_columns_are_named_row_and_col_with_no_grid_named": True,
                "fixed":
                    "measure_drawn_pixel.py now derives the probe from the door's lon/lat and "
                    "records which cell that is. Regenerating changed that one probe and nothing "
                    "else: every other probe and every exposure figure is byte-identical.",
            },

        "the_reading": {
            "cell_label_the_page_printed": "(row 282, col 126)",
            "at_the_pages_default_20_min": CARD_AT_20,
            "at_the_15_min_band_this_journey_is_in": CARD_AT_15,
            "painted_pixel_under_the_pointer": [24, 119, 241, 150],
            "painted_pixel_note":
                "PX_IN (24,119,242,150) as a canvas returns it: a translucent pixel is stored "
                "premultiplied, so the blue channel reads one count low. Blue, included, and it "
                "agrees with the card -- this is a cell CENTRE, where the two placement rules "
                "agree exactly, so it is inert for the displacement by construction.",
            "screenshot": "s3-12/card-at-the-walked-cell-15min.png",
        },

        "the_page_agrees_with_the_sheet_row": {
            "checked": ["encoded_minutes", "outcome_15min", "predicted_destination",
                        "the restricted approach"],
            "sheet": {"encoded_minutes": 14, "outcome_15min": "PASS",
                      "predicted_destination": "Hill's Family Asian Markets",
                      "restricted": "routes 305 m down OSM way 1254722641, access=private"},
            "page": {"minutes_shown": 14, "outcome": "PASS",
                     "destination_named": "Hill's Family Asian Markets",
                     "restricted": "the restricted-route warning is rendered"},
            "so":
            "a displayed candidate claim has been identified: at the cell the journey's query "
            "coordinate falls in, the page shows 14 minutes to Hill's Family Asian Markets on a "
            "route that may use a private way. CORRECTED 2026-11-16, Codex pass 55 F4: this said "
            "'the re-walk's precondition is met', which is too broad. The start door still has "
            "to be chosen inside the cell and recorded -- that is what start_lon/start_lat are "
            "for and they are still blank. What has been removed is the risk of walking to the "
            "wrong cell's claim.",
        },

        "the_costs_this_session_could_measure": {
            "card_round_trip_one_cell": "0.3 ms last / 0.2 ms median over 17 hovers",
            "card_round_trip_note":
                "the figure the card plan listed as unverified. It is a real browser message "
                "round trip on one desktop, measured between sending the request and receiving "
                "the reply: it does NOT include the DOM update, so it is not pointer-to-visible "
                "latency. CORRECTED 2026-11-16, Codex pass 55 F5: this said the figure 'matches "
                "the order of' the Node worker-side measurement and that one explainAt per "
                "pointer move is 'free'. 0.2 ms is 1,000 times 0.0002 ms, not the same order, "
                "and the handler figure excludes the message passing that dominates it. What it "
                "does support is retaining the current architecture on this desktop: no "
                "batching and no cached outcome plane are justified by anything measured here.",
            "worker_compute_whole_raster": "7.7 ms last / 9.1 ms median over 20 scripted changes",
        },

        "the_cost_this_session_could_not_measure": {
            "what": "slider to repaint, total -- the figure a household feels",
            "what_the_page_reported": "1002.3 ms last / 1002.7 ms median over 20 changes",
            "why_that_number_is_the_instrument":
                "requestAnimationFrame was firing once a second. The page reported "
                "visibilityState 'visible', document.hidden false and hasFocus() true, because "
                "an OCCLUDED window is not a hidden document -- and Chrome throttles frames in a "
                "window nothing is displaying. Paint completion is detected on a frame, so every "
                "repaint measured one frame clock.",
            "the_control":
                "frame gaps sampled for ten seconds read 1000, 450, 33, 1000, 1000, 1000, 1000, "
                "33, 17, 17, 17, 17, 17, 17, 17, 1000, 1017, 1000 ms. The run of 17 ms frames is "
                "exactly the window in which a screenshot was captured. CORRECTED 2026-11-16, "
                "Codex pass 55 F5: this concluded 'the page renders at 60 fps when something is "
                "looking at it'. The observation is a capture-associated burst of animation-frame "
                "callbacks; it does not establish product rendering performance, and it does not "
                "exclude the reading in which the one-second delay is real in that operating "
                "state and the capture is the intervention. BOTH readings are live. Foreground "
                "interactive latency is unresolved and needs a person with the window on screen.",
            "the_one_sample_taken_after_a_capture":
                "a single manual threshold change made immediately after two screen captures: "
                "68.9 ms total, 54.8 ms transfer and paint, 13.5 ms compute. n=1, and reported "
                "as n=1. CORRECTED 2026-11-16, Codex pass 55 F5: this was called 'untainted'. It "
                "was taken immediately after the very intervention that is said to change frame "
                "scheduling, so it is evidence that a faster response occurred, not an "
                "unconfounded baseline.",
            "to_measure_it_properly":
                "click Auto-bench with the window actually on screen and read the stats row. "
                "One click, and it needs a person at the machine rather than a session.",
        },

        "what_this_establishes": [
            "the page, at the cell the walked door is in, shows 14 min, PASS at a 15-minute "
            "limit, the restricted-route warning and Hill's Family Asian Markets -- which is the "
            "sheet row, rendered",
            "the oracle's 'walked cell' probe was 400 m away from the walked cell, and is not any "
            "more",
            "the card round trip in a real browser is 0.2 ms median, so the per-pointer-move "
            "explanation needs no batching and no cached outcome plane",
        ],
        "what_this_does_not_establish": [
            "that the 14 minutes is right. The owner reported about 25. This reading is about "
            "what the page SAYS, not about whether it is true, and the walk is still owed",
            "the slider-to-repaint cost, which this session measured only through a throttled "
            "frame clock and one untainted sample",
            "anything about a phone",
            "that a household would read this card the way the model that wrote it does",
        ],
    }

    # **Carry the browser run forward.** Everything above is a literal this script can rebuild;
    # the probe run is eleven points of browser output that cannot be recomputed from anything
    # here, and a rebuild that dropped it would destroy the only copy. It is appended by
    # `collect_probe_run.py` after a run and preserved by every later rebuild.
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        kept = previous.get("the_rerun_against_the_corrected_oracle")
        if kept is not None:
            doc["the_rerun_against_the_corrected_oracle"] = kept
            print(f"  carried forward a run of {len(kept['run']['probes'])} probes")

    # CRLF: this working copy is CRLF, and a generator that writes LF makes every
    # regeneration look like a whole-file change until git normalises it on commit.
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\r\n")
    print(f"{OUT.name}: {OUT.stat().st_size} bytes")
    print(f"  walked cell {walked['published_cell']}  {walked['value_byte_minutes']} min  "
          f"flag {walked['route_flag_byte']}  {walked['place_names']}")
    print(f"  the index's lookalike {lookalike['published_cell']}  "
          f"{lookalike['value_byte_minutes']} min  flag {lookalike['route_flag_byte']}  "
          f"{lookalike['place_names']}")


if __name__ == "__main__":
    main()
