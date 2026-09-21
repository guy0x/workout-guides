#!/usr/bin/env python3
"""add_back_links.py — Inject a "← Card directory" back link into every guide's index.html.

Adds:
  1. A back link in the <nav> (first item) — "← Cards"
  2. A back link in the <footer> — "← Back to Cards"
Idempotent: skips guides already having the marker. Dry-run with --dry.
"""
import argparse
import re
from pathlib import Path

REPO = Path("/Users/guy/tmp_work/workout-guides")
MARKER = "card-dir-link"

NAV_BACK = '<a href="../cards.html" class="card-dir-link" style="background:#10b981;color:#fff;font-weight:700">← Cards</a>'
FOOT_BACK = '<span class="card-dir-link"><a href="../cards.html" style="color:#34d399;text-decoration:underline">← Card directory</a></span>'

# For the root-level cards.html we don't add back-links (it's the directory itself)
SKIP = {"cards.html"}


def process_file(path: Path, dry: bool) -> bool:
    txt = path.read_text(encoding="utf-8")
    if MARKER in txt:
        return False  # already has back link
    orig = txt

    # 1) nav injection — insert at the start of <nav ...>
    nav_re = re.compile(r"(<nav[^>]*>)(.*?)(</nav>)", re.S)
    m = nav_re.search(txt)
    if m:
        open_tag, inner, close_tag = m.groups()
        inner = NAV_BACK + inner
        txt = txt[:m.start()] + open_tag + inner + close_tag + txt[m.end():]
    else:
        # no nav — inject right after <header> block (before container)
        txt = txt.replace("</header>", "</header>\n" + NAV_BACK.replace('../', '') + "\n", 1)

    # 2) footer injection — before </footer>
    foot_re = re.compile(r"(<footer[^>]*>)(.*?)(</footer>)", re.S)
    m = foot_re.search(txt)
    if m:
        open_tag, inner, close_tag = m.groups()
        txt = txt[:m.start()] + open_tag + inner + FOOT_BACK + close_tag + txt[m.end():]

    if txt == orig:
        return False
    if dry:
        return True
    path.write_text(txt, encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    updated, skipped = [], []
    for d in sorted(REPO.iterdir()):
        if not d.is_dir():
            continue
        idx = d / "index.html"
        if not idx.exists():
            continue
        if process_file(idx, args.dry):
            updated.append(d.name)
        else:
            skipped.append(d.name)

    print(f"dry={args.dry} updated={len(updated)} skipped_already={len(skipped)}")
    for u in updated:
        print(f"  U {u}")


if __name__ == "__main__":
    main()
