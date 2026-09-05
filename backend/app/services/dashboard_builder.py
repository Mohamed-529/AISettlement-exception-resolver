"""
Builds the judge-facing Phase 3 dashboard: one self-contained HTML file
with the Phase 1 + Phase 2 results embedded directly as JSON, so it
opens by double-click with no server, no build step, and no network
dependency for the data itself (only the two Google Fonts links need
network — everything still renders with system-font fallbacks without
it).

Design: a finance-audit "ledger room" — dark ink background, a serif
display face for headline numbers, monospace for every amount/id/
timestamp (so figures read the way a real statement does), and a
rotated ink-stamp badge as the one signature element, reused for every
decision (AUTO / APPROVAL / ESCALATE) so it reads as a real audit
stamp rather than a generic status pill.
"""

import json


def _safe_json(data: dict) -> str:
    # Prevent a literal "</script" inside any string field from closing
    # the embedding <script> tag early.
    return json.dumps(data).replace("</", "<\\/")


def build_dashboard_html(phase1_payload: dict, phase2_payload: dict) -> str:
    embedded = {
        "phase1": phase1_payload,
        "phase2": phase2_payload,
    }
    data_json = _safe_json(embedded)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Finance Controller — Reconciliation Ledger</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{_CSS}
</style>
</head>
<body>
  <div class="scanline-overlay"></div>

  <header class="topband">
    <div class="brand">
      <span class="eyebrow">AI FINANCE CONTROLLER</span>
      <h1>Reconciliation Ledger</h1>
    </div>
    <div class="meta" id="meta-line">— dataset loading —</div>
  </header>

  <section class="statline" id="statline"></section>

  <main class="workspace">
    <section class="register-panel">
      <div class="register-head">
        <h2>Exception Register</h2>
        <div class="filters" id="filters"></div>
      </div>
      <div class="register-table-wrap">
        <table class="register-table">
          <thead>
            <tr>
              <th>Payment</th>
              <th>Type</th>
              <th class="num">Payment ₹</th>
              <th class="num">Bank ₹</th>
              <th class="num">Ledger ₹</th>
              <th class="num">Confidence</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody id="register-body"></tbody>
        </table>
      </div>
    </section>

    <aside class="evidence-panel" id="evidence-panel">
      <div class="evidence-empty" id="evidence-empty">
        <p class="empty-glyph">§</p>
        <p>Select a case from the register to open its evidence file.</p>
      </div>
      <div class="evidence-content" id="evidence-content" hidden></div>
    </aside>
  </main>

  <section class="tape-section">
    <div class="tape-head">
      <h2>Audit Tape</h2>
      <span class="tape-sub">every decision, timestamped &amp; evidence-backed</span>
    </div>
    <div class="tape" id="tape"></div>
  </section>

  <footer class="foot">
    <span>Phase 1 → deterministic reconciliation · Phase 2 → agent investigation · Phase 3 → this ledger</span>
  </footer>

<script id="embedded-data" type="application/json">{data_json}</script>
<script>
{_JS}
</script>
</body>
</html>
"""


_CSS = """
:root {
  --ink: #0B1220;
  --panel: #121B2B;
  --panel-raised: #172336;
  --hairline: #263349;
  --paper: #EDE7D8;
  --ink-text: #DCE3EE;
  --muted-text: #8593AA;
  --resolved-teal: #4FB0A5;
  --review-brass: #D6A24C;
  --escalate-rust: #C9603F;
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'IBM Plex Sans', -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ink);
  color: var(--ink-text);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
}

.scanline-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(180deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px, transparent 1px, transparent 3px);
  z-index: 999;
}

.topband {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 40px 48px 24px;
  border-bottom: 1px solid var(--hairline);
}

.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--review-brass);
}

.brand h1 {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 34px;
  margin: 6px 0 0;
  letter-spacing: -0.01em;
}

.meta {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--muted-text);
  text-align: right;
}

/* ---- Statement summary strip ---- */
.statline {
  display: flex;
  padding: 0 48px;
  border-bottom: 1px solid var(--hairline);
  overflow-x: auto;
}

.stat {
  flex: 1;
  min-width: 140px;
  padding: 22px 28px;
  border-right: 1px solid var(--hairline);
  opacity: 0;
  transform: translateY(6px);
  animation: rise 0.5s ease forwards;
}
.stat:last-child { border-right: none; }

.stat-label {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted-text);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 600;
  margin-top: 6px;
  font-variant-numeric: tabular-nums;
}

.stat-value.teal { color: var(--resolved-teal); }
.stat-value.brass { color: var(--review-brass); }
.stat-value.rust { color: var(--escalate-rust); }

