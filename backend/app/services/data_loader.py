"""
Reads the three raw source CSVs into plain lists of dicts.

Kept deliberately dumb: no normalization or business logic here, just
I/O. That way normalizer.py and reconciliation.py stay testable in
isolation.
"""

import csv
import os


def _read_csv(path: str) -> list:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected data file not found: {path}")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_payments(data_dir: str) -> list:
    return _read_csv(os.path.join(data_dir, "payments.csv"))


def load_bank_transactions(data_dir: str) -> list:
    return _read_csv(os.path.join(data_dir, "bank_transactions.csv"))


def load_ledger(data_dir: str) -> list:
    return _read_csv(os.path.join(data_dir, "ledger.csv"))


def load_ground_truth(data_dir: str) -> list:
    return _read_csv(os.path.join(data_dir, "ground_truth.csv"))


def load_all(data_dir: str) -> dict:
    return {
        "payments": load_payments(data_dir),
        "bank_transactions": load_bank_transactions(data_dir),
        "ledger": load_ledger(data_dir),
        "ground_truth": load_ground_truth(data_dir),
    }
