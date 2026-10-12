"""Tests for scripts/verify_publication.py — layered publication status."""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from verify_publication import classify  # noqa: E402


def layers(local_html=True, local_gifs=True, github=200, pages=200, icloud=True):
    return {"local_html": local_html, "local_gifs": local_gifs,
            "github_contents": github, "pages_route": pages,
            "icloud_mirror": icloud}


def test_all_layers_ok_is_verified():
    assert classify(layers()) == "verified"


def test_pages_404_is_deployment_pending_not_live():
    assert classify(layers(pages=404)) == "deployment_pending"


def test_pages_timeout_is_deployment_pending():
    assert classify(layers(pages=0)) == "deployment_pending"


def test_github_missing_is_failed():
    assert classify(layers(github=404)) == "failed"


def test_local_missing_is_failed_even_if_pages_200():
    assert classify(layers(local_html=False)) == "failed"
    assert classify(layers(local_gifs=False)) == "failed"


def test_missing_icloud_mirror_does_not_block_publication():
    assert classify(layers(icloud=False)) == "verified"


def test_classifier_never_claims_live_from_github_alone():
    """GitHub contents 200 alone (Pages 404) must NOT be 'verified'."""
    assert classify(layers(pages=404)) != "verified"
    assert classify(layers(pages=0)) != "verified"


def test_report_counts(tmp_path):
    from verify_publication import build_report
    repo = tmp_path / "repo"
    (repo / "guide-a").mkdir(parents=True)
    (repo / "guide-a" / "index.html").write_text("<html><img src='g.gif'/></html>")
    (repo / "guide-a" / "g.gif").write_bytes(b"GIF")
    (repo / "guide-b").mkdir()
    (repo / "guide-b" / "index.html").write_text("<html></html>")
    cat = tmp_path / "cat.json"
    cat.write_text(json.dumps({"schema_version": 1, "guides": [
        {"id": "guide-a", "public_path": "guide-a/", "icloud_path": None},
        {"id": "guide-b", "public_path": "guide-b/", "icloud_path": None},
    ]}))
    # mocked network: guide-a fully live, guide-b pages 404
    def fake_pages(slug, base):
        return 200 if slug == "guide-a" else 404

    def fake_gh(url):
        return 200

    report = build_report(repo, json.loads(cat.read_text()),
                          icloud_root=tmp_path / "icloud-missing",
                          pages_base="https://x.test/", pages_check=fake_pages,
                          github_check=fake_gh)
    assert report["counts"] == {"verified": 1, "deployment_pending": 1, "failed": 0}
    by_id = {e["id"]: e for e in report["guides"]}
    assert by_id["guide-a"]["status"] == "verified"
    assert by_id["guide-b"]["status"] == "deployment_pending"
    assert by_id["guide-a"]["missing_mirror"] is True
