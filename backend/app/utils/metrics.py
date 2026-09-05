"""
Computes the numbers Phase 1 needs to report:

- Total records processed
- Match rate
- Accuracy against known ground truth
- Automatically resolved cases
- Unresolved exceptions

Nothing here should ever be a made-up percentage — every number is
derived directly from the reconciliation results and the ground truth
file.
"""

from typing import List, Dict
from app.models.transaction import ReconciliationResult
from app.services.reconciliation import is_auto_resolved


def basic_metrics(results: List[ReconciliationResult]) -> dict:
    total = len(results)
    matched = sum(1 for r in results if r.status == "MATCHED")
    exceptions = total - matched
    auto_resolved = sum(1 for r in results if is_auto_resolved(r))
    unresolved = exceptions - auto_resolved

    return {
        "total_records": total,
        "matched": matched,
        "exceptions": exceptions,
        "match_rate": round(matched / total * 100, 2) if total else 0.0,
        "auto_resolved": auto_resolved,
        "unresolved_exceptions": unresolved,
    }


def exception_breakdown(results: List[ReconciliationResult]) -> Dict[str, int]:
    breakdown: Dict[str, int] = {}
    for r in results:
        if r.exception_type:
            breakdown[r.exception_type] = breakdown.get(r.exception_type, 0) + 1
    return dict(sorted(breakdown.items(), key=lambda kv: -kv[1]))


def accuracy_against_ground_truth(results: List[ReconciliationResult], ground_truth_rows: List[dict]) -> dict:
    """
    Compares engine output to ground_truth.csv and returns accuracy plus
    the list of specific misclassifications, so we never have to just
    assert a number without evidence.
    """
    truth_by_id = {row["payment_id"]: row for row in ground_truth_rows}
    results_by_id = {r.payment_id: r for r in results}

    correct = 0
    incorrect = 0
    mismatches = []

    for pid, truth in truth_by_id.items():
        result = results_by_id.get(pid)
        if result is None:
            incorrect += 1
            mismatches.append({
                "payment_id": pid,
                "expected_status": truth["expected_status"],
                "expected_exception_type": truth["expected_exception_type"],
                "actual_status": "MISSING",
                "actual_exception_type": "MISSING",
            })
            continue

        expected_status = truth["expected_status"]
        expected_exc = truth["expected_exception_type"] or None
        actual_exc = result.exception_type

        is_correct = (result.status == expected_status) and (actual_exc == expected_exc)

        if is_correct:
            correct += 1
        else:
            incorrect += 1
            mismatches.append({
                "payment_id": pid,
                "expected_status": expected_status,
                "expected_exception_type": expected_exc,
                "actual_status": result.status,
                "actual_exception_type": actual_exc,
            })

    total = correct + incorrect
    return {
        "total_compared": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": round(correct / total * 100, 2) if total else 0.0,
        "mismatches": mismatches,
    }


def full_report(results: List[ReconciliationResult], ground_truth_rows: List[dict]) -> dict:
    return {
        "metrics": basic_metrics(results),
        "exception_breakdown": exception_breakdown(results),
        "ground_truth_comparison": accuracy_against_ground_truth(results, ground_truth_rows),
    }
