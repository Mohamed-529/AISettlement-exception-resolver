import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.decision_engine import decide, DECISION_AUTO_RESOLVE, DECISION_SUGGEST_APPROVAL, DECISION_ESCALATE
from app.services.agent import AgentInvestigator
from app.services.audit import AuditTrail
from app.utils.phase2_metrics import evaluate_agent


# ---------------- decision_engine ----------------

def test_decide_high_confidence_auto_resolves():
    d = decide(0.95)
    assert d.decision == DECISION_AUTO_RESOLVE


def test_decide_boundary_90_is_auto_resolve():
    d = decide(0.90)
    assert d.decision == DECISION_AUTO_RESOLVE


def test_decide_mid_confidence_suggests_approval():
    d = decide(0.75)
    assert d.decision == DECISION_SUGGEST_APPROVAL


def test_decide_low_confidence_escalates():
    d = decide(0.4)
    assert d.decision == DECISION_ESCALATE


def test_decide_none_confidence_escalates_safely():
    d = decide(None)
    assert d.decision == DECISION_ESCALATE


# ---------------- mock agent ----------------

def _result(payment_id, exception_type, payment_amount=5000, bank_amount=5000,
            ledger_amount=5000, payment_date="2026-08-20", bank_date="2026-08-20",
            ledger_date="2026-08-20", duplicate_count=None):
    return {
        "payment_id": payment_id,
        "payment_amount": payment_amount,
        "bank_amount": bank_amount,
        "ledger_amount": ledger_amount,
        "payment_date": payment_date,
        "bank_date": bank_date,
        "ledger_date": ledger_date,
        "status": "EXCEPTION",
        "exception_type": exception_type,
        "difference": None,
        "notes": None,
        "duplicate_count": duplicate_count,
    }


def test_mock_agent_date_mismatch_is_high_confidence_auto_resolve():
    agent = AgentInvestigator(mode="mock")
    evidence = agent.build_evidence(_result("P100", "DATE_MISMATCH", bank_date="2026-08-24"))
    analysis = agent.investigate(evidence)
    assert analysis["exception_type"] == "POSSIBLE_DELAYED_SETTLEMENT"
    assert analysis["confidence"] >= 0.90


def test_mock_agent_amount_mismatch_never_hits_auto_resolve_threshold():
    agent = AgentInvestigator(mode="mock")
    evidence = agent.build_evidence(_result("P101", "AMOUNT_MISMATCH", bank_amount=4500))
    analysis = agent.investigate(evidence)
    assert analysis["exception_type"] == "AMOUNT_MISMATCH"
    assert analysis["confidence"] < 0.90  # money never auto-resolves


def test_mock_agent_bank_missing_recommends_human_review():
    agent = AgentInvestigator(mode="mock")
    result = _result("P102", "BANK_RECORD_MISSING", bank_amount=None, bank_date=None)
    evidence = agent.build_evidence(result)
    analysis = agent.investigate(evidence)
    assert analysis["exception_type"] == "BANK_RECORD_MISSING"
    assert analysis["recommendation"] == "Human review"


def test_mock_agent_duplicate_is_flagged_not_deleted():
    agent = AgentInvestigator(mode="mock")
    result = _result("P103", "POSSIBLE_DUPLICATE", duplicate_count=2)
    evidence = agent.build_evidence(result)
    analysis = agent.investigate(evidence)
    assert analysis["exception_type"] == "DUPLICATE_TRANSACTION"
    # High confidence, but the action is a flag/status update, never a
    # record deletion — enforced by decision_engine.decide(), not the agent.
    assert analysis["confidence"] >= 0.90


def test_mock_agent_invalid_type_normalizes_to_unresolved():
    agent = AgentInvestigator(mode="mock")
    evidence = agent.build_evidence(_result("P104", "SOME_UNKNOWN_TYPE"))
    analysis = agent.investigate(evidence)
    assert analysis["exception_type"] == "UNRESOLVED"


# ---------------- audit trail ----------------

def test_audit_trail_records_entry_with_all_fields():
    audit = AuditTrail()
    entry = audit.log(
        payment_id="P105",
        exception_type="AMOUNT_MISMATCH",
        evidence={"payment": {"amount": 100}},
        reasoning_summary="test reasoning",
        confidence=0.6,
        decision="ESCALATE_HUMAN_REVIEW",
        action="escalated_for_investigation",
    )
    assert entry["payment_id"] == "P105"
    assert "timestamp" in entry
    assert len(audit.to_list()) == 1


# ---------------- phase2 evaluation ----------------

def test_evaluate_agent_scores_correct_and_flags_false_auto_resolve():
    ground_truth_rows = [
        {"payment_id": "P1", "scenario": "DATE_MISMATCH"},
        {"payment_id": "P2", "scenario": "AMOUNT_MISMATCH"},
    ]
    agent_outputs = [
        {
            "payment_id": "P1", "agent_exception_type": "POSSIBLE_DELAYED_SETTLEMENT",
            "decision": "AUTO_RESOLVE", "confidence": 0.95,
        },
        {
            # Wrongly auto-resolved an amount mismatch -> should be flagged
            "payment_id": "P2", "agent_exception_type": "AMOUNT_MISMATCH",
            "decision": "AUTO_RESOLVE", "confidence": 0.95,
        },
    ]
    evaluation = evaluate_agent(agent_outputs, ground_truth_rows)
    assert evaluation["classification_accuracy"] == 100.0  # both classified correctly
    assert evaluation["safe_auto_resolves"] == 1
    assert len(evaluation["false_auto_resolves"]) == 1
    assert evaluation["false_auto_resolves"][0]["payment_id"] == "P2"
