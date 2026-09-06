#!/usr/bin/env python3
"""Integrate 3 new mobility guides into the workout-guides repo:
   1. Copy built HTMLs from iCloud into repo with clean kebab slugs.
   2. Insert entries into data/index-overrides.json (alphabetical position).
   3. Rebuild the guide card blocks in index.html (alphabetical) + hero stats.
   4. Update README.md guide list.
"""
import json, os, re, shutil, sys

REPO = "/Users/guy/tmp_work/workout-guides"
CLOUD = "/Users/guy/Library/Mobile Documents/com~apple~CloudDocs/Workout Guides"

# slug -> (source iCloud dir, title, desc, tags, cat, gear, meta[], search, readme_line)
NEW = {
  "ankle-grip-mobility-progression": {
    "src": "garcia_effect_official_ankle-grip-mobility-10-move-progression_Dcl9dWGlIgz",
    "title": "Ankle-Grip Mobility — 10-Move Progression",
    "desc": "10 mobility moves on one connective cue — grip the ankles and drive joints through end range: rocks, roller bridges, cone clearances, hero pose, bridge finisher. From @garcia_effect_official.",
    "tags": ["Mobility", "Legs & Knees"],
    "cat": "mobility legs",
    "gear": ["none"],
    "meta": [
      '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 15,14"/></svg>~10 min',
      '<svg viewBox="0 0 24 24"><path d="M13 2 L3 14 h7 l-1 8 10-12 h-7z"/></svg>10 moves',
      '<svg viewBox="0 0 24 24"><path d="M2 12 a10 10 0 0 1 20 0Z"/><path d="M2 12 a10 10 0 0 0 20 0"/><circle cx="12" cy="12" r="2"/></svg>No equipment'
    ],
    "search": "ankle grip mobility progression garcia effect ankles hips foam roller cones Ankle-Grip Mobility — 10-Move Progression",
    "readme": "- **Ankle-Grip Mobility — 10-Move Progression** — grip the ankles, drive joints through end-range: 10 grounded moves (rocks, roller bridges, L-sit dorsiflexion, cone drills, hero pose), built as one connected cue system. From Luis Garcia (@garcia_effect_official, ATC/LAT · CSCS) → `ankle-grip-mobility-progression/`"
  },
  "lower-back-4-exercises": {
    "src": "lennycalisthenics_lower-back-4-exercises-not-more-stretches_Dc6PS5hIqBU",
    "title": "Lower Back — 4 Exercises, Not More Stretches",
    "desc": "Windshield wipers, ankle-grip glute bridge, wide-stance glute bridge, straight leg raise — bodyweight lower-back strengthening over passive stretching. From @lennycalisthenics.",
    "tags": ["Mobility", "Lower Back"],
    "cat": "mobility legs",
    "gear": ["none"],
    "meta": [
      '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 15,14"/></svg>~5 min',
      '<svg viewBox="0 0 24 24"><path d="M13 2 L3 14 h7 l-1 8 10-12 h-7z"/></svg>4 exercises',
      '<svg viewBox="0 0 24 24"><path d="M2 12 a10 10 0 0 1 20 0Z"/><path d="M2 12 a10 10 0 0 0 20 0"/><circle cx="12" cy="12" r="2"/></svg>No equipment'
    ],
    "search": "lower back lennycalisthenics windshield wipers glute bridge straight leg raise stretches Lower Back — 4 Exercises, Not More Stretches",
    "readme": "- **Lower Back — 4 Exercises, Not More Stretches** — windshield wipers, ankle-grip glute bridge, wide-stance glute bridge, straight leg raise. Mat-only lower-back strengthening, from @lennycalisthenics → `lower-back-4-exercises/`"
  },
  "mobility-from-zero-4-exercises": {
    "src": "leo.moves_rebuild-mobility-from-zero-4-exercises_DcGh81lN_yt",
    "title": "Rebuild Mobility From Zero — 4 Exercises",
    "desc": "Lunge-to-fold, hip-lift toe taps, prone arch ↔ forearm plank flow, kneeling diagonal stretch — the 4 moves to restart full mobility from nothing. From @leo.moves.",
    "tags": ["Mobility", "Beginner"],
    "cat": "mobility",
    "gear": ["none"],
    "meta": [
      '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 15,14"/></svg>~6 min',
      '<svg viewBox="0 0 24 24"><path d="M13 2 L3 14 h7 l-1 8 10-12 h-7z"/></svg>4 exercises',
      '<svg viewBox="0 0 24 24"><path d="M2 12 a10 10 0 0 1 20 0Z"/><path d="M2 12 a10 10 0 0 0 20 0"/><circle cx="12" cy="12" r="2"/></svg>No equipment'
    ],
    "search": "mobility from zero rebuild leo.moves leomoves lunge forward fold toe taps prone arch plank kneeling diagonal Rebuild Mobility From Zero — 4 Exercises",
    "readme": "- **Rebuild Mobility From Zero — 4 Exercises** — lunge-to-fold, hip-lift toe taps, prone arch ↔ forearm plank flow, kneeling diagonal stretch. What one coach would do if he lost all mobility, from @leo.moves → `mobility-from-zero-4-exercises/`"
  },
}

