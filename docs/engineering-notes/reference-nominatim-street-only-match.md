# Nominatim can match the street instead of the address, and nothing errors

**2026-11-15.** Found while measuring walk times for the Carolina Pitstop page
(`docs/trips/carolina-pitstop/morning.py`).

## The fact

For a house-number query such as `2149 Pickens Street, Columbia, SC 29201`, Nominatim's
first result is sometimes the **street itself** (`display_name` begins `Pickens Street, ...`
with no number). The point it returns is somewhere along that street, which can be a mile or
more from the address. Nothing errors and the response looks normal. The walk time routed to
that point is wrong, yet it carries a correct "measured" label.

Seen twice in one batch of eight:
- `2149 Pickens St`: matched "Pickens Street, Five Points". The real address is on BullStreet,
  next to Gather COLA. The routed walk came back as 41 min, against 30 min measured from Gather COLA.
- `729 Saluda Ave`: matched "Saluda Avenue, Five Points".

Earlier, place-name queries (`Page Ellington Park`, `Coastal Crust`) failed the same way.

## How to apply

- Print `display_name` beside every routed figure, and read it before using the figure.
  Both scripts in that folder do this.
- Treat a house-number query whose match does not start with the number as a failed geocode.
- Either borrow a measured neighbour and label the figure "about" (what the page does), or
  show no figure. Never publish the street-centroid figure.
- This is an instance of [provenance is not correctness](feedback-provenance-is-not-correctness.md).
