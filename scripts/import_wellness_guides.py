#!/usr/bin/env python3
"""Import missing Wellness/Workouts HTML guides into the workout-guides repo.
De-base64s embedded GIFs into per-guide gif-NN.gif files."""
import re, base64
from pathlib import Path

W = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Wellness/Workouts"
REPO = Path.home() / "tmp_work/workout-guides"

MAP = {
 "02 Squat University - Foot Shape and Arch Strength (4 exercises).html": "squat-university-foot-shape-arch-strength",
 "03 Wrestling Physi - Korea Wrestlers Kettlebell Training (4 exercises).html": "korea-wrestlers-kettlebell-training",
 "04 Large Dumbbells - 3-Day Summer Prep Dumbbell Blast (2 exercises).html": "3-day-summer-prep-dumbbell-blast",
 "05 Ryo Oya - Floor Calisthenics Push and Hollow Hold (2 exercises).html": "ryo-oya-floor-calisthenics-push-hollow-hold",
 "06 Mace Odyssey - Clubbell and Kettlebell 30-Min Power (4 exercises).html": "mace-odyssey-clubbell-kettlebell-power",
 "07 Vivona Flow - Russian Calisthenics Floor Mobility and Core (3 exercises).html": "vivona-flow-russian-calisthenics-mobility-core",
 "08 WhatKaidoes - Single Kettlebell Room Shred (3 exercises).html": "single-kettlebell-room-shred",
 "09 Zhamedi Performance - Hip Strength for Runners (2 exercises).html": "hip-strength-for-runners",
 "10 Running Ability - Hackenschmidt Bulletproof Knee (3 exercises).html": "hackenschmidt-bulletproof-knee",
}

PAT = re.compile(r'((?:src|poster|data-src)\s*=\s*")data:image/gif;base64,([A-Za-z0-9+/=]+)"')

for src, slug in MAP.items():
    p = W / src
    if not p.exists():
        print("MISSING SRC:", src)
        continue
    html = p.read_text(errors="ignore")
    d = REPO / slug
    d.mkdir(exist_ok=True)
    n = 0
    def repl(m):
        global n
        n += 1
        raw = base64.b64decode(m.group(2))
        (d / f"gif-{n:02d}.gif").write_bytes(raw)
        return f'{m.group(1)}gif-{n:02d}.gif"'
    html2 = PAT.sub(repl, html)
    (d / "index.html").write_text(html2)
    print(slug, n, "gifs,", len(html2) // 1024, "KB html")
