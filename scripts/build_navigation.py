#!/usr/bin/env python3
"""build_navigation.py — single local orchestrator for the workout-guides hub.

Order (canonical catalog first, everything downstream derived from it):
  build_catalog.py  -> data/guides.json
  build_cards.py    -> cards.html
  build_program.py  -> program.html (--date)
  build_mixes.py    -> mixes.html + mix pages
  build_today.py    -> today.html (--date)
  sync_workout_guides.py (librarian) -> index.html [+ iCloud mirror]

--check-only never writes: it validates the CURRENT artifacts against the
catalog and reports errors (zero = healthy).
--no-push regenerates local artifacts but never invokes git push
(sync script honors WG_NO_PUSH=1).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
SYNC_SCRIPT = Path("/Users/guy/.hermes/profiles/librarian/scripts/sync_workout_guides.py")
NAV_PAGES = ("index.html", "cards.html", "program.html", "mixes.html", "today.html")
GUIDE_LINK_RE = re.compile(r'href="([a-z0-9][a-z0-9._-]*)/"')


def _catalog_ids(repo: Path) -> tuple[set, set]:
    cat = json.loads((repo / "data" / "guides.json").read_text(encoding="utf-8"))
    ids = {g["id"] for g in cat["guides"]}
    mixes = set()
    if (repo / "data" / "mixes.json").is_file():
        mixes = {m["slug"] for m in json.loads((repo / "data" / "mixes.json").read_text())}
    return ids, mixes


def check_navigation(repo: Path, catalog_path: Path) -> list[str]:
    """Deterministic navigation errors; empty list = healthy."""
    repo = Path(repo)
    errors: list[str] = []

    for page in NAV_PAGES:
        p = repo / page
        if not p.is_file():
            errors.append(f"missing navigation page: {page}")
    if errors:
        return errors

    pages = {page: (repo / page).read_text(encoding="utf-8", errors="replace")
             for page in NAV_PAGES}
    for page, html in pages.items():
        if page == "today.html":
            continue  # it IS the Today page
        if 'href="today.html"' not in html:
            errors.append(f"{page}: does not link today.html")
    if 'href="index.html"' not in pages["today.html"]:
        errors.append("today.html: does not link index.html")
    if 'href="cards.html"' not in pages["today.html"]:
        errors.append("today.html: does not link cards.html")

    ids, mixes = _catalog_ids(repo)
    for page, html in pages.items():
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http", "#", "mailto:")):
                continue
            if "'" in href or "+" in href:
                continue  # JS-built hrefs (runtime templates), not real links
            root = href.split("/")[0].split("#")[0]
            if not root or root.endswith(".html") or root in ("thumbs",):
                continue
            if root in ids or root in mixes:
                continue
            errors.append(f"{page}: unknown link target {root!r} ({href})")

    guides = json.loads(catalog_path.read_text(encoding="utf-8"))["guides"]
    n_guides = len(guides)
    visible_cards = sum(1 for g in guides for c in g["cards"] if not c.get("hidden"))
    guides_with_cards = sum(1 for g in guides
                            if any(not c.get("hidden") for c in g["cards"]))
    no_eq = sum(1 for g in guides if g.get("equipment") == ["none"])
    thumbs = sum(1 for g in guides if (repo / "thumbs" / f"{g['id']}.jpg").is_file())

    index = pages["index.html"]
    if f"<b>{n_guides}</b> guides" not in index:
        errors.append("index.html: guides stat does not match catalog")
    if f"<b>{no_eq}</b> no-equipment" not in index:
        errors.append("index.html: no-equipment stat does not match catalog")
    if f"<b>{thumbs}</b> thumbnails" not in index:
        errors.append("index.html: thumbnails stat does not match catalog")
    cards = pages["cards.html"]
    if f"<b>{visible_cards}</b> cards" not in cards:
        errors.append("cards.html: card count does not match catalog")
    if f"<b>{guides_with_cards}</b> guides" not in cards:
        errors.append("cards.html: guide count does not match catalog")

    y, w, _ = dt.date.today().isocalendar()
    stamps = set(re.findall(r"ISO week (\d+) of (\d+)", pages["program.html"]))
    if stamps != {(str(w), str(y))}:
        errors.append(f"program.html: ISO week stamps {sorted(stamps)} != current {w}/{y}")

    return sorted(set(errors))


def _run(cmd: list, env_extra: dict | None = None) -> int:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, cwd=REPO, env=env)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="YYYY-MM-DD")
    ap.add_argument("--check-only", action="store_true",
                    help="validate current artifacts; write nothing")
    ap.add_argument("--no-push", action="store_true",
                    help="regenerate local artifacts but never git push")
    args = ap.parse_args()

    py = sys.executable
    if args.check_only:
        rc = _run([py, str(SCRIPTS / "build_catalog.py"),
                   "--repo", str(REPO), "--output", str(REPO / "data" / "guides.json"),
                   "--check-only"])
        errors = check_navigation(REPO, REPO / "data" / "guides.json")
        for e in errors:
            print(f"NAV ERROR: {e}")
        print(f"navigation check: {len(errors)} error(s)")
        return 0 if (rc == 0 and not errors) else 1

    steps: list[tuple[str, list, dict | None]] = [
        ("catalog", [py, str(SCRIPTS / "build_catalog.py"), "--repo", str(REPO),
                     "--output", str(REPO / "data" / "guides.json"),
                     "--metadata-report", str(REPO / "data" / "metadata-gaps.json")], None),
        ("cards", [py, str(SCRIPTS / "build_cards.py")], None),
        ("program", [py, str(SCRIPTS / "build_program.py"), "--date", args.date], None),
        ("mixes", [py, str(SCRIPTS / "build_mixes.py")], None),
        ("today", [py, str(SCRIPTS / "build_today.py"),
                   "--catalog", str(REPO / "data" / "guides.json"),
                   "--presets", str(REPO / "data" / "today.json"),
                   "--date", args.date, "--output", str(REPO / "today.html")], None),
        ("hub-sync", [py, str(SYNC_SCRIPT)],
         {"WG_NO_PUSH": "1"} if args.no_push else None),
    ]
    for name, cmd, env_extra in steps:
        print(f"==> {name}")
        rc = _run(cmd, env_extra)
        if rc != 0:
            print(f"step {name} failed (rc={rc})", file=sys.stderr)
            return rc

    errors = check_navigation(REPO, REPO / "data" / "guides.json")
    for e in errors:
        print(f"NAV ERROR: {e}")
    print(f"navigation check: {len(errors)} error(s)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
