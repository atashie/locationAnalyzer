"""Premium search is a module with no provider behind it.

It must say so plainly. The whole point of removing the TripAdvisor client
rather than leaving it in place is that a dead provider used to look like an
empty neighbourhood; these tests make each state distinguishable over HTTP:

* no provider configured   -> 503, and it says what is missing
* provider cannot be reached -> 502, never a 200 with an empty list
* provider answers nothing  -> 200 with an empty list, which is the truth
* provider answers          -> 200, filtered to the polygon
"""

from typing import List

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.places import ProviderPlace, ProviderUnavailable, register_provider

# A square covering roughly Durham, NC. (-78.92,35.98) to (-78.88,36.01)
POLYGON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-78.92, 35.98],
                        [-78.88, 35.98],
                        [-78.88, 36.01],
                        [-78.92, 36.01],
                        [-78.92, 35.98],
                    ]
                ],
            },
        }
    ],
}

INSIDE = ProviderPlace(
    provider_id="1",
    name="Gonza Tacos y Tequila",
    lat=35.994,
    lon=-78.899,
    rating=4.5,
)
OUTSIDE = ProviderPlace(
    provider_id="2",
    name="Somewhere In Raleigh",
    lat=35.779,
    lon=-78.638,
)


class FakeProvider:
    """A provider that answers from a fixed list, and records how it was asked."""

    name = "fake"

    def __init__(self, places: List[ProviderPlace]):
        self.places = places
        self.calls = 0
        self.asked = []

    def nearby_search(self, lat, lon, category, *, limit=10, subcategory=None):
        self.calls += 1
        self.asked.append(
            {
                "lat": lat,
                "lon": lon,
                "category": category,
                "limit": limit,
                "subcategory": subcategory,
            }
        )
        return list(self.places)

    def monthly_usage(self):
        return self.calls

    def monthly_limit(self):
        return 0


class BrokenProvider:
    """A provider that cannot be reached. This is what TripAdvisor became."""

    name = "broken"

    def nearby_search(self, lat, lon, category, *, limit=10, subcategory=None):
        raise ProviderUnavailable(
            "HTTP 403: User is not authorized to access this resource"
        )

    def monthly_usage(self):
        return 0

    def monthly_limit(self):
        return 0


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_provider_by_default():
    """Every test starts with no provider, and leaves none behind."""
    register_provider(None)
    yield
    register_provider(None)


def _search(client, **kwargs):
    body = {"geojson": POLYGON, "category": "restaurants", "max_locations": 10}
    body.update(kwargs)
    return client.post("/api/v1/premium-search", json=body)


def test_no_provider_configured_is_503_and_explains_itself(client):
    response = _search(client)

    assert response.status_code == 503
    detail = response.json()["detail"].lower()
    assert "provider" in detail
    assert "premium search" in detail


def test_an_unreachable_provider_is_502_not_an_empty_success(client):
    register_provider(BrokenProvider())

    response = _search(client)

    assert response.status_code == 502, "a failed lookup must not read as 'no results'"
    assert "403" in response.json()["detail"]


def test_a_provider_that_finds_nothing_is_an_honest_empty_result(client):
    provider = FakeProvider([])
    register_provider(provider)

    response = _search(client)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["total_found"] == 0
    assert body["locations"] == []
    assert provider.calls > 0, "an empty result must mean the provider was actually asked"


def test_the_subcategory_filter_reaches_the_provider(client):
    """The schema accepts it and the UI sends it, so it must not be dropped."""
    provider = FakeProvider([INSIDE])
    register_provider(provider)

    response = _search(client, subcategory="pizza")

    assert response.status_code == 200
    assert provider.asked[0]["subcategory"] == "pizza"


def test_ranking_survives_the_provider_boundary(client):
    """PremiumLocation.ranking_string is rendered by the map, so a provider
    must be able to populate it."""
    ranked = ProviderPlace(
        provider_id="1",
        name="Gonza Tacos y Tequila",
        lat=35.994,
        lon=-78.899,
        ranking_string="#1 of 20 Restaurants in Durham",
    )
    register_provider(FakeProvider([ranked]))

    response = _search(client)

    assert response.status_code == 200
    location = response.json()["locations"][0]
    assert location["ranking_string"] == "#1 of 20 Restaurants in Durham"


def test_results_are_filtered_to_the_polygon(client):
    register_provider(FakeProvider([INSIDE, OUTSIDE]))

    response = _search(client)

    assert response.status_code == 200
    body = response.json()
    assert body["total_found"] == 1
    assert [loc["name"] for loc in body["locations"]] == ["Gonza Tacos y Tequila"]
    assert body["locations"][0]["rating"] == 4.5


def test_the_response_names_the_provider_that_answered(client):
    register_provider(FakeProvider([INSIDE]))

    response = _search(client)

    assert response.json()["provider"] == "fake"


def test_max_locations_is_respected(client):
    many = [
        ProviderPlace(provider_id=str(i), name=f"Place {i}", lat=35.99, lon=-78.90)
        for i in range(10)
    ]
    register_provider(FakeProvider(many))

    response = _search(client, max_locations=3)

    assert len(response.json()["locations"]) == 3


def test_a_geojson_with_no_polygons_is_a_400(client):
    register_provider(FakeProvider([INSIDE]))

    response = _search(client, geojson={"type": "FeatureCollection", "features": []})

    assert response.status_code == 400
