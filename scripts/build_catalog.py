#!/usr/bin/env python3
"""build_catalog.py — build data/guides.json, the canonical navigation manifest.

Sources, in priority order:
  1. guide_pipeline specs  (authored content: title, author, reel, cards, clips)
  2. data/index-overrides.json  (legacy display titles/descriptions/gear)
  3. parsed guide HTML  (card anchors <div class="card" id="exN">)

Never invents unknown metadata (duration/intensity/locations stay null/unknown).
Derived mix-* pages are navigation surfaces, not guides: excluded from the
catalog; they remain built from data/mixes.json.

Status semantics (no network needed unless --verify-pages):
  draft              local index.html missing OR a referenced GIF is missing
  published          local files complete AND Pages cache/verify says 200
  deployment_pending local files complete but Pages not (yet) 200
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cards import detect_body_parts  # reuse the established classifier
from catalog import card_id, catalog_summary, validate_catalog, validate_daily_metadata

GYM_GEAR = {"machine", "cable", "barbell", "bench", "plate", "bosu", "bar"}
HOME_GEAR = {"none", "mat", "wall"}
REEL_IN_SLUG_RE = re.compile(r"_([A-Za-z0-9][A-Za-z0-9-]{7,19})$")
CARD_DIV_RE = re.compile(r'<div class="card" id="ex(\d+)">')
GIF_SRC_RE = re.compile(r'src="([^"/:]+\.(?:gif|jpe?g|png|webp))"')


def parse_html_cards(html: str) -> list[dict]:
    """Extract legacy cards from guide HTML anchors; None for unknown fields."""
    marks = list(CARD_DIV_RE.finditer(html))
    cards = []
    for i, m in enumerate(marks):
        block = html[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(html)]
        name_m = re.search(r"<h2>(.*?)</h2>", block, re.S)
        tag_m = re.search(r'class="section-tag">(.*?)</span>', block, re.S)
        dose_m = re.search(r'class="dose">(.*?)</div>', block, re.S)
        clean = lambda s: re.sub(r"<[^>]+>", "", s).strip() if s else None  # noqa: E731
        cards.append({
            "position": int(m.group(1)),
            "name": clean(name_m.group(1)) if name_m else None,
            "tag": clean(tag_m.group(1)) if tag_m else None,
            "dose": clean(dose_m.group(1)) if dose_m else None,
            "clip": None,
        })
    return cards


def local_files_ok(gdir: Path) -> bool:
    """index.html exists and every referenced relative image exists locally."""
    index = gdir / "index.html"
    if not index.is_file():
        return False
    html = index.read_text(encoding="utf-8", errors="replace")
    for src in GIF_SRC_RE.findall(html):
        if not (gdir / src).is_file():
            return False
    return True


def match_icloud_folder(slug: str, reel: str | None, icloud_root: Path) -> str | None:
    """Find the iCloud mirror folder for a slug without writing anything."""
    if not icloud_root.is_dir():
        return None
    low = slug.lower()
    hits = []
    for entry in icloud_root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        nlow = name.lower()
        if nlow == low or nlow.startswith(low + "_") or f"_{low}_" in nlow or nlow.endswith("_" + low):
            hits.append(name)
    if not hits:
        return None
    with_index = [h for h in hits if (icloud_root / h / "index.html").is_file()]
    pool = with_index or hits
    if reel:
        reel_hits = [h for h in pool if reel.lower() in h.lower()]
        if reel_hits:
            pool = reel_hits
    return sorted(pool)[0] + "/"


def derive_locations(categories: list, equipment: list, office_safe_fn) -> list:
    """Conservative, rule-based location tags. Empty list = unknown."""
    eq = set(equipment or [])
    if "gym" in categories or eq & GYM_GEAR:
        return ["gym"]
    if eq and eq <= HOME_GEAR:
        return ["home"]
    if "chair" in eq:
        return ["home", "office"]
    if eq and office_safe_fn and office_safe_fn(sorted(eq)):
        return ["home", "office"]
    return []


def check_pages(url: str, timeout: float = 6.0) -> int:
    """HEAD one Pages route; returns the HTTP status code or 0 on failure."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "wg-catalog/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:  # noqa: TRY302
        return exc.code
    except Exception:
        return 0


