#!/usr/bin/env python3
"""build_cards.py — Generate the card-directory page (cards.html) for the workout-guides hub.

Reads every non-draft spec in guide_pipeline/specs/*.json (the canonical source of truth),
extracts each exercise card (name, tag, dose, cues, guide slug, guide title, categories, gear)
and renders a filterable static HTML page with the same UX as the main index:
  - search box (matches card name, tag, dose, cues, guide, category, keyword)
  - category chips (mobility/core/legs/hips/upper/gym/rehab/mastery)
  - body-part chips derived from card tags (hip/knee/foot/ankle/shoulder/core/...)
  - gear chips
Each card links to its parent guide page. Run after any guide is added/published.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path("/Users/guy/tmp_work/workout-guides")
SPECS = Path("/Users/guy/.hermes/profiles/librarian/scripts/guide_pipeline/specs")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import context as guy_ctx  # type: ignore  # noqa: E402

CAT_COLORS = {
    "mobility": "#3b82f6", "core": "#8b5cf6", "legs": "#10b981", "hips": "#ec4899",
    "upper": "#f59e0b", "gym": "#ef4444", "rehab": "#14b8a6", "mastery": "#6366f1",
}
CAT_LABEL = {
    "mobility": "Mobility", "core": "Core", "legs": "Legs & Knees", "hips": "Hips",
    "upper": "Upper Body", "gym": "Gym", "rehab": "Rehab", "mastery": "Mastery",
}
GEAR_LABEL = {
    "none": "No equipment", "mat": "Mat", "band": "Band", "kettlebell": "Kettlebell",
    "dumbbell": "Dumbbells", "cable": "Cable", "bench": "Bench", "box": "Box",
    "bar": "Bar", "barbell": "Barbell", "chair": "Chair", "wall": "Wall",
    "plate": "Plate", "bosu": "Bosu", "machine": "Machine",
}

# Body-part detection from card tag + name + cues (lowercased substring match)
BODY_PARTS = [
    ("hips", ["hip", "glute", "psoas", "pelvic", "90/90", "adductor"]),
    ("knees", ["knee", "quad", "vmo", "hamstring", "patella", "tendon", "leg"]),
    ("feet-ankles", ["foot", "ankle", "arch", "calf", "toe", "heel", "pronat", "supinat", "bunion"]),
    ("shoulders", ["shoulder", "trap", "deltoid", "rotator", "lat", "scapula"]),
    ("core", ["abs", "core", "abdominal", "tva", "oblique", "plank", "crunch", "rectus", "transverse"]),
    ("back", ["back", "spine", "thoracic", "erector", "ql", "lumbar", "multifidus"]),
    ("wrists-hands", ["wrist", "hand", "finger", "carpal", "grip"]),
]
# Canonical ordering for body-part chips
BODY_ORDER = ["hips", "knees", "feet-ankles", "shoulders", "core", "back", "wrists-hands"]
BODY_LABEL = {
    "hips": "Hips", "knees": "Knees", "feet-ankles": "Feet & Ankles",
    "shoulders": "Shoulders", "core": "Core", "back": "Back", "wrists-hands": "Wrists & Hands",
}


def detect_body_parts(card, guide_cats, gear_text):
    """Return list of body-part ids matched from card tag/name/cues/desc."""
    blob = " ".join([
        card.get("name", ""), card.get("tag", ""), card.get("desc", ""),
        " ".join(card.get("cues", [])), " ".join(guide_cats), gear_text,
    ]).lower()
    hits = []
    for bp, keys in BODY_PARTS:
        if any(k in blob for k in keys):
            hits.append(bp)
    # Maps: leg/knee tags to knees; hips mag; foot/ankle
    return hits


def load_cards():
    """Return list of dicts: {slug, guide_title, card_name, tag, dose, ncues, cats, gear, bodies}."""
    rows = []
    for f in sorted(SPECS.glob("*.json")):
        if f.name.startswith("draft-"):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        slug = d.get("slug", f.stem)
        if not (REPO / slug).exists():
            continue  # only published guides
        cats = d.get("categories", [])
        gear = d.get("gear", [])
        gear_text = " ".join(gear)
        guide_title = d.get("title", slug)
        for c in d.get("cards", []):
            bodies = detect_body_parts(c, cats, gear_text)
            rows.append({
                "slug": slug,
                "guide_title": guide_title,
                "card_name": c.get("name", ""),
                "tag": c.get("tag", ""),
                "dose": c.get("dose", ""),
                "cues": c.get("cues", []),
                "cats": cats,
                "gear": gear,
                "bodies": bodies,
            })
    return rows


CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body { font-family: -apple-system, "SF Pro Text", Helvetica, Arial, sans-serif;
         background: #f4f6f8; color: #1c2128; line-height: 1.55; }
  a { color: inherit; text-decoration: none; }
  header { background: #ffffff; border-bottom: 1px solid #e3e7ee; padding: 34px 22px 26px; text-align: center; }
  header .kicker { display: inline-block; background: #eef2f7; color: #4a5b7a; font-size: .72rem;
                     letter-spacing: 2px; text-transform: uppercase; padding: 5px 14px; border-radius: 20px; }
  header h1 { font-size: clamp(1.8rem, 5vw, 2.6rem); letter-spacing: -0.5px; font-weight: 800; margin-top: 12px; }
  header p.sub { color: #5a6472; font-size: .98rem; margin-top: 6px; max-width: 620px; margin-left: auto; margin-right: auto; }
  header .stats { display: inline-flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
  header .stat { background: #f4f6f8; border: 1px solid #e3e7ee; border-radius: 999px; padding: 4px 12px;
                   font-size: .8rem; color: #3b4654; }
  header .stat b { color: #1c2128; font-weight: 700; }
  .navline { max-width: 960px; margin: 0 auto; padding: 14px 22px 0; text-align: center; }
  .navline a { display: inline-block; background: #eef2f7; color: #2563eb; border-radius: 20px;
                padding: 6px 16px; font-size: .85rem; font-weight: 600; margin: 0 4px; }
  .navline a.on { background: #2563eb; color: #fff; }
  .toolbar { position: sticky; top: 0; background: #ffffff; border-bottom: 1px solid #e3e7ee;
                padding: 12px 22px; display: flex; gap: 10px; align-items: center; z-index: 20; }
  .search { flex: 1; min-width: 0; border: 1px solid #d6dce6; background: #ffffff; border-radius: 12px;
              padding: 9px 14px; font-size: .92rem; color: #1c2128; outline: none; }
  .search:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.18); }
  .fbtn { border: 1px solid #d6dce6; background: #ffffff; border-radius: 12px; padding: 9px 14px;
            font-size: .88rem; font-weight: 600; color: #3b4654; cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
  .fbtn .badge { display: none; background: #ef4444; color: #fff; border-radius: 999px; min-width: 20px;
                   height: 20px; font-size: .72rem; line-height: 20px; text-align: center; }
  .fbtn .chev { display: inline-block; width: 0; height: 0; border-left: 5px solid transparent;
                  border-right: 5px solid transparent; border-top: 6px solid #3b4654; margin-left: 2px; }
  .fbtn.open .chev { transform: rotate(180deg); }
  #filters { background: #f7f9fc; border: 1px solid #e3e7ee; border-radius: 14px; margin: 12px 22px 0;
               overflow: hidden; max-height: 0; transition: max-height .25s ease; }
  #filters .inner { padding: 14px 18px; }
  #filters .row-label { font-size: .78rem; color: #6b7480; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .5px; }
  #filters .rows { display: flex; flex-direction: column; gap: 8px; }
  #filters .clear { border: none; background: none; color: #ef4444; font-size: .78rem; cursor: pointer; text-decoration: underline; }
  .chip { display: inline-flex; align-items: center; gap: 5px; border: 1px solid #d6dce6; background: #ffffff;
            border-radius: 999px; padding: 5px 12px; font-size: .82rem; color: #3b4654; cursor: pointer; }
  .chip b { background: #eef2f7; color: #5a6472; border-radius: 999px; font-size: .7rem; padding: 1px 7px; }
  .chip.on { background: #e8f1fd; border-color: #3b82f6; color: #1d4ed8; font-weight: 600; }
  .chip.on b { background: #3b82f6; color: #fff; }
  .chiprow { display: flex; flex-wrap: wrap; gap: 6px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 22px;
            padding: 22px; }
  .card { background: #ffffff; border: 1px solid #e3e7ee; border-radius: 18px; overflow: hidden;
            display: flex; flex-direction: column; transition: transform .15s ease, box-shadow .15s ease; }
  .card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(28,33,40,.12); border-color: #cdd6e2; }
  .card .top { display: flex; align-items: center; gap: 8px; padding: 10px 14px 0; flex-wrap: wrap; }
  .card .bodies { display: flex; flex-wrap: wrap; gap: 5px; padding: 10px 14px 2px; }
  .card .bodychip { background: #dcfce7; color: #166534; border-radius: 8px; font-size: .66rem; padding: 2px 8px; font-weight: 600; }
  .card .ctxflags { display: flex; flex-wrap: wrap; gap: 5px; padding: 4px 14px 0; }
  .card .ctxflags span { display: inline-block; font-size: .64rem; font-weight: 700; padding: 2px 8px; border-radius: 8px; letter-spacing: .3px; }
  .ctx-for-guy { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
  .ctx-knee { background: #ccfbf1; color: #115e59; border: 1px solid #2dd4bf; }
  .ctx-office-safe { background: #dbeafe; color: #1e40af; border: 1px solid #60a5fa; }
  .ctx-needs-gym { background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
  .card h3 { font-size: 1rem; font-weight: 700; letter-spacing: -0.2px; padding: 4px 14px 0; }
  .card .guide { font-size: .72rem; color: #6b7280; padding: 2px 14px 0; }
  .card .meta { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 14px 0; }
  .card .met { display: inline-flex; align-items: center; gap: 4px; background: #f4f6f8; border: 1px solid #e3e7ee;
                 border-radius: 999px; padding: 3px 9px; font-size: .72rem; color: #45505e; }
  .card .dose { font-size: .78rem; color: #d97706; font-weight: 600; padding: 4px 14px 0; }
  .card .cues-preview { font-size: .82rem; color: #5a6472; padding: 6px 14px 0; display: -webkit-box;
                          -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .card .open { margin-top: auto; align-self: flex-end; padding: 8px 14px 10px; font-size: .82rem; font-weight: 600; color: #2563eb;
                  border-top: 1px solid #eef2f7; display: flex; align-items: center; gap: 6px; }
  .card .cat { position: absolute; top: 8px; right: 10px; background: var(--accent); color: #fff;
                 font-size: .68rem; font-weight: 700; padding: 3px 9px; border-radius: 8px; }
  #empty { display: none; text-align: center; padding: 60px 20px; color: #6b7480; }
  #empty b { color: #1c2128; }
  #empty button { border: 1px solid #d6dce6; background: #fff; border-radius: 10px; padding: 8px 16px;
                    margin-top: 12px; cursor: pointer; color: #45505e; }
  footer { text-align: center; color: #9aa3b0; font-size: .78rem; padding: 22px 20px; }
  @media (max-width: 520px) { .grid { grid-template-columns: 1fr; } header { padding: 24px 14px; }
                                .toolbar { padding: 10px 14px; flex-wrap: wrap; } }
"""

