"""Canonical workout-guide catalog: load, validate, summarize.

data/guides.json is the navigation manifest (card t_749084c1). This module is
pure: it reads nothing from disk except through load_catalog() and never writes.
Validation is deterministic — same catalog, same error list.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ALLOWED_STATUSES = ("draft", "published", "deployment_pending", "blocked")

_CARD_ID_RE = re.compile(r"^.+#\d{2}$")


class CatalogError(Exception):
    """Raised when a catalog file cannot be loaded at all."""


def card_id(guide_id: str, position: int) -> str:
    """Stable card id: <guide-id>#<two-digit position>."""
    return f"{guide_id}#{position:02d}"


def load_catalog(path: Path) -> dict:
    """Load and shape-check the catalog JSON. Raises CatalogError on garbage."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"cannot read catalog {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CatalogError("catalog root must be an object")
    if not isinstance(data.get("schema_version"), int):
        raise CatalogError("catalog missing integer schema_version")
    if not isinstance(data.get("guides"), list):
        raise CatalogError("catalog missing guides list")
    return data


def _guide_errors(g: dict, repo_root: Path, icloud_root: Path, seen_guides: dict,
                  seen_cards: dict) -> list[str]:
    errs: list[str] = []
    gid = g.get("id")
    if not gid or not isinstance(gid, str):
        return [f"guide with missing id: {g!r}"[:120]]
    if gid in seen_guides:
        errs.append(f"duplicate guide id: {gid}")
    seen_guides[gid] = True

    status = g.get("status")
    if status not in ALLOWED_STATUSES:
        errs.append(f"guide {gid}: invalid status {status!r}")

    duration = g.get("duration_min")
    if duration is not None and (not isinstance(duration, (int, float))
                                 or isinstance(duration, bool) or duration < 0):
        errs.append(f"guide {gid}: duration_min must be null or non-negative number, got {duration!r}")

    public_path = g.get("public_path")
    if status == "published":
        if not public_path:
            errs.append(f"guide {gid}: published but public_path missing")
        else:
            index = repo_root / public_path / "index.html"
            if not index.is_file():
                errs.append(f"guide {gid}: published public_path {public_path} has no index.html")

    icloud_path = g.get("icloud_path")
    if icloud_path is not None and not (icloud_root / icloud_path / "index.html").is_file():
        # Reported as missing mirror in catalog_summary, not a hard error.
        pass

    cards = g.get("cards", [])
    if not isinstance(cards, list):
        errs.append(f"guide {gid}: cards must be a list")
        return errs
    for c in cards:
        if not isinstance(c, dict):
            errs.append(f"guide {gid}: card entry is not an object")
            continue
        cid = c.get("id")
        pos = c.get("position")
        expected = card_id(gid, pos) if isinstance(pos, int) else None
        if cid in seen_cards:
            errs.append(f"duplicate card id: {cid}")
        seen_cards[cid] = True
        if not cid or not isinstance(cid, str) or not _CARD_ID_RE.match(cid):
            errs.append(f"guide {gid}: card id {cid!r} does not match <guide-id>#NN")
        elif expected is not None and cid != expected:
            errs.append(f"guide {gid}: card id {cid} does not match position {pos}")
    return errs


def validate_catalog(catalog: dict, repo_root: Path, icloud_root: Path) -> list[str]:
    """Return a deterministic list of error strings; empty means valid."""
    errs: list[str] = []
    seen_guides: dict = {}
    seen_cards: dict = {}
    for g in catalog.get("guides", []):
        if not isinstance(g, dict):
            errs.append(f"guide entry is not an object: {g!r}"[:120])
            continue
        errs.extend(_guide_errors(g, Path(repo_root), Path(icloud_root), seen_guides, seen_cards))
    return errs


def _mirror_missing(g: dict, icloud_root: Path) -> bool:
    icloud_path = g.get("icloud_path")
    if not icloud_path:
        return True
    return not (icloud_root / icloud_path / "index.html").is_file()


def catalog_summary(catalog: dict, repo_root: Path, icloud_root: Path) -> dict:
    """Counts for guides, cards, and missing iCloud mirrors."""
    guides = [g for g in catalog.get("guides", []) if isinstance(g, dict)]
    missing = [g["id"] for g in guides if _mirror_missing(g, Path(icloud_root))]
    return {
        "guides": len(guides),
        "cards": sum(len(g.get("cards", [])) for g in guides),
        "missing_mirrors": len(missing),
        "missing_mirror_ids": missing,
        "published": sum(1 for g in guides if g.get("status") == "published"),
        "deployment_pending": sum(1 for g in guides if g.get("status") == "deployment_pending"),
    }
