import json
from urllib.parse import parse_qs, unquote, urlparse

from locfinder.listings.links import BBox, leakage_ratio, redfin_url, zillow_url

BB = BBox(west=-79.10, south=35.88, east=-79.00, north=35.95)


def test_zillow_url_encodes_map_bounds_and_filters():
    u = zillow_url(BB, max_price=600000, min_beds=3)
    q = parse_qs(urlparse(u).query)
    state = json.loads(unquote(q["searchQueryState"][0]))
    assert state["mapBounds"] == {"west": -79.10, "east": -79.00, "south": 35.88, "north": 35.95}
    assert state["isMapVisible"] is True
    assert state["filterState"]["price"]["max"] == 600000
    assert state["filterState"]["beds"]["min"] == 3


def test_zillow_url_without_filters_has_empty_filter_state():
    state = json.loads(unquote(parse_qs(urlparse(zillow_url(BB)).query)["searchQueryState"][0]))
    assert state["filterState"] == {}


def test_redfin_url_uses_north_south_east_west_order():
    u = redfin_url(BB)
    assert "viewport=35.95:35.88:-79.0:-79.1" in u


def test_leakage_ratio_is_bbox_area_over_region_area():
    assert leakage_ratio(bbox_area_km2=10.0, region_area_km2=2.5) == 4.0
