"""Phase 1 S0.4. Surface identity, and the wall-clock rules a deadline must satisfy."""
from datetime import date, time

import pytest

from locfinder import profile
from locfinder.identity import METRO_TZ, REFERENCE_SERVICE_DATE, SurfaceKey, TransitQuery
from locfinder.metros import TRIANGLE

MORNING = time(8, 45)
WINDOW_S = 90 * 60.0
# Derived, not typed: `SurfaceKey` refuses a hand-written version string (Codex pass-8 H3).
PROFILE_V = profile.profile_version()
GRID_V = profile.grid_version(TRIANGLE.grid(100.0))


def tq(**kw) -> TransitQuery:
    base = dict(service_date=REFERENCE_SERVICE_DATE, deadline_local=MORNING, window_s=WINDOW_S)
    return TransitQuery(**{**base, **kw})


def key(**kw) -> SurfaceKey:
    base = dict(metro="triangle", mode="drive", engine="valhalla-expansion", target="rdu",
                aggregation="single_anchor", horizon_s=120 * 60.0, grid_version=GRID_V,
                source_release="2026-10-21.0", profile_version=PROFILE_V, code_version="fc55be1",
                max_access_m=200.0, poi_snap_max_m=300.0,
                anchor_lonlat=(-78.7875, 35.8776), anchor_round_dp=5)
    return SurfaceKey(**{**base, **kw})


def transit_key(**kw) -> SurfaceKey:
    """A transit key, whose window and horizon must be one number."""
    q = kw.pop("transit", tq())
    return key(mode="transit", engine="motis-one-to-all", transit=q, horizon_s=q.window_s,
               anchor_lonlat=None, anchor_round_dp=None, **kw)


# ---------------------------------------------------------------- the deadline is an instant

def test_the_reference_deadline_resolves_to_a_single_instant_in_est():
    """2026 DST ended on 11-01, so the reference Tuesday is EST (UTC-5): 08:45 local is 13:45 UTC."""
    q = tq()
    assert q.deadline_utc.hour == 13 and q.deadline_utc.minute == 45
    assert REFERENCE_SERVICE_DATE.weekday() == 1, "a Tuesday"
    assert q.timezone == METRO_TZ


def test_an_ambiguous_deadline_is_refused():
    """2026-11-01 01:30 local happens twice. There is no single deadline to route to."""
    with pytest.raises(ValueError, match="ambiguous"):
        tq(service_date=date(2026, 11, 1), deadline_local=time(1, 30))


def test_a_nonexistent_deadline_is_refused():
    """2027-03-14 02:30 local never happens."""
    with pytest.raises(ValueError, match="does not exist"):
        tq(service_date=date(2027, 3, 14), deadline_local=time(2, 30))


def test_a_morning_deadline_is_safe_on_both_transition_dates():
    """The rule exists for deadlines we do not yet use, not for the one we do."""
    for d in (date(2026, 11, 1), date(2027, 3, 14)):
        assert tq(service_date=d).deadline_utc is not None


def test_an_eight_am_deadline_shifts_with_dst_rather_than_staying_put():
    """A local wall-clock deadline is not a fixed UTC offset; a surface built in summer and reused
    in winter would be routing to the wrong instant."""
    summer = tq(service_date=date(2026, 7, 14)).deadline_utc
    winter = tq(service_date=date(2026, 12, 15)).deadline_utc
    assert summer.hour == 12 and winter.hour == 13


def test_the_window_must_be_positive():
    with pytest.raises(ValueError, match="window_s"):
        tq(window_s=0.0)


def test_the_prior_service_day_is_part_of_the_requirement():
    """An overnight trip with a stop_time past 24:00:00 can serve an 08:45 arrival."""
    assert tq().fields()["requires_prior_service_day"] is True


# ---------------------------------------------------------------- surface identity

def test_transit_fields_belong_to_transit_surfaces_only():
    with pytest.raises(ValueError, match="TransitQuery"):
        key(mode="transit")
    with pytest.raises(ValueError, match="nothing else may carry one"):
        key(mode="drive", transit=tq(), horizon_s=WINDOW_S)


def test_only_arrival_surfaces_exist():
    with pytest.raises(ValueError, match="arrival"):
        key(direction="departure")


def test_a_different_service_date_is_a_different_surface():
    assert transit_key().digest() != transit_key(
        transit=tq(service_date=date(2026, 11, 11))).digest()


def test_a_different_deadline_window_or_source_release_is_a_different_surface():
    base = transit_key()
    variants = [
        transit_key(transit=tq(deadline_local=time(9, 0))),
        transit_key(transit=tq(window_s=45 * 60.0)),
        transit_key(source_release="2026-11-21.0"),
        transit_key(profile_version="speeds-v1+deadbeefdeadbeef"),
        transit_key(grid_version=profile.grid_version(TRIANGLE.grid(200.0))),
    ]
    digests = {base.digest()} | {v.digest() for v in variants}
    assert len(digests) == len(variants) + 1, "every one of these changes the answer"


def test_the_digest_is_stable_across_processes():
    """`hash()` is salted per process, which would silently invalidate a disk cache on restart."""
    expected = key().digest()
    assert len(expected) == 16
    assert key().digest() == expected
    import subprocess
    import sys
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'.'); "
         "from locfinder import profile; from locfinder.metros import TRIANGLE; "
         "from locfinder.identity import SurfaceKey; "
         "print(SurfaceKey(metro='triangle',mode='drive',engine='valhalla-expansion',"
         "target='rdu',aggregation='single_anchor',horizon_s=7200.0,"
         "grid_version=profile.grid_version(TRIANGLE.grid(100.0)),"
         "source_release='2026-10-21.0',profile_version=profile.profile_version(),"
         "code_version='fc55be1',max_access_m=200.0,poi_snap_max_m=300.0,"
         "anchor_lonlat=(-78.7875,35.8776),anchor_round_dp=5).digest())"],
        capture_output=True, text=True, check=True)
    assert out.stdout.strip() == expected


