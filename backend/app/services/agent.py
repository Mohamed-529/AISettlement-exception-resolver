"""
The investigation + reasoning layer (Phase 2 §2.3-2.5).

Two modes:

- mode="llm": calls the real Anthropic API (requires `anthropic` package
  and ANTHROPIC_API_KEY). This is what a live demo should run with.
- mode="mock": a deterministic, rule-based stand-in for the LLM that
  follows the exact same "fact vs hypothesis" discipline described in
  the plan. No network calls, fully reproducible — this is what lets
  Phase 2 be unit-tested and run offline (e.g. in this sandbox, which
  has no network access).

Both modes return the same structured shape, so decision_engine and
everything downstream never has to know which one produced it.
"""

import json
import os

SYSTEM_PROMPT = """You are a financial reconciliation investigator for an AI Finance Controller.

You are given evidence about ONE payment that a deterministic reconciliation \
engine already flagged as an exception across three sources: payment platform, \
bank, and merchant ledger.

Your job:
1. State the FACTS present in the evidence (what's missing, what disagrees).
2. State a POSSIBLE CAUSE as a hypothesis, clearly separate from the facts.
3. Classify the exception into exactly one of:
   AMOUNT_MISMATCH, BANK_RECORD_MISSING, LEDGER_RECORD_MISSING,
   DUPLICATE_TRANSACTION, DATE_MISMATCH, POSSIBLE_DELAYED_SETTLEMENT, UNRESOLVED
4. Give a confidence score from 0.0 to 1.0 for how sure you are about the
   root cause. Be conservative — this number gates whether the system is
   allowed to auto-resolve anything, so do not inflate it.
5. Recommend one of: "Auto-resolve", "Human review".

Respond with ONLY a JSON object, no prose outside it, in this exact shape:
{
  "exception_type": "...",
  "root_cause": "...",
  "evidence": ["fact 1", "fact 2", "..."],
  "confidence": 0.0,
  "recommendation": "..."
}
"""

VALID_EXCEPTION_TYPES = {
    "AMOUNT_MISMATCH",
    "BANK_RECORD_MISSING",
    "LEDGER_RECORD_MISSING",
    "DUPLICATE_TRANSACTION",
    "DATE_MISMATCH",
    "POSSIBLE_DELAYED_SETTLEMENT",
    "UNRESOLVED",
}


