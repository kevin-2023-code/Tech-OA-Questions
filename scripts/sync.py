#!/usr/bin/env python3
"""Regenerate the repository from TrueInterview's public catalog.

    python3 scripts/sync.py                         # read the live API, write what changed
    python3 scripts/sync.py --check                 # exit 1 if anything WOULD change
    python3 scripts/sync.py --snapshot-out s.json   # also save what was read
    python3 scripts/sync.py --catalog-file s.json   # render from a saved read, no network

The whole repository is rendered in memory first. If any page is over its byte
budget or any relative link points at a file that would not exist, NOTHING is
written and the run fails: a scheduled job that quietly published a truncated
or broken README at 3am is the failure this script exists to prevent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api  # noqa: E402
import build  # noqa: E402
import model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

#: Every directory the sync owns. A file in one of these that the render did not
#: produce is an orphan (a company that lost its last question, a list that fell
#: under the minimum) and is deleted. Nothing outside them is ever touched.
GENERATED_DIRS = ("lists", "rounds", "formats", "companies", "question-bank", "data")
GENERATED_FILES = ("README.md",)

#: Hand-written files a generated page may link to.
STATIC_FILES = ("CONTRIBUTING.md", "LICENSE", "assets/practice.svg", "assets/free.svg")

LINK = re.compile(r"\]\(([^)\s]+)\)|^\[[a-z]\]:\s*(\S+)", re.MULTILINE)


def broken_links(files: dict[str, str]) -> list[str]:
    """Relative links that would not resolve once ``files`` are written."""
    present = set(files) | set(STATIC_FILES)
    problems = []
    for path, text in files.items():
        if not path.endswith(".md"):
            continue
        base = os.path.dirname(path)
        for match in LINK.finditer(text):
            target = match.group(1) or match.group(2)
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            resolved = os.path.normpath(os.path.join(base, target.split("#", 1)[0]))
            if resolved not in present:
                problems.append(f"{path} → {target}")
    return problems


def plan(files: dict[str, str]) -> tuple[dict[str, str], list[Path]]:
    """``(to_write, to_delete)`` against what is on disk."""
    writes = {}
    for path, text in files.items():
        target = ROOT / path
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            writes[path] = text
    deletes = []
    for directory in GENERATED_DIRS:
        folder = ROOT / directory
        if not folder.exists():
            continue
        for file in sorted(folder.rglob("*")):
            if file.is_file() and file.relative_to(ROOT).as_posix() not in files:
                deletes.append(file)
    return writes, deletes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=os.environ.get("TRUEINTERVIEW_BASE_URL", api.DEFAULT_BASE_URL))
    parser.add_argument("--catalog-file", help="render from a saved snapshot instead of the API")
    parser.add_argument("--snapshot-out", help="save the snapshot that was read")
    parser.add_argument("--today", help="YYYY-MM-DD; defaults to today in UTC")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if anything would change")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.catalog_file:
            snapshot = json.loads(Path(args.catalog_file).read_text(encoding="utf-8"))
            api.check_questions(snapshot["questions"])
        else:
            snapshot = api.fetch_snapshot(args.base_url)
    except (api.CatalogError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"sync: could not read the catalog — nothing written. {error}", file=sys.stderr)
        return 2

    if args.snapshot_out:
        Path(args.snapshot_out).write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    today = date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    catalog = model.load(snapshot)
    files = build.build(catalog, today)

    problems = build.over_budget(files) + [f"broken link: {p}" for p in broken_links(files)]
    if problems:
        print("sync: refusing to write —", *problems[:40], sep="\n  ", file=sys.stderr)
        return 3

    writes, deletes = plan(files)
    future = [q.slug for q in catalog.questions if model.is_future(q, today)]
    summary = (
        f"{len(catalog.questions):,} questions · {len(writes)} file(s) changed · {len(deletes)} removed"
        + (f" · future-dated upstream (shown undated): {', '.join(future[:5])}" if future else "")
    )

    if args.check:
        if writes or deletes:
            print(f"sync --check: out of date — {summary}", file=sys.stderr)
            for path in list(writes)[:20]:
                print(f"  ~ {path}", file=sys.stderr)
            for file in deletes[:20]:
                print(f"  - {file.relative_to(ROOT)}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"sync --check: up to date — {summary}")
        return 0

    for path, text in writes.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for file in deletes:
        file.unlink()
    if not args.quiet:
        print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
