"""Regression tests for hub header stat patching + nav (card t_749084c1 Phase 6).

Imports the live hub builder from the librarian profile — the same module the
cron runs — so the test breaks exactly when the selectors drift again.
"""

import importlib.util
import sys
from pathlib import Path

SYNC_PATH = Path("/Users/guy/.hermes/profiles/librarian/scripts/sync_workout_guides.py")

CURRENT_MARKUP = """
<header>
  <h1>Guides</h1>
  <div class="stats">
    <span class="stat"><b>128</b> guides</span>
    <span class="stat"><b>81</b> no-equipment</span>
    <span class="stat"><b>168</b> thumbnails</span>
  </div>
  <a href="cards.html" style="display:inline-block">Browse Exercise Cards</a>
</header>
"""


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_workout_guides", SYNC_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sync_workout_guides"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_patch_stats_updates_all_three_current_selectors():
    mod = load_sync_module()
    header = mod.patch_header_stats(CURRENT_MARKUP, stats_guides=174, stat_noeq=71,
                                    stat_thumbs=170)
    assert "<b>174</b> guides" in header
    assert "<b>71</b> no-equipment" in header
    assert "<b>170</b> thumbnails" in header
    assert "<b>128</b>" not in header and "<b>81</b>" not in header and "<b>168</b>" not in header


def test_patch_stats_is_exact_count_not_pattern_miss():
    """The old bug: selectors silently missed the current markup and left 128."""
    mod = load_sync_module()
    header = mod.patch_header_stats(CURRENT_MARKUP, stats_guides=174, stat_noeq=71,
                                    stat_thumbs=170)
    assert header != CURRENT_MARKUP  # something must actually change


def test_install_hub_nav_links_today_deterministically():
    mod = load_sync_module()
    once, changed1 = mod.install_hub_nav(CURRENT_MARKUP)
    assert changed1
    assert 'href="today.html"' in once
    for link in ("index.html", "cards.html", "program.html", "mixes.html"):
        assert f'href="{link}"' in once
    twice, changed2 = mod.install_hub_nav(once)
    assert twice == once and not changed2  # idempotent


def test_grid_enumeration_excludes_derived_mixes():
    mod = load_sync_module()
    slugs = mod.discover_guide_slugs()
    assert "mix-kettlebell-circuit" not in slugs
    assert "karin-avi-happier-spine-four-wall-mobility-drills_DeUvd7COzVv" in slugs
    assert len(slugs) == 226  # real guides only, matches data/guides.json count