class AgentInvestigator:
    def __init__(self, mode: str = "mock", model: str = "claude-sonnet-4-6", api_key: str = None):
        if mode not in ("mock", "llm"):
            raise ValueError("mode must be 'mock' or 'llm'")
        self.mode = mode
        self.model = model
        self.client = None

        if mode == "llm":
            try:
                import anthropic
            except ImportError as e:
                raise ImportError(
                    "mode='llm' requires the 'anthropic' package: pip install anthropic"
                ) from e
            key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError(
                    "mode='llm' requires ANTHROPIC_API_KEY to be set (or pass api_key=...)"
                )
            self.client = anthropic.Anthropic(api_key=key)

    # ---- Investigation layer: build the minimal evidence packet ----

    def build_evidence(self, result_dict: dict) -> dict:
        """
        result_dict: a ReconciliationResult.to_dict() from Phase 1.
        Only relevant fields are passed to the agent (Phase 2 §2.3) —
        we don't dump the whole batch at it.
        """
        return {
            "payment_id": result_dict["payment_id"],
            "payment": {
                "amount": result_dict["payment_amount"],
                "date": result_dict["payment_date"],
            },
            "bank": (
                {"amount": result_dict["bank_amount"], "date": result_dict["bank_date"]}
                if result_dict.get("bank_amount") is not None else None
            ),
            "ledger": (
                {"amount": result_dict["ledger_amount"], "date": result_dict["ledger_date"]}
                if result_dict.get("ledger_amount") is not None else None
            ),
            "engine_exception_type": result_dict["exception_type"],
            "engine_notes": result_dict.get("notes"),
            "duplicate_count": result_dict.get("duplicate_count"),
        }

    # ---- Reasoning layer ----

    def investigate(self, evidence: dict) -> dict:
        if self.mode == "llm":
            analysis = self._investigate_llm(evidence)
        else:
            analysis = self._investigate_mock(evidence)

        # Defensive normalization regardless of which mode produced this,
        # so a malformed LLM response can never crash the decision engine
        # or silently inflate confidence.
        exception_type = analysis.get("exception_type")
        if exception_type not in VALID_EXCEPTION_TYPES:
            exception_type = "UNRESOLVED"

        try:
            confidence = float(analysis.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        return {
            "exception_type": exception_type,
            "root_cause": analysis.get("root_cause", "Not determined"),
            "evidence": analysis.get("evidence", []),
            "confidence": confidence,
            "recommendation": analysis.get("recommendation", "Human review"),
        }

    def _investigate_llm(self, evidence: dict) -> dict:
        prompt = (
            "Evidence for this exception:\n"
            f"{json.dumps(evidence, indent=2)}\n\n"
            "Investigate and respond with the JSON object described in your instructions."
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fail safe: an unparseable LLM response becomes a
            # zero-confidence UNRESOLVED case, never a crash and never
            # a false auto-resolve.
            return {
                "exception_type": "UNRESOLVED",
                "root_cause": "Agent response could not be parsed",
                "evidence": [],
                "confidence": 0.0,
                "recommendation": "Human review",
            }

    def _investigate_mock(self, evidence: dict) -> dict:
        """
        Deterministic stand-in for the LLM. Mirrors the reasoning style
        the plan describes (facts vs hypothesis) with fixed, conservative
        confidence bands per exception type, computed from the evidence
        itself rather than hardcoded per-case — so it behaves sensibly
        on any dataset, not just the demo numbers in the plan.
        """
        engine_type = evidence.get("engine_exception_type")
        payment = evidence["payment"]
        bank = evidence.get("bank")
        ledger = evidence.get("ledger")

        if engine_type == "DATE_MISMATCH":
            facts = ["Payment, bank, and ledger amounts agree", "Bank settlement date differs from payment date"]
            return {
                "exception_type": "POSSIBLE_DELAYED_SETTLEMENT",
                "root_cause": "Amounts reconcile; the bank side settled later than the payment date, "
                               "consistent with normal settlement delay.",
                "evidence": facts,
                "confidence": 0.95,
                "recommendation": "Auto-resolve",
            }

        if engine_type == "BANK_RECORD_MISSING":
            facts = ["Payment was captured", "Ledger entry exists"]
            facts.append("No matching bank transaction found" if not bank else "Bank record present but unmatched")
            return {
                "exception_type": "BANK_RECORD_MISSING",
                "root_cause": "Payment was captured and recorded in the ledger, but no corresponding bank "
                               "transaction is present. Possible delayed or missing settlement — not confirmed.",
                "evidence": facts,
                "confidence": 0.80,
                "recommendation": "Human review",
            }

        if engine_type == "LEDGER_RECORD_MISSING":
            facts = ["Payment was captured", "Bank transaction is present"]
            facts.append("No matching ledger entry found")
            return {
                "exception_type": "LEDGER_RECORD_MISSING",
                "root_cause": "Bank confirms settlement, but the merchant ledger has no matching entry. "
                               "Possible posting delay or an internal bookkeeping gap — not confirmed.",
                "evidence": facts,
                "confidence": 0.75,
                "recommendation": "Human review",
            }

        if engine_type == "POSSIBLE_DUPLICATE":
            dup_count = evidence.get("duplicate_count") or 2
            facts = [f"{dup_count} bank transactions reference this single payment",
                     "Ledger shows only one corresponding entry"]
            return {
                "exception_type": "DUPLICATE_TRANSACTION",
                "root_cause": f"{dup_count} bank-side transactions reference one payment while the ledger "
                               "shows a single entry, consistent with a duplicate bank posting.",
                "evidence": facts,
                "confidence": 0.91,
                "recommendation": "Auto-resolve",  # flag as suspected duplicate, do not delete anything
            }

        if engine_type == "AMOUNT_MISMATCH":
            bank_amt = bank["amount"] if bank else None
            ledger_amt = ledger["amount"] if ledger else None
            pay_amt = payment["amount"]
            diff = None
            if bank_amt is not None and abs(bank_amt - pay_amt) >= abs((ledger_amt or pay_amt) - pay_amt):
                diff = bank_amt - pay_amt
                mismatched_source = "bank"
            elif ledger_amt is not None:
                diff = ledger_amt - pay_amt
                mismatched_source = "ledger"
            else:
                mismatched_source = "unknown"

            rel = abs(diff) / pay_amt if diff is not None and pay_amt else 1.0
            # Larger relative gaps are easier to be sure ARE a real
            # discrepancy, but we still never treat an amount mismatch
            # as safe to touch automatically — money always gets a human.
            confidence = 0.55 if rel < 0.02 else (0.68 if rel < 0.15 else 0.60)

            facts = [f"Payment amount: {pay_amt}"]
            if bank_amt is not None:
                facts.append(f"Bank amount: {bank_amt}")
            if ledger_amt is not None:
                facts.append(f"Ledger amount: {ledger_amt}")

            return {
                "exception_type": "AMOUNT_MISMATCH",
                "root_cause": f"The {mismatched_source} amount disagrees with the payment amount by {diff}. "
                               "Cause not confirmed — could be a fee, partial settlement, or data entry error.",
                "evidence": facts,
                "confidence": confidence,
                "recommendation": "Human review",
            }

        # AMBIGUOUS or anything else unclassified
        facts = ["Multiple small discrepancies across sources", "No single field disagreement explains it cleanly"]
        return {
            "exception_type": "UNRESOLVED",
            "root_cause": "Evidence shows small, multi-field drift that does not match a single known pattern "
                           "confidently enough to classify.",
            "evidence": facts,
            "confidence": 0.45,
            "recommendation": "Human review",
        }
