#!/usr/bin/env python3
"""Build a brighter, no-gradient workout-guides index with hideable filters + thumbnails.

Reads data/index-overrides.json (card metadata) + thumbs/<slug>.jpg (thumbnails).
Writes index.html. Idempotent — run this whenever a guide is added.
"""
import json
from pathlib import Path

REPO = Path("/Users/guy/tmp_work/workout-guides")
OV = json.load(open(REPO / "data" / "index-overrides.json"))
THUMBS = REPO / "thumbs"

CAT_COLORS = {
    "mobility": "#3b82f6", "core": "#8b5cf6", "legs": "#10b981", "hips": "#ec4899",
    "upper": "#f59e0b", "gym": "#ef4444", "rehab": "#14b8a6", "mastery": "#6366f1",
}
CAT_LABEL = {
    "mobility": "Mobility", "core": "Core", "legs": "Legs & Knees", "hips": "Hips",
    "upper": "Upper Body", "gym": "Gym", "rehab": "Rehab", "mastery": "Mastery",
}


def render_card(slug, cfg, idx):
    cat0 = cfg["cat"].split()[0]
    color = CAT_COLORS.get(cat0, "#3b82f6")
    label = CAT_LABEL.get(cat0, cat0.title())
    seen, uniq = set(), []
    for t in cfg["tags"]:
        t = t.strip()
        if t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    tags = "".join(f'<span class="tag">{t}</span>' for t in uniq)
    metas = "".join(f'<span class="met">{m}</span>' for m in cfg["meta"])
    gear = " ".join(cfg["gear"])
    title = cfg["title"]
    thumb = THUMBS / f"{slug}.jpg"
    img = f'<img src="thumbs/{slug}.jpg" alt="{title}" loading="lazy">' if thumb.exists() else ""
    if not img:
        img = f'<div class="thumb-ph"><span>{title[:2]}</span></div>'
    data_tags = f'{cfg["search"]} {title} {title}'
    return f'''  <a class="card" href="{slug}/" data-cat="{cfg["cat"]}" data-gear="{gear}" data-tags="{data_tags}">
    <div class="thumb" style="--accent:{color}">{img}<span class="num">{idx:02d}</span><span class="cat">{label}</span></div>
    <div class="tags">{tags}</div>
    <h2>{title}</h2>
    <p class="desc">{cfg["desc"]}</p>
    <div class="meta">{metas}</div>
    <span class="open">Open guide <svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12,5 19,12 12,19"/></svg></span>
  </a>
'''


slugs = sorted(OV)
cards = "".join(render_card(s, OV[s], i + 1) for i, s in enumerate(slugs))

from collections import Counter
goal_counts = Counter()
gear_counts = Counter()
for s in slugs:
    for w in OV[s]["cat"].split():
        goal_counts[CAT_LABEL.get(w, w.title())] += 1
    for g in OV[s]["gear"]:
        gear_counts[g] += 1

GOAL_ORDER = ["Mobility", "Core", "Legs & Knees", "Hips", "Upper Body", "Gym", "Rehab", "Mastery"]


def goal_chips():
    return "".join(
        f'<button class="chip goal" data-g="{g.lower()}">{g} <b>{goal_counts[g]}</b></button>'
        for g in GOAL_ORDER if g in goal_counts)


GEAR_LABEL = {"none": "No equipment", "mat": "Mat", "band": "Band", "kettlebell": "Kettlebell",
              "dumbbell": "Dumbbells", "cable": "Cable", "bench": "Bench", "box": "Box"}
GEAR_ORDER = ["none", "mat", "band", "kettlebell", "dumbbell", "cable", "bench", "box"]


def gear_chips():
    return "".join(
        f'<button class="chip gear" data-g="{g}">{GEAR_LABEL[g]} <b>{gear_counts[g]}</b></button>'
        for g in GEAR_ORDER if g in gear_counts)


