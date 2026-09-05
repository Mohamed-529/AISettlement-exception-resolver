"""
Scores what the Phase 2 agent did against ground_truth.csv, the same
honesty discipline Phase 1 uses. Two separate questions matter here:

1. Classification accuracy — did the agent's exception_type match what
   actually happened?
2. Auto-resolve safety — of the cases the agent was confident enough to
   auto-resolve, how many were ACTUALLY safe to auto-resolve? This is
   the number that matters most for trust: a system that's accurate on
   average but wrong on some of its auto-resolves is dangerous in a way
   overall accuracy hides.
"""

from typing import List, Dict

# Ground truth "scenario" labels (from scripts/generate_data.py) mapped
# to the set of agent exception_type labels that count as a correct call.
SCENARIO_TO_ACCEPTABLE_AGENT_TYPES = {
    "AMOUNT_MISMATCH": {"AMOUNT_MISMATCH"},
    "BANK_MISSING": {"BANK_RECORD_MISSING"},
    "LEDGER_MISSING": {"LEDGER_RECORD_MISSING"},
    "DUPLICATE": {"DUPLICATE_TRANSACTION"},
    "DATE_MISMATCH": {"DATE_MISMATCH", "POSSIBLE_DELAYED_SETTLEMENT"},
    # AMBIGUOUS has no single correct label by design — the "correct"
    # agent behavior is to NOT be confidently wrong (see safety check).
    "AMBIGUOUS": {"UNRESOLVED", "AMOUNT_MISMATCH", "BANK_RECORD_MISSING",
                  "LEDGER_RECORD_MISSING", "DUPLICATE_TRANSACTION",
                  "DATE_MISMATCH", "POSSIBLE_DELAYED_SETTLEMENT"},
}

# Scenarios where auto-resolving is actually safe. Anything auto-resolved
# outside this set is a false auto-resolve, regardless of confidence.
SAFE_TO_AUTO_RESOLVE_SCENARIOS = {"DATE_MISMATCH", "DUPLICATE"}


def evaluate_agent(agent_outputs: List[dict], ground_truth_rows: List[dict]) -> dict:
    truth_by_id = {row["payment_id"]: row for row in ground_truth_rows}

    correct = 0
    incorrect = 0
    misclassifications = []

    auto_resolved = [o for o in agent_outputs if o["decision"] == "AUTO_RESOLVE"]
    safe_auto_resolves = 0
    false_auto_resolves = []

    for output in agent_outputs:
        pid = output["payment_id"]
        truth = truth_by_id.get(pid)
        if truth is None:
            continue
        scenario = truth["scenario"]
        acceptable = SCENARIO_TO_ACCEPTABLE_AGENT_TYPES.get(scenario, set())

        if output["agent_exception_type"] in acceptable:
            correct += 1
        else:
            incorrect += 1
            misclassifications.append({
                "payment_id": pid,
                "scenario": scenario,
                "agent_exception_type": output["agent_exception_type"],
            })

        if output["decision"] == "AUTO_RESOLVE":
            if scenario in SAFE_TO_AUTO_RESOLVE_SCENARIOS:
                safe_auto_resolves += 1
            else:
                false_auto_resolves.append({
                    "payment_id": pid,
                    "scenario": scenario,
                    "agent_exception_type": output["agent_exception_type"],
                    "confidence": output["confidence"],
                })

    total = correct + incorrect
    return {
        "classification_accuracy": round(correct / total * 100, 2) if total else 0.0,
        "correct": correct,
        "incorrect": incorrect,
        "misclassifications": misclassifications,
        "auto_resolved_count": len(auto_resolved),
        "safe_auto_resolves": safe_auto_resolves,
        "false_auto_resolves": false_auto_resolves,
        "false_auto_resolve_rate": (
            round(len(false_auto_resolves) / len(auto_resolved) * 100, 2) if auto_resolved else 0.0
        ),
    }
