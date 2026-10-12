"""Navigation-surface tests over the live hub (card t_749084c1 Phase 6).

Every navigation page must link Today; guide links must resolve to catalog IDs;
displayed counts must equal catalog-derived counts; program.html must show the
CURRENT ISO week (never a hard-coded stale one).
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from build_navigation import check_navigation  # noqa: E402

PAGES = ["index.html", "cards.html", "program.html", "mixes.html", "today.html"]


def catalog():
    return json.loads((REPO / "data" / "guides.json").read_text())


def test_all_pages_link_today():
    for page in PAGES:
        if page == "today.html":
            continue  # it IS the Today page
        html = (REPO / page).read_text()
        assert 'href="today.html"' in html, f"{page} does not link today.html"


def test_today_links_back():
    html = (REPO / "today.html").read_text()
    assert 'href="index.html"' in html
    assert 'href="cards.html"' in html


def test_check_navigation_reports_zero_errors():
    errs = check_navigation(REPO, REPO / "data" / "guides.json")
    assert errs == []


def test_guide_links_resolve_to_catalog():
    cat = catalog()
    ids = {g["id"] for g in cat["guides"]}
    mixes = {m["slug"] for m in json.loads((REPO / "data" / "mixes.json").read_text())}
    allowed = ids | mixes | set(PAGES) | {"thumbs"}
    for page in PAGES:
        html = (REPO / page).read_text()
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http", "#", "mailto:")):
                continue
            if "'" in href or "+" in href:
                continue  # JS-built hrefs (runtime templates), not real links
            root = href.split("/")[0].split("#")[0]
            if not root or root in allowed or root.endswith(".html"):
                continue
            # guide-directory links must be catalog IDs or known mixes
            assert root in allowed, f"{page}: unknown link target {root!r} ({href})"


def test_displayed_counts_equal_catalog_counts():
    cat = catalog()
    guides = cat["guides"]
    n_guides = len(guides)
    visible_cards = sum(1 for g in guides for c in g["cards"] if not c.get("hidden"))
    guides_with_cards = sum(1 for g in guides
                            if any(not c.get("hidden") for c in g["cards"]))
    no_eq = sum(1 for g in guides if g.get("equipment") == ["none"])
    thumbs = sum(1 for g in guides if (REPO / "thumbs" / f"{g['id']}.jpg").is_file())

    index = (REPO / "index.html").read_text()
    assert f"<b>{n_guides}</b> guides" in index, "index guides stat stale"
    assert f"<b>{no_eq}</b> no-equipment" in index, "index no-equipment stat stale"
    assert f"<b>{thumbs}</b> thumbnails" in index, "index thumbnails stat stale"

    cards = (REPO / "cards.html").read_text()
    assert f"<b>{visible_cards}</b> cards" in cards, "cards.html card count stale"
    assert f"<b>{guides_with_cards}</b> guides" in cards, "cards.html guide count stale"


def test_program_html_uses_current_iso_week():
    html = (REPO / "program.html").read_text()
    y, w, _ = dt.date.today().isocalendar()
    stamps = set(re.findall(r"ISO week (\d+) of (\d+)", html))
    assert stamps == {(str(w), str(y))}, f"stale ISO week stamps {stamps}, want {w}/{y}"
