"""
Normalization layer.

Each source has its own column names, id fields, and formats. This
module maps all three onto the common TransactionRecord shape so the
reconciliation engine never has to know where a field came from.

If a source is later swapped out (a new bank feed, a different ledger
export), only this file should need to change.
"""

from typing import List
from app.models.transaction import TransactionRecord


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Could not parse amount: {value!r}")


def normalize_payments(rows: List[dict]) -> List[TransactionRecord]:
    records = []
    for row in rows:
        records.append(TransactionRecord(
            transaction_id=row["payment_id"],
            source="payment",
            amount=_to_float(row["amount"]),
            date=row["payment_date"],
            native_id=row["payment_id"],
            currency=row.get("currency"),
            status=row.get("status"),
            extra={"customer_id": row.get("customer_id")},
        ))
    return records


def normalize_bank_transactions(rows: List[dict]) -> List[TransactionRecord]:
    records = []
    for row in rows:
        records.append(TransactionRecord(
            # Bank rows reference the payment via reference_id
            transaction_id=row["reference_id"],
            source="bank",
            amount=_to_float(row["amount"]),
            date=row["transaction_date"],
            native_id=row["bank_transaction_id"],
            extra={"transaction_type": row.get("transaction_type")},
        ))
    return records


def normalize_ledger(rows: List[dict]) -> List[TransactionRecord]:
    records = []
    for row in rows:
        records.append(TransactionRecord(
            transaction_id=row["payment_id"],
            source="ledger",
            amount=_to_float(row["amount"]),
            date=row["entry_date"],
            native_id=row["ledger_id"],
            extra={"invoice_id": row.get("invoice_id")},
        ))
    return records


def normalize_all(raw: dict) -> dict:
    """raw: output of data_loader.load_all()"""
    return {
        "payment": normalize_payments(raw["payments"]),
        "bank": normalize_bank_transactions(raw["bank_transactions"]),
        "ledger": normalize_ledger(raw["ledger"]),
    }