JS = """
  const q = document.getElementById('q');
  const ft = document.getElementById('ftoggle');
  const fl = document.getElementById('filters');
  const badge = document.getElementById('fbadge');
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const cards = [...grid.querySelectorAll('.card')];
  let cats = new Set(), bodies = new Set(), gears = new Set();

  function apply() {
    const term = q.value.trim().toLowerCase();
    let shown = 0;
    for (const c of cards) {
      const t = c.dataset.tags.toLowerCase();
      const cat = c.dataset.cat.split(' ');
      const body = c.dataset.body.split(' ');
      const gear = c.dataset.gear.split(' ');
      const okTerm = !term || t.includes(term);
      const okCat = cats.size === 0 || [...cats].every(g => cat.some(w => w === g));
      const okBody = bodies.size === 0 || [...bodies].every(b => body.includes(b));
      const okGear = gears.size === 0 || [...gears].every(g => gear.includes(g));
      const ok = okTerm && okCat && okBody && okGear;
      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    const n = cats.size + bodies.size + gears.size;
    badge.style.display = n ? '' : 'none';
    badge.textContent = n;
    empty.style.display = shown ? 'none' : '';
    grid.style.display = shown ? '' : 'none';
  }

  function toggleFilter(type, val, btn) {
    let set = type === 'c' ? cats : type === 'b' ? bodies : gears;
    if (set.has(val)) { set.delete(val); btn.classList.remove('on'); }
    else { set.add(val); btn.classList.add('on'); }
    apply();
  }

  function clearAll() {
    q.value = '';
    cats = new Set(); bodies = new Set(); gears = new Set();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('on'));
    apply();
  }

  document.querySelectorAll('.chip.cat').forEach(b => b.addEventListener('click', () => toggleFilter('c', b.dataset.g, b)));
  document.querySelectorAll('.chip.body').forEach(b => b.addEventListener('click', () => toggleFilter('b', b.dataset.g, b)));
  document.querySelectorAll('.chip.gear').forEach(b => b.addEventListener('click', () => toggleFilter('e', b.dataset.g, b)));
  document.getElementById('clear').addEventListener('click', clearAll);
  ft.addEventListener('click', () => {
    const open = fl.style.maxHeight !== '0px';
    fl.style.maxHeight = open ? '0px' : fl.scrollHeight + 'px';
    ft.classList.toggle('open');
  });
  q.addEventListener('input', apply);
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="description" content="Card-level directory of every exercise in the workout-guides library — filter by category, body part, and keyword."/>
<title>Exercise Cards — Workout Guides</title>
<style>
__CSS__</style>
</head>
<body>
<header>
  <span class="kicker">Move Better · Recover Faster · Train Smarter</span>
  <h1>Exercise Cards</h1>
  <p class="sub">Every move in the library, one card at a time — filter by category, body part, or keyword.</p>
  <span class="stats">
    <span class="stat"><b>__N__</b> cards</span>
    <span class="stat"><b>__G__</b> guides</span>
  </span>
  <div class="navline">
    <a href="index.html">← Guides</a>
    <a href="cards.html" class="on">Cards</a>
  </div>
</header>

<div class="toolbar">
  <input class="search" id="q" type="text" placeholder="Search cards — e.g. plank, hip, kettlebell, bird dog…" autocomplete="off">
  <button class="fbtn" id="ftoggle">
    <span>Filters</span><span class="badge" id="fbadge">0</span><span class="chev"></span>
  </button>
</div>

<div id="filters" style="max-height:0">
  <div class="inner">
  <div class="rows">
    <div>
      <span class="row-label">Category</span>
      <div class="chiprow">__CAT_CHIPS__</div>
    </div>
    <div>
      <span class="row-label">Body Part</span>
      <div class="chiprow">__BODY_CHIPS__</div>
    </div>
    <div>
      <span class="row-label">Gear</span>
      <div class="chiprow">__GEAR_CHIPS__</div>
    </div>
    <div style="text-align:right"><button class="clear" id="clear">Clear all filters</button></div>
  </div>
  </div>
</div>

<main class="grid" id="grid">
__CARDS__</main>
<div class="empty" id="empty">
  <b>No cards match.</b>
  <div>Try a different search or clear the filters.</div>
  <button onclick="clearAll()">Clear filters</button>
</div>

<footer>Card directory · compiled by ATHENA · every card links to its parent guide</footer>

<script>
__JS__</script>
</body>
</html>
"""


