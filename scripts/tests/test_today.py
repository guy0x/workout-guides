"""Tests for scripts/build_today.py — deterministic Today page (card t_749084c1)."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from build_today import no_equipment_ok, select_session  # noqa: E402

PY = sys.executable
DATE = "2026-10-12"

PRESETS = {
    "schema_version": 1,
    "presets": [
        {"id": "morning", "label": "Morning reset", "duration_max": 12, "goals": ["mobility", "posture"]},
        {"id": "desk-break", "label": "Desk break", "duration_max": 8, "locations": ["office", "home"], "intensity": ["recovery", "easy"]},
        {"id": "gym", "label": "Gym warm-up", "duration_max": 12, "best_for": ["pre-gym"]},
        {"id": "recovery", "label": "Recovery", "duration_max": 15, "intensity": ["recovery", "easy"]},
    ],
}


def guide(gid, duration=10, goals=("mobility",), equipment=("none",), locations=("home",),
          intensity="easy", best_for=(), cards=3):
    return {
        "id": gid, "title": f"Title {gid}", "status": "published",
        "duration_min": duration, "goals": list(goals), "equipment": list(equipment),
        "locations": list(locations), "intensity": intensity, "best_for": list(best_for),
        "cards": [
            {"id": f"{gid}#{i:02d}", "position": i, "name": f"Move {i}",
             "dose": "2 x 10", "tag": None, "clip": None, "url": f"{gid}/#ex{i}"}
            for i in range(1, cards + 1)
        ],
    }


def catalog_of(*guides):
    return {"schema_version": 1, "guides": list(guides)}


def run_build(tmp_path, catalog, *extra):
    cat_p = tmp_path / "guides.json"
    cat_p.write_text(json.dumps(catalog))
    pres_p = tmp_path / "today.json"
    pres_p.write_text(json.dumps(PRESETS))
    out = tmp_path / "today.html"
    cmd = [PY, str(REPO / "scripts" / "build_today.py"), "--catalog", str(cat_p),
           "--presets", str(pres_p), "--date", DATE, "--output", str(out), *extra]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc, out


def test_no_equipment_filter():
    assert no_equipment_ok(guide("a", equipment=["none"]))
    assert not no_equipment_ok(guide("a", equipment=["none", "band"]))
    assert not no_equipment_ok(guide("a", equipment=["kettlebell"]))


def test_duration_filter_strict():
    preset = {"id": "x", "duration_max": 8}
    pool = [guide("short", duration=8), guide("long", duration=12),
            guide("unknown", duration=None)]
    picked = select_session(catalog_of(*pool), preset)
    ids = [g["id"] for g in picked["guides"]]
    assert "short" in ids and "long" not in ids  # strict pool filters by duration


def test_stable_card_ordering():
    pool = [guide("b", duration=5), guide("a", duration=5)]
    picked = select_session(catalog_of(*pool), {"id": "x"})
    flat = [(g["id"], c["position"]) for g in picked["guides"] for c in g["picked_cards"]]
    assert flat == sorted(flat)
    assert [g["id"] for g in picked["guides"]] == ["a", "b"]  # tie-break by id


def test_relaxed_fallback_marks_flexible():
    # gym preset wants best_for pre-gym; nobody has it -> flexible match
    pool = [guide("warm", duration=10, goals=("gym",))]
    picked = select_session(catalog_of(*pool), PRESETS["presets"][2])
    assert picked["flexible"] is True
    assert [g["id"] for g in picked["guides"]] == ["warm"]


def test_draft_and_cardless_excluded():
    draft = guide("draft")
    draft["status"] = "draft"
    cardless = guide("cardless")
    cardless["cards"] = []
    picked = select_session(catalog_of(draft, cardless, guide("real")), {"id": "x"})
    assert [g["id"] for g in picked["guides"]] == ["real"]


def test_presets_diverge_before_reusing_guides():
    pool = [guide(f"m{i}", duration=5, goals=("mobility",)) for i in range(8)]
    a = select_session(catalog_of(*pool), {"id": "a"})
    b = select_session(catalog_of(*pool), {"id": "b"}, exclude_ids={g["id"] for g in a["guides"]})
    a_ids = {g["id"] for g in a["guides"]}
    b_ids = {g["id"] for g in b["guides"]}
    assert not (a_ids & b_ids)  # fresh picks while the pool allows
    assert len(b_ids) == 3


def test_page_contains_presets_links_and_done_keys(tmp_path):
    pool = [guide(f"g{i}", duration=5) for i in range(4)]
    proc, out = run_build(tmp_path, catalog_of(*pool))
    assert proc.returncode == 0, proc.stderr
    html = out.read_text()
    for pid in ("morning", "desk-break", "gym", "recovery"):
        assert f'data-preset="{pid}"' in html
    assert "<h1" in html and "Today" in html
    assert "wg.done." in html and DATE in html
    assert 'href="index.html"' in html and 'href="cards.html"' in html
    assert "device-local" in html
    assert "g0/#ex1" in html  # direct anchor links
    assert "http" not in {s.split(":")[0] for s in
                          [l.split('src="')[1].split('"')[0] for l in html.split("\n") if 'src="http' in l]}


def test_deterministic_byte_for_byte(tmp_path):
    pool = [guide(f"g{i}", duration=5 + i) for i in range(5)]
    p1, out1 = run_build(tmp_path, catalog_of(*pool))
    p2, out2 = run_build(tmp_path, catalog_of(*pool))
    assert out1.read_bytes() == out2.read_bytes()


def test_dry_run_writes_nothing(tmp_path):
    pool = [guide("g0", duration=5)]
    proc, out = run_build(tmp_path, catalog_of(*pool), "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert not out.exists()
    assert "today" in proc.stdout.lower()
