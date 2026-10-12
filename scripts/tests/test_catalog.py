"""Tests for scripts/catalog.py — canonical catalog contract (card t_749084c1)."""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from catalog import CatalogError, card_id, catalog_summary, load_catalog, validate_catalog  # noqa: E402


def make_guide(gid="guide-a", cards=2, status="published", **over):
    g = {
        "id": gid,
        "title": f"Title {gid}",
        "author": None,
        "source_reel_id": None,
        "source_url": None,
        "public_path": f"{gid}/",
        "icloud_path": None,
        "status": status,
        "goals": [],
        "body_parts": [],
        "equipment": [],
        "locations": [],
        "duration_min": None,
        "intensity": "unknown",
        "best_for": [],
        "avoid_if": [],
        "cards": [
            {
                "id": card_id(gid, i + 1),
                "position": i + 1,
                "name": f"Move {i + 1}",
                "dose": None,
                "tag": None,
                "clip": None,
                "url": f"{gid}/#ex{i + 1}",
            }
            for i in range(cards)
        ],
    }
    g.update(over)
    return g


def make_catalog(guides=None):
    return {
        "schema_version": 1,
        "generated_at": "2026-10-12T00:00:00Z",
        "guides": guides if guides is not None else [make_guide()],
    }


@pytest.fixture()
def env(tmp_path):
    repo = tmp_path / "repo"
    icloud = tmp_path / "icloud"
    (repo / "guide-a").mkdir(parents=True)
    (repo / "guide-a" / "index.html").write_text("<html></html>")
    (icloud / "author_guide-a_reel1").mkdir(parents=True)
    (icloud / "author_guide-a_reel1" / "index.html").write_text("<html></html>")
    return repo, icloud


def test_card_id_format():
    assert card_id("guide-a", 1) == "guide-a#01"
    assert card_id("guide-a", 12) == "guide-a#12"


def test_load_catalog_rejects_non_dict(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(CatalogError):
        load_catalog(p)


def test_load_catalog_rejects_missing_guides(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps({"schema_version": 1}))
    with pytest.raises(CatalogError):
        load_catalog(p)


def test_valid_catalog_has_no_errors(env):
    repo, icloud = env
    cat = make_catalog()
    cat["guides"][0]["icloud_path"] = "author_guide-a_reel1/"
    assert validate_catalog(cat, repo, icloud) == []


def test_duplicate_guide_ids_fail(env):
    repo, icloud = env
    cat = make_catalog([make_guide(), make_guide()])
    errs = validate_catalog(cat, repo, icloud)
    assert any("duplicate guide id" in e.lower() for e in errs)


def test_duplicate_card_ids_fail(env):
    repo, icloud = env
    g = make_guide()
    g["cards"][1]["id"] = g["cards"][0]["id"]
    cat = make_catalog([g])
    errs = validate_catalog(cat, repo, icloud)
    assert any("duplicate card id" in e.lower() for e in errs)


def test_card_id_must_match_guide_and_position(env):
    repo, icloud = env
    g = make_guide(gid="guide-a")
    g["cards"][0]["id"] = "other-guide#01"
    g["cards"][1]["position"] = 5  # id says 02, position says 5
    cat = make_catalog([g])
    errs = validate_catalog(cat, repo, icloud)
    assert any("card id" in e.lower() for e in errs)


def test_status_must_be_known(env):
    repo, icloud = env
    g = make_guide(status="live")
    errs = validate_catalog(make_catalog([g]), repo, icloud)
    assert any("status" in e.lower() for e in errs)


def test_duration_must_be_null_or_nonnegative(env):
    repo, icloud = env
    g = make_guide(duration_min=-3)
    errs = validate_catalog(make_catalog([g]), repo, icloud)
    assert any("duration_min" in e for e in errs)
    g2 = make_guide(duration_min="ten")
    errs2 = validate_catalog(make_catalog([g2]), repo, icloud)
    assert any("duration_min" in e for e in errs2)


def test_published_requires_existing_public_index(env):
    repo, icloud = env
    g = make_guide(public_path="missing-guide/")
    errs = validate_catalog(make_catalog([g]), repo, icloud)
    assert any("public_path" in e for e in errs)
    # deployment_pending does not demand the live route yet
    g2 = make_guide(public_path="missing-guide/", status="deployment_pending")
    assert validate_catalog(make_catalog([g2]), repo, icloud) == []


def test_null_legacy_metadata_accepted(env):
    repo, icloud = env
    g = make_guide(
        author=None,
        duration_min=None,
        intensity="unknown",
        locations=["unknown"],
        best_for=["unknown"],
        equipment=["none"],
        goals=[],
        body_parts=[],
        avoid_if=[],
    )
    g["cards"] = [{"id": "guide-a#01", "position": 1, "name": "M", "dose": None,
                   "tag": None, "clip": None, "url": "guide-a/#ex1"}]
    assert validate_catalog(make_catalog([g]), repo, icloud) == []


def test_summary_counts_guides_cards_missing_mirrors(env):
    repo, icloud = env
    cat = make_catalog(
        [make_guide(icloud_path="author_guide-a_reel1/"), make_guide(gid="guide-b")]
    )
    s = catalog_summary(cat, repo, icloud)
    assert s["guides"] == 2
    assert s["cards"] == 4
    assert s["missing_mirrors"] == 1  # guide-b has icloud_path None
    assert s["missing_mirror_ids"] == ["guide-b"]
