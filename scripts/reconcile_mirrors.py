#!/usr/bin/env python3
"""reconcile_mirrors.py — additive iCloud mirror reconciliation (report-first).

Classifies each catalog guide's iCloud mirror as unchanged / missing / drifted.
Default mode is a dry-run that writes nothing outside the --report file.
--apply requires exactly one --id and only ever creates or updates that guide's
mirror folder from the hub repo. It NEVER deletes mirror files — bulk repair is
a separate, Guy-approved task.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

IMAGE_RE = None  # comparison is whole-directory, no pattern needed


def classify_guide(gdir: Path, mirror: Path) -> str:
    """unchanged | missing | drifted — comparing every hub file against the mirror."""
    if not gdir.is_dir():
        return "missing"  # nothing to protect: no hub source either
    if not mirror.is_dir() or not any(mirror.rglob("*")):
        return "missing"
    for f in sorted(gdir.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(gdir)
        target = mirror / rel
        if not target.is_file() or target.read_bytes() != f.read_bytes():
            return "drifted"
    return "unchanged"


def apply_one(gdir: Path, mirror: Path) -> list[str]:
    """Copy hub files into the mirror folder. Create-if-missing, update-if-drifted,
    never delete. Returns list of copied relative paths."""
    copied = []
    mirror.mkdir(parents=True, exist_ok=True)
    for f in sorted(gdir.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(gdir)
        target = mirror / rel
        if not target.is_file() or target.read_bytes() != f.read_bytes():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            copied.append(str(rel))
    return copied


def reconcile(catalog: dict, repo: Path, icloud: Path) -> dict:
    result = {"unchanged": [], "missing": [], "drifted": []}
    for g in catalog.get("guides", []):
        slug = g.get("id")
        gdir = Path(repo) / slug
        icloud_path = g.get("icloud_path")
        mirror = (Path(icloud) / icloud_path.rstrip("/")) if icloud_path else None
        if mirror is None:
            status = "missing"
        else:
            status = classify_guide(gdir, mirror)
        result[status].append(slug)
    for key in result:
        result[key].sort()
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--icloud", required=True)
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="default: classify only, write nothing but the report")
    ap.add_argument("--apply", action="store_true",
                    help="mirror exactly one --id from the hub into iCloud (additive)")
    ap.add_argument("--id", action="append", default=[], metavar="GUIDE_ID")
    ap.add_argument("--report", default=None, help="write the classification report here")
    args = ap.parse_args()

    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    repo, icloud = Path(args.repo), Path(args.icloud)

    if args.apply:
        if len(args.id) != 1:
            print("REFUSED: --apply requires exactly one --id (bulk repair is a "
                  "separate, explicitly approved task)", file=sys.stderr)
            return 2
        slug = args.id[0]
        g = next((g for g in catalog["guides"] if g["id"] == slug), None)
        if g is None:
            print(f"REFUSED: {slug} is not in the catalog", file=sys.stderr)
            return 2
        gdir = repo / slug
        if not (gdir / "index.html").is_file():
            print(f"REFUSED: hub guide {slug} has no index.html", file=sys.stderr)
            return 2
        icloud_path = g.get("icloud_path") or f"{slug}/"
        mirror = icloud / icloud_path.rstrip("/")
        copied = apply_one(gdir, mirror)
        print(f"applied {slug}: {len(copied)} file(s) written to {icloud_path} "
              f"(nothing deleted)")
        if args.report:
            Path(args.report).write_text(json.dumps(
                {"applied": slug, "copied": copied}, indent=2) + "\n", encoding="utf-8")
        return 0

    result = reconcile(catalog, repo, icloud)
    counts = {k: len(v) for k, v in result.items()}
    print("mirror reconciliation (dry-run): "
          + " ".join(f"{k}={n}" for k, n in counts.items()))
    if args.report:
        payload = {
            "schema_version": 1,
            "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "counts": counts,
            **result,
        }
        Path(args.report).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
        print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