@keyframes rise { to { opacity: 1; transform: translateY(0); } }

/* ---- Workspace ---- */
.workspace {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 1px;
  background: var(--hairline);
}

.register-panel, .evidence-panel {
  background: var(--ink);
  min-height: 420px;
}

.register-panel { padding: 28px 48px 28px 48px; }
.evidence-panel { padding: 28px 40px; }

.register-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.register-head h2, .tape-head h2 {
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 600;
  margin: 0;
}

.filters {
  display: flex;
  gap: 6px;
}

.filter-btn {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted-text);
  background: var(--panel);
  border: 1px solid var(--hairline);
  border-radius: 4px;
  padding: 6px 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.filter-btn:hover { color: var(--ink-text); border-color: var(--muted-text); }
.filter-btn.active {
  color: var(--ink);
  background: var(--review-brass);
  border-color: var(--review-brass);
}

.register-table-wrap {
  border: 1px solid var(--hairline);
  border-radius: 6px;
  overflow: hidden;
}

.register-table { width: 100%; border-collapse: collapse; font-size: 13px; }

.register-table thead th {
  text-align: left;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted-text);
  background: var(--panel);
  padding: 10px 14px;
  border-bottom: 1px solid var(--hairline);
}
.register-table th.num, .register-table td.num { text-align: right; }

.register-table tbody tr {
  cursor: pointer;
  border-bottom: 1px solid var(--hairline);
  transition: background 0.12s ease;
}
.register-table tbody tr:nth-child(even) { background: rgba(255,255,255,0.012); }
.register-table tbody tr:hover { background: var(--panel-raised); }
.register-table tbody tr.selected { background: var(--panel-raised); outline: 1px solid var(--review-brass); outline-offset: -1px; }

.register-table td { padding: 10px 14px; font-family: var(--font-mono); font-size: 12.5px; }
.register-table td.type-cell { font-family: var(--font-body); font-size: 12.5px; color: var(--muted-text); }

.conf-bar-wrap { display: inline-flex; align-items: center; gap: 6px; }
.conf-bar { width: 46px; height: 4px; background: var(--hairline); border-radius: 2px; overflow: hidden; }
.conf-bar-fill { height: 100%; background: var(--muted-text); }

/* ---- Ink stamp badge — signature element ---- */
.stamp {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 4px 9px;
  border: 1.5px dashed currentColor;
  border-radius: 3px;
  transform: rotate(-2deg);
}
.stamp.auto { color: var(--resolved-teal); }
.stamp.approval { color: var(--review-brass); }
.stamp.escalate { color: var(--escalate-rust); }
.stamp.matched { color: var(--resolved-teal); }
.stamp.large { font-size: 13px; padding: 8px 16px; transform: rotate(-3deg); }

/* ---- Evidence panel ---- */
.evidence-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--muted-text);
  text-align: center;
  padding: 40px 20px;
  font-size: 13px;
}
/* Author `display` rules above beat the UA stylesheet's [hidden]
   default, so hidden must be re-asserted explicitly here or the
   "hidden" attribute set from JS silently does nothing. */
.evidence-empty[hidden], .evidence-content[hidden] { display: none; }
.empty-glyph { font-family: var(--font-display); font-size: 40px; color: var(--hairline); margin: 0 0 10px; }

.evidence-content h3 {
  font-family: var(--font-display);
  font-size: 22px;
  margin: 0 0 2px;
}
.evidence-sub { font-family: var(--font-mono); font-size: 11px; color: var(--muted-text); margin-bottom: 18px; }

.ev-amounts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}
.ev-amount-box {
  background: var(--panel);
  border: 1px solid var(--hairline);
  border-radius: 6px;
  padding: 10px 12px;
}
.ev-amount-label { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted-text); }
.ev-amount-value { font-family: var(--font-mono); font-size: 15px; margin-top: 4px; }
.ev-amount-value.missing { color: var(--escalate-rust); }

.ev-block { margin-bottom: 18px; }
.ev-block-title { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted-text); margin-bottom: 8px; }
.ev-facts { list-style: none; margin: 0; padding: 0; font-size: 13px; line-height: 1.7; }
.ev-facts li::before { content: "✓ "; color: var(--resolved-teal); font-family: var(--font-mono); }

.ev-hypothesis {
  font-size: 13px;
  line-height: 1.6;
  color: var(--ink-text);
  background: var(--panel);
  border-left: 2px solid var(--review-brass);
  padding: 10px 14px;
  border-radius: 0 6px 6px 0;
}

