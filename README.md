# AI Settlement & Exception Resolver (AI Finance Controller)

An AI-powered financial reconciliation and exception resolution platform that automates payment matching across payment gateways (Razorpay), bank settlements, and internal general ledgers with confidence-driven AI policy guardrails.

---

## 🌟 Key Features

- **Multi-Source Financial Reconciliation**: Reconciles transaction feeds across customer payments, bank settlements, and ledger records.
- **3-Tier AI Decision Policy Engine**:
  - ⚡ **Auto-Resolved ($\ge$ 90% Confidence)**: Zero-touch autonomous resolution for safe, verified discrepancies (e.g., standard 1-day bank clearance delay).
  - ⏱️ **Needs Approval (70% – 89% Confidence)**: Human-in-the-loop workflow with forensic clues and 1-click **"Approve & Resolve"**.
  - 🚨 **Escalated (< 70% Confidence)**: Safety guardrail preventing financial loss on high-variance or anomalous records (e.g., severe amount mismatches).
- **Explainable Evidence Breakdown**: Explicit separation of **Confirmed Facts** from **Agent Hypotheses** to eliminate hallucination risks.
- **Auditable Lifecycle Trails**: Chronological, timestamped audit events for every reconciliation and operator decision.
- **Interactive Analytics Dashboard**: Built with Vue 3 and Tailwind CSS, featuring live KPIs, tabbed exception queues, and sliding audit inspection panels.

---

## 📁 Project Structure

```text
├── index.html               # Main application entry point & interactive dashboard
├── server.js                # Node.js / Express API backend & static server
├── package.json             # Application dependencies & npm scripts
├── metadata.json            # AI Studio app metadata & capability declarations
├── .env.example             # Environment configuration template
├── frontend/
│   └── dashboard.html       # Standalone dashboard template
└── data/                    # Reconciliation datasets & agent audit logs
    ├── payments.csv         # Gateway payment transactions
    ├── bank_transactions.csv# Bank settlement clearing records
    ├── ledger.csv           # Merchant general ledger entries
    ├── ground_truth.csv     # Benchmarked ground-truth verification data
    ├── phase1_results.json  # Multi-way deterministic match outputs
    └── phase2_results.json  # AI agent investigation & decision classifications
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Node.js** (v18.0 or higher recommended)
- **npm** (comes bundled with Node.js)

### 2. Installation
Clone the repository and install dependencies:

```bash
# Clone repository
git clone https://github.com/Mohamed-529/AISettlement-exception-resolver.git
cd AISettlement-exception-resolver

# Install dependencies
npm install
```

### 3. Run the Development Server
Start the unified backend server and frontend dashboard:

```bash
npm run dev
```

You will see:
```text
Loaded 40 financial exceptions from phase2_results.json
AI Settlement Exception Resolver running at http://localhost:3000
```

### 4. Open the Application
Open your browser and navigate to:
```text
http://localhost:3000
```

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive reconciliation dashboard |
| `GET` | `/health` | Service health status and records loaded check |
| `GET` | `/api/dashboard-data` | Aggregated reconciliation metrics & exceptions payload |
| `GET` | `/api/exceptions` | Filterable exceptions list (`?decision=AUTO_RESOLVE`) |
| `GET` | `/api/exceptions/:id` | Detailed evidence and audit history for an exception |
| `POST` | `/api/exceptions/:id/approve`| Approves and resolves an exception with audit trail logging |

---

## 🛡️ AI Safety & Policy Guardrails

- **Zero Direct Ledger Alterations**: The AI agent operates as an intelligence layer; it only calculates confidence and diagnoses root causes.
- **Strict Thresholding**: State transitions are strictly enforced by policy logic (`AUTO_RESOLVE_THRESHOLD = 0.90`, `SUGGEST_APPROVAL_THRESHOLD = 0.70`).
- **Regulatory Readiness**: Every operator approval or rejection records the operator note, timestamp, and previous state to ensure compliance transparency.

---

## 📄 License
MIT License. Built for financial reconciliation and automated dispute settlement.
