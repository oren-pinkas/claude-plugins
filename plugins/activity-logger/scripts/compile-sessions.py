#!/usr/bin/env python3
"""Compile session logs for a date range into structured JSON for the activity-report skill.

Usage:
    compile-sessions.py <start-date> [<end-date>]
    compile-sessions.py today | yesterday | this-week | last-week | this-month

Output: JSON to stdout with this shape:
{
  "date_range": {"start": "2026-04-20", "end": "2026-04-20"},
  "stats": {"total_sessions": 5, "unique_sessions": 3, "duplicates_removed": 2, ...},
  "projects": {
    "my-project": {
      "sessions": [ {frontmatter fields + "narrative": "..."} ],
      "totals": {"files_changed": 10, "insertions": 200, "deletions": 50}
    }
  }
}
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional


LOG_DIR = os.path.expanduser("~/claude-activity-log")


def resolve_date_range(arg: str, end_arg: Optional[str] = None) -> tuple:
    today = date.today()
    shorthands = {
        "today": (today, today),
        "yesterday": (today - timedelta(days=1), today - timedelta(days=1)),
        "this-week": (today - timedelta(days=today.weekday()), today),
        "last-week": (
            today - timedelta(days=today.weekday() + 7),
            today - timedelta(days=today.weekday() + 1),
        ),
        "this-month": (today.replace(day=1), today),
    }
    if arg in shorthands:
        return shorthands[arg]

    if ".." in arg:
        start_s, end_s = arg.split("..", 1)
        return date.fromisoformat(start_s), date.fromisoformat(end_s)

    start = date.fromisoformat(arg)
    end = date.fromisoformat(end_arg) if end_arg else start
    return start, end


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not m:
        return {}, text

    fm_raw, narrative = m.group(1), m.group(2).strip()
    fm = {}
    for line in fm_raw.split("\n"):
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"')
        if val in ("true", "false"):
            fm[key] = val == "true"
        elif val == "[]":
            fm[key] = []
        elif re.match(r"^\d+$", val):
            fm[key] = int(val)
        else:
            fm[key] = val
    return fm, narrative


def date_range_days(start: date, end: date) -> list[str]:
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def read_sessions(start: date, end: date) -> list[dict]:
    sessions = []
    for day_str in date_range_days(start, end):
        day_dir = os.path.join(LOG_DIR, day_str)
        if not os.path.isdir(day_dir):
            continue
        for fname in sorted(os.listdir(day_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(day_dir, fname)
            with open(fpath) as f:
                content = f.read()
            fm, narrative = parse_frontmatter(content)
            if not fm:
                continue
            fm["narrative"] = narrative
            fm["_source_file"] = fpath
            sessions.append(fm)
    return sessions


def dedup_sessions(sessions: list[dict]) -> tuple[list[dict], int]:
    seen: dict[str, dict] = {}
    for s in sessions:
        sid = s.get("session_id", "")
        if sid not in seen:
            seen[sid] = s
            continue
        existing = seen[sid]
        if not existing.get("processed") and s.get("processed"):
            seen[sid] = s
        elif existing.get("processed") == s.get("processed"):
            if len(s.get("narrative", "")) > len(existing.get("narrative", "")):
                seen[sid] = s
    deduped = list(seen.values())
    return deduped, len(sessions) - len(deduped)


def group_by_project(sessions: list[dict]) -> dict:
    projects = defaultdict(lambda: {"sessions": [], "totals": {"files_changed": 0, "insertions": 0, "deletions": 0}})
    for s in sessions:
        pname = s.get("project_name", "unknown")
        projects[pname]["sessions"].append(s)
        projects[pname]["totals"]["files_changed"] += s.get("files_changed", 0)
        projects[pname]["totals"]["insertions"] += s.get("insertions", 0)
        projects[pname]["totals"]["deletions"] += s.get("deletions", 0)
    return dict(projects)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <date-range>", file=sys.stderr)
        sys.exit(1)

    end_arg = sys.argv[2] if len(sys.argv) > 2 else None
    start, end = resolve_date_range(sys.argv[1], end_arg)

    all_sessions = read_sessions(start, end)
    deduped, dups_removed = dedup_sessions(all_sessions)
    grouped = group_by_project(deduped)

    result = {
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "stats": {
            "total_sessions": len(all_sessions),
            "unique_sessions": len(deduped),
            "duplicates_removed": dups_removed,
            "projects": list(grouped.keys()),
        },
        "projects": grouped,
    }

    json.dump(result, sys.stdout, indent=2, default=str)


if __name__ == "__main__":
    main()
