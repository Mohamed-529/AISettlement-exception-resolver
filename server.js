import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// In-memory data store for financial reconciliation exceptions
let exceptions = [];
let totalRecordsCount = 100;
let lastSyncTime = new Date().toISOString();

// Load reconciliation and AI agent audit data
function loadInitialData() {
  try {
    const dataDir = path.join(__dirname, 'data');
    const p1Path = path.join(dataDir, 'phase1_results.json');
    const p2Path = path.join(dataDir, 'phase2_results.json');

    let p1Results = [];
    if (fs.existsSync(p1Path)) {
      const p1Raw = JSON.parse(fs.readFileSync(p1Path, 'utf-8'));
      p1Results = p1Raw.results || [];
      if (p1Raw.report?.metrics?.total_records) {
        totalRecordsCount = p1Raw.report.metrics.total_records;
      }
    }

    const p1Map = new Map();
    for (const r of p1Results) {
      p1Map.set(r.payment_id, r);
    }

    if (fs.existsSync(p2Path)) {
      const p2Raw = JSON.parse(fs.readFileSync(p2Path, 'utf-8'));
      const outputs = p2Raw.agent_outputs || [];
      
      exceptions = outputs.map((ao) => {
        const p1 = p1Map.get(ao.payment_id) || {};
        
        let normDecision = 'NEEDS_APPROVAL';
        if (ao.decision === 'AUTO_RESOLVE') {
          normDecision = 'AUTO_RESOLVE';
        } else if (ao.decision === 'SUGGEST_HUMAN_APPROVAL' || ao.decision === 'NEEDS_APPROVAL') {
          normDecision = 'NEEDS_APPROVAL';
        } else if (ao.decision === 'ESCALATE_HUMAN_REVIEW' || ao.decision === 'ESCALATED') {
          normDecision = 'ESCALATED';
        }

        const paymentAmount = Number(p1.payment_amount || 0);
        const bankAmount = p1.bank_amount != null ? Number(p1.bank_amount) : null;
        const ledgerAmount = p1.ledger_amount != null ? Number(p1.ledger_amount) : paymentAmount;

        return {
          exception_id: `EXC-${ao.payment_id}`,
          payment_id: ao.payment_id,
          exception_type: ao.agent_exception_type || ao.engine_exception_type || 'RECONCILIATION_EXCEPTION',
          transaction_1: {
            transaction_id: `RZP-${ao.payment_id}`,
            amount: paymentAmount,
            date: p1.payment_date || '2026-08-25',
            source: 'Razorpay Gateway',
            description: 'Captured customer payment',
          },
          transaction_2: {
            transaction_id: bankAmount != null ? `BNK-${ao.payment_id}` : `LDG-${ao.payment_id}`,
            amount: bankAmount != null ? bankAmount : ledgerAmount,
            date: p1.bank_date || p1.ledger_date || p1.payment_date || '2026-08-26',
            source: bankAmount != null ? 'Bank Statement' : 'General Ledger',
            description: p1.notes || (bankAmount != null ? 'Settlement transaction' : 'Ledger posting'),
          },
          confidence: ao.confidence ?? 0.85,
          decision: normDecision,
          reasoning: ao.root_cause || 'AI automated exception analysis.',
          audit_trail: [
            `[2026-08-30 09:15:00] Ingested record ${ao.payment_id}`,
            `[2026-08-30 09:15:01] Engine flagged discrepancy: ${ao.engine_exception_type}`,
            `[2026-08-30 09:15:02] AI Agent root-cause diagnosis: ${ao.agent_exception_type}`,
            `[2026-08-30 09:15:03] Confidence: ${Math.round((ao.confidence || 0) * 100)}% -> Decision: ${normDecision}`,
          ],
          evidence: {
            facts: Array.isArray(ao.evidence)
              ? ao.evidence
              : [
                  `Payment captured: ₹${paymentAmount.toFixed(2)}`,
                  bankAmount != null ? `Bank settlement: ₹${bankAmount.toFixed(2)}` : 'Bank record missing',
                  `Ledger entry: ₹${ledgerAmount.toFixed(2)}`,
                ],
            hypotheses: [
              ao.recommendation ? `Agent Recommendation: ${ao.recommendation}` : 'Manual confirmation recommended',
              ao.engine_exception_type ? `Deterministic Engine Flag: ${ao.engine_exception_type}` : null,
              p1.difference ? `Calculated Variance: ₹${p1.difference}` : null,
            ].filter(Boolean),
          },
          timestamp: new Date().toISOString(),
        };
      });

      console.log(`Loaded ${exceptions.length} financial exceptions from phase2_results.json`);
    } else {
      console.warn('phase2_results.json not found, initializing with default sample dataset.');
      exceptions = getFallbackExceptions();
    }
  } catch (err) {
    console.error('Error loading initial data:', err);
    exceptions = getFallbackExceptions();
  }
}

