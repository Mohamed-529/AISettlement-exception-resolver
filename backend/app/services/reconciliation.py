"""
Deterministic reconciliation engine.

Takes normalized TransactionRecords from all three sources, groups them
by transaction_id (== payment_id), and decides for each payment whether
it MATCHED or has an EXCEPTION, and which kind.

This engine is intentionally rule-based and has no AI in it. It is the
baseline Phase 1 asks for: something we can trust and measure before an
LLM-based agent is layered on top in Phase 2.
"""

from datetime import datetime
from typing import List, Dict
from app.models.transaction import TransactionRecord, ReconciliationResult

# Amount drift below this (in rupees) is considered "rounding noise" and
# gets flagged AMBIGUOUS rather than a clear AMOUNT_MISMATCH.
SMALL_AMOUNT_THRESHOLD = 5.0


def _parse_date(d: str):
    return datetime.strptime(d, "%Y-%m-%d")


def _group_by_transaction_id(records: List[TransactionRecord]) -> Dict[str, List[TransactionRecord]]:
    groups: Dict[str, List[TransactionRecord]] = {}
    for r in records:
        groups.setdefault(r.transaction_id, []).append(r)
    return groups


def reconcile(normalized: dict) -> List[ReconciliationResult]:
    """
    normalized: output of normalizer.normalize_all(), i.e.
        {"payment": [...], "bank": [...], "ledger": [...]}

    Every payment_id present in the "payment" source gets exactly one
    ReconciliationResult. Payments are the anchor because in this
    domain nothing gets reconciled without first having been charged.
    """
    payments = normalized["payment"]
    bank_by_id = _group_by_transaction_id(normalized["bank"])
    ledger_by_id = _group_by_transaction_id(normalized["ledger"])

    results = []

    for payment in payments:
        pid = payment.transaction_id
        bank_records = bank_by_id.get(pid, [])
        ledger_records = ledger_by_id.get(pid, [])

        bank_amount = bank_records[0].amount if bank_records else None
        ledger_amount = ledger_records[0].amount if ledger_records else None
        bank_date = bank_records[0].date if bank_records else None
        ledger_date = ledger_records[0].date if ledger_records else None

        # --- Structural exceptions first: these override everything else ---
        if len(bank_records) > 1:
            results.append(ReconciliationResult(
                payment_id=pid,
                payment_amount=payment.amount,
                bank_amount=bank_amount,
                ledger_amount=ledger_amount,
                payment_date=payment.date,
                bank_date=bank_date,
                ledger_date=ledger_date,
                status="EXCEPTION",
                exception_type="POSSIBLE_DUPLICATE",
                notes=f"{len(bank_records)} bank transactions reference this payment",
                duplicate_count=len(bank_records),
            ))
            continue

        if not bank_records:
            results.append(ReconciliationResult(
                payment_id=pid,
                payment_amount=payment.amount,
                bank_amount=None,
                ledger_amount=ledger_amount,
                payment_date=payment.date,
                bank_date=None,
                ledger_date=ledger_date,
                status="EXCEPTION",
                exception_type="BANK_RECORD_MISSING",
                notes="no bank transaction found for this payment",
            ))
            continue

        if not ledger_records:
            results.append(ReconciliationResult(
                payment_id=pid,
                payment_amount=payment.amount,
                bank_amount=bank_amount,
                ledger_amount=None,
                payment_date=payment.date,
                bank_date=bank_date,
                ledger_date=None,
                status="EXCEPTION",
                exception_type="LEDGER_RECORD_MISSING",
                notes="no ledger entry found for this payment",
            ))
            continue

        # --- All three sources present: compare amounts and dates ---
        diff_bank = round(bank_amount - payment.amount, 2)
        diff_ledger = round(ledger_amount - payment.amount, 2)
        date_diff_days = abs((_parse_date(bank_date) - _parse_date(payment.date)).days)

        amounts_all_equal = diff_bank == 0 and diff_ledger == 0

        if amounts_all_equal and date_diff_days == 0:
            results.append(ReconciliationResult(
                payment_id=pid,
                payment_amount=payment.amount,
                bank_amount=bank_amount,
                ledger_amount=ledger_amount,
                payment_date=payment.date,
                bank_date=bank_date,
                ledger_date=ledger_date,
                status="MATCHED",
                exception_type=None,
            ))
            continue

        if amounts_all_equal and date_diff_days > 0:
            results.append(ReconciliationResult(
                payment_id=pid,
                payment_amount=payment.amount,
                bank_amount=bank_amount,
                ledger_amount=ledger_amount,
                payment_date=payment.date,
                bank_date=bank_date,
                ledger_date=ledger_date,
                status="EXCEPTION",
                exception_type="DATE_MISMATCH",
                notes=f"amounts agree; bank settlement delayed {date_diff_days} day(s)",
            ))
            continue

        max_abs_diff = max(abs(diff_bank), abs(diff_ledger))

        if max_abs_diff <= SMALL_AMOUNT_THRESHOLD:
            results.append(ReconciliationResult(
                payment_id=pid,
                payment_amount=payment.amount,
                bank_amount=bank_amount,
                ledger_amount=ledger_amount,
                payment_date=payment.date,
                bank_date=bank_date,
                ledger_date=ledger_date,
                status="EXCEPTION",
                exception_type="AMBIGUOUS",
                difference=max_abs_diff,
                notes="small multi-field drift; needs review before auto-resolving",
            ))
            continue

        results.append(ReconciliationResult(
            payment_id=pid,
            payment_amount=payment.amount,
            bank_amount=bank_amount,
            ledger_amount=ledger_amount,
            payment_date=payment.date,
            bank_date=bank_date,
            ledger_date=ledger_date,
            status="EXCEPTION",
            exception_type="AMOUNT_MISMATCH",
            difference=diff_bank if abs(diff_bank) >= abs(diff_ledger) else diff_ledger,
            notes="amount disagreement between sources",
        ))

    return results


# Exception types the deterministic engine is confident enough to
# auto-resolve without human/AI review. DATE_MISMATCH is safe because
# amounts already agree across all three sources — the only issue is a
# delayed bank settlement, which is a known, benign pattern.
AUTO_RESOLVABLE_TYPES = {"DATE_MISMATCH"}


def is_auto_resolved(result: ReconciliationResult) -> bool:
    return result.status == "EXCEPTION" and result.exception_type in AUTO_RESOLVABLE_TYPES
