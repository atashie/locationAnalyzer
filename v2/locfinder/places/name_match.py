"""Does the OSM feature under a place have the same business's name on it?

**Owner decision 2026-11-18**, *"1-4) yes, proceed"*, answering *"whether to put a name-agreement
floor on the OSM prefill"*. The question came out of the FSQ accuracy run, which found **42 of 338
(12.4%)** of OSM's proposals resting on a match with name agreement 0.00 against **3 of 338
(0.9%)** for Foursquare — and that was in the half of the data treated as the good half. On the
open records the prefill is actually used on it is **worse**: 51 of 117 grocery proposals (43.6%)
and 29 of 102 pharmacy proposals (28.4%).

This module is where that floor lives. It was moved out of `scripts/prefill_from_osm.py`, which
four other scripts import it from, because a threshold that decides what goes into a **published**
layer's candidate list is not a script-local helper. The script keeps re-exporting the two names
so nothing that imports them breaks.

**The rule, in one line:** *a proposal is worth what its match is worth* — the replacement for
"FSQ confirms, never rejects" — so a match whose name denies the record's own name is not evidence
for anything, and the proposal built on it is withheld.

---

## Why this is a verdict and not a number

`name_agreement` returns **0.0 for two facts that are not the same fact**:

* both names carry informative words and share none — **a different business**;
* one side carries no informative word at all — an unnamed OSM feature, or a name made entirely of
  category words — which is **unknown**, not disagreement.

Measured on the grocery prefill sheet: of the 51 proposals at 0.00, **42 (82.4%)** are the first
and **9 (17.6%)** the second; pharmacy, 23 (79.3%) and 6 (20.7%). Both matter, and a float cannot
carry the difference, so the gate is `match_verdict` and the float is only ever *reported* — a
reader who disagrees with the gate still needs to see how close the call was.

*(The prediction written before that measurement was that the unknown share would be over a third,
which would have justified a more elaborate rule. It was 17.6%. The prediction was wrong and the
simpler rule stands; ledger instance 57.)*

## Why the floor is "one shared word" and not a Jaccard threshold

This is the counter-intuitive half, and the reason the constant below is a token test rather than
the `0.34` this project uses elsewhere. **The partial-agreement band is almost all correct
matches**, because our names and OSM's differ by suffixes and spellings rather than by identity:

| our record | OSM feature | distance | Jaccard |
|---|---|---|---|
| Walmart Grocery Pickup and Delivery | Walmart Supercenter | 0.0 m | 0.25 |
| Handee Hugo 77 | Han Dee Hugo | 0.0 m | 0.25 |
| Apna Bazar | Apna Bazaar | 10.7 m | 0.33 |
| Larry's Super Market | Larry's Supermarket | 2.0 m | 0.50 |
| H Mart Cary | H Mart | 2.2 m | 0.50 |

A floor at 0.34 would reject the first three and 12 rows like them. **The wrong matches in that
band are wrong for a different reason: they share a GENERIC word.** `Han-Ah-Rum Mart` vs
`Han-Dee Hugo's` share `han`; `Tazza Mandi` vs `Sabzi Mandi` share `mandi`; `The Produce Box` vs
`Ford's Produce Garage` share `produce`. The knob for those is the stop-word list, not the
threshold, and raising the threshold punishes the good rows to catch three bad ones.

**So three proposals clear this floor on a shared generic word and should not.** That residue is
stated rather than fixed: `han` and `mandi` are parts of real business names and excluding them
would cost more than they do. Two of the three sit at 78.5 m and 83.3 m, which the distance column
already shows.
"""
from __future__ import annotations

import re

#: The three answers. Only `AGREES` clears the floor; the other two are kept apart because they
#: are different facts and a reader acting on the sheet needs to know which one they have.
AGREES = "agrees"
DIFFERS = "differs"
UNVERIFIED = "unverified"

_WORD = re.compile(r"[a-z0-9]+")

#: Words that agree between almost any two shop names and so carry no information. Moved here
#: unchanged from `scripts/prefill_from_osm.py`.
#:
#: **This list, not a numeric threshold, is the knob for a false match that shares a word.** See
#: the module docstring: every wrong proposal that clears the floor does so on a generic word.
STOP_WORDS = frozenset({
    "the", "and", "of", "market", "store", "shop", "food", "foods", "inc", "llc", "co",
    "company", "center", "centre", "supermarket", "grocery", "pharmacy",
})

#: What the floor is, written as prose because it is not a number. A proposal needs **at least one
#: shared informative word**. Expressed as `match_verdict(...) == AGREES` rather than as
#: `name_agreement(...) > 0` so that the unverified case cannot silently fall on the blocking side.
FLOOR = "at least one shared informative word"


def tokens(name: str) -> set[str]:
    """The informative words in a name: lowercased, over two letters, not a category word."""
    return {w for w in _WORD.findall((name or "").lower()) if w not in STOP_WORDS and len(w) > 2}


def name_agreement(a: str, b: str) -> float:
    """Jaccard over informative words. 0 when either side has none, which is honest: a name made
    entirely of stop-words tells us nothing, and scoring it 1.0 would invent agreement.

    **Reported, never used as the gate.** Use `match_verdict` for that — this returns 0.0 both for
    a different business and for a nameless feature, and those must not be treated alike.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match_verdict(our_name: str, their_name: str) -> str:
    """`AGREES`, `DIFFERS` or `UNVERIFIED` for a candidate match.

    `UNVERIFIED` means one of the two names cannot speak — an unnamed OSM feature, or a name that
    is nothing but category words. It is deliberately not `DIFFERS`: those rows keep their tag and
    distance in the sheet so a human can still use them, they just do not get a proposal asserted
    on their behalf.
    """
    ours, theirs = tokens(our_name), tokens(their_name)
    if not ours or not theirs:
        return UNVERIFIED
    return AGREES if ours & theirs else DIFFERS


def clears_the_floor(verdict: str) -> bool:
    """Only `AGREES`. Named rather than inlined so a caller reads the policy, not the comparison."""
    return verdict == AGREES


def why_withheld(verdict: str) -> str:
    """The sentence a sheet prints instead of a proposal, so a reader is never guessing."""
    if verdict == DIFFERS:
        return ("names do NOT agree -- the nearest tagged feature is a DIFFERENT business, so no "
                "proposal is made from its tag")
    if verdict == UNVERIFIED:
        return ("no name to compare -- the OSM feature is unnamed or both names are category "
                "words only, so the match is unverified rather than wrong")
    return "names agree"
