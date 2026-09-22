#!/usr/bin/env python3
"""context.py — Load Guy's personal workout context (single source of truth).

Reads ~/.hermes/knowledge/health-tracker/guy-workout-context.json and exposes
helpers used by build_mixes.py and build_cards.py:

  - is_knee_sensitive(blob: str) -> bool   # card text mentions knee-irritating keywords
  - office_safe(gear: list) -> bool        # all gear tokens are office-safe
  - context_available() -> bool            # file present & parseable

The JSON twin (guy-workout-context.md) is the human-readable record; this file
is the machine rule source. If the context file is missing, every helper returns
a safe default (no annotations, no knee preference) so generation never breaks.
"""
import json
import os
from pathlib import Path

CONTEXT_PATH = Path(
    os.path.expanduser("~/.hermes/knowledge/health-tracker/guy-workout-context.json")
)

_ctx = None


def _load():
    global _ctx
    if _ctx is None:
        if CONTEXT_PATH.exists():
            try:
                _ctx = json.load(open(CONTEXT_PATH))
            except Exception:
                _ctx = {}
        else:
            _ctx = {}
    return _ctx


def context_available():
    return bool(_load())


def is_knee_sensitive(blob: str):
    """True when the lowercased card text carries a knee-irritating keyword."""
    if not context_available():
        return False
    blob = (blob or "").lower()
    kws = _load().get("knee", {}).get("knee_sensitive_keywords", [])
    return any(k in blob for k in kws)


def knee_safe_guides():
    if not context_available():
        return set()
    return set(_load().get("knee", {}).get("knee_safe_guide_slugs", []))


def office_safe(gear):
    """All gear tokens are office-safe (none/mat/band/wall/chair/box/plate)."""
    if not context_available():
        return False  # unknown -> don't claim safe
    safe = set(_load().get("office", {}).get("office_safe_gears", []))
    g = set(g for g in (gear or []) if g)
    if not g:
        return True  # no gear = bodyweight = office-safe by definition
    return bool(g <= safe)


def needs_gym(gear):
    """Any gear token requires the gym."""
    if not context_available():
        return bool(gear)  # conservative: gear present -> likely gym
    gym = set(_load().get("office", {}).get("needs_gym_gears", []))
    g = set(g for g in (gear or []) if g)
    return bool(g & gym)


def for_guy(guide_slug):
    """True when the guide slug is context-relevant (knee/morning/desk/gait)."""
    if not context_available():
        return False
    c = _load().get("for_guy_guide_slugs", {})
    return any(guide_slug in v for v in c.values())


def context_blob():
    """Debug/verification: return the loaded context dict."""
    return _load()
