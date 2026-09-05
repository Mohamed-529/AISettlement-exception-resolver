# AI Finance Controller

An AI-powered financial reconciliation and analytics system that automates ledger validation, payment matching, and transaction auditing.

## 📁 Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── models/          # Transaction schemas
│   │   ├── services/        # AI Agent, Reconciliation, Audit engines
│   │   ├── utils/           # Performance & processing metrics
│   │   ├── main.py          # Backend entry point
│   │   └── run_all.py       # Full pipeline runner (Phases 1-3)
│   └── requirements.txt     # Python dependencies
├── frontend/
│   └── dashboard.html       # UI Analytics dashboard
├── data/                    # Ledgers, bank transactions, and logs
├── scripts/                 # Mock data generation utilities
└── tests/                   # Automated validation suites
```

## 🚀 Getting Started

### 1. Prerequisites
Make sure you have **Python 3.8+** installed.

### 2. Backend Setup
Navigate to the backend directory, set up a virtual environment, and install dependencies:
```bash
cd backend
python -m venv venv
# Activate on Windows:
.\venv\Scripts\activate
# Activate on Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Generate Mock Data (Optional)
If you need fresh transactional datasets to test with, run:
```bash
python scripts/generate_data.py
```

### 4. Run the Pipeline
To execute the full multi-phase reconciliation and agent decision-making process:
```bash
python backend/app/run_all.py
```

### 5. Launch the Dashboard
Simply open `frontend/dashboard.html` in any web browser to view the processed financial analytics and system normalizer insights.

## 🧪 Running Tests
To verify the accuracy of the reconciliation and decision engines, run:
```bash
pytest tests/
```