N = len(slugs)
N_NOEQ = sum(1 for s in slugs if "none" in OV[s]["gear"])
N_DEMO = len(list(THUMBS.glob("*.jpg")))

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
  .card .thumb { position: relative; aspect-ratio: 16/9; background: #e8ecf2; }
  .card .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .card .thumb .num { position: absolute; top: 8px; left: 10px; background: rgba(20,24,30,.72); color: #fff;
                        font-size: .72rem; font-weight: 700; padding: 2px 8px; border-radius: 8px; }
  .card .thumb .cat { position: absolute; bottom: 8px; right: 10px; background: var(--accent); color: #fff;
                        font-size: .68rem; font-weight: 700; padding: 3px 9px; border-radius: 8px; }
  .card .thumb-ph { aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; background: var(--accent); }
  .card .thumb-ph span { color: #fff; font-size: 2rem; font-weight: 800; }
  .card .tags { display: flex; flex-wrap: wrap; gap: 5px; padding: 10px 14px 2px; }
  .card .tag { background: #eef2f7; color: #4a5b7a; border-radius: 8px; font-size: .66rem; padding: 2px 8px; }
  .card h2 { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.2px; padding: 4px 14px 0; }
  .card .desc { font-size: .86rem; color: #5a6472; padding: 6px 14px 0; display: -webkit-box;
                  -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
  .card .meta { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 14px 0; }
  .card .met { display: inline-flex; align-items: center; gap: 4px; background: #f4f6f8; border: 1px solid #e3e7ee;
                 border-radius: 999px; padding: 3px 9px; font-size: .72rem; color: #45505e; }
  .card .met svg { width: 13px; height: 13px; stroke: currentColor; fill: none; }
  .open { margin-top: auto; align-self: flex-end; padding: 8px 14px 10px; font-size: .82rem; font-weight: 600; color: #2563eb;
            border-top: 1px solid #eef2f7; display: flex; align-items: center; gap: 6px; }
  .open svg { width: 15px; height: 15px; stroke: currentColor; fill: none; }

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
  let goals = new Set(), gears = new Set();

  function apply() {
    const term = q.value.trim().toLowerCase();
    let shown = 0;
    for (const c of cards) {
      const t = c.dataset.tags.toLowerCase();
      const cat = c.dataset.cat.split(' ');
      const gear = c.dataset.gear.split(' ');
      const okTerm = !term || t.includes(term);
      const okGoal = goals.size === 0 || [...goals].every(g => cat.some(w => w === g));
      const okGear = gears.size === 0 || [...gears].every(g => gear.includes(g));
      const ok = okTerm && okGoal && okGear;
      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    }
    const n = goals.size + gears.size;
    badge.style.display = n ? '' : 'none';
    badge.textContent = n;
    empty.style.display = shown ? 'none' : '';
    grid.style.display = shown ? '' : 'none';
  }

  function toggleFilter(type, val, btn) {
    const set = type === 'g' ? goals : gears;
    if (set.has(val)) { set.delete(val); btn.classList.remove('on'); }
    else { set.add(val); btn.classList.add('on'); }
    apply();
  }

  function clearAll() {
    q.value = ''; goals = new Set(); gears = new Set();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('on'));
    apply();
  }

  document.querySelectorAll('.chip.goal').forEach(b => b.addEventListener('click', () => toggleFilter('g', b.dataset.g, b)));
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
<meta name="description" content="Workout guides: mobility flows, core circuits, gym sessions, rehab protocols — offline-capable, GIF-inline."/>
<title>Workout Guides — Library</title>
<style>
__CSS__</style>
</head>
<body>

<header>
  <span class="kicker">Move Better · Recover Faster · Train Smarter</span>
  <h1>Workout Guides</h1>
  <p class="sub">Self-contained training guides — every move with an inline GIF demo. Pick a focus or just start scrolling.</p>
  <span class="stats">
    <span class="stat"><b>__N__</b> guides</span>
    <span class="stat"><b>__N_NOEQ__</b> no-equipment</span>
    <span class="stat"><b>__N_DEMO__</b> thumbnails</span>
  </span>
</header>

<div class="toolbar">
  <input class="search" id="q" type="text" placeholder="Search — e.g. mobility, hips, kettlebell…" autocomplete="off">
  <button class="fbtn" id="ftoggle">
    <span>Filters</span><span class="badge" id="fbadge">0</span><span class="chev"></span>
  </button>
</div>

<div id="filters" style="max-height:0">
  <div class="inner">
  <div class="rows">
    <div>
      <span class="row-label">Focus</span>
      <div class="chiprow" id="goals">__GOAL_CHIPS__</div>
    </div>
    <div>
      <span class="row-label">Gear</span>
      <div class="chiprow" id="gear">__GEAR_CHIPS__</div>
    </div>
    <div style="text-align:right"><button class="clear" id="clear">Clear all filters</button></div>
  </div>
  </div>
</div>

<main class="grid" id="grid">
__CARDS__</main>
<div class="empty" id="empty">
  <b>No guides match.</b>
  <div>Try a different search or clear the filters.</div>
  <button onclick="clearAll()">Clear filters</button>
</div>

<footer>Workout guides library · compiled by ATHENA · each guide is a single offline HTML file</footer>

<script>
__JS__</script>
</body>
</html>
"""

html = (TEMPLATE
        .replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__CARDS__", cards)
        .replace("__GOAL_CHIPS__", goal_chips())
        .replace("__GEAR_CHIPS__", gear_chips())
        .replace("__N__", str(N))
        .replace("__N_NOEQ__", str(N_NOEQ))
        .replace("__N_DEMO__", str(N_DEMO)))

(out := REPO / "index.html").write_text(html)
print(f"wrote index.html ({len(html)} chars, {N} guides, {N_NOEQ} no-equipment)")