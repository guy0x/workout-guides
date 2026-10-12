#!/usr/bin/env python3
"""verify_publication.py — layered, report-only publication verification.

Per catalog guide, checks in order:
  local_html      <repo>/<slug>/index.html exists
  local_gifs      every image referenced by the guide HTML exists locally
  github_contents GitHub contents API returns 200 for the guide directory
  pages_route     the live Pages child route returns 200 / 404 / 0 (timeout)
  icloud_mirror   the iCloud folder (per catalog icloud_path) has index.html

status:
  verified           local complete + GitHub 200 + Pages 200
  deployment_pending local complete + GitHub 200 but Pages not 200 yet
  failed             local files or GitHub layer broken

A GitHub contents 200 alone NEVER makes a guide live. Report-only: writes
--report and nothing else (--update-cache additionally refreshes
data/pages-statuses.json for build_catalog).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_catalog import GIF_SRC_RE, check_pages  # noqa: E402


def local_layers(repo: Path, slug: str) -> tuple[bool, bool]:
    gdir = repo / slug
    index = gdir / "index.html"
    if not index.is_file():
        return False, False
    html = index.read_text(encoding="utf-8", errors="replace")
    gifs_ok = all((gdir / src).is_file() for src in GIF_SRC_RE.findall(html))
    return True, gifs_ok


def github_check_default(url: str) -> int:
    """GitHub contents API status via gh (authed) or urllib fallback."""
    gh = subprocess.run(["gh", "api", "-i", url], capture_output=True, text=True)
    if gh.returncode == 0 and gh.stdout:
        m = [ln for ln in gh.stdout.splitlines() if ln.startswith("HTTP/")]
        if m:
            try:
                return int(m[-1].split()[1])
            except (IndexError, ValueError):
                pass
    req = urllib.request.Request(url, headers={"User-Agent": "wg-verify/1",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def classify(layers: dict) -> str:
    if not (layers.get("local_html") and layers.get("local_gifs")):
        return "failed"
    if layers.get("github_contents") != 200:
        return "failed"
    if layers.get("pages_route") == 200:
        return "verified"
    return "deployment_pending"


def build_report(repo: Path, catalog: dict, icloud_root: Path, pages_base: str,
                 pages_check=None, github_check=None, github_owner_repo=None) -> dict:
    pages_check = pages_check or (lambda slug, base: check_pages(f"{base}/{slug}/"))
    github_check = github_check or github_check_default
    base = pages_base.rstrip("/")

    entries = []
    guides = catalog.get("guides", [])
    for g in guides:
        slug = g["id"]
        local_html, local_gifs = local_layers(Path(repo), slug)
        api = (f"https://api.github.com/repos/{github_owner_repo}/contents/{slug}/index.html"
               if github_owner_repo else
               f"https://api.github.com/repos/OWNER/REPO/contents/{slug}/index.html")
        github = github_check(api)
        pages = pages_check(slug, base)
        icloud_path = g.get("icloud_path")
        icloud_ok = bool(icloud_path) and (Path(icloud_root) / icloud_path / "index.html").is_file()
        layers = {"local_html": local_html, "local_gifs": local_gifs,
                  "github_contents": github, "pages_route": pages,
                  "icloud_mirror": icloud_ok}
        entries.append({"id": slug, **layers, "status": classify(layers),
                        "missing_mirror": not icloud_ok})

    counts = {"verified": sum(1 for e in entries if e["status"] == "verified"),
              "deployment_pending": sum(1 for e in entries if e["status"] == "deployment_pending"),
              "failed": sum(1 for e in entries if e["status"] == "failed")}
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages_base": base,
        "counts": counts,
        "missing_mirrors": sum(1 for e in entries if e["missing_mirror"]),
        "guides": entries,
    }


def git_owner_repo() -> str | None:
    proc = subprocess.run(["git", "remote", "get-url", "origin"],
                          cwd=Path(__file__).resolve().parent.parent,
                          capture_output=True, text=True)
    url = (proc.stdout or "").strip()
    m = (re.search(r"github\.com[:/](.+?/.+?)(?:\.git)?$", url))
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--catalog", default="data/guides.json")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--icloud",
                    default="/Users/guy/Library/Mobile Documents/com~apple~CloudDocs/Workout Guides")
    ap.add_argument("--pages-base", default="https://guides.guyovadia.com")
    ap.add_argument("--report", default="data/publication-report.json")
    ap.add_argument("--update-cache", action="store_true",
                    help="also refresh data/pages-statuses.json from this run")
    args = ap.parse_args()

    repo = Path(args.repo)
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    report = build_report(repo, catalog, Path(args.icloud), args.pages_base,
                          github_owner_repo=git_owner_repo())
    Path(args.report).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    c = report["counts"]
    print(f"publication: verified={c['verified']} deployment_pending={c['deployment_pending']} "
          f"failed={c['failed']} missing_mirrors={report['missing_mirrors']} -> {args.report}")
    if args.update_cache:
        cache = repo / "data" / "pages-statuses.json"
        codes = {e["id"]: e["pages_route"] for e in report["guides"]}
        cache.write_text(json.dumps(dict(sorted(codes.items())), indent=1) + "\n")
        print(f"refreshed {cache.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
