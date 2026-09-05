"""
Synthetic financial data generator for the AI Finance Controller.

Generates three raw source files (payments, bank transactions, ledger)
that deliberately DON'T all agree with each other, plus a ground_truth.csv
that records what actually happened to every payment_id. The ground truth
is the answer key we use later to score both the deterministic engine
and the AI agent.

Usage:
    python scripts/generate_data.py [--count 100] [--seed 42] [--out data]
"""

import argparse
import csv
import os
import random
from datetime import datetime, timedelta

CURRENCY = "INR"
STATUS_CAPTURED = "captured"

# Scenario distribution (must sum to --count when using default of 100)
DEFAULT_DISTRIBUTION = {
    "MATCH": 60,
    "AMOUNT_MISMATCH": 10,
    "BANK_MISSING": 8,
    "LEDGER_MISSING": 7,
    "DUPLICATE": 5,
    "DATE_MISMATCH": 5,
    "AMBIGUOUS": 5,
}

BASE_DATE = datetime(2026, 8, 20)


def random_amount(rng: random.Random) -> int:
    # Round rupee amounts, weighted toward realistic small/medium transactions
    return rng.choice([
        rng.randint(100, 999),
        rng.randint(1000, 9999),
        rng.randint(10000, 49999),
    ])


def fmt_date(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def build_records(count: int, distribution: dict, seed: int):
    rng = random.Random(seed)

    payments = []
    bank_txns = []
    ledger_entries = []
    ground_truth = []

    # Expand the distribution into a flat, shuffled list of scenario labels
    scenarios = []
    for label, n in distribution.items():
        scenarios.extend([label] * n)
    if len(scenarios) != count:
        raise ValueError(
            f"Distribution sums to {len(scenarios)} but count is {count}. "
            "Adjust --count or the DEFAULT_DISTRIBUTION."
        )
    rng.shuffle(scenarios)

    bank_id_counter = 1
    ledger_id_counter = 1

    for i, scenario in enumerate(scenarios, start=1):
        pid = f"P{i:03d}"
        cid = f"C{rng.randint(1, 40):03d}"
        base_amount = random_amount(rng)
        pay_date = BASE_DATE + timedelta(days=rng.randint(0, 10))

        payments.append({
            "payment_id": pid,
            "customer_id": cid,
            "amount": base_amount,
            "payment_date": fmt_date(pay_date),
            "status": STATUS_CAPTURED,
            "currency": CURRENCY,
        })

        exception_type = None
        # NOTE: this must match the literal status strings the
        # reconciliation engine emits ("MATCHED" / "EXCEPTION"), not the
        # scenario label, so ground-truth comparison is a clean string match.
        expected_status = "MATCHED"
        notes = ""

        if scenario == "MATCH":
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": base_amount,
                "transaction_date": fmt_date(pay_date),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            ledger_entries.append({
                "ledger_id": f"L{ledger_id_counter:03d}",
                "payment_id": pid,
                "invoice_id": f"INV{i:03d}",
                "amount": base_amount,
                "entry_date": fmt_date(pay_date),
            })
            ledger_id_counter += 1

        elif scenario == "AMOUNT_MISMATCH":
            drift = rng.choice([-500, -250, -100, 100, 250, 500, 750])
            bank_amount = max(base_amount + drift, 1)
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": bank_amount,
                "transaction_date": fmt_date(pay_date),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            ledger_entries.append({
                "ledger_id": f"L{ledger_id_counter:03d}",
                "payment_id": pid,
                "invoice_id": f"INV{i:03d}",
                "amount": base_amount,
                "entry_date": fmt_date(pay_date),
            })
            ledger_id_counter += 1
            exception_type = "AMOUNT_MISMATCH"
            expected_status = "EXCEPTION"
            notes = f"bank amount off by {bank_amount - base_amount}"

        elif scenario == "BANK_MISSING":
            # No bank transaction at all for this payment
            ledger_entries.append({
                "ledger_id": f"L{ledger_id_counter:03d}",
                "payment_id": pid,
                "invoice_id": f"INV{i:03d}",
                "amount": base_amount,
                "entry_date": fmt_date(pay_date),
            })
            ledger_id_counter += 1
            exception_type = "BANK_RECORD_MISSING"
            expected_status = "EXCEPTION"
            notes = "no matching bank transaction found"

        elif scenario == "LEDGER_MISSING":
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": base_amount,
                "transaction_date": fmt_date(pay_date),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            # No ledger entry recorded
            exception_type = "LEDGER_RECORD_MISSING"
            expected_status = "EXCEPTION"
            notes = "no matching ledger entry found"

        elif scenario == "DUPLICATE":
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": base_amount,
                "transaction_date": fmt_date(pay_date),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            # Same reference charged twice on the bank side
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": base_amount,
                "transaction_date": fmt_date(pay_date),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            ledger_entries.append({
                "ledger_id": f"L{ledger_id_counter:03d}",
                "payment_id": pid,
                "invoice_id": f"INV{i:03d}",
                "amount": base_amount,
                "entry_date": fmt_date(pay_date),
            })
            ledger_id_counter += 1
            exception_type = "POSSIBLE_DUPLICATE"
            expected_status = "EXCEPTION"
            notes = "two bank transactions found for one payment"

        elif scenario == "DATE_MISMATCH":
            # Settlement lands a few days late but amount agrees
            settle_delay = rng.randint(2, 6)
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": base_amount,
                "transaction_date": fmt_date(pay_date + timedelta(days=settle_delay)),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            ledger_entries.append({
                "ledger_id": f"L{ledger_id_counter:03d}",
                "payment_id": pid,
                "invoice_id": f"INV{i:03d}",
                "amount": base_amount,
                "entry_date": fmt_date(pay_date),
            })
            ledger_id_counter += 1
            exception_type = "DATE_MISMATCH"
            expected_status = "EXCEPTION"
            notes = f"bank settlement delayed by {settle_delay} days"

        elif scenario == "AMBIGUOUS":
            # Small rounding-level amount drift on the bank side AND a
            # delayed settlement date, so no single rule cleanly explains
            # it. Also ledger sometimes disagrees by a trivial amount.
            # These are the cases a deterministic engine should flag
            # for review rather than auto-resolve.
            rounding_drift = rng.choice([-2, -1, 1, 2, 3])
            settle_delay = rng.randint(1, 3)
            bank_amount = base_amount + rounding_drift
            ledger_amount = base_amount + rng.choice([0, -1, 1])
            bank_txns.append({
                "bank_transaction_id": f"B{bank_id_counter:03d}",
                "reference_id": pid,
                "amount": bank_amount,
                "transaction_date": fmt_date(pay_date + timedelta(days=settle_delay)),
                "transaction_type": "credit",
            })
            bank_id_counter += 1
            ledger_entries.append({
                "ledger_id": f"L{ledger_id_counter:03d}",
                "payment_id": pid,
                "invoice_id": f"INV{i:03d}",
                "amount": ledger_amount,
                "entry_date": fmt_date(pay_date),
            })
            ledger_id_counter += 1
            exception_type = "AMBIGUOUS"
            expected_status = "EXCEPTION"
            notes = "small multi-field drift, needs human/AI judgement"

        ground_truth.append({
            "payment_id": pid,
            "expected_status": expected_status,
            "expected_exception_type": exception_type or "",
            "scenario": scenario,
            "notes": notes,
        })

    return payments, bank_txns, ledger_entries, ground_truth


def write_csv(path: str, rows: list, fieldnames: list):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic reconciliation data")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="data")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    payments, bank_txns, ledger_entries, ground_truth = build_records(
        args.count, DEFAULT_DISTRIBUTION, args.seed
    )

    write_csv(
        os.path.join(args.out, "payments.csv"),
        payments,
        ["payment_id", "customer_id", "amount", "payment_date", "status", "currency"],
    )
    write_csv(
        os.path.join(args.out, "bank_transactions.csv"),
        bank_txns,
        ["bank_transaction_id", "reference_id", "amount", "transaction_date", "transaction_type"],
    )
    write_csv(
        os.path.join(args.out, "ledger.csv"),
        ledger_entries,
        ["ledger_id", "payment_id", "invoice_id", "amount", "entry_date"],
    )
    write_csv(
        os.path.join(args.out, "ground_truth.csv"),
        ground_truth,
        ["payment_id", "expected_status", "expected_exception_type", "scenario", "notes"],
    )

    print(f"Generated {args.count} payment records -> {args.out}/")
    print(f"  payments.csv:          {len(payments)} rows")
    print(f"  bank_transactions.csv: {len(bank_txns)} rows")
    print(f"  ledger.csv:            {len(ledger_entries)} rows")
    print(f"  ground_truth.csv:      {len(ground_truth)} rows")


if __name__ == "__main__":
    main()
