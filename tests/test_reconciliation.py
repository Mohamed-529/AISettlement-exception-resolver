"""
Unit tests for the deterministic reconciliation engine.

Run from backend/ directory:
    python -m pytest ../tests -v
(or add backend/ to PYTHONPATH)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.models.transaction import TransactionRecord
from app.services import reconciliation
from app.utils import metrics as metrics_utils


def _norm(payment_rows, bank_rows, ledger_rows):
    return {"payment": payment_rows, "bank": bank_rows, "ledger": ledger_rows}


def test_exact_match():
    normalized = _norm(
        [TransactionRecord("P001", "payment", 5000, "2026-08-20", "P001")],
        [TransactionRecord("P001", "bank", 5000, "2026-08-20", "B001")],
        [TransactionRecord("P001", "ledger", 5000, "2026-08-20", "L001")],
    )
    results = reconciliation.reconcile(normalized)
    assert len(results) == 1
    assert results[0].status == "MATCHED"
    assert results[0].exception_type is None


def test_amount_mismatch():
    normalized = _norm(
        [TransactionRecord("P003", "payment", 7500, "2026-08-21", "P003")],
        [TransactionRecord("P003", "bank", 7000, "2026-08-21", "B003")],
        [TransactionRecord("P003", "ledger", 7500, "2026-08-21", "L003")],
    )
    results = reconciliation.reconcile(normalized)
    assert results[0].status == "EXCEPTION"
    assert results[0].exception_type == "AMOUNT_MISMATCH"
    assert results[0].difference == -500


def test_bank_missing():
    normalized = _norm(
        [TransactionRecord("P004", "payment", 3000, "2026-08-20", "P004")],
        [],
        [TransactionRecord("P004", "ledger", 3000, "2026-08-20", "L004")],
    )
    results = reconciliation.reconcile(normalized)
    assert results[0].exception_type == "BANK_RECORD_MISSING"


def test_ledger_missing():
    normalized = _norm(
        [TransactionRecord("P005", "payment", 3000, "2026-08-20", "P005")],
        [TransactionRecord("P005", "bank", 3000, "2026-08-20", "B005")],
        [],
    )
    results = reconciliation.reconcile(normalized)
    assert results[0].exception_type == "LEDGER_RECORD_MISSING"


def test_duplicate_bank_transaction():
    normalized = _norm(
        [TransactionRecord("P006", "payment", 2000, "2026-08-20", "P006")],
        [
            TransactionRecord("P006", "bank", 2000, "2026-08-20", "B006a"),
            TransactionRecord("P006", "bank", 2000, "2026-08-20", "B006b"),
        ],
        [TransactionRecord("P006", "ledger", 2000, "2026-08-20", "L006")],
    )
    results = reconciliation.reconcile(normalized)
    assert results[0].exception_type == "POSSIBLE_DUPLICATE"
    assert results[0].duplicate_count == 2


def test_date_mismatch_is_auto_resolvable():
    normalized = _norm(
        [TransactionRecord("P007", "payment", 4000, "2026-08-20", "P007")],
        [TransactionRecord("P007", "bank", 4000, "2026-08-24", "B007")],
        [TransactionRecord("P007", "ledger", 4000, "2026-08-20", "L007")],
    )
    results = reconciliation.reconcile(normalized)
    assert results[0].exception_type == "DATE_MISMATCH"
    assert reconciliation.is_auto_resolved(results[0]) is True


def test_ambiguous_small_drift_is_not_auto_resolved():
    normalized = _norm(
        [TransactionRecord("P008", "payment", 4000, "2026-08-20", "P008")],
        [TransactionRecord("P008", "bank", 4002, "2026-08-21", "B008")],
        [TransactionRecord("P008", "ledger", 4001, "2026-08-20", "L008")],
    )
    results = reconciliation.reconcile(normalized)
    assert results[0].exception_type == "AMBIGUOUS"
    assert reconciliation.is_auto_resolved(results[0]) is False


def test_basic_metrics_and_ground_truth_accuracy():
    normalized = _norm(
        [
            TransactionRecord("P001", "payment", 5000, "2026-08-20", "P001"),
            TransactionRecord("P002", "payment", 3000, "2026-08-20", "P002"),
        ],
        [
            TransactionRecord("P001", "bank", 5000, "2026-08-20", "B001"),
            TransactionRecord("P002", "bank", 2500, "2026-08-20", "B002"),
        ],
        [
            TransactionRecord("P001", "ledger", 5000, "2026-08-20", "L001"),
            TransactionRecord("P002", "ledger", 3000, "2026-08-20", "L002"),
        ],
    )
    results = reconciliation.reconcile(normalized)
    m = metrics_utils.basic_metrics(results)
    assert m["total_records"] == 2
    assert m["matched"] == 1
    assert m["exceptions"] == 1
    assert m["match_rate"] == 50.0

    ground_truth_rows = [
        {"payment_id": "P001", "expected_status": "MATCHED", "expected_exception_type": ""},
        {"payment_id": "P002", "expected_status": "EXCEPTION", "expected_exception_type": "AMOUNT_MISMATCH"},
    ]
    gt = metrics_utils.accuracy_against_ground_truth(results, ground_truth_rows)
    assert gt["accuracy"] == 100.0
    assert gt["mismatches"] == []
