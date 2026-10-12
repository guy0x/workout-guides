"""Tests for scripts/reconcile_mirrors.py — additive iCloud mirror reconciliation."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable

CATALOG = {
    "schema_version": 1,
    "generated_at": "2026-10-12T00:00:00Z",
    "guides": [
        {"id": "guide-ok", "icloud_path": "Author_guide-ok_Reel1/"},
        {"id": "guide-miss", "icloud_path": None},
        {"id": "guide-drift", "icloud_path": "Author_guide-drift_Reel3/"},
    ],
}


def make_world(tmp_path):
    repo = tmp_path / "repo"
    icloud = tmp_path / "icloud"
    for slug in ("guide-ok", "guide-miss", "guide-drift"):
        d = repo / slug
        d.mkdir(parents=True)
        (d / "index.html").write_text(f"<html>{slug}</html>")
        (d / "gif-01.gif").write_bytes(b"GIF")
    (icloud / "Author_guide-ok_Reel1").mkdir(parents=True)
    (icloud / "Author_guide-ok_Reel1" / "index.html").write_text("<html>guide-ok</html>")
    (icloud / "Author_guide-ok_Reel1" / "gif-01.gif").write_bytes(b"GIF")
    (icloud / "Author_guide-drift_Reel3").mkdir(parents=True)
    (icloud / "Author_guide-drift_Reel3" / "index.html").write_text("<html>OLD</html>")
    # extra legacy file in the drift mirror must NEVER be deleted by apply
    (icloud / "Author_guide-drift_Reel3" / "old-asset.txt").write_text("keep me")
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps(CATALOG))
    return repo, icloud, cat


def run(tmp_path, *extra):
    repo, icloud, cat = make_world(tmp_path)
    report = tmp_path / "report.json"
    cmd = [PY, str(REPO / "scripts" / "reconcile_mirrors.py"),
           "--catalog", str(cat), "--repo", str(repo), "--icloud", str(icloud),
           "--report", str(report), *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc, report, repo, icloud


def tree(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def test_classifies_unchanged_missing_drifted(tmp_path):
    proc, report, *_ = run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(report.read_text())
    assert data["counts"] == {"unchanged": 1, "missing": 1, "drifted": 1}
    assert data["unchanged"] == ["guide-ok"]
    assert data["missing"] == ["guide-miss"]
    assert data["drifted"] == ["guide-drift"]


def test_dry_run_writes_nothing_to_icloud(tmp_path):
    proc, report, repo, icloud = run(tmp_path)  # default is dry-run
    before = tree(icloud)
    assert before == tree(icloud)
    # also explicit --dry-run
    proc2, *_ = run(tmp_path, "--dry-run")
    assert proc2.returncode == 0


def test_apply_single_id_copies_and_never_deletes(tmp_path):
    proc, report, repo, icloud = run(tmp_path, "--apply", "--id", "guide-drift")
    assert proc.returncode == 0, proc.stderr
    mirror = icloud / "Author_guide-drift_Reel3"
    assert (mirror / "index.html").read_text() == "<html>guide-drift</html>"
    assert (mirror / "gif-01.gif").read_bytes() == b"GIF"
    assert (mirror / "old-asset.txt").read_text() == "keep me"  # preserved
    # other guides untouched
    assert not (icloud / "Author_guide-ok_Reel1" / "extra").exists()
    assert tree(icloud / "Author_guide-ok_Reel1") == ["gif-01.gif", "index.html"]


def test_apply_without_id_refused(tmp_path):
    proc, *_ = run(tmp_path, "--apply")
    assert proc.returncode != 0
    assert "id" in (proc.stderr + proc.stdout).lower()


def test_apply_bulk_refused(tmp_path):
    proc, *_ = run(tmp_path, "--apply", "--id", "guide-drift", "--id", "guide-miss")
    assert proc.returncode != 0


def test_apply_missing_guide_creates_folder_additively(tmp_path):
    proc, report, repo, icloud = run(tmp_path, "--apply", "--id", "guide-miss")
    assert proc.returncode == 0, proc.stderr
    # guide-miss has icloud_path null -> apply must create <slug>/ folder
    mirror = icloud / "guide-miss"
    assert (mirror / "index.html").read_text() == "<html>guide-miss</html>"
    assert (mirror / "gif-01.gif").read_bytes() == b"GIF"
