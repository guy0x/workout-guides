"""Tests for scripts/build_catalog.py — canonical catalog builder (card t_749084c1)."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from catalog import card_id, load_catalog, validate_catalog  # noqa: E402

PY = sys.executable
GEN_AT = "2026-10-12T00:00:00Z"

SPEC = {
    "slug": "spec-guide",
    "title": "Spec Guide Title",
    "author": "spec.author",
    "reel_id": "ReeLid123",
    "source_url": "https://www.instagram.com/reel/ReeLid123/",
    "categories": ["mobility"],
    "gear": ["mat"],
    "duration_min": 7,
    "status": "live",
    "cards": [
        {"name": "Drill One", "tag": "Drill 1", "dose": "2 x 10",
         "clip": {"start": 0.0, "duration": 6.0}},
        {"name": "Drill Two", "tag": "Drill 2", "dose": "60 sec",
         "clip": {"start": 6.0, "duration": 5.0}, "hidden": True},
    ],
}

LEGACY_HTML = """<!DOCTYPE html><html><head><title>Legacy Guide</title></head><body>
<div class="card" id="ex1"><div class="card-num">1</div><div class="card-body">
<div class="card-title-row"><h2>Old Move A</h2><span class="section-tag">Drill 1</span></div>
<div class="dose">3 x 8</div></div></div>
<div class="card" id="ex2"><div class="card-num">2</div><div class="card-body">
<div class="card-title-row"><h2>Old Move B</h2></div></div></div>
</body></html>"""

OVERRIDES = {"legacy-guide": {"title": "Legacy Override Title", "desc": "d", "tags": [],
                              "gear": ["none"]}}


def make_world(tmp_path):
    """A mini hub: one spec-backed guide, one legacy guide, one derived mix page."""
    repo = tmp_path / "repo"
    specs = tmp_path / "specs"
    icloud = tmp_path / "icloud"
    for d in (repo, specs, icloud):
        d.mkdir(parents=True, exist_ok=True)

    # spec-backed guide
    g1 = repo / "spec-guide"
    g1.mkdir(exist_ok=True)
    (g1 / "index.html").write_text(
        '<html><body><div class="card" id="ex1"></div>'
        '<img class="gif" src="gif-01.gif"/></body></html>', encoding="utf-8")
    (g1 / "gif-01.gif").write_bytes(b"GIF89a")
    (specs / "spec-guide.json").write_text(json.dumps(SPEC), encoding="utf-8")

    # legacy guide (no spec, HTML anchors, override title)
    g2 = repo / "legacy-guide"
    g2.mkdir(exist_ok=True)
    (g2 / "index.html").write_text(LEGACY_HTML, encoding="utf-8")

    # derived mix page — must be excluded from the guide catalog
    mix = repo / "mix-kettlebell-circuit"
    mix.mkdir(exist_ok=True)
    (mix / "index.html").write_text("<html><body>mix</body></html>", encoding="utf-8")

    (icloud / "Spec Author_spec-guide_ReeLid123").mkdir(exist_ok=True)
    (icloud / "Spec Author_spec-guide_ReeLid123" / "index.html").write_text("x")
    (icloud / "someone_legacy-guide_abCd12345").mkdir(exist_ok=True)
    (icloud / "someone_legacy-guide_abCd12345" / "index.html").write_text("x")

    overrides_p = tmp_path / "overrides.json"
    overrides_p.write_text(json.dumps(OVERRIDES), encoding="utf-8")
    pages_p = tmp_path / "pages.json"
    pages_p.write_text(json.dumps({"spec-guide": 200, "legacy-guide": 200}), encoding="utf-8")
    return repo, specs, icloud, overrides_p, pages_p


def run_build(tmp_path, *extra, **kw):
    repo, specs, icloud, overrides_p, pages_p = make_world(tmp_path)
    out = tmp_path / "guides.json"
    cmd = [PY, str(REPO / "scripts" / "build_catalog.py"),
           "--repo", str(repo), "--specs", str(specs), "--icloud", str(icloud),
           "--overrides", str(overrides_p), "--pages-cache", str(pages_p),
           "--output", str(out), "--generated-at", GEN_AT, *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return proc, out, repo, icloud


def test_build_produces_valid_catalog_with_stable_ids(tmp_path):
    proc, out, *_ = run_build(tmp_path)
    assert proc.returncode == 0, proc.stderr
    cat = load_catalog(out)
    by_id = {g["id"]: g for g in cat["guides"]}
    assert set(by_id) == {"spec-guide", "legacy-guide"}  # mix excluded
    assert [c["id"] for c in by_id["spec-guide"]["cards"]] == [
        card_id("spec-guide", 1), card_id("spec-guide", 2)]
    assert [c["id"] for c in by_id["legacy-guide"]["cards"]] == [
        card_id("legacy-guide", 1), card_id("legacy-guide", 2)]
    assert validate_catalog(cat, REPO, tmp_path) != []  # REPO paths differ; ids still well-formed
    # validate inside its own world instead
    errs = validate_catalog(cat, tmp_path / "repo", tmp_path / "icloud")
    assert errs == []


def test_prefers_spec_fields(tmp_path):
    proc, out, *_ = run_build(tmp_path)
    g = {g["id"]: g for g in load_catalog(out)["guides"]}["spec-guide"]
    assert g["title"] == "Spec Guide Title"
    assert g["author"] == "spec.author"
    assert g["source_reel_id"] == "ReeLid123"
    assert g["duration_min"] == 7
    assert g["goals"] == ["mobility"]
    assert g["equipment"] == ["mat"]
    assert g["cards"][0]["clip"] == {"start": 0.0, "duration": 6.0}
    assert g["cards"][0]["url"] == "spec-guide/#ex1"
    assert "hidden" not in g["cards"][0]
    assert g["cards"][1].get("hidden") is True  # curation flag preserved, not re-guessed


def test_legacy_falls_back_to_overrides_and_html(tmp_path):
    proc, out, *_ = run_build(tmp_path)
    g = {g["id"]: g for g in load_catalog(out)["guides"]}["legacy-guide"]
    assert g["title"] == "Legacy Override Title"
    assert g["duration_min"] is None          # unknown stays null, never guessed
    assert g["intensity"] == "unknown"
    assert [c["name"] for c in g["cards"]] == ["Old Move A", "Old Move B"]
    assert g["cards"][0]["dose"] == "3 x 8"
    assert g["cards"][1]["dose"] is None


def test_icloud_paths_derived_without_writing(tmp_path):
    proc, out, _, icloud = run_build(tmp_path)
    before = sorted(p.name for p in icloud.iterdir())
    g = {g["id"]: g for g in load_catalog(out)["guides"]}
    assert g["spec-guide"]["icloud_path"] == "Spec Author_spec-guide_ReeLid123/"
    assert g["legacy-guide"]["icloud_path"] == "someone_legacy-guide_abCd12345/"
    after = sorted(p.name for p in icloud.iterdir())
    assert before == after  # read-only


def test_idempotent_byte_for_byte(tmp_path):
    p1, out1, *_ = run_build(tmp_path)
    p2, out2, *_ = run_build(tmp_path)
    assert out1.read_bytes() == out2.read_bytes()


def test_check_only_writes_nothing(tmp_path):
    proc, out, *_ = run_build(tmp_path)          # first build writes the file
    first = out.read_bytes()
    proc2, out2, *_ = run_build(tmp_path, "--check-only")
    assert proc2.returncode == 0, proc2.stderr + proc2.stdout
    assert out.read_bytes() == first             # unchanged
    assert not out2.exists() or out2.read_bytes() == first


def test_missing_local_files_mark_draft_not_published(tmp_path):
    repo, specs, icloud, overrides_p, pages_p = make_world(tmp_path)
    (repo / "spec-guide" / "gif-01.gif").unlink()   # referenced GIF gone
    out = tmp_path / "guides.json"
    cmd = [PY, str(REPO / "scripts" / "build_catalog.py"),
           "--repo", str(repo), "--specs", str(specs), "--icloud", str(icloud),
           "--overrides", str(overrides_p), "--pages-cache", str(pages_p),
           "--output", str(out), "--generated-at", GEN_AT]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    g = {g["id"]: g for g in load_catalog(out)["guides"]}["spec-guide"]
    assert g["status"] == "draft"


def test_pages_not_200_marks_deployment_pending(tmp_path):
    repo, specs, icloud, overrides_p, pages_p = make_world(tmp_path)
    pages_p.write_text(json.dumps({"spec-guide": 200, "legacy-guide": 404}))
    out = tmp_path / "guides.json"
    cmd = [PY, str(REPO / "scripts" / "build_catalog.py"),
           "--repo", str(repo), "--specs", str(specs), "--icloud", str(icloud),
           "--overrides", str(overrides_p), "--pages-cache", str(pages_p),
           "--output", str(out), "--generated-at", GEN_AT]
    subprocess.run(cmd, capture_output=True, text=True)
    g = {g["id"]: g for g in load_catalog(out)["guides"]}["legacy-guide"]
    assert g["status"] == "deployment_pending"
