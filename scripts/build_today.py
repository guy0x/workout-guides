#!/usr/bin/env python3
"""build_today.py — generate today.html, the constraint-first daily page.

Deterministic preset selection over data/guides.json:
  strict pool  = published guides with cards that satisfy every resolved
                 preset constraint (duration_max, goals, locations, intensity,
                 best_for). Unresolved guide fields (unknown/empty) are
                 wildcards, not vetoes.
  relaxed fill = when the strict pool is short, constraints are dropped in a
                 fixed order (best_for -> intensity -> locations -> duration_max,
                 goals last) and matches are flagged "flexible" on the page.

Same inputs + same --date => byte-identical HTML. Completion checkmarks are
device-local via localStorage (no backend in this phase).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

GUIDE_LIMIT = 3
CARDS_PER_GUIDE = 3
# duration_max is a hard time budget: never relaxed. Soft match constraints
# relax in this fixed order when the strict pool is shorter than the limit.
_RELAX_ORDER = ("best_for", "intensity", "locations", "goals")


def no_equipment_ok(g: dict) -> bool:
    eq = g.get("equipment") or []
    return all(x == "none" for x in eq)


def _matches(g: dict, preset: dict, active: set) -> bool:
    """Wildcard-tolerant constraint check for the constraints in `active`."""
    if "duration_max" in active:
        d = g.get("duration_min")
        if d is not None and d > preset["duration_max"]:
            return False
        if d is None:
            return False  # strict duration matching requires a duration
    if "goals" in active:
        if not set(g.get("goals") or []) & set(preset.get("goals") or []):
            return False
    if "locations" in active:
        locs = g.get("locations") or []
        if locs and not set(locs) & set(preset.get("locations") or []):
            return False
    if "intensity" in active:
        it = g.get("intensity") or "unknown"
        if it != "unknown" and it not in (preset.get("intensity") or []):
            return False
    if "best_for" in active:
        bf = g.get("best_for") or []
        if bf and not set(bf) & set(preset.get("best_for") or []):
            return False
    return True


def _sort_key(g: dict):
    d = g.get("duration_min")
    return (1 if d is None else 0, d if d is not None else 0, g["id"])


def select_session(catalog: dict, preset: dict,
                   guide_limit: int = GUIDE_LIMIT,
                   cards_per_guide: int = CARDS_PER_GUIDE,
                   exclude_ids: set | None = None) -> dict:
    """Return {guides: [...picked_cards...], flexible: bool, dropped: [...]}.

    exclude_ids: guides already used by an earlier preset in the same build —
    skipped while enough fresh candidates remain, so the day's presets differ.
    """
    exclude_ids = exclude_ids or set()
    pool = [g for g in catalog.get("guides", [])
            if g.get("status") == "published" and g.get("cards")
            and g["id"] not in exclude_ids]
    all_constraints = {k for k in ("duration_max", "goals", "locations",
                                   "intensity", "best_for") if preset.get(k)}
    active = set(all_constraints)
    relaxable = active - {"duration_max"}
    dropped: list[str] = []
    picked: list[dict] = []
    while True:
        picked = sorted((g for g in pool if _matches(g, preset, active)), key=_sort_key)
        if len(picked) >= guide_limit or not relaxable:
            break
        for key in _RELAX_ORDER:
            if key in relaxable:
                relaxable.discard(key)
                active.discard(key)
                dropped.append(key)
                break
    picked = picked[:guide_limit]
    # diversity: if exclusion starved this preset below the limit, refill from
    # the full pool (deterministic; shared guides are better than empty slots)
    if len(picked) < guide_limit:
        refill = sorted((g for g in catalog.get("guides", [])
                         if g.get("status") == "published" and g.get("cards")
                         and _matches(g, preset, active)),
                        key=_sort_key)
        seen = {g["id"] for g in picked}
        for g in refill:
            if g["id"] not in seen:
                picked.append(g)
                seen.add(g["id"])
            if len(picked) >= guide_limit:
                break
    for g in picked:
        cards = [c for c in g["cards"] if not c.get("hidden")][:cards_per_guide]
        g["picked_cards"] = cards
    return {"guides": picked, "flexible": bool(dropped), "dropped": dropped}


def _session_stats(session: dict) -> dict:
    guides = session["guides"]
    durations = [g.get("duration_min") for g in guides]
    total = sum(d for d in durations if isinstance(d, (int, float)))
    equipment = sorted({e for g in guides for e in (g.get("equipment") or [])}) or ["none"]
    locations = sorted({l for g in guides for l in (g.get("locations") or [])}) or ["unspecified"]
    intensities = sorted({i for g in guides for i in [(g.get("intensity") or "unknown")]
                          if i != "unknown"}) or ["unspecified"]
    return {"total_min": int(total) if total else None,
            "equipment": equipment, "locations": locations, "intensities": intensities}


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Today — Workout Guides</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "SF Pro Text", Helvetica, Arial, sans-serif; background: #f4f6f8; color: #1c2128; line-height: 1.55; }
  header { background: #fff; border-bottom: 1px solid #e3e7ee; padding: 26px 20px 20px; text-align: center; }
  header h1 { font-size: 2rem; font-weight: 800; }
  header .date { color: #5a6472; margin-top: 4px; }
  header .back { display:inline-block; margin-top:12px; color:#2563eb; font-weight:600; margin-right: 14px; }
  .presets { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; padding: 18px 16px 4px; }
  .presets button { border: 1px solid #e3e7ee; background:#fff; border-radius: 999px; padding: 9px 16px; font-size: .95rem; font-weight: 600; cursor: pointer; color:#1c2128; }
  .presets button.active { background:#1c2128; color:#fff; border-color:#1c2128; }
  .session { max-width: 720px; margin: 0 auto; padding: 18px 16px 60px; }
  .session h2 { font-size: 1.25rem; margin: 8px 0 2px; }
  .badge { display:inline-block; background:#fef3c7; color:#92400e; border-radius: 999px; font-size: .72rem; padding: 2px 10px; margin-left: 6px; vertical-align: middle; }
  .meta { color: #5a6472; font-size: .9rem; margin-bottom: 14px; }
  .card { background:#fff; border:1px solid #e3e7ee; border-radius:14px; padding:14px 16px; margin-bottom:10px; display:flex; gap:12px; align-items:flex-start; }
  .card input[type=checkbox] { width: 20px; height: 20px; margin-top: 2px; }
  .card a { color:#2563eb; font-weight:600; text-decoration:none; }
  .card .dose { color:#5a6472; font-size:.85rem; }
  .card .from { color:#8a93a1; font-size:.78rem; }
  .done-true .card-title { text-decoration: line-through; color:#8a93a1; }
  .toolbar { display:flex; gap:10px; align-items:center; margin: 16px 0 4px; }
  .toolbar button { border:1px solid #e3e7ee; background:#fff; border-radius:10px; padding:8px 14px; font-weight:600; cursor:pointer; }
  .note { color:#8a93a1; font-size:.8rem; margin-top: 14px; }
  .empty { background:#fff; border:1px dashed #e3e7ee; border-radius:14px; padding:18px; color:#5a6472; }
</style>
</head>
<body>
<header>
  <h1>Today</h1>
  <div class="date">__DATE_LABEL__</div>
  <div>
    <a class="back" href="index.html">&larr; All guides</a>
    <a class="back" href="cards.html">Exercise cards</a>
  </div>
</header>
<div class="presets" id="presets">__PRESET_BUTTONS__</div>
<div class="session" id="session"></div>
<script>
var DATE = "__DATE__";
var SESSIONS = __SESSIONS_JSON__;
function doneKey(cid) { return "wg.done." + DATE + "." + cid; }
function pick(pid) {
  var s = SESSIONS[pid];
  document.querySelectorAll(".presets button").forEach(function (b) {
    b.classList.toggle("active", b.dataset.preset === pid);
  });
  var el = document.getElementById("session");
  if (!s || !s.guides.length) { el.innerHTML = '<div class="empty">No guides matched this preset yet.</div>'; return; }
  var h = "<h2>" + s.label + (s.flexible ? '<span class="badge">flexible match</span>' : '') + "</h2>";
  h += '<div class="meta">' + (s.total_min ? "~" + s.total_min + " min total &middot; " : "") +
       "equipment: " + s.equipment.join(", ") + " &middot; location: " + s.locations.join(", ") +
       " &middot; intensity: " + s.intensities.join(", ") + "</div>";
  var n = 0;
  s.guides.forEach(function (g) {
    g.cards.forEach(function (c) {
      n++;
      h += '<label class="card" id="row-' + n + '">' +
           '<input type="checkbox" data-cid="' + c.id + '"/>' +
           '<span><a href="' + c.url + '">' + (c.name || "Move") + '</a>' +
           (c.dose ? '<div class="dose">' + c.dose + '</div>' : '') +
           '<div class="from">from ' + g.title + '</div></span></label>';
    });
  });
  h += '<div class="toolbar"><button id="reset">Reset today</button></div>';
  h += '<div class="note">Checkmarks are stored device-local (localStorage) for ' + DATE + ' — no account, no sync. Links open the guide at the exact drill.</div>';
  el.innerHTML = h;
  el.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
    cb.checked = localStorage.getItem(doneKey(cb.dataset.cid)) === "1";
    cb.addEventListener("change", function () {
      if (cb.checked) { localStorage.setItem(doneKey(cb.dataset.cid), "1"); }
      else { localStorage.removeItem(doneKey(cb.dataset.cid)); }
      cb.closest(".card").classList.toggle("done-true", cb.checked);
    });
    cb.closest(".card").classList.toggle("done-true", cb.checked);
  });
  document.getElementById("reset").addEventListener("click", function () {
    el.querySelectorAll("input[type=checkbox]").forEach(function (cb) {
      localStorage.removeItem(doneKey(cb.dataset.cid));
      cb.checked = false;
      cb.closest(".card").classList.remove("done-true");
    });
  });
}
(function init() {
  var ids = Object.keys(SESSIONS);
  var pre = ids[0];
  document.querySelectorAll(".presets button").forEach(function (b) {
    b.addEventListener("click", function () { pick(b.dataset.preset); });
  });
  pick(pre);
})();
</script>
</body>
</html>
"""


