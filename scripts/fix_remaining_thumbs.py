#!/usr/bin/env python3
"""Extract first embedded GIF from data-URI guides and render thumbnails."""
import re, base64, subprocess
from pathlib import Path

REPO = Path.home() / "tmp_work/workout-guides"
for slug in ["carpal-tunnel-prevention-wrist-stretches", "core-circuit-boat-hollow-crunch-plank"]:
    html = (REPO / slug / "index.html").read_text()
    m = re.search(r'data:image/gif;base64,([A-Za-z0-9+/=]+)', html)
    tmp = REPO / slug / "_thumb_src.gif"
    tmp.write_bytes(base64.b64decode(m.group(1)))
    out = REPO / "thumbs" / f"{slug}.jpg"
    r = subprocess.run(["ffmpeg", "-y", "-i", str(tmp), "-vframes", "1",
                        "-vf", "scale=640:-2", str(out)], capture_output=True, text=True)
    tmp.unlink()
    print(("OK " if r.returncode == 0 else "FAIL ") + slug)