function getFallbackExceptions() {
  return [
    {
      exception_id: 'EXC-P003',
      payment_id: 'P003',
      exception_type: 'POSSIBLE_DELAYED_SETTLEMENT',
      transaction_1: {
        transaction_id: 'RZP-P003',
        amount: 27219.0,
        date: '2026-08-29',
        source: 'Razorpay Gateway',
        description: 'Captured customer payment',
      },
      transaction_2: {
        transaction_id: 'BNK-P003',
        amount: 27219.0,
        date: '2026-08-30',
        source: 'Bank Statement',
        description: 'Settlement transaction',
      },
      confidence: 0.95,
      decision: 'AUTO_RESOLVE',
      reasoning: 'Amounts reconcile; the bank side settled later than the payment date, consistent with normal settlement delay.',
      audit_trail: [
        '[2026-08-30 09:15:00] Ingested record P003',
        '[2026-08-30 09:15:01] Engine flagged discrepancy: DATE_MISMATCH',
        '[2026-08-30 09:15:02] AI Agent diagnosis: POSSIBLE_DELAYED_SETTLEMENT',
        '[2026-08-30 09:15:03] Confidence: 95% -> Decision: AUTO_RESOLVE',
      ],
      evidence: {
        facts: [
          'Payment, bank, and ledger amounts agree: ₹27,219.00',
          'Bank settlement date differs from payment date (1 day variance)',
        ],
        hypotheses: [
          'Agent Recommendation: Auto-resolve',
          'Deterministic Engine Flag: DATE_MISMATCH',
        ],
      },
      timestamp: new Date().toISOString(),
    },
    {
      exception_id: 'EXC-P008',
      payment_id: 'P008',
      exception_type: 'BANK_RECORD_MISSING',
      transaction_1: {
        transaction_id: 'RZP-P008',
        amount: 27486.0,
        date: '2026-08-25',
        source: 'Razorpay Gateway',
        description: 'Captured customer payment',
      },
      transaction_2: {
        transaction_id: 'LDG-P008',
        amount: 27486.0,
        date: '2026-08-25',
        source: 'General Ledger',
        description: 'Ledger posting record',
      },
      confidence: 0.8,
      decision: 'NEEDS_APPROVAL',
      reasoning: 'Payment was captured and recorded in the ledger, but no corresponding bank transaction is present. Possible delayed or missing settlement.',
      audit_trail: [
        '[2026-08-30 09:15:00] Ingested record P008',
        '[2026-08-30 09:15:01] Engine flagged discrepancy: BANK_RECORD_MISSING',
        '[2026-08-30 09:15:02] AI Agent diagnosis: BANK_RECORD_MISSING',
        '[2026-08-30 09:15:03] Confidence: 80% -> Decision: NEEDS_APPROVAL',
      ],
      evidence: {
        facts: [
          'Payment was captured: ₹27,486.00',
          'Ledger entry exists: ₹27,486.00',
          'No matching bank transaction found',
        ],
        hypotheses: [
          'Agent Recommendation: Human review',
          'Deterministic Engine Flag: BANK_RECORD_MISSING',
        ],
      },
      timestamp: new Date().toISOString(),
    },
    {
      exception_id: 'EXC-P005',
      payment_id: 'P005',
      exception_type: 'AMOUNT_MISMATCH',
      transaction_1: {
        transaction_id: 'RZP-P005',
        amount: 193.0,
        date: '2026-08-30',
        source: 'Razorpay Gateway',
        description: 'Captured customer payment',
      },
      transaction_2: {
        transaction_id: 'BNK-P005',
        amount: 1.0,
        date: '2026-08-30',
        source: 'Bank Statement',
        description: 'Settlement transaction',
      },
      confidence: 0.6,
      decision: 'ESCALATED',
      reasoning: 'The bank amount disagrees with the payment amount by -192.0. Cause not confirmed — could be fee deduction, partial settlement, or entry error.',
      audit_trail: [
        '[2026-08-30 09:15:00] Ingested record P005',
        '[2026-08-30 09:15:01] Engine flagged discrepancy: AMOUNT_MISMATCH',
        '[2026-08-30 09:15:02] AI Agent diagnosis: AMOUNT_MISMATCH',
        '[2026-08-30 09:15:03] Confidence: 60% -> Decision: ESCALATED',
      ],
      evidence: {
        facts: [
          'Payment amount: ₹193.00',
          'Bank amount: ₹1.00',
          'Ledger amount: ₹193.00',
        ],
        hypotheses: [
          'Agent Recommendation: Human review',
          'Deterministic Engine Flag: AMOUNT_MISMATCH',
          'Calculated Variance: ₹-192.00',
        ],
      },
      timestamp: new Date().toISOString(),
    },
  ];
}

