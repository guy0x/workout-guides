#!/usr/bin/env python3
"""build_program.py — Rotating 'This Week' program page (program.html).

Reads curated pillar pools from data/program.json ({source, card, dose, tag})
and the canonical guide specs (guide_pipeline/specs/*.json) for titles/descs,
then deterministically seeds a 3-day split by ISO week: posture / physique / gait.
Each pillar gets 6 cards via a seeded random shuffle (seed = ISO year*100 + ISO week),
with no source guide repeated inside the same day's slot. Re-running the script on
the same ISO week always yields the same program; the rotation advances every Monday.

Also keeps the hub cross-linked: patches index.html and mixes.html so regenerating
those pages (build_index.py / build_mixes.py) never drops the program link.
Safe to re-run; only touches data/program.json + program.html + the two index links.
"""
import json
import random
from datetime import date
from pathlib import Path

REPO = Path("/Users/guy/tmp_work/workout-guides")
SPECS = Path("/Users/guy/.hermes/profiles/librarian/scripts/guide_pipeline/specs")
PROGRAM_F = REPO / "data" / "program.json"

PER_PILLAR = 6  # 3 pillars × 6 = 18 movements/week (Guy's 15–25 mastery range)


def load_specs():
    db = {}
    for f in SPECS.glob("*.json"):
        if f.name.startswith("draft-"):
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        db[d.get("slug", f.stem)] = d
    return db


def iso_week(today=None):
    today = today or date.today()
    y, w, _ = today.isocalendar()
    return y, w


def pick_pool(pool, seed):
    """Deterministic per-week pick: shuffled pool, no guide slug repeats in the slot."""
    rng = random.Random(seed)
    items = list(pool)
    rng.shuffle(items)
    chosen, used_sources = [], set()
    for it in items:
        if len(chosen) >= PER_PILLAR:
            break
        if it["source"] in used_sources:
            continue
        chosen.append(it)
        used_sources.add(it["source"])
    # If the pool is tight, top up without the no-repeat guarantee
    for it in items:
        if len(chosen) >= PER_PILLAR:
            break
        if it not in chosen:
            chosen.append(it)
    return chosen


def render_step(i, step, db):
    src = step["source"]
    card_name = step["card"]
    spec = db.get(src)
    card = None
    if spec:
        card = next((c for c in spec.get("cards", []) if c.get("name") == card_name), None)
    if not card:
        card = {"name": card_name, "desc": "", "dose": step.get("dose", ""), "cues": []}
    dose = f'<span class="dose">{step.get("dose") or card.get("dose", "")}</span>'
    tag = f'<span class="tag">{step.get("tag", "")}</span>' if step.get("tag") else ""
    link = f'<a class="src" href="{src}/">From: {spec["title"] if spec else src}</a>' if spec else ""
    return (
        f'<li class="step">'
        f'<span class="num">{i}</span>'
        f'<div class="s-body"><div class="s-title">{card["name"]} {tag}</div>{dose}{link}</div>'
        f"</li>"
    )


def build_program_html(db, program, y, w, slots):
    meta = program["meta"]
    cards_html = []
    for pillar in meta["pillars"]:
        steps = slots[pillar["id"]]
        step_html = "\n".join(
            render_step(i, s, db) for i, s in enumerate(steps, 1)
        )
        src_count = len({s["source"] for s in steps})
        cards_html.append(
            f"""<section class="day">
  <div class="day-head">
    <span class="day-label">{pillar["day"]} · <b>{pillar["label"]}</b></span>
    <span class="n">{len(steps)} moves · {src_count} guides</span>
  </div>
  <p class="blurb">{pillar["blurb"]}</p>
  <ol class="steps">{step_html}</ol>
</section>"""
        )
    meta_line = f"ISO week {w} of {y} · rotation rolls over Monday · repeat the same {PER_PILLAR * 3} movements through the week toward mastery"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="description" content="ATHENA's rotating weekly program — 3-day split themed posture, physique and gait, built from the workout-guides card library. Changes every ISO week."/>