def build_catalog(repo: Path, specs_dir: Path, icloud_root: Path,
                  overrides_path: Path | None, pages_codes: dict[str, int],
                  generated_at: str, verify_pages_base: str | None = None) -> dict:
    import context as guy_ctx  # import-safe lazy loader

    specs = {}
    for p in sorted(Path(specs_dir).glob("*.json")):
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(s, dict) and s.get("slug"):
            specs[s["slug"]] = s
    overrides = {}
    if overrides_path and Path(overrides_path).is_file():
        overrides = json.loads(Path(overrides_path).read_text(encoding="utf-8"))

    guides = []
    for gdir in sorted(Path(repo).iterdir()):
        if not gdir.is_dir() or not (gdir / "index.html").is_file():
            continue
        slug = gdir.name
        if slug.startswith(("mix-", "_", ".")):
            continue  # derived navigation surfaces, not guides
        spec = specs.get(slug)
        ov = overrides.get(slug, {})
        html = (gdir / "index.html").read_text(encoding="utf-8", errors="replace")

        reel = (spec or {}).get("reel_id")
        if not reel:
            m = REEL_IN_SLUG_RE.search(slug)
            reel = m.group(1) if m else None
        source_url = (spec or {}).get("source_url") or (
            f"https://www.instagram.com/reel/{reel}/" if reel else None)

        categories = (spec or {}).get("categories") or []
        equipment = (spec or {}).get("gear") or ov.get("gear") or []

        if spec and spec.get("cards"):
            raw_cards = spec["cards"]
        else:
            raw_cards = parse_html_cards(html)
        cards = []
        body_parts: set = set()
        gear_text = " ".join(equipment)
        for i, c in enumerate(raw_cards, start=1):
            safe = {"name": c.get("name") or "", "tag": c.get("tag") or "",
                    "desc": c.get("desc") or "", "cues": c.get("cues") or []}
            body_parts.update(detect_body_parts(safe, categories, gear_text))
            cards.append({
                "id": card_id(slug, i),
                "position": i,
                "name": c.get("name"),
                "dose": c.get("dose"),
                "tag": c.get("tag"),
                "clip": c.get("clip"),
                "url": f"{slug}/#ex{i}",
                **({"hidden": True} if c.get("hidden") else {}),
            })

        ok = local_files_ok(gdir)
        if not ok:
            status = "draft"
        elif verify_pages_base:
            status = "published" if check_pages(f"{verify_pages_base}/{slug}/") == 200 else "deployment_pending"
        else:
            status = "published" if pages_codes.get(slug) == 200 else "deployment_pending"

        guides.append({
            "id": slug,
            "title": (spec or {}).get("title") or ov.get("title") or slug,
            "author": (spec or {}).get("author"),
            "source_reel_id": reel,
            "source_url": source_url,
            "public_path": f"{slug}/",
            "icloud_path": match_icloud_folder(slug, reel, Path(icloud_root)),
            "status": status,
            "goals": list(categories),
            "body_parts": sorted(body_parts),
            "equipment": list(equipment),
            "locations": derive_locations(categories, equipment, guy_ctx.office_safe),
            "duration_min": (spec or {}).get("duration_min")
            if isinstance((spec or {}).get("duration_min"), (int, float)) else None,
            "intensity": "unknown",
            "best_for": [],
            "avoid_if": [],
            "cards": cards,
        })

    guides.sort(key=lambda g: g["id"])
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "guides": guides,
    }


def dump_catalog(catalog: dict) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"


