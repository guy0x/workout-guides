#!/usr/bin/env python3
"""Generate thumbs/<slug>.jpg from the first frame of each guide's first GIF,
plus add the 9 imported Wellness guides to data/index-overrides.json."""
import json, subprocess, glob, os
from pathlib import Path

REPO = Path.home() / "tmp_work/workout-guides"

# 1. thumbnails
for slug_dir in sorted(glob.glob(str(REPO / "*/"))):
    slug = Path(slug_dir).name.rstrip("/")
    if slug in ("thumbs", "scripts", "data"):
        continue
    out = REPO / "thumbs" / f"{slug}.jpg"
    if out.exists():
        continue
    gifs = sorted(glob.glob(os.path.join(slug_dir, "*.gif")))
    if not gifs:
        print("NO GIF for thumb:", slug)
        continue
    r = subprocess.run(["ffmpeg", "-y", "-i", gifs[0], "-vframes", "1",
                        "-vf", "scale=640:-2", str(out)],
                       capture_output=True, text=True)
    print(("OK " if r.returncode == 0 else "FAIL ") + slug)

# 2. index-overrides entries
OV_PATH = REPO / "data" / "index-overrides.json"
OV = json.load(open(OV_PATH))

def meta(mins, moves, gear):
    return [
      f'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 15,14"/></svg>{mins}',
      f'<svg viewBox="0 0 24 24"><path d="M13 2 L3 14 h7 l-1 8 10-12 h-7z"/></svg>{moves}',
      f'<svg viewBox="0 0 24 24"><path d="M2 12 a10 10 0 0 1 20 0Z"/><path d="M2 12 a10 10 0 0 0 20 0"/><circle cx="12" cy="12" r="2"/></svg>{gear}'
    ]

NEW = {
 "squat-university-foot-shape-arch-strength": dict(
   title="Foot Shape & Arch Strength — 4 Exercises", cat="rehab legs", gear=["none"],
   tags=["Rehab", "Feet & Ankles"], meta=meta("~8 min", "4 exercises", "No equipment"),
   desc="Squat University's foot-shape assessment and arch-strength drills: short foot, toe splay, arch doming and calf work to fix flat/collapsed feet at the source.",
   search="squat university foot shape arch strength flat feet pronation short foot toe splay aaron horsching"),
 "korea-wrestlers-kettlebell-training": dict(
   title="Korea Wrestlers Kettlebell Training — 4 Exercises", cat="gym legs", gear=["kettlebell"],
   tags=["Gym", "Legs", "Kettlebell"], meta=meta("~20 min", "4 exercises", "Kettlebell"),
   desc="Traditional Korean wrestling kettlebell conditioning: swings, cleans, front rack squats and presses — full-body power built on heavy KB fundamentals.",
   search="korea wrestlers kettlebell training swings cleans squats presses ssireum conditioning"),
 "3-day-summer-prep-dumbbell-blast": dict(
   title="3-Day Summer Prep Dumbbell Blast", cat="gym upper", gear=["dumbbells"],
   tags=["Gym", "Upper Body", "Dumbbells"], meta=meta("3-day split", "2 exercises/day", "Dumbbells"),
   desc="Large Dumbbells' 3-day dumbbell split for summer prep — focused push and pull pairings per day, minimal equipment, maximum density.",
   search="large dumbbells 3 day summer prep dumbbell blast split push pull"),
 "ryo-oya-floor-calisthenics-push-hollow-hold": dict(
   title="Floor Calisthenics — Push & Hollow Hold", cat="core", gear=["mat"],
   tags=["Core", "Bodyweight", "Mat"], meta=meta("~10 min", "2 exercises", "Mat only"),
   desc="Ryo Oya's floor calisthenics pair: strict pushing variations with hollow-body hold work — calisthenics strength with trunk tension.",
   search="ryo oya floor calisthenics push hollow hold bodyweight japan"),
 "mace-odyssey-clubbell-kettlebell-power": dict(
   title="Clubbell & Kettlebell 30-Min Power", cat="gym", gear=["kettlebell"],
   tags=["Gym", "Kettlebell", "Full Body"], meta=meta("~30 min", "4 exercises", "Kettlebell + clubbell"),
   desc="Mace Odyssey's 30-minute clubbell and kettlebell power circuit — rotational strength, swings and press patterns for full-body conditioning.",
   search="mace odyssey clubbell kettlebell 30 min power rotational strength circuit"),
 "vivona-flow-russian-calisthenics-mobility-core": dict(
   title="Russian Calisthenics — Floor Mobility & Core", cat="mobility core", gear=["mat"],
   tags=["Mobility", "Core", "Mat"], meta=meta("~12 min", "3 exercises", "Mat only"),
   desc="Vivona Flow's Russian-style floor work: mobility transitions woven with core tension drills — control through full range, not just holds.",
   search="vivona flow russian calisthenics floor mobility core transitions"),
 "single-kettlebell-room-shred": dict(
   title="Single Kettlebell Room Shred", cat="gym core", gear=["kettlebell"],
   tags=["Gym", "Kettlebell", "Full Body"], meta=meta("~15 min", "3 exercises", "1 kettlebell"),
   desc="WhatKaidoes' single-kettlebell room shred — three KB movements, minimal space, high density. Hotel-room or home friendly conditioning.",
   search="whatkaidoes single kettlebell room shred conditioning home hotel"),
 "hip-strength-for-runners": dict(
   title="Hip Strength for Runners", cat="rehab hips", gear=["none"],
   tags=["Rehab", "Hips", "Running"], meta=meta("~8 min", "2 exercises", "No equipment"),
   desc="Zhamedi Performance's runner-focused hip strength pair — glute med and deep hip work to keep knees tracking and strides stable.",
   search="zhamedi performance hip strength runners glute medius running knees"),
 "hackenschmidt-bulletproof-knee": dict(
   title="Hackenschmidt Bulletproof Knee", cat="rehab legs", gear=["none"],
   tags=["Rehab", "Legs & Knees"], meta=meta("~10 min", "3 exercises", "No equipment"),
   desc="Running Ability's George Hackenschmidt-inspired knee bulletproofing: legacy strength drills for tendon resilience and stable knees.",
   search="running ability hackenschmidt bulletproof knee tendon strength legs"),
}
added = 0
for slug, cfg in NEW.items():
    if slug not in OV:
        OV[slug] = cfg
        added += 1
json.dump(OV, open(OV_PATH, "w"), indent=2, ensure_ascii=False)
print("overrides added:", added, "| total:", len(OV))
