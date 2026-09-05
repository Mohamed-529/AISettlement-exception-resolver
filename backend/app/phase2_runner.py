"""
Phase 2 pipeline runner.

    Phase 1 results.json
            │
            ▼
    Filter to EXCEPTION records only
            │
            ▼
    For each: Agent.investigate() -> Decision policy -> Audit log
            │
            ▼
    phase2_results.json

Run from backend/ directory:

    python -m app.phase2_runner --phase1-json ../data/phase1_results.json \\
        --ground-truth ../data/ground_truth.csv --mode mock \\
        --json-out ../data/phase2_results.json
"""

import argparse
import csv
import json

from app.services.agent import AgentInvestigator
from app.services.decision_engine import decide
from app.services.audit import AuditTrail
from app.utils.phase2_metrics import evaluate_agent


def run(phase1_results: list, mode: str = "mock", model: str = "claude-sonnet-4-6", api_key: str = None) -> dict:
    exceptions = [r for r in phase1_results if r["status"] == "EXCEPTION"]
    matched_count = len(phase1_results) - len(exceptions)

    agent = AgentInvestigator(mode=mode, model=model, api_key=api_key)
    audit = AuditTrail()
    agent_outputs = []

    for result in exceptions:
        evidence = agent.build_evidence(result)
        analysis = agent.investigate(evidence)
        d = decide(analysis["confidence"])

        audit.log(
            payment_id=result["payment_id"],
            exception_type=analysis["exception_type"],
            evidence=evidence,
            reasoning_summary=analysis["root_cause"],
            confidence=analysis["confidence"],
            decision=d.decision,
            action=d.action,
        )

        agent_outputs.append({
            "payment_id": result["payment_id"],
            "engine_exception_type": result["exception_type"],
            "agent_exception_type": analysis["exception_type"],
            "root_cause": analysis["root_cause"],
            "evidence": analysis["evidence"],
            "confidence": analysis["confidence"],
            "recommendation": analysis["recommendation"],
            "decision": d.decision,
            "action": d.action,
        })

    auto_resolved = [o for o in agent_outputs if o["decision"] == "AUTO_RESOLVE"]
    suggest_approval = [o for o in agent_outputs if o["decision"] == "SUGGEST_HUMAN_APPROVAL"]
    escalated = [o for o in agent_outputs if o["decision"] == "ESCALATE_HUMAN_REVIEW"]

    summary = {
        "total_records": len(phase1_results),
        "matched": matched_count,
        "exceptions_total": len(exceptions),
        "agent_auto_resolved": len(auto_resolved),
        "agent_suggested_approval": len(suggest_approval),
        "agent_escalated": len(escalated),
    }

    return {
        "summary": summary,
        "agent_outputs": agent_outputs,
        "audit_trail": audit.to_list(),
    }


def main():
    parser = argparse.ArgumentParser(description="Run Phase 2 AI reconciliation agent")
    parser.add_argument("--phase1-json", type=str, required=True,
                         help="Path to phase1_results.json produced by `python -m app.main --json-out ...`")
    parser.add_argument("--ground-truth", type=str, default=None,
                         help="Path to ground_truth.csv, to also score agent accuracy")
    parser.add_argument("--mode", type=str, default="mock", choices=["mock", "llm"],
                         help="'mock' = deterministic offline stand-in, 'llm' = real Anthropic API call")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-6")
    parser.add_argument("--json-out", type=str, default=None)
    args = parser.parse_args()

    with open(args.phase1_json) as f:
        phase1_payload = json.load(f)
    phase1_results = phase1_payload["results"]

    outcome = run(phase1_results, mode=args.mode, model=args.model)

    s = outcome["summary"]
    print("=" * 50)
    print("AI FINANCE CONTROLLER — PHASE 2 AGENT REPORT")
    print("=" * 50)
    print(f"Mode:                      {args.mode}")
    print(f"Total records:             {s['total_records']}")
    print(f"Matched (untouched):       {s['matched']}")
    print(f"Exceptions investigated:   {s['exceptions_total']}")
    print(f"Auto-resolved:             {s['agent_auto_resolved']}")
    print(f"Suggested (needs approval):{s['agent_suggested_approval']}")
    print(f"Escalated (human review):  {s['agent_escalated']}")

    if args.ground_truth:
        with open(args.ground_truth, newline="") as f:
            gt_rows = list(csv.DictReader(f))
        evaluation = evaluate_agent(outcome["agent_outputs"], gt_rows)
        outcome["evaluation"] = evaluation
        print()
        print("Agent evaluation vs ground truth:")
        print(f"  Classification accuracy:  {evaluation['classification_accuracy']}%")
        print(f"  Correct / Incorrect:      {evaluation['correct']} / {evaluation['incorrect']}")
        print(f"  Auto-resolved:            {evaluation['auto_resolved_count']}")
        print(f"  Safe auto-resolves:       {evaluation['safe_auto_resolves']}")
        print(f"  False auto-resolves:      {len(evaluation['false_auto_resolves'])} "
              f"({evaluation['false_auto_resolve_rate']}%)")
        if evaluation["false_auto_resolves"]:
            print("  ⚠️  False auto-resolve details:")
            for f_ar in evaluation["false_auto_resolves"]:
                print(f"     - {f_ar['payment_id']}: scenario={f_ar['scenario']}, "
                      f"agent_type={f_ar['agent_exception_type']}, confidence={f_ar['confidence']}")
    print("=" * 50)

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(outcome, f, indent=2)
        print(f"\nFull Phase 2 results written to {args.json_out}")


if __name__ == "__main__":
    main()
