"""Run a user access review from the command line: python -m app.cli [--as-of YYYY-MM-DD]"""
import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from app.checks import ReviewContext
from app.config import BACKEND_DIR, ReviewConfig
from app.data_loading import load_review_data
from app.review import run_all_checks, summarize


def main():
    parser = argparse.ArgumentParser(description="Run all AccessGuard audit checks on a folder of CSVs.")
    parser.add_argument("--data-dir", type=Path, default=BACKEND_DIR / "data")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="Date the data was extracted; used for dormancy (default: today)")
    parser.add_argument("--output", type=Path, default=BACKEND_DIR / "output" / "findings.csv")
    args = parser.parse_args()

    hr, systems = load_review_data(args.data_dir)
    context = ReviewContext(hr, systems, ReviewConfig(as_of_date=args.as_of))
    findings = run_all_checks(context)
    summary = summarize(findings)

    print(f"Reviewed {len(hr)} HR records and {sum(len(df) for df in systems.values())} accounts "
          f"across {len(systems)} systems (as of {args.as_of}).\n")
    print(f"Total findings: {summary['total']}")
    print("\nBy risk:")
    for risk, count in summary["by_risk"].items():
        print(f"  {risk:15s} {count:4d}")
    print("\nBy check:")
    for check, count in summary["by_check"].items():
        print(f"  {check:35s} {count:4d}")
    print("\nBy system:")
    for system, count in summary["by_system"].items():
        print(f"  {system:35s} {count:4d}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([f.to_dict() for f in findings]).to_csv(args.output, index=False)
    print(f"\nFull findings written to {args.output}")


if __name__ == "__main__":
    main()
