"""
Phase 1 pipeline runner.

    Data Loader -> Normalizer -> Reconciliation Engine -> Metrics -> Report

Run from the backend/ directory:

    python -m app.main --data ../data
"""

import argparse
import json
import os
import sys

from app.services import data_loader, normalizer, reconciliation
from app.utils import metrics as metrics_utils


def run(data_dir: str) -> dict:
    raw = data_loader.load_all(data_dir)
    normalized = normalizer.normalize_all(raw)
    results = reconciliation.reconcile(normalized)
    report = metrics_utils.full_report(results, raw["ground_truth"])
    return {"results": results, "report": report}


def print_report(report: dict):
    m = report["metrics"]
    gt = report["ground_truth_comparison"]

    print("=" * 50)
    print("AI FINANCE CONTROLLER — PHASE 1 RECONCILIATION REPORT")
    print("=" * 50)
    print(f"Total records processed:   {m['total_records']}")
    print(f"Matched:                   {m['matched']}")
    print(f"Exceptions:                {m['exceptions']}")
    print(f"Match rate:                {m['match_rate']}%")
    print(f"Automatically resolved:    {m['auto_resolved']}")
    print(f"Unresolved exceptions:     {m['unresolved_exceptions']}")
    print()
    print("Exception breakdown:")
    for exc_type, count in report["exception_breakdown"].items():
        print(f"  {exc_type:<22} {count}")
    print()
    print("Ground truth comparison:")
    print(f"  Correct classifications:   {gt['correct']}")
    print(f"  Incorrect classifications: {gt['incorrect']}")
    print(f"  Accuracy:                  {gt['accuracy']}%")
    if gt["mismatches"]:
        print()
        print(f"  {len(gt['mismatches'])} misclassification(s):")
        for mm in gt["mismatches"][:15]:
            print(f"   - {mm['payment_id']}: expected "
                  f"{mm['expected_status']}/{mm['expected_exception_type']} "
                  f"got {mm['actual_status']}/{mm['actual_exception_type']}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Run Phase 1 reconciliation pipeline")
    parser.add_argument("--data", type=str, default="../data", help="Path to data directory")
    parser.add_argument("--json-out", type=str, default=None,
                         help="Optional path to write full results+report as JSON")
    args = parser.parse_args()

    outcome = run(args.data)
    print_report(outcome["report"])

    if args.json_out:
        payload = {
            "report": outcome["report"],
            "results": [r.to_dict() for r in outcome["results"]],
        }
        with open(args.json_out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\nFull results written to {args.json_out}")


if __name__ == "__main__":
    main()
