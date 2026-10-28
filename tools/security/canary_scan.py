"""Scan exported operational artifacts for a canary value.

The script deliberately scans only supplied files; it never fetches logs or
credentials. CI passes sanitized log, analytics, and trace exports to it.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canary", required=True)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    leaks = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if path.is_file() and args.canary in path.read_text(encoding="utf-8", errors="replace"):
            leaks.append(str(path))
    for leak in leaks:
        print(f"CANARY_FOUND {leak}")
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
