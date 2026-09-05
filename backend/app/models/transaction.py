"""
Normalized internal representation of a financial record.

Every record coming from any of the three sources (payment platform,
bank, merchant ledger) gets converted into one of these before the
reconciliation engine ever touches it.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TransactionRecord:
    # The canonical identifier we reconcile on. For all three sources
    # this resolves to the payment_id (payments.payment_id,
    # bank.reference_id, ledger.payment_id).
    transaction_id: str

    # Which source this record came from: "payment" | "bank" | "ledger"
    source: str

    amount: float
    date: str

    # Source-specific native id, kept for traceability
    # (payment_id / bank_transaction_id / ledger_id)
    native_id: str

    currency: Optional[str] = None
    status: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "source": self.source,
            "amount": self.amount,
            "date": self.date,
            "native_id": self.native_id,
            "currency": self.currency,
            "status": self.status,
            **self.extra,
        }


@dataclass
class ReconciliationResult:
    payment_id: str
    payment_amount: Optional[float]
    bank_amount: Optional[float]
    ledger_amount: Optional[float]
    payment_date: Optional[str]
    bank_date: Optional[str]
    ledger_date: Optional[str]
    status: str  # "MATCHED" | "EXCEPTION"
    exception_type: Optional[str]
    difference: Optional[float] = None
    notes: Optional[str] = None
    duplicate_count: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "payment_amount": self.payment_amount,
            "bank_amount": self.bank_amount,
            "ledger_amount": self.ledger_amount,
            "payment_date": self.payment_date,
            "bank_date": self.bank_date,
            "ledger_date": self.ledger_date,
            "status": self.status,
            "exception_type": self.exception_type,
            "difference": self.difference,
            "notes": self.notes,
            "duplicate_count": self.duplicate_count,
        }