def build_html(catalog: dict, presets: dict, date: str) -> str:
    sessions = {}
    used: set = set()
    for preset in presets.get("presets", []):
        sel = select_session(catalog, preset, exclude_ids=used)
        used.update(g["id"] for g in sel["guides"])
        stats = _session_stats(sel)
        sessions[preset["id"]] = {
            "label": preset.get("label", preset["id"]),
            "flexible": sel["flexible"],
            "total_min": stats["total_min"],
            "equipment": stats["equipment"],
            "locations": stats["locations"],
            "intensities": stats["intensities"],
            "guides": [
                {"title": g.get("title", g["id"]),
                 "cards": [{"id": c["id"], "name": c.get("name"),
                            "dose": c.get("dose"), "url": c.get("url")}
                           for c in g["picked_cards"]]}
                for g in sel["guides"]
            ],
        }
    buttons = "\n".join(
        f'<button data-preset="{p["id"]}" type="button">{p.get("label", p["id"])}</button>'
        for p in presets.get("presets", []))
    day = dt.date.fromisoformat(date)
    label = day.strftime("%A, %d %B %Y")
    html = (TEMPLATE
            .replace("__DATE_LABEL__", label)
            .replace("__PRESET_BUTTONS__", buttons)
            .replace("__DATE__", date)
            .replace("__SESSIONS_JSON__", json.dumps(sessions, ensure_ascii=False)))
    return html


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--catalog", default="data/guides.json")
    ap.add_argument("--presets", default="data/today.json")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (deterministic key)")
    ap.add_argument("--output", default="today.html")
    ap.add_argument("--dry-run", action="store_true", help="print summary; write nothing")
    args = ap.parse_args()

    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    presets = json.loads(Path(args.presets).read_text(encoding="utf-8"))
    html = build_html(catalog, presets, args.date)
    sessions = json.loads(_extract_sessions(html))
    n_moves = sum(len(s["guides"]) for s in sessions.values())
    if args.dry_run:
        print(f"today dry-run: date={args.date} presets={len(sessions)} "
              f"sessions_moves={n_moves} (wrote nothing)")
        return 0
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"wrote {args.output} (date={args.date}, presets={len(sessions)}, "
          f"moves={n_moves})")
    return 0


def _extract_sessions(html: str) -> str:
    marker = "var SESSIONS = "
    i = html.index(marker) + len(marker)
    j = html.index(";\n", i)
    return html[i:j]


if __name__ == "__main__":
    sys.exit(main())