def render_card(c, i):
    cat0 = c["cats"][0] if c["cats"] else "mobility"
    color = CAT_COLORS.get(cat0, "#3b82f6")
    label = CAT_LABEL.get(cat0, cat0.title())
    gear = " ".join(c["gear"])
    bodies = " ".join(c["bodies"])
    cat_tags = "".join(f'<span class="met">{CAT_LABEL.get(x, x.title())}</span>' for x in c["cats"])
    gear_tags = "".join(f'<span class="met">{GEAR_LABEL.get(x, x)}</span>' for x in c["gear"])
    body_chips = "".join(f'<span class="bodychip">{BODY_LABEL[x]}</span>' for x in c["bodies"])
    # personal-context flags (guy_ctx)
    ifg = guy_ctx.for_guy(c["slug"])
    blob = " ".join([c["card_name"], c["tag"], " ".join(c["cues"]), " ".join(c["cats"]), gear]).lower()
    knee = guy_ctx.is_knee_sensitive(blob) or c["slug"] in guy_ctx.knee_safe_guides()
    if guy_ctx.office_safe(c["gear"]):
        loc = "office-safe"
    elif guy_ctx.needs_gym(c["gear"]):
        loc = "needs-gym"
    else:
        loc = ""
    parts = []
    if ifg:
        parts.append('<span class="ctx-for-guy">★ For Guy</span>')
    if knee:
        parts.append('<span class="ctx-knee">knee-aware</span>')
    if loc:
        parts.append(f'<span class="ctx-{loc}">{loc.replace("-", " ").title()}</span>')
    ctx_html = f'<div class="ctxflags">{"".join(parts)}</div>' if parts else ""
    tag = f'<span class="met">{c["tag"]}</span>' if c["tag"] else ""
    dose = f'<div class="dose">⚡ {c["dose"]}</div>' if c["dose"] else ""
    cues_preview = " ".join(c["cues"][:2])
    search_blob = " ".join([c["card_name"], c["tag"], c["dose"], c["guide_title"],
                            " ".join(c["cats"]), " ".join(c["gear"]), " ".join(c["cues"])]).lower()
    return f'''  <a class="card" href="{c["slug"]}/" data-cat="{" ".join(c["cats"])}" data-body="{bodies}" data-gear="{gear}" data-tags="{search_blob}" data-idx="{i}">
    <div style="position:relative">
      <div class="top"><span class="met" style="background:#eef2f7;color:#4a5b7a">#{i:03d}</span><span class="cat" style="--accent:{color};position:static;margin-left:auto">{label}</span></div>
      <h3>{c["card_name"]}</h3>
      <div class="guide">in <b>{c["guide_title"]}</b></div>
      {ctx_html}
      <div class="bodies">{body_chips}</div>
      <div class="meta">{cat_tags}{gear_tags}{tag}</div>
      {dose}
      <div class="cues-preview">{cues_preview}</div>
    </div>
    <span class="open">Open guide <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12,5 19,12 12,19"/></svg></span>
  </a>
'''