def derive_generated_at(repo: Path, specs_dir: Path, overrides_path: Path) -> str:
    """Deterministic stamp: UTC date of the newest input file (T00:00:00Z).

    Byte-for-byte rebuilds hold whenever inputs are unchanged, regardless of
    wall-clock time. --generated-at overrides for tests.
    """
    candidates: list[Path] = list(Path(specs_dir).glob("*.json")) if Path(specs_dir).is_dir() else []
    if Path(overrides_path).is_file():
        candidates.append(Path(overrides_path))
    candidates.extend(p / "index.html" for p in Path(repo).iterdir()
                      if p.is_dir() and (p / "index.html").is_file())
    newest = max((p.stat().st_mtime for p in candidates if p.is_file()), default=0)
    day = dt.datetime.fromtimestamp(newest, dt.timezone.utc).date() if newest else dt.datetime.now(dt.timezone.utc).date()
    return f"{day.isoformat()}T00:00:00Z"


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--repo", default="/Users/guy/tmp_work/workout-guides")
    ap.add_argument("--specs", default="/Users/guy/.hermes/profiles/librarian/scripts/guide_pipeline/specs")
    ap.add_argument("--icloud", default="/Users/guy/Library/Mobile Documents/com~apple~CloudDocs/Workout Guides")
    ap.add_argument("--overrides", default=None,
                    help="index-overrides.json (default <repo>/data/index-overrides.json)")
    ap.add_argument("--pages-cache", default=None,
                    help="JSON {slug: last_http_code}; default <repo>/data/pages-statuses.json")
    ap.add_argument("--output", default=None, help="default <repo>/data/guides.json")
    ap.add_argument("--generated-at", default=None,
                    help="fixed ISO stamp for byte-identical rebuilds (default: now UTC)")
    ap.add_argument("--verify-pages", default=None, metavar="BASE_URL",
                    help="live-HEAD every guide route at BASE_URL instead of the cache")
    ap.add_argument("--check-only", action="store_true",
                    help="build, validate, compare to the output file; write nothing")
    ap.add_argument("--metadata-report", default=None, metavar="PATH",
                    help="write the daily-metadata gap report (complete/unknown/invalid)")
    args = ap.parse_args()

    repo = Path(args.repo)
    output = Path(args.output) if args.output else repo / "data" / "guides.json"
    overrides_path = Path(args.overrides) if args.overrides else repo / "data" / "index-overrides.json"
    pages_cache = Path(args.pages_cache) if args.pages_cache else repo / "data" / "pages-statuses.json"
    pages_codes = {}
    if pages_cache.is_file():
        pages_codes = {k: int(v) for k, v in json.loads(pages_cache.read_text()).items()}

    generated_at = args.generated_at or derive_generated_at(repo, args.specs, overrides_path)
    catalog = build_catalog(repo, args.specs, args.icloud, overrides_path, pages_codes,
                            generated_at, verify_pages_base=args.verify_pages)

    errs = validate_catalog(catalog, repo, args.icloud and Path(args.icloud))
    summary = catalog_summary(catalog, repo, Path(args.icloud) if args.icloud else repo)
    meta = validate_daily_metadata(catalog)
    for e in errs:
        print(f"ERROR: {e}", file=sys.stderr)
    for e in meta["invalid_errors"]:
        print(f"METADATA: {e}", file=sys.stderr)

    if args.metadata_report:
        Path(args.metadata_report).write_text(json.dumps({
            "schema_version": 1,
            "generated_at": generated_at,
            "counts": meta["counts"],
            "complete": meta["complete"],
            "unknown": meta["unknown"],
            "invalid": meta["invalid"],
            "invalid_errors": meta["invalid_errors"],
        }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"metadata report: complete={meta['counts']['complete']} "
              f"unknown={meta['counts']['unknown']} invalid={meta['counts']['invalid']} "
              f"-> {args.metadata_report}")

    payload = dump_catalog(catalog)
    if args.check_only:
        current = output.read_text(encoding="utf-8") if output.is_file() else None
        drift = current != payload
        print(f"check-only: guides={summary['guides']} cards={summary['cards']} "
              f"published={summary['published']} pending={summary['deployment_pending']} "
              f"errors={len(errs)} drift={str(drift).lower()}")
        return 1 if (drift or errs) else 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"wrote {output.relative_to(repo) if output.is_relative_to(repo) else output} "
          f"({summary['guides']} guides, {summary['cards']} cards, "
          f"published={summary['published']} pending={summary['deployment_pending']}, "
          f"errors={len(errs)})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
