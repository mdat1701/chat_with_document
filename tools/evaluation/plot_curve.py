from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = []
    for filename in args.reports:
        report = json.loads(Path(filename).read_text(encoding="utf-8"))
        rows.append((report.get("tau", Path(filename).stem), report["metrics"]))
    rows.sort(key=lambda row: float(row[0]))
    table = "".join(
        f"<tr><td>{html.escape(str(tau))}</td><td>{metrics.get('not_found_recall')}</td>"
        f"<td>{metrics.get('false_not_found_rate')}</td><td>{metrics.get('uncited_rate')}</td></tr>"
        for tau, metrics in rows
    )
    Path(args.out).write_text(
        "<html><body><h1>Retrieval threshold sweep</h1>"
        "<table><tr><th>tau</th><th>not_found_recall</th>"
        "<th>false_not_found_rate</th><th>uncited_rate</th></tr>"
        f"{table}</table></body></html>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
