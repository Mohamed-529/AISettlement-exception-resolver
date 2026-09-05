# AI Finance Controller

Three-phase build for the Razorpay Buildathon "Multi-Source Financial
Reconciliation" loop:

- **Phase 1** — deterministic data foundation: synthetic multi-source
  data with ground truth, a normalization layer, and a rule-based
  reconciliation engine. No LLM, fully testable offline.
- **Phase 2** — an AI investigation agent that takes the exceptions
  Phase 1 couldn't cleanly explain, gathers evidence, separates fact
  from hypothesis, classifies root cause, assigns a confidence score,
  and — through a fixed decision policy, never the LLM directly —
  either auto-resolves the status, suggests a resolution for human
  approval, or escalates. Every decision is logged to an audit trail.
- **Phase 3** — a self-contained dashboard (`frontend/dashboard.html`)
  that turns Phase 1 + Phase 2 output into a judge-facing product:
  summary metrics, an exception register, a per-case evidence view,
  and the audit tape — including an honest accounting of what the
  agent could **not** confidently resolve.

## Project structure

```
ai-finance-controller/
├── backend/
│   ├── app/
│   │   ├── main.py                    # Phase 1 CLI
│   │   ├── phase2_runner.py           # Phase 2 CLI
│   │   ├── phase3_runner.py           # Phase 3 CLI (builds dashboard.html)
│   │   ├── run_all.py                 # runs all three phases in one command
│   │   ├── models/transaction.py      # TransactionRecord, ReconciliationResult
│   │   ├── services/
│   │   │   ├── data_loader.py         # reads raw CSVs
│   │   │   ├── normalizer.py          # raw rows -> TransactionRecord
│   │   │   ├── reconciliation.py      # Phase 1 matching rules + auto-resolve
│   │   │   ├── agent.py               # Phase 2 investigator (LLM mode + offline mock mode)
│   │   │   ├── decision_engine.py     # Phase 2 confidence -> action policy
│   │   │   ├── audit.py               # Phase 2 audit trail recorder
│   │   │   └── dashboard_builder.py   # Phase 3 HTML dashboard renderer
│   │   └── utils/
│   │       ├── metrics.py             # Phase 1 metrics + ground-truth accuracy
│   │       └── phase2_metrics.py      # Phase 2 classification + auto-resolve safety scoring
│   └── requirements.txt
├── data/                              # generated CSVs + JSON results land here
├── frontend/dashboard.html            # generated Phase 3 dashboard (open directly in a browser)
├── scripts/generate_data.py           # synthetic data generator
├── tests/
│   ├── test_reconciliation.py         # Phase 1 tests
│   └── test_agent_decision.py         # Phase 2 tests
└── README.md
```

## Setup

```bash
cd ai-finance-controller
pip install -r backend/requirements.txt
```

`anthropic` is only needed for `--mode llm` in Phase 2. The default
`--mode mock` needs nothing beyond the standard library and is what
the test suite and CI should run against.

## Run everything in one command

```bash
python scripts/generate_data.py --count 100 --seed 42 --out data
cd backend
python -m app.run_all --data ../data --mode mock --dashboard-out ../frontend/dashboard.html \
    --phase1-out ../data/phase1_results.json --phase2-out ../data/phase2_results.json
```

Then open `frontend/dashboard.html` in a browser.

## Or run each phase individually

### 1. Generate synthetic data

```bash
python scripts/generate_data.py --count 100 --seed 42 --out data
```

Writes `payments.csv`, `bank_transactions.csv`, `ledger.csv`, and
`ground_truth.csv` into `data/`. Re-running with the same `--seed`
reproduces the exact same dataset.

Default distribution (100 records):

| Scenario                  | Count |
|----------------------------|-------|
| Exact match                | 60    |
| Amount mismatch            | 10    |
| Bank transaction missing   | 8     |
| Ledger entry missing       | 7     |
| Duplicate bank transaction | 5     |
| Date mismatch (delayed)    | 5     |
| Ambiguous (multi-field)    | 5     |

### 2. Phase 1 — deterministic reconciliation

```bash
cd backend
python -m app.main --data ../data --json-out ../data/phase1_results.json
```

Prints total records, match rate, exception breakdown, auto-resolved
count, and accuracy against ground truth (with the specific
misclassifications listed, never a bare percentage).

### 3. Phase 2 — AI investigation agent

```bash
python -m app.phase2_runner --phase1-json ../data/phase1_results.json \
    --ground-truth ../data/ground_truth.csv --mode mock \
    --json-out ../data/phase2_results.json
```

For every Phase 1 exception: builds an evidence packet → agent
investigates (fact vs hypothesis) → classifies into one of
`AMOUNT_MISMATCH`, `BANK_RECORD_MISSING`, `LEDGER_RECORD_MISSING`,
`DUPLICATE_TRANSACTION`, `DATE_MISMATCH`, `POSSIBLE_DELAYED_SETTLEMENT`,
`UNRESOLVED` → confidence score → decision policy:

| Confidence | Decision |
|---|---|
| ≥ 0.90 | `AUTO_RESOLVE` — reconciliation status updated, never the underlying amounts |
| 0.70 – 0.89 | `SUGGEST_HUMAN_APPROVAL` |
| < 0.70 | `ESCALATE_HUMAN_REVIEW` |

Every decision is written to the audit trail with its full evidence.
With `--ground-truth`, it also prints classification accuracy and,
more importantly, the **false auto-resolve rate** — how many of the
agent's confident auto-resolutions were actually wrong. That number
matters more than average accuracy for a system that's allowed to
touch financial reconciliation state.

Swap `--mode mock` for `--mode llm` (with `ANTHROPIC_API_KEY` set) to
route investigation through the real Anthropic API instead of the
deterministic offline stand-in — both return the same structured shape,
so nothing downstream changes.

### 4. Phase 3 — dashboard

```bash
python -m app.phase3_runner --phase1-json ../data/phase1_results.json \
    --phase2-json ../data/phase2_results.json --out ../frontend/dashboard.html
```

Builds one self-contained HTML file (no server, no build step) with
the results embedded directly: a summary strip, a filterable exception
register, a click-through evidence panel per case, and a timestamped
audit tape.

### 5. Run tests

```bash
cd ai-finance-controller
python -m pytest tests -v
```

## Design notes

- **Auto-resolve is conservative on purpose, at every layer.** Phase
  1's deterministic engine only auto-resolves `DATE_MISMATCH` (amounts
  already agree everywhere). Phase 2's agent can auto-resolve more —
  but only above a 0.90 confidence threshold, and "auto-resolve" always
  means updating reconciliation *status*, never touching a payment,
  bank, or ledger amount. Amount mismatches are never auto-resolved
  regardless of confidence, by design.
- **Fact vs hypothesis stays separated all the way to the UI.** The
  agent's evidence list (facts) and root-cause explanation (hypothesis)
  are rendered as visually distinct blocks in the dashboard, not
  merged into one confident-sounding paragraph.
- **Ground truth is the source of truth for every accuracy claim** —
  in Phase 1 (`metrics.py`), Phase 2 (`phase2_metrics.py`), and the
  dashboard. Every number comes with the specific mismatches behind
  it, never a bare percentage.
- **The mock agent mode exists so this is actually testable.** It's a
  deterministic, evidence-driven stand-in for the LLM — not hardcoded
  per-payment answers — so `test_agent_decision.py` and this sandbox
  (no network access) can both exercise the full Phase 2 pipeline
  without an API key.
