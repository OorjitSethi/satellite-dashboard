#!/usr/bin/env python3
"""
Fetch TLEs from CelesTrak groups and build a 3-line TLE catalog file.
Uses the same CelesTrak API as the app backend.

Default output: ../data/tle_catalog.txt

Usage:
  python build_tle_catalog.py
  python build_tle_catalog.py --output /absolute/path/to/tle_catalog.txt

Environment:
  You can also set TLE_FILE to choose an output path.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests


GROUPS = [
    'active', 'stations', 'weather', 'noaa', 'goes', 'resource', 'sarsat',
    'dmc', 'tdrss', 'argos', 'planet', 'spire'
]

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"


def fetch_group_tle_text(group: str, timeout: int = 30) -> str:
    """Fetch a group's TLEs as raw 3-line blocks (name, 1, 2)."""
    params = {"GROUP": group, "FORMAT": "tle"}
    resp = requests.get(CELESTRAK_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.text or ""


def parse_tle_text_to_entries(tle_text: str) -> List[Tuple[str, str, str]]:
    """Parse raw TLE text into (name, line1, line2) tuples."""
    lines = [ln.strip() for ln in tle_text.splitlines() if ln.strip()]
    out: List[Tuple[str, str, str]] = []
    i = 0
    while i + 2 < len(lines):
        name = lines[i]
        l1 = lines[i + 1]
        l2 = lines[i + 2]
        if l1.startswith('1 ') and l2.startswith('2 '):
            out.append((name, l1, l2))
            i += 3
        else:
            # Try resync
            i += 1
    return out


def build_catalog(groups: List[str], sleep_secs: float = 0.5) -> Dict[str, dict]:
    """Return a dict keyed by NORAD_CAT_ID with name, line1, line2."""
    catalog: Dict[str, dict] = {}
    total_linesets = 0
    for i, group in enumerate(groups):
        try:
            print(f"[{i+1}/{len(groups)}] Fetching group '{group}' (FORMAT=tle)...")
            tle_text = fetch_group_tle_text(group)
            entries = parse_tle_text_to_entries(tle_text)
            print(f"  -> {len(entries)} TLE sets")
            total_linesets += len(entries)
            for name, l1, l2 in entries:
                norad = l1[2:7].strip()
                if not norad:
                    continue
                if norad not in catalog:
                    catalog[norad] = {
                        'name': name,
                        'line1': l1,
                        'line2': l2,
                    }
            time.sleep(sleep_secs)
        except Exception as e:
            print(f"  !! Error fetching group '{group}': {e}")
            continue
    print(f"Fetched {total_linesets} TLE sets across groups; unique by NORAD: {len(catalog)}")
    return catalog


def write_tle_file(catalog: Dict[str, dict], output_path: str) -> int:
    # Sort by satellite name for readability
    items = sorted(catalog.items(), key=lambda kv: kv[1]['name'])
    written = 0
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for _, sat in items:
            f.write(f"{sat['name']}\n")
            f.write(f"{sat['line1']}\n")
            f.write(f"{sat['line2']}\n")
            written += 1
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build local TLE catalog from CelesTrak groups")
    default_output = os.environ.get(
        'TLE_FILE',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'tle_catalog.txt'))
    )
    parser.add_argument('--output', '-o', default=default_output, help='Output path for tle_catalog.txt')
    parser.add_argument('--groups', '-g', nargs='*', default=GROUPS, help='CelesTrak groups to include')
    parser.add_argument('--sleep', type=float, default=0.5, help='Delay between group requests (seconds)')
    args = parser.parse_args(argv)

    start = datetime.now()
    print(f"Starting TLE catalog build at {start}")
    print(f"Output: {args.output}")
    print(f"Groups: {args.groups}")
    try:
        catalog = build_catalog(args.groups, sleep_secs=args.sleep)
        count = write_tle_file(catalog, args.output)
        end = datetime.now()
        print(f"\nWrote {count} TLEs to {args.output}")
        print(f"Done in {end - start}")
        return 0
    except Exception as e:
        print(f"Error building catalog: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
