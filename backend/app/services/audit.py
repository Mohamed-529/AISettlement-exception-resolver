"""
Records a timestamped, evidence-backed entry for every decision the
agent makes. This is what gives the system explainability +
auditability (Phase 2 §2.9) instead of just a black-box verdict.
"""

import csv
import json
from datetime import datetime, timezone


class AuditTrail:
    def __init__(self):
        self.entries = []

    def log(self, payment_id: str, exception_type: str, evidence: dict,
             reasoning_summary: str, confidence: float, decision: str, action: str) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "payment_id": payment_id,
            "exception_type": exception_type,
            "evidence": evidence,
            "agent_reasoning_summary": reasoning_summary,
            "confidence": confidence,
            "decision": decision,
            "action": action,
        }
        self.entries.append(entry)
        return entry

    def to_list(self) -> list:
        return self.entries

    def write_json(self, path: str):
        with open(path, "w") as f:
            json.dump(self.entries, f, indent=2)

    def write_csv(self, path: str):
        if not self.entries:
            return
        fieldnames = list(self.entries[0].keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for e in self.entries:
                row = dict(e)
                row["evidence"] = json.dumps(row["evidence"])
                writer.writerow(row)