def main():
    rows = load_cards()
    cards_html = "".join(render_card(r, i + 1) for i, r in enumerate(rows))

    from collections import Counter
    cat_counts = Counter()
    body_counts = Counter()
    gear_counts = Counter()
    for r in rows:
        for c in r["cats"]:
            cat_counts[CAT_LABEL.get(c, c.title())] += 1
        for b in r["bodies"]:
            body_counts[BODY_LABEL[b]] += 1
        for g in r["gear"]:
            gear_counts[g] += 1

    cat_chips = "".join(
        f'<button class="chip cat" data-g="{c}">{CAT_LABEL.get(c, c.title())} <b>{cat_counts[CAT_LABEL.get(c, c.title())]}</b></button>'
        for c in CAT_LABEL if cat_counts.get(CAT_LABEL[c]))
    body_chips = "".join(
        f'<button class="chip body" data-g="{b}">{BODY_LABEL[b]} <b>{body_counts[BODY_LABEL[b]]}</b></button>'
        for b in BODY_ORDER if body_counts.get(BODY_LABEL[b]))
    gear_chips = "".join(
        f'<button class="chip gear" data-g="{g}">{GEAR_LABEL.get(g, g)} <b>{gear_counts[g]}</b></button>'
        for g in GEAR_LABEL if gear_counts.get(g))

    guides = len({r["slug"] for r in rows})
    html = (TEMPLATE
            .replace("__CSS__", CSS)
            .replace("__JS__", JS)
            .replace("__CARDS__", cards_html)
            .replace("__CAT_CHIPS__", cat_chips)
            .replace("__BODY_CHIPS__", body_chips)
            .replace("__GEAR_CHIPS__", gear_chips)
            .replace("__N__", str(len(rows)))
            .replace("__G__", str(guides)))
    (REPO / "cards.html").write_text(html, encoding="utf-8")
    print(f"wrote cards.html ({len(html):,} chars, {len(rows)} cards, {guides} guides)")


if __name__ == "__main__":
    main()
