"""Tests for daily-decision metadata validation (card t_749084c1 Phase 4)."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from catalog import validate_daily_metadata  # noqa: E402


def guide(gid="g1", **over):
    g = {
        "id": gid,
        "duration_min": 10,
        "intensity": "easy",
        "locations": ["home"],
        "best_for": ["morning"],
        "avoid_if": [],
    }
    g.update(over)
    return g


def catalog_of(*guides):
    return {"schema_version": 1, "guides": list(guides)}


def test_complete_guide_buckets():
    rep = validate_daily_metadata(catalog_of(guide()))
    assert rep["complete"] == ["g1"]
    assert rep["unknown"] == []
    assert rep["invalid"] == []


def test_intensity_enum_enforced():
    rep = validate_daily_metadata(catalog_of(guide(intensity="brutal")))
    assert any("intensity" in e for e in rep["invalid_errors"])
    assert rep["invalid"] == ["g1"]


def test_locations_enum_enforced():
    rep = validate_daily_metadata(catalog_of(guide(locations=["mars"])))
    assert any("locations" in e for e in rep["invalid_errors"])
    rep2 = validate_daily_metadata(catalog_of(guide(locations=["unknown"])))
    assert rep2["invalid"] == []
    assert rep2["unknown"] == ["g1"]  # 'unknown' is legal but unresolved


def test_best_for_enum_enforced():
    rep = validate_daily_metadata(catalog_of(guide(best_for=["brunch"])))
    assert any("best_for" in e for e in rep["invalid_errors"])


def test_duration_required_else_unknown():
    rep = validate_daily_metadata(catalog_of(guide(duration_min=None)))
    assert rep["unknown"] == ["g1"]
    assert rep["invalid"] == []


def test_avoid_if_must_be_list():
    rep = validate_daily_metadata(catalog_of(guide(avoid_if="bad knees")))
    assert any("avoid_if" in e for e in rep["invalid_errors"])


def test_avoid_if_rejects_medical_diagnoses():
    for term in ("sciatica relief", "herniated disc fix", "cures arthritis",
                 "treats scoliosis", "rebuilds ACL tear"):
        rep = validate_daily_metadata(catalog_of(guide(avoid_if=[term])))
        assert rep["invalid"] == ["g1"], term
        assert any("medical" in e for e in rep["invalid_errors"]), term


def test_unknown_reported_separately_not_invalid():
    rep = validate_daily_metadata(catalog_of(guide(gid="new"), guide(gid="legacy", duration_min=None, intensity="unknown", locations=[], best_for=[])))
    assert rep["complete"] == ["new"]
    assert rep["unknown"] == ["legacy"]
    assert rep["invalid"] == []


def test_counts_sum_to_all_guides():
    rep = validate_daily_metadata(catalog_of(
        guide(gid="a"), guide(gid="b", duration_min=None),
        guide(gid="c", intensity="nope")))
    assert rep["counts"] == {"complete": 1, "unknown": 1, "invalid": 1}
