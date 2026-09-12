#!/usr/bin/env python3
"""Generate hub thumbnails (thumbs/<slug>.jpg) for workout guides.

Thumbnail convention:
  a mid-clip frame of one of the guide's own images, cropped to the hub's
  16:9 card ratio, 640x360, JPEG.

Source resolution order per guide:
  1. <slug>/gif-*.gif                       (relative-GIF guides)
  2. first data:image/gif;base64 in index.html (self-contained guides)
  3. no source -> an existing thumbs/<slug>.jpg is KEPT (curated), otherwise the
     hub renders its .thumb-ph accent placeholder card

Distinctness guarantee (the point of this script):
  Several guides legitimately share movement media (the Mastery programs are
  compilations drawn from other guides' libraries), so naively sampling the
  first frame made different cards render the IDENTICAL image. After building,
  collisions are detected by output hash and the loser is re-rendered from its
  next own image / a different time offset until it is visually distinct.

usage:
  python3 scripts/make_thumbs.py [--force] [--only slug[,slug]] [--at 0.3]
"""
import argparse
import base64
import hashlib
import re
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image   # optional: used only for the visual safety net
except ImportError:         # pragma: no cover
    Image = None

REPO = Path(__file__).resolve().parent.parent
THUMBS = REPO / "thumbs"
FFMPEG = "/opt/homebrew/bin/ffmpeg"


def guide_sources(slug_dir: Path):
    """All renderable image payloads for a guide, in card order."""
    out = []
    for g in sorted(slug_dir.glob("gif-*.gif")):
        out.append(("file", g))
    html = (slug_dir / "index.html").read_text(errors="ignore")
    for m in re.findall(r'data:image/gif;base64,([A-Za-z0-9+/=]+)', html):
        out.append(("bytes", base64.b64decode(m)))
    return out


def render(src_kind, payload, out: Path, at: float) -> bool:
    """Frame at ~`at` of the clip (not frame 1 — reels open on black frames or
    title cards), cropped to the card's 16:9 ratio."""
    tmp = None
    if src_kind == "bytes":
        tmp = REPO / "_thumb_tmp.gif"
        tmp.write_bytes(payload)
        src = tmp
    else:
        src = payload
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(src)], capture_output=True, text=True)
    try:
        dur = float(probe.stdout.strip() or 0)
    except ValueError:
        dur = 0.0
    vf = "scale=640:-2,crop=640:360"
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", f"{max(0.0, dur * at):.2f}",
                        "-i", str(src), "-vframes", "1", "-vf", vf, str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-vframes", "1",
                            "-vf", vf, str(out)], capture_output=True, text=True)
    if tmp:
        tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        print(f"   ffmpeg failed: {r.stderr.strip()[:160]}")
        return False
    return True


def digest(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rebuild thumbs that already exist")
    ap.add_argument("--only", help="comma-separated slugs")
    ap.add_argument("--at", type=float, default=0.3, help="sample fraction into the clip")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None

    THUMBS.mkdir(exist_ok=True)
    guides = sorted(p for p in REPO.iterdir()
                    if p.is_dir() and (p / "index.html").exists()
                    and p.name not in ("data", "scripts", "thumbs"))

    sources, built, kept, placeholder = {}, [], [], []
    for g in guides:
        if only and g.name not in only:
            continue
        out = THUMBS / f"{g.name}.jpg"
        if out.exists() and not args.force:
            kept.append(g.name)
            continue
        srcs = guide_sources(g)
        sources[g.name] = srcs
        if not srcs:
            if out.exists():
                kept.append(g.name)          # curated thumb, no in-guide source
            else:
                placeholder.append(g.name)   # hub shows the accent placeholder
                print(f"  no image source (placeholder card): {g.name}")
            continue
        if render(srcs[0][0], srcs[0][1], out, args.at):
            built.append(g.name)
            print(f"  OK  {g.name}.jpg  ({out.stat().st_size/1024:.0f} KB)")

    # --- distinctness pass -------------------------------------------------
    # Several guides legitimately draw on the SAME source clips (the Mastery
    # programs are compilations of other guides' movements). Sampling a
    # different timestamp of the same clip still reads as "the same picture",
    # so the rule is: every card must use a distinct (source image, offset)
    # pair, preferring images that guide owns outright.
    OFFSETS = (0.3, 0.6, 0.15, 0.45, 0.8)
    src_hash = {}
    for name, srcs in sources.items():
        src_hash[name] = [hashlib.md5(p if isinstance(p, bytes) else p.read_bytes()).hexdigest()[:12]
                          for _, p in srcs]

    order = sorted(sources, key=lambda n: (-len(src_hash[n]), n))
    used_combos = set()
    combos = {}
    for name in order:
        best = None
        for idx in range(len(sources[name])):
            for off in OFFSETS:
                combo = (src_hash[name][idx], round(off, 2))
                if combo not in used_combos:
                    best = (idx, off, combo)
                    break
            if best:
                break
        if best:
            used_combos.add(best[2])
            combos[name] = best

    fixed = []
    for name, (idx, off, _) in combos.items():
        p = THUMBS / f"{name}.jpg"
        if not p.exists() or not built or name not in built:
            continue
        kind, payload = sources[name][idx]
        if render(kind, payload, p, off):
            fixed.append(name)

    # safety net: if two outputs look similar, re-render the loser from whichever
    # of its own frames is MOST visually distinct from the rest of the library
    # (a different timestamp of a shared clip is still "the same picture").
    def sig(path):
        im = Image.open(path).convert("L").resize((8, 8))
        return tuple(list(im.getdata()))

    def dist(a, b):
        return sum(abs(x - y) for x, y in zip(a, b))

    if Image is not None:
        sigs = {n: sig(THUMBS / f"{n}.jpg") for n in combos if (THUMBS / f"{n}.jpg").exists()}
        names_sorted = sorted(sigs)
        for i in range(len(names_sorted)):
            for j in range(i + 1, len(names_sorted)):
                a, b = names_sorted[i], names_sorted[j]
                if dist(sigs[a], sigs[b]) >= 48:
                    continue
                loser = b
                p = THUMBS / f"{loser}.jpg"
                others = [s for n, s in sigs.items() if n != loser]
                best = None
                for idx in range(len(sources[loser])):
                    for off in OFFSETS:
                        kind, payload = sources[loser][idx]
                        cand = Path("/tmp/_thumb_candidate.jpg")
                        if not render(kind, payload, cand, off):
                            continue
                        s = sig(cand)
                        score = min(dist(s, o) for o in others)
                        if best is None or score > best[0]:
                            best = (score, idx, off, s)
                if best and best[0] > dist(sigs[a], sigs[loser]):
                    score, idx, off, s = best
                    kind, payload = sources[loser][idx]
                    render(kind, payload, p, off)
                    sigs[loser] = s
                    print(f"  visually de-duped {loser}.jpg vs {a} "
                          f"(img {idx}, offset {off}, separation {score})")

    final = {}
    for p in sorted(THUMBS.glob("*.jpg")):
        final.setdefault(digest(p), []).append(p.stem)
    collisions = {k: v for k, v in final.items() if len(v) > 1}
    print(f"\nbuilt={len(built)} distinct-combos={len(fixed)} kept={len(kept)} "
          f"placeholder={len(placeholder)} | thumbs={len(list(THUMBS.glob('*.jpg')))} "
          f"guides={len(guides)}")
    if placeholder:
        print("placeholder cards:", ", ".join(placeholder))
    print("remaining byte-identical thumbnails:", collisions or "none")
    return 1 if collisions else 0


if __name__ == "__main__":
    sys.exit(main())
