"""
Runs the complete pipeline end to end:

    generate data (optional) -> Phase 1 reconciliation -> Phase 2 agent
    -> Phase 3 dashboard.html

Run from backend/ directory:

    python -m app.run_all --data ../data --dashboard-out ../frontend/dashboard.html --mode mock
"""

import argparse
import csv
import json

from app.services import data_loader, normalizer, reconciliation
from app.utils import metrics as metrics_utils
from app.utils.phase2_metrics import evaluate_agent
from app.services.agent import AgentInvestigator
from app.services.decision_engine import decide
from app.services.audit import AuditTrail
from app.services.dashboard_builder import build_dashboard_html


def run_phase1(data_dir: str) -> dict:
    raw = data_loader.load_all(data_dir)
    normalized = normalizer.normalize_all(raw)
    results = reconciliation.reconcile(normalized)
    report = metrics_utils.full_report(results, raw["ground_truth"])
    return {
        "report": report,
        "results": [r.to_dict() for r in results],
        "ground_truth": raw["ground_truth"],
    }


def run_phase2(phase1_results: list, ground_truth_rows: list, mode: str, model: str) -> dict:
    exceptions = [r for r in phase1_results if r["status"] == "EXCEPTION"]
    matched_count = len(phase1_results) - len(exceptions)

    agent = AgentInvestigator(mode=mode, model=model)
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

    evaluation = evaluate_agent(agent_outputs, ground_truth_rows)

    return {
        "summary": summary,
        "agent_outputs": agent_outputs,
        "audit_trail": audit.to_list(),
        "evaluation": evaluation,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the full Phase 1+2+3 pipeline")
    parser.add_argument("--data", type=str, default="../data")
    parser.add_argument("--mode", type=str, default="mock", choices=["mock", "llm"])
    parser.add_argument("--model", type=str, default="claude-sonnet-4-6")
    parser.add_argument("--phase1-out", type=str, default=None)
    parser.add_argument("--phase2-out", type=str, default=None)
    parser.add_argument("--dashboard-out", type=str, default="../frontend/dashboard.html")
    args = parser.parse_args()

    phase1 = run_phase1(args.data)
    print(f"[Phase 1] {phase1['report']['metrics']['total_records']} records — "
          f"match rate {phase1['report']['metrics']['match_rate']}%, "
          f"ground-truth accuracy {phase1['report']['ground_truth_comparison']['accuracy']}%")

    phase2 = run_phase2(phase1["results"], phase1["ground_truth"], args.mode, args.model)
    print(f"[Phase 2] {phase2['summary']['exceptions_total']} exceptions investigated — "
          f"{phase2['summary']['agent_auto_resolved']} auto-resolved, "
          f"{phase2['summary']['agent_suggested_approval']} need approval, "
          f"{phase2['summary']['agent_escalated']} escalated. "
          f"Classification accuracy {phase2['evaluation']['classification_accuracy']}%, "
          f"false auto-resolve rate {phase2['evaluation']['false_auto_resolve_rate']}%")

    phase1_payload = {"report": phase1["report"], "results": phase1["results"]}
    html = build_dashboard_html(phase1_payload, phase2)
    with open(args.dashboard_out, "w") as f:
        f.write(html)
    print(f"[Phase 3] Dashboard written to {args.dashboard_out} ({len(html):,} bytes)")

    if args.phase1_out:
        with open(args.phase1_out, "w") as f:
            json.dump(phase1_payload, f, indent=2)
    if args.phase2_out:
        with open(args.phase2_out, "w") as f:
            json.dump(phase2, f, indent=2)


if __name__ == "__main__":
    main()
