"""
Decision policy: turns an agent's confidence score into a controlled
action. This is what makes the system an *agent* rather than a chatbot
that free-associates about financial records — the LLM never gets to
change reconciliation state directly, it only produces a confidence
score that this policy interprets.

Thresholds are intentionally conservative and centralized here so they
can be tuned in one place during testing.
"""

from dataclasses import dataclass

AUTO_RESOLVE_THRESHOLD = 0.90
SUGGEST_APPROVAL_THRESHOLD = 0.70

DECISION_AUTO_RESOLVE = "AUTO_RESOLVE"
DECISION_SUGGEST_APPROVAL = "SUGGEST_HUMAN_APPROVAL"
DECISION_ESCALATE = "ESCALATE_HUMAN_REVIEW"


@dataclass
class Decision:
    decision: str
    action: str


def decide(confidence: float) -> Decision:
    """
    confidence >= 0.90  -> eligible for automatic resolution
    0.70 <= confidence < 0.90 -> suggest a resolution, needs human approval
    confidence < 0.70   -> escalate for human investigation

    "Automatic resolution" here means updating the reconciliation
    STATUS (e.g. marking a delayed-settlement exception as resolved).
    It never means silently altering payment, bank, or ledger amounts —
    those stay exactly as ingested, no matter how confident the agent is.
    """
    if confidence is None:
        confidence = 0.0

    if confidence >= AUTO_RESOLVE_THRESHOLD:
        return Decision(decision=DECISION_AUTO_RESOLVE, action="reconciliation_status_updated")
    elif confidence >= SUGGEST_APPROVAL_THRESHOLD:
        return Decision(decision=DECISION_SUGGEST_APPROVAL, action="pending_human_approval")
    else:
        return Decision(decision=DECISION_ESCALATE, action="escalated_for_investigation")