<title>This Week's Program — Workout Guides</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "SF Pro Text", Helvetica, Arial, sans-serif;
         background: #f4f6f8; color: #1c2128; line-height: 1.55; }}
  a {{ color: inherit; text-decoration: none; }}
  header {{ background: #ffffff; border-bottom: 1px solid #e3e7ee; padding: 32px 22px 26px; text-align: center; }}
  header .kicker {{ display: inline-block; background: #eef2f7; color: #4a5b7a; font-size: .72rem;
                     letter-spacing: 2px; text-transform: uppercase; padding: 5px 14px; border-radius: 20px; }}
  header h1 {{ font-size: clamp(1.8rem, 5vw, 2.6rem); letter-spacing: -0.5px; font-weight: 800; margin-top: 12px; }}
  header p.sub {{ color: #5a6472; font-size: .98rem; margin-top: 6px; max-width: 640px; margin-left: auto; margin-right: auto; }}
  header .meta {{ margin-top: 14px; background: #f4f6f8; border: 1px solid #e3e7ee; display: inline-block;
                   border-radius: 999px; padding: 6px 16px; font-size: .84rem; color: #3b4654; font-weight: 600; }}
  header .nav {{ margin-top: 14px; }}
  header .nav a {{ display: inline-block; background: #eef2f7; color: #2563eb; border-radius: 20px;
                    padding: 6px 16px; font-size: .85rem; font-weight: 600; margin: 0 4px; }}
  header .nav a.home {{ background: #10b981; color: #fff; }}
  header .nav a.on {{ background: #2563eb; color: #fff; }}
  .container {{ max-width: 760px; margin: 0 auto; padding: 20px 16px 40px; }}
  .day {{ background: #ffffff; border: 1px solid #e3e7ee; border-radius: 20px; padding: 20px 22px; margin-bottom: 22px; }}
  .day-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }}
  .day-label {{ font-size: 1.15rem; font-weight: 800; letter-spacing: -0.2px; color: #2563eb; }}
  .day-label b {{ color: #1c2128; }}
  .n {{ font-size: .76rem; color: #6b7480; background: #f4f6f8; border-radius: 999px; padding: 3px 10px; font-weight: 600; }}
  .blurb {{ color: #5a6472; font-size: .88rem; margin: 8px 0 14px; }}
  .steps {{ list-style: none; display: flex; flex-direction: column; gap: 8px; }}
  .step {{ display: flex; gap: 12px; align-items: flex-start; background: #f8fafc; border: 1px solid #edf0f5;
            border-radius: 14px; padding: 10px 14px; }}
  .step .num {{ flex: 0 0 28px; height: 28px; background: #2563eb; color: #fff; border-radius: 12px;
                 display: inline-flex; align-items: center; justify-content: center; font-size: .82rem; font-weight: 700; }}
  .step .s-body {{ flex: 1; min-width: 0; }}
  .step .s-title {{ font-size: .95rem; font-weight: 700; }}
  .step .tag {{ display: inline-block; margin-left: 6px; background: #eef2f7; color: #4a5b7a; font-size: .68rem;
                 padding: 1px 8px; border-radius: 10px; text-transform: uppercase; letter-spacing: .5px; vertical-align: 2px; }}
  .step .dose {{ display: inline-block; font-size: .8rem; color: #d97706; font-weight: 600; margin-top: 2px; }}
  .step .src {{ display: inline-block; margin-left: 10px; font-size: .76rem; color: #2563eb; font-weight: 600; }}
  .step .src:hover {{ text-decoration: underline; }}
  footer {{ text-align: center; color: #9aa3b0; font-size: .78rem; padding: 10px 20px 26px; }}
  footer a {{ color: #2563eb; }}
  @media (max-width: 520px) {{ .container {{ padding: 14px 10px 30px; }} .day {{ padding: 16px; }} }}
</style>
</head>
<body>
<header>
  <span class="kicker">Move Better · Recover Faster · Train Smarter</span>
  <h1>This Week's Program</h1>
  <p class="sub">{meta["intent"]}</p>
  <div class="meta">{meta_line}</div>
  <div class="nav">
    <a class="home" href="index.html">← Guides</a>
    <a href="cards.html">Cards</a>
    <a href="mixes.html">Mixes</a>
    <a class="on" href="program.html">Program</a>
  </div>
</header>
<div class="container">
  {chr(10).join(cards_html)}
</div>
<footer>Compiled by ATHENA · every move links back to its source guide · <a href="cards.html">browse all cards</a></footer>
</body>
</html>"""
    (REPO / "program.html").write_text(html, encoding="utf-8")
    print(f"wrote program.html ({len(html):,} chars, ISO {y}-W{w}, {len(slots)} pillars)")


def patch_index_link():
    """Add/refresh the program link in index.html + mixes.html in place.

    Deliberately does NOT call build_index.py / build_mixes.py: those generators
    regenerate the whole hub and would sweep in unrelated sync changes. We only
    patch the two shared pages' nav rows so the program page stays linked without
    touching anything else. Idempotent — safe to re-run.
    """
    # index.html nav row
    idx = REPO / "index.html"
    if idx.exists():
        txt = idx.read_text(encoding="utf-8")
        if "program.html" not in txt:
            marker = '<a href="mixes.html" style="display:inline-block;background:#2563eb'
            prog_btn = ('<a href="program.html" style="display:inline-block;background:#8b5cf6;color:#fff;'
                        'font-weight:700;padding:7px 18px;border-radius:20px;font-size:.9rem">This Week\'s Program →</a>')
            if marker in txt:
                txt = txt.replace(marker, prog_btn + marker)
                idx.write_text(txt, encoding="utf-8")
                print("patched index.html: added program link")
            else:
                print("WARN: index.html nav marker not found — program link NOT added")

    # mixes.html back row
    mix = REPO / "mixes.html"
    if mix.exists():
        txt = mix.read_text(encoding="utf-8")
        if "program.html" not in txt:
            marker = '<a class="back" href="index.html">← Workout Guides</a>'
            if marker in txt:
                txt = txt.replace(
                    marker,
                    marker
                    + ' <a class="back" href="program.html" style="margin-left:10px">This Week\'s Program →</a>',
                )
                mix.write_text(txt, encoding="utf-8")
                print("patched mixes.html: added program link")


def main():
    if not PROGRAM_F.exists():
        print("no data/program.json — nothing to build", file=__import__("sys").stderr)
        return 1
    program = json.load(open(PROGRAM_F))
    db = load_specs()
    y, w = iso_week()
    seed = y * 100 + w
    slots = {}
    for pid, entries in program["pools"].items():
        slots[pid] = pick_pool(entries, seed)
        print(f"  {pid}: {len(slots[pid])} moves")
    build_program_html(db, program, y, w, slots)
    patch_index_link()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
