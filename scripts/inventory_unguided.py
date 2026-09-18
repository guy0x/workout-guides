import json, os, re
from datetime import datetime

REELS = "/Users/guy/Documents/Reels"
REG = f"{REELS}/metadata/REEL-REGISTRY.json"
SPECS = "/Users/guy/.hermes/profiles/librarian/scripts/guide_pipeline/specs"
HUB = "/Users/guy/tmp_work/workout-guides"

reg = json.load(open(REG))
reels = reg["reels"]

guided = set()
for f in os.listdir(SPECS):
    if f.endswith(".json"):
        try:
            dd = json.load(open(os.path.join(SPECS, f)))
            if dd.get("reel_id"): guided.add(dd["reel_id"])
        except: pass
for rid, e in reels.items():
    a = e.get("artifacts")
    if isinstance(a, dict) and a.get("guide"): guided.add(rid)
for d in os.listdir(HUB):
    p = os.path.join(HUB, d)
    if os.path.isdir(p) and os.path.isfile(os.path.join(p, "index.html")):
        for rid in reels:
            if rid in d: guided.add(rid)

def parse_ts(s):
    if not s: return None
    s = s.replace('Z', '+00:00')
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is None: d = d.replace(tzinfo=__import__('datetime').timezone.utc)
        return d
    except: return None

rows = []
for rid, e in reels.items():
    coll = (e.get("collection") or "")
    if not coll.lower().startswith("workout"): continue
    if rid in guided: continue
    if not os.path.exists(f"{REELS}/sources/{rid}.mp4"): continue
    has_sum = os.path.exists(f"{REELS}/final/summaries/{rid}.md")
    has_srt = os.path.exists(f"{REELS}/final/srt/{rid}.srt")
    ts = parse_ts(e.get("processed_at"))
    rows.append((ts or datetime(2020,1,1,tzinfo=__import__('datetime').timezone.utc), rid, coll, has_sum, has_srt))

rows.sort(reverse=True)
recent = [r for r in rows if r[0].year >= 2026 and r[0].month >= 9]
older  = [r for r in rows if r not in recent]

print(f"TOTAL processable unguided: {len(rows)}")
print(f"  recent (Sep 2026+): {len(recent)}   (with summary: {sum(1 for r in recent if r[3])}, with srt: {sum(1 for r in recent if r[4])})")
print(f"  older backlog: {len(older)}   (with summary: {sum(1 for r in older if r[3])})")
print("\n=== RECENT (Sep 2026+) candidates ===")
for ts, rid, coll, hs, hsrt in recent:
    print(f"{rid}  [{coll}]  {ts.date()}  sum={hs} srt={hsrt}")