.ev-confidence-row { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.ev-confidence-bar { flex: 1; height: 8px; background: var(--hairline); border-radius: 4px; overflow: hidden; }
.ev-confidence-fill { height: 100%; border-radius: 4px; }
.ev-confidence-num { font-family: var(--font-mono); font-size: 13px; min-width: 44px; text-align: right; }

/* ---- Audit tape ---- */
.tape-section { padding: 28px 48px 40px; border-top: 1px solid var(--hairline); }
.tape-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; }
.tape-sub { font-family: var(--font-mono); font-size: 11px; color: var(--muted-text); }

.tape {
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  background: repeating-linear-gradient(180deg, var(--panel) 0px, var(--panel) 39px, var(--ink) 39px, var(--ink) 40px);
}

.tape-row {
  display: grid;
  grid-template-columns: 150px 90px 190px 1fr 110px;
  gap: 14px;
  padding: 10px 16px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  align-items: center;
  border-bottom: 1px dashed var(--hairline);
}
.tape-row:last-child { border-bottom: none; }
.tape-time { color: var(--muted-text); }
.tape-reason { color: var(--muted-text); font-family: var(--font-body); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.foot {
  padding: 20px 48px 40px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted-text);
  text-align: center;
}

@media (max-width: 900px) {
  .workspace { grid-template-columns: 1fr; }
  .topband, .register-panel, .evidence-panel, .tape-section { padding-left: 20px; padding-right: 20px; }
  .ev-amounts { grid-template-columns: 1fr; }
}

:focus-visible { outline: 2px solid var(--review-brass); outline-offset: 2px; }

@media (prefers-reduced-motion: reduce) {
  .stat { animation: none; opacity: 1; transform: none; }
}
"""

_JS = r"""
const RAW = JSON.parse(document.getElementById('embedded-data').textContent);
const p1 = RAW.phase1.report;
const p1results = RAW.phase1.results;
const p2 = RAW.phase2.summary;
const agentOutputs = RAW.phase2.agent_outputs;
const auditTrail = RAW.phase2.audit_trail;
const evaluation = RAW.phase2.evaluation || null;

const resultsById = {};
p1results.forEach(r => { resultsById[r.payment_id] = r; });

const DECISION_META = {
  AUTO_RESOLVE: { label: 'Auto', cls: 'auto', barColor: 'var(--resolved-teal)' },
  SUGGEST_HUMAN_APPROVAL: { label: 'Approval', cls: 'approval', barColor: 'var(--review-brass)' },
  ESCALATE_HUMAN_REVIEW: { label: 'Escalate', cls: 'escalate', barColor: 'var(--escalate-rust)' },
};

function fmtMoney(v) {
  if (v === null || v === undefined) return '—';
  return '₹' + Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

// ---- Meta line ----
document.getElementById('meta-line').textContent =
  `${p1.metrics.total_records} records · generated ${new Date().toISOString().slice(0,10)}`;

// ---- Stat strip ----
const humanReview = p2.agent_suggested_approval + p2.agent_escalated;
const stats = [
  { label: 'Records Processed', value: p1.metrics.total_records, cls: '' },
  { label: 'Match Rate', value: p1.metrics.match_rate + '%', cls: '' },
  { label: 'Classification Accuracy', value: (evaluation ? evaluation.classification_accuracy : p1.ground_truth_comparison.accuracy) + '%', cls: 'teal' },
  { label: 'Auto Resolved', value: p2.agent_auto_resolved, cls: 'teal' },
  { label: 'Needs Approval', value: p2.agent_suggested_approval, cls: 'brass' },
  { label: 'Escalated', value: p2.agent_escalated, cls: 'rust' },
];
document.getElementById('statline').innerHTML = stats.map(s => `
  <div class="stat">
    <div class="stat-label">${s.label}</div>
    <div class="stat-value ${s.cls}">${s.value}</div>
  </div>
`).join('');

// ---- Filters ----
const FILTERS = [
  { key: 'ALL', label: 'All' },
  { key: 'AUTO_RESOLVE', label: 'Auto-Resolved' },
  { key: 'SUGGEST_HUMAN_APPROVAL', label: 'Needs Approval' },
  { key: 'ESCALATE_HUMAN_REVIEW', label: 'Escalated' },
];
let activeFilter = 'ALL';

document.getElementById('filters').innerHTML = FILTERS.map(f =>
  `<button class="filter-btn ${f.key === activeFilter ? 'active' : ''}" data-key="${f.key}">${f.label}</button>`
).join('');

document.getElementById('filters').addEventListener('click', (e) => {
  const btn = e.target.closest('.filter-btn');
  if (!btn) return;
  activeFilter = btn.dataset.key;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.key === activeFilter));
  renderRegister();
});