function computeMetrics() {
  let autoResolved = 0;
  let needsApproval = 0;
  let escalated = 0;

  for (const exc of exceptions) {
    if (exc.decision === 'AUTO_RESOLVE') autoResolved++;
    else if (exc.decision === 'NEEDS_APPROVAL') needsApproval++;
    else if (exc.decision === 'ESCALATED') escalated++;
  }

  const unresolved = needsApproval + escalated;
  const rate = totalRecordsCount > 0
    ? Number((((totalRecordsCount - unresolved) / totalRecordsCount) * 100).toFixed(1))
    : 0;

  return {
    total_transactions: totalRecordsCount,
    total_exceptions: exceptions.length,
    auto_resolved: autoResolved,
    needs_approval: needsApproval,
    escalated: escalated,
    reconciliation_rate: rate,
    last_sync: lastSyncTime,
  };
}

// Initialize dataset
loadInitialData();

// Serve static assets
app.use(express.static(__dirname));
app.use('/frontend', express.static(path.join(__dirname, 'frontend')));

// Primary UI Dashboard
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/dashboard', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    records_loaded: totalRecordsCount,
    exceptions_count: exceptions.length,
  });
});

// Full Dashboard Data endpoint (consumed by dashboard.html Vue 3 frontend)
app.get('/api/dashboard-data', (req, res) => {
  const metrics = computeMetrics();
  res.json({
    ...metrics,
    exceptions,
  });
});

// List exceptions with optional ?decision= filter
app.get('/api/exceptions', (req, res) => {
  const { decision } = req.query;
  let list = exceptions;
  if (decision) {
    list = list.filter((e) => e.decision === decision);
  }
  res.json({
    exceptions: list,
    count: list.length,
  });
});

// Single exception lookup
app.get('/api/exceptions/:id', (req, res) => {
  const { id } = req.params;
  const exc = exceptions.find((e) => e.exception_id === id || e.payment_id === id);
  if (!exc) {
    return res.status(404).json({ error: `Exception ${id} not found` });
  }
  res.json(exc);
});

// Approve & Resolve Exception (POST)
app.post('/api/exceptions/:id/approve', (req, res) => {
  const { id } = req.params;
  const { notes } = req.body || {};

  const exc = exceptions.find((e) => e.exception_id === id || e.payment_id === id);
  if (!exc) {
    return res.status(404).json({ error: `Exception ${id} not found` });
  }

  exc.decision = 'AUTO_RESOLVE';
  const approvalTime = new Date().toISOString();
  exc.audit_trail.push(
    `[${approvalTime}] Exception approved and resolved by finance operator. Note: ${notes || 'Approved'}`
  );
  lastSyncTime = approvalTime;

  res.json({
    status: 'approved',
    exception_id: exc.exception_id,
    timestamp: approvalTime,
    notes: notes || 'Approved by user',
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`AI Settlement Exception Resolver running at http://0.0.0.0:${PORT}`);
});