# ---------- 1. Copy guide HTMLs into repo ----------
for slug, cfg in NEW.items():
    src_html = os.path.join(CLOUD, cfg["src"], "index.html")
    if not os.path.exists(src_html):
        print(f"!! missing source: {src_html}"); sys.exit(1)
    dest = os.path.join(REPO, slug)
    os.makedirs(dest, exist_ok=True)
    shutil.copy2(src_html, os.path.join(dest, "index.html"))
    print(f"copied {slug}/index.html  ({os.path.getsize(os.path.join(dest,'index.html'))//1_000_000} MB)")

# ---------- 2. Update data/index-overrides.json ----------
ovp = os.path.join(REPO, "data", "index-overrides.json")
ov = json.load(open(ovp))
for slug, cfg in NEW.items():
    ov[slug] = {
        "title": cfg["title"], "desc": cfg["desc"], "tags": cfg["tags"],
        "cat": cfg["cat"], "gear": cfg["gear"], "meta": cfg["meta"],
        "search": cfg["search"],
    }
# write with sorted keys (matching existing file style), 2-space indent kept
ordered = {k: ov[k] for k in sorted(ov)}
tmp = ovp + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(ordered, f, ensure_ascii=False, indent=2)
    f.write("\n")
shutil.move(tmp, ovp)
print(f"overrides json: {len(ordered)} guides")

# ---------- 3. Rebuild index.html cards + stats ----------
idx = os.path.join(REPO, "index.html")
html = open(idx, encoding="utf-8").read()

def card_block(slug, cfg):
    tags = "".join(f'<span class="tag">{t}</span>' for t in cfg["tags"])
    metas = "".join(f"<span>{m}</span>" for m in cfg["meta"])
    data_tags = f'{cfg["search"]} {cfg["title"]} {cfg["title"]}'
    return (f'  <a class="card" href="{slug}/" data-cat="{cfg["cat"]}" '
            f'data-gear="{" ".join(cfg["gear"])}" data-tags="{data_tags}">\n'
            f'    <div class="tags">{tags}</div>\n'
            f'    <h2>{cfg["title"]}</h2>\n'
            f'    <p class="desc">{cfg["desc"]}</p>\n'
            f'    <div class="meta">{metas}</div>\n'
            f'    <span class="open">Open guide <svg viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12,5 19,12 12,19"/></svg></span>\n'
            f'  </a>\n')

cards_html = ""
for slug in sorted(NEW):
    cards_html += card_block(slug, NEW[slug])

# insert alphabetically among existing card anchors — reframe: rebuild the whole grid block
start = html.index('<main class="grid" id="grid">')
end = html.index('<div class="empty" id="empty">')
head = html[:start]
tail = html[end:]

# parse existing cards to keep their exact blocks, then merge with new ones by slug
existing_block = html[start:end]
# existing cards each start with '<a class="card" href=' on its own line
existing_cards = re.findall(r'  <a class="card" href="([^"]+)/" .*?\n  </a>\n', existing_block, re.S)
existing_pairs = []
pos = 0
for m in re.finditer(r'(  <a class="card" href="[^"]+/".*?\n  </a>\n)', existing_block, re.S):
    blk = m.group(1)
    slug_m = re.search(r'<a class="card" href="([^"]+)/"', blk)
    existing_pairs.append((slug_m.group(1), blk))

# merge: existing + new, sorted by slug
merged = {}
for s, b in existing_pairs:
    merged[s] = b
for slug in NEW:
    merged[slug] = card_block(slug, NEW[slug])

grid_body = "".join(merged[k] for k in sorted(merged))
new_grid = '<main class="grid" id="grid">\n' + grid_body + '\n'
html2 = head + new_grid + tail

# hero stats: count guides + no-equipment
n_guides = len(merged)
n_noeq = len([k for k in merged if "none" in merged[k].split('data-gear="')[1].split('"')[0].split()]) if False else 0
n_noeq = sum(1 for k in merged for g in [re.search(r'data-gear="([^"]+)"', merged[k]).group(1).split()] if "none" in g)
n_mastery = sum(1 for k in merged if k.startswith("mastery-"))
html2 = re.sub(r'(<b id="stat-guides">)\d+(</b>)', rf"\g<1>{n_guides}\g<2>", html2)
html2 = re.sub(r'(<div class="stat"><b>)\d+(</b><span>No-equipment</span>)', rf"\g<1>{n_noeq}\g<2>", html2)
html2 = re.sub(r'(<div class="stat"><b>)\d+(</b><span>Mastery series</span>)', rf"\g<1>{n_mastery}\g<2>", html2)

with open(idx, "w", encoding="utf-8") as f:
    f.write(html2)
print(f"index.html: {n_guides} guides, {n_noeq} no-equipment, {n_mastery} mastery")

# ---------- 4. README ----------
rmp = os.path.join(REPO, "README.md")
rm = open(rmp, encoding="utf-8").read()
# insert new bullets after the guide-list header line "## Guides"
insert_at = rm.index("## Guides\n") + len("## Guides\n")
bullets = "\n".join(cfg["readme"] for cfg in NEW.values()) + "\n"
# put new bullets at top of list (most recent)
rm2 = rm[:insert_at] + bullets + rm[insert_at:]
# fix guide count if present
with open(rmp, "w", encoding="utf-8") as f:
    f.write(rm2)
print("README updated")
print("DONE")