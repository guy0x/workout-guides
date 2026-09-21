#!/usr/bin/env python3
"""build_mixes.py — Curated 'mix' pages: combine exercise cards from across guides into
ready-to-run circuits. Reads mix definitions from data/mixes.json (slug + ordered list of
{sources: [guide slugs], text: ..., cards: [names]}) and emits <mix-slug>/index.html.

Each mix page: title, intent, numbered circuit steps (card name, source guide, dose, cues),
and a footer linking back to the card directory. Regenerated on demand; safe to re-run.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path("/Users/guy/tmp_work/workout-guides")
SPECS = Path("/Users/guy/.hermes/profiles/librarian/scripts/guide_pipeline/specs")

# Load all specs once: slug -> {cards: {card_name: card}}
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

CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "SF Pro Text", Helvetica, Arial, sans-serif;
         background: #0f1115; color: #e8eaf0; line-height: 1.6; padding-bottom: 60px; }
  header { padding: 28px 20px 20px; background: linear-gradient(135deg,#1a1d24,#1e2430);
            border-bottom: 1px solid #2c2f38; }
  header h1 { font-size: 1.6rem; letter-spacing: -0.3px; }
  header .meta { color: #9aa0ae; font-size: .9rem; margin-top: 6px; }
  .nav { position: sticky; top: 0; background: #15171d; border-bottom: 1px solid #262a33; z-index: 5;
          display: flex; gap: 6px; overflow-x: auto; padding: 8px 12px; }
  .nav a { flex: 0 0 auto; background: #1d2027; color: #c5c9d4; text-decoration: none;
            padding: 5px 10px; border-radius: 14px; font-size: .78rem; }
  .nav a.home { background: #10b981; color: #fff; font-weight: 700; }
  .container { max-width: 720px; margin: 0 auto; padding: 18px 16px; }
  .intent { background:#1a1e26; border-left:3px solid #10b981; padding:10px 14px; border-radius:6px;
             font-size:.92rem; color:#b8bed0; margin-bottom:18px; }
  .card { background:#161920; border:1px solid #262a33; border-radius:14px; overflow:hidden; margin-bottom:22px; }
  .card-num { background:#2a2f3c; color:#c8d9fd; font-weight:700; text-align:center; font-size:1.3rem; padding:10px 0; letter-spacing:1px; }
  .card-body { padding:16px; }
  .card-title-row { display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin-bottom:12px; }
  .card-title-row h2 { font-size:1.15rem; color:#f2f4ff; }
  .section-tag { background:#1e2a3a; color:#93c5fd; font-size:.7rem; padding:2px 8px; border-radius:10px; text-transform:uppercase; letter-spacing:.5px; white-space:nowrap; }
  .dose { font-size:.8rem; color:#fbbf24; margin:0 0 10px; font-weight:600; }
  .desc { font-size:.92rem; color:#cdd2de; margin-bottom:10px; }
  .cues { margin:0 0 0 18px; color:#aab0c0; font-size:.9rem; }
  .cues li { margin-bottom:4px; }
  .src { display:inline-block; margin-top:10px; background:#223; border:1px solid #3a3f4d; padding:4px 10px; border-radius:20px; font-size:.8rem; color:#b8c0ff; word-break:break-all; }
  footer { text-align:center; color:#6b707d; font-size:.78rem; padding:20px 12px; }
  footer a { color:#34d399; text-decoration:underline; }
"""

def build_mix(mix, db):
    slug = mix["slug"]
    title = mix["title"]
    intent = mix["intent"]
    steps = mix["steps"]
    cards_html = []
    nav = '<a class="home" href="../index.html">← Guides</a><a href="../cards.html">Cards</a>'
    for i, step in enumerate(steps, 1):
        src = step["source"]
        card_name = step["card"]
        spec = db.get(src)
        card = None
        if spec:
            card = next((c for c in spec.get("cards", []) if c.get("name") == card_name), None)
        if not card:
            card = {"name": card_name, "desc": step.get("text", ""), "dose": step.get("dose", ""), "cues": step.get("cues", [])}
        cues = "".join(f"<li>{x}</li>" for x in (card.get("cues") or step.get("cues", [])))
        tag = f'<span class="section-tag">{step.get("tag", "")}</span>' if step.get("tag") else ""
        dose = f'<div class="dose">{card.get("dose") or step.get("dose", "")}</div>'
        link = f'<a class="src" href="../{src}/">From: {spec["title"] if spec else src}</a>' if spec else ""
        cards_html.append(
            f'<div class="card">\n  <div class="card-num">{i}</div>\n'
            f'  <div class="card-body">\n'
            f'    <div class="card-title-row"><h2>{card["name"]}</h2>{tag}</div>\n'
            f'    {dose}\n'
            f'    <p class="desc">{card.get("desc") or step.get("text", "")}</p>\n'
            + (f'    <ol class="cues">{cues}</ol>\n' if cues else "")
            + (f'    {link}\n' if link else "")
            + '  </div>\n</div>')
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} — Workout Mix</title>
<style>
{CSS}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="meta">ATHENA curated mix · {len(steps)} steps · source guides linked</div>
  <div class="nav">{nav}</div>
</header>
<div class="container">
  <div class="intent">💡 <b>Why this mix:</b> {intent}</div>
  {chr(10).join(cards_html)}
</div>
<footer><a href="../cards.html">Browse all exercise cards</a> · compiled by ATHENA</footer>
</body>
</html>"""
    out = REPO / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {slug}/index.html ({len(html):,} chars, {len(steps)} steps)")


def main():
    mixes_f = REPO / "data" / "mixes.json"
    if not mixes_f.exists():
        print("no data/mixes.json — nothing to build", file=sys.stderr)
        return 1
    db = load_specs()
    mixes = json.load(open(mixes_f))
    for mix in mixes:
        build_mix(mix, db)
    # Mixes index page
    cards = []
    for mix in mixes:
        cards.append(
            f'<a class="mixcard" href="{mix["slug"]}/"><h2>{mix["title"]}</h2>'
            f'<p>{mix["intent"]}</p><span class="n">{len(mix["steps"])} steps</span></a>')
    idx_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Curated Mixes — Workout Guides</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "SF Pro Text", Helvetica, Arial, sans-serif; background: #f4f6f8; color: #1c2128; line-height: 1.55; }}
  a {{ color: inherit; text-decoration: none; }}
  header {{ background: #fff; border-bottom: 1px solid #e3e7ee; padding: 28px 22px; text-align: center; }}
  header h1 {{ font-size: 1.9rem; font-weight: 800; }}
  header p {{ color: #5a6472; margin-top: 6px; }}
  header .back {{ display:inline-block; margin-top:12px; color:#2563eb; font-weight:600; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:20px; padding:22px; max-width:1100px; margin:0 auto; }}
  .mixcard {{ background:#fff; border:1px solid #e3e7ee; border-radius:18px; padding:18px; transition:transform .15s,box-shadow .15s; }}
  .mixcard:hover {{ transform:translateY(-3px); box-shadow:0 10px 24px rgba(28,33,40,.12); }}
  .mixcard h2 {{ font-size:1.1rem; color:#2563eb; margin-bottom:8px; }}
  .mixcard p {{ font-size:.88rem; color:#5a6472; }}
  .mixcard .n {{ display:inline-block; margin-top:10px; background:#eef2f7; border-radius:999px; padding:4px 12px; font-size:.78rem; color:#3b4654; font-weight:600; }}
  footer {{ text-align:center; color:#9aa3b0; font-size:.78rem; padding:22px; }}
</style>
</head>
<body>
<header>
  <h1>Curated Mixes</h1>
  <p>Ready-to-run circuits assembled from exercise cards across the library.</p>
  <a class="back" href="index.html">← Workout Guides</a>
</header>
<main class="grid">
  {chr(10).join(cards)}
</main>
<footer>Compiled by ATHENA · each step links back to its source guide</footer>
</body>
</html>"""
    (REPO / "mixes.html").write_text(idx_html, encoding="utf-8")
    print(f"wrote mixes.html ({len(idx_html):,} chars, {len(mixes)} mixes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
