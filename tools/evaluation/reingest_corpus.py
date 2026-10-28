"""Requeue every corpus document for a new chunking configuration."""

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--cookie", default="")
    args = parser.parse_args()
    for path in sorted(Path(args.corpus).glob("*.pdf")):
        request = Request(
            f"{args.base_url.rstrip('/')}/api/v1/documents",
            data=path.read_bytes(),
            method="POST",
            headers={"Cookie": args.cookie, "Content-Type": "application/pdf", "X-Filename": path.name},
        )
        with urlopen(request) as response:
            print(json.dumps({"file": path.name, "status": response.status}))


if __name__ == "__main__":
    main()
