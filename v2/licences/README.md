# Licence texts that have to travel with the published bundle

`scripts/export_published_layers.py` copies the texts in this directory into the published
output and writes an `ATTRIBUTION.md` beside them. The exporter **refuses to finish** if a
licence appearing in a side table has no text here, so a bundle cannot ship with a label it
cannot resolve.

**Why this directory exists.** Codex pass 49 finding 3. The side table carried SPDX identifiers
and an Overture release label and nothing else, and that is not redistribution compliance:

* **CDLA-Permissive-2.0 §2.1** — *"A Data Recipient may share Data, with or without
  modifications, so long as the Data Recipient makes available the text of this agreement with
  the shared Data."* The text, not the name of the text. 411 of the published place records are
  CDLA.
* **Apache-2.0 §4** — a redistributor gives recipients a copy of the licence, states that files
  were changed and when, and keeps the attribution notices from the source `NOTICE` file. 35 of
  the published place records are Apache, which in Overture means Foursquare-sourced.
* **CC0-1.0** imposes no conditions. Its text is here anyway so that every label in a published
  table resolves to a file, rather than only the ones with obligations.

The earlier note said the names were "publishable with attribution". They are — but "publishable
with attribution" is a description of the licence, not a thing the build had done.

## Provenance of each file

| File | Fetched from | On |
|---|---|---|
| `CDLA-Permissive-2.0.txt` | `raw.githubusercontent.com/spdx/license-list-data/main/text/CDLA-Permissive-2.0.txt` | 2026-11-14 |
| `Apache-2.0.txt` | `www.apache.org/licenses/LICENSE-2.0.txt` | 2026-11-14 |
| `CC0-1.0.txt` | `raw.githubusercontent.com/spdx/license-list-data/main/text/CC0-1.0.txt` | 2026-11-14 |

## The gap, stated rather than papered over

`NOTICE-foursquare.txt` holds the one attribution line Overture's own documentation names as the
minimum. **The upstream `NOTICE.txt` itself could not be retrieved:** the Foursquare dataset
repository on Hugging Face is gated and returns HTTP 401 without an account. So this file is
what the documentation requires at minimum, and not a copy of the upstream file.

Before anything is published outside this repository, fetch the real `NOTICE.txt` from the
Foursquare dataset and replace that file. Absence of the full notice is not evidence that the
line below is all of it.