def test_anchor_rounding_is_part_of_the_key_not_applied_silently():
    """Rounding can move an anchor across a divided road, so the rounding used is recorded and a
    coordinate alone is not an identity (Codex pass-7 H6)."""
    with pytest.raises(ValueError, match="recorded together"):
        key(anchor_round_dp=None)
    coarse = key(anchor_round_dp=2)
    assert coarse.digest() != key(anchor_round_dp=5).digest()
    assert coarse.fields()["anchor_lonlat"] == [-78.79, 35.88]


def test_fields_are_json_safe_and_ordered():
    import json
    f = transit_key().fields()
    assert list(f) == sorted(f)
    json.dumps(f)   # a manifest entry must serialise without a custom encoder
    assert f["transit"]["service_date"] == "2026-11-10"
    assert f["transit"]["deadline_local"] == "08:45:00"


# ---------------------------------------------------------------- derived versions (S0.4)

def test_the_access_bounds_are_part_of_the_identity():
    """`max_access_m` decides which cells are OFF_NETWORK and `poi_snap_max_m` which destinations
    exist at all. Both move published values, so neither may be absent from the key."""
    assert key(max_access_m=300.0).digest() != key().digest()
    assert key(poi_snap_max_m=150.0).digest() != key().digest()


def test_the_profile_version_is_derived_from_the_constants_not_typed():
    """A hand-typed version string does not change when the model changes. This one does."""
    from locfinder import profile
    from locfinder.traveltime import access, speeds

    before = profile.profile_version()
    assert before.startswith("speeds-v0+")

    original = dict(speeds.MODE_SPEED_MPS)
    try:
        speeds.MODE_SPEED_MPS["walk"] = 1.5      # a faster pedestrian is a different profile
        assert profile.profile_version() != before
    finally:
        speeds.MODE_SPEED_MPS.clear()
        speeds.MODE_SPEED_MPS.update(original)
    assert profile.profile_version() == before

    original_pen = dict(access.RESTRICTED_PENALTY_S)
    try:
        access.RESTRICTED_PENALTY_S["drive"] = 300.0   # the 450 s prior is explicitly unvalidated
        assert profile.profile_version() != before
    finally:
        access.RESTRICTED_PENALTY_S.clear()
        access.RESTRICTED_PENALTY_S.update(original_pen)
    assert profile.profile_version() == before


def test_the_grid_version_distinguishes_grids_that_are_not_nested():
    """The 100 m and 200 m Triangle grids have different origins (661900/4003500 against
    661800/4003600), so a cached surface from one must never be served for the other."""
    from locfinder import profile
    from locfinder.metros import TRIANGLE

    g100, g200 = TRIANGLE.grid(100.0), TRIANGLE.grid(200.0)
    assert (g100.x_min, g100.y_max) != (g200.x_min, g200.y_max), "not nested, as measured"
    assert profile.grid_version(g100) != profile.grid_version(g200)
    assert profile.grid_version(g100) == profile.grid_version(TRIANGLE.grid(100.0))


def test_the_profile_digest_is_stable_across_processes():
    import subprocess
    import sys

    from locfinder import profile
    expected = profile.profile_version()
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'.'); from locfinder import profile; "
         "print(profile.profile_version())"],
        capture_output=True, text=True, check=True)
    assert out.stdout.strip() == expected


# ---------------------------------------------------------------- Codex pass-8 regressions

def test_a_non_finite_window_is_refused():
    """Pass-8 M3. `window_s <= 0` is false for NaN, so NaN and +inf both passed."""
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            tq(window_s=bad)


def test_the_transit_window_and_the_surface_horizon_must_be_one_number():
    """Pass-8 M3. Two numbers mean two definitions of "past the horizon"; `snap.py` needs one."""
    with pytest.raises(ValueError, match="same number"):
        key(mode="transit", engine="motis-one-to-all", transit=tq(), horizon_s=120 * 60.0,
            anchor_lonlat=None, anchor_round_dp=None)
    assert transit_key().horizon_s == WINDOW_S


def test_a_hand_typed_version_string_is_refused():
    """Pass-8 H3. Convention is not enforcement: a version that cannot change when the model
    changes is worse than none, because it looks like provenance."""
    for bad in ("speeds-v0", "g1", "", "whatever"):
        with pytest.raises(ValueError, match="not a derived version"):
            key(profile_version=bad)
    with pytest.raises(ValueError, match="not a derived version"):
        key(grid_version="g1")


def test_the_expansion_adapter_constants_are_in_the_profile_digest():
    """Pass-8 H3's executed counterexample: changing the expansion node-merge quantisation changed
    which endpoints merge, and neither the profile nor the key noticed."""
    from locfinder.traveltime import expansion
    before = profile.profile_version()
    original = expansion._NODE_SNAP_M
    try:
        expansion._NODE_SNAP_M = 1.0
        assert profile.profile_version() != before
    finally:
        expansion._NODE_SNAP_M = original
    assert profile.profile_version() == before


def test_a_non_finite_horizon_is_refused():
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="horizon_s"):
            key(horizon_s=bad)
