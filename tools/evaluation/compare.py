import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--max-grounded-regression", type=float, default=0.05)
    parser.add_argument("--require-gates", action="store_true")
    args = parser.parse_args()
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    for key in ("not_found_recall", "uncited_rate", "grounded_accuracy"):
        print(f"{key}: {baseline['metrics'].get(key)} -> {candidate['metrics'].get(key)}")
    metrics = candidate["metrics"]
    failures = []
    if args.require_gates and metrics.get("not_found_recall") != 1.0:
        failures.append("not_found_recall must equal 1.0")
    if args.require_gates and metrics.get("uncited_rate") != 0:
        failures.append("uncited_rate must equal 0")
    baseline_grounded = baseline["metrics"].get("grounded_accuracy")
    candidate_grounded = metrics.get("grounded_accuracy")
    if baseline_grounded is not None and candidate_grounded is not None:
        if candidate_grounded < baseline_grounded - args.max_grounded_regression:
            failures.append("grounded_accuracy regression exceeds allowed margin")
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