// ---- Register table ----
let selectedId = null;

function renderRegister() {
  const rows = agentOutputs.filter(o => activeFilter === 'ALL' || o.decision === activeFilter);
  const tbody = document.getElementById('register-body');
  tbody.innerHTML = rows.map(o => {
    const r = resultsById[o.payment_id] || {};
    const meta = DECISION_META[o.decision] || DECISION_META.ESCALATE_HUMAN_REVIEW;
    const confPct = Math.round(o.confidence * 100);
    return `
      <tr data-id="${o.payment_id}" class="${o.payment_id === selectedId ? 'selected' : ''}">
        <td>${o.payment_id}</td>
        <td class="type-cell">${o.agent_exception_type.replaceAll('_',' ').toLowerCase()}</td>
        <td class="num">${fmtMoney(r.payment_amount)}</td>
        <td class="num">${fmtMoney(r.bank_amount)}</td>
        <td class="num">${fmtMoney(r.ledger_amount)}</td>
        <td class="num">
          <span class="conf-bar-wrap">
            <span class="conf-bar"><span class="conf-bar-fill" style="width:${confPct}%; background:${meta.barColor}"></span></span>
            ${confPct}%
          </span>
        </td>
        <td><span class="stamp ${meta.cls}">${meta.label}</span></td>
      </tr>`;
  }).join('') || `<tr><td colspan="7" style="padding:24px; text-align:center; color:var(--muted-text); font-family:var(--font-body);">No cases in this bucket.</td></tr>`;

  tbody.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', () => selectCase(tr.dataset.id));
  });
}

function selectCase(paymentId) {
  selectedId = paymentId;
  renderRegister();
  const output = agentOutputs.find(o => o.payment_id === paymentId);
  const r = resultsById[paymentId] || {};
  const meta = DECISION_META[output.decision] || DECISION_META.ESCALATE_HUMAN_REVIEW;
  const confPct = Math.round(output.confidence * 100);

  document.getElementById('evidence-empty').hidden = true;
  const content = document.getElementById('evidence-content');
  content.hidden = false;
  content.innerHTML = `
    <h3>${output.payment_id}</h3>
    <div class="evidence-sub">${output.agent_exception_type.replaceAll('_',' ')}</div>

    <div class="ev-amounts">
      <div class="ev-amount-box">
        <div class="ev-amount-label">Payment</div>
        <div class="ev-amount-value">${fmtMoney(r.payment_amount)}</div>
      </div>
      <div class="ev-amount-box">
        <div class="ev-amount-label">Bank</div>
        <div class="ev-amount-value ${r.bank_amount === null ? 'missing' : ''}">${fmtMoney(r.bank_amount)}</div>
      </div>
      <div class="ev-amount-box">
        <div class="ev-amount-label">Ledger</div>
        <div class="ev-amount-value ${r.ledger_amount === null ? 'missing' : ''}">${fmtMoney(r.ledger_amount)}</div>
      </div>
    </div>

    <div class="ev-block">
      <div class="ev-block-title">Facts</div>
      <ul class="ev-facts">${(output.evidence || []).map(f => `<li>${f}</li>`).join('')}</ul>
    </div>

    <div class="ev-block">
      <div class="ev-block-title">Hypothesis — not confirmed</div>
      <div class="ev-hypothesis">${output.root_cause}</div>
    </div>

    <div class="ev-block">
      <div class="ev-block-title">Confidence</div>
      <div class="ev-confidence-row">
        <div class="ev-confidence-bar"><div class="ev-confidence-fill" style="width:${confPct}%; background:${meta.barColor}"></div></div>
        <div class="ev-confidence-num">${confPct}%</div>
      </div>
    </div>

    <span class="stamp large ${meta.cls}">${output.decision.replaceAll('_',' ')}</span>
  `;
}

renderRegister();

// ---- Audit tape ----
document.getElementById('tape').innerHTML = auditTrail.slice().reverse().map(e => {
  const meta = DECISION_META[e.decision] || DECISION_META.ESCALATE_HUMAN_REVIEW;
  return `
    <div class="tape-row">
      <span class="tape-time">${e.timestamp}</span>
      <span>${e.payment_id}</span>
      <span class="stamp ${meta.cls}">${e.decision.replaceAll('_',' ')}</span>
      <span class="tape-reason" title="${e.agent_reasoning_summary.replace(/"/g,'&quot;')}">${e.agent_reasoning_summary}</span>
      <span>${Math.round(e.confidence*100)}% conf.</span>
    </div>`;
}).join('');
"""
