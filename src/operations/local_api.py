import hashlib
import json
import os
from typing import Any, Dict, Optional

from flask import Flask, Response, jsonify, redirect, render_template_string, request, session, url_for

from src.config_loader import ConfigLoader
from src.data_entry.waveapps_account_discovery import WaveappsAccountDiscoveryService
from src.operations.local_autonomy import LocalAutonomousService
from src.operations.local_backup import LocalBackupService, RESTORE_CONFIRMATION_PHRASE
from src.operations.local_bank_transactions import LocalBankTransactionImportService
from src.operations.local_bookkeeping_records import (
    BOOKKEEPING_RECORD_RESOLUTION_STATUSES,
    LocalBookkeepingRecordService,
)
from src.operations.local_close_readiness import LocalCloseReadinessService
from src.operations.local_close_pack import LocalClosePackService
from src.operations.local_exceptions import LocalExceptionQueueService
from src.operations.local_exports import (
    EXPORT_APPROVAL_PHRASE,
    EXPORT_REJECTION_PHRASE,
    EXPORT_RESULT_CONFIRMATION_PHRASE,
    LocalExportAttemptService,
)
from src.operations.local_health import LocalOperationsHealth
from src.operations.local_grouping import LocalDocumentGroupingService
from src.operations.local_intake import DEFAULT_ALLOWED_EXTENSIONS, LocalFolderIntake
from src.operations.local_ledger import (
    VENDOR_CATEGORY_RULE_STATUSES,
    LocalOperationsLedger,
    default_ledger_path,
)
from src.operations.local_master_ledger import LocalMasterLedgerService
from src.operations.local_mijngeldzaken_control import LocalMijngeldzakenControlService
from src.operations.local_processing import LocalDocumentProcessor
from src.operations.local_readiness import LocalReadinessService
from src.operations.local_reconciliation import LocalReconciliationService
from src.operations.local_review import LocalReviewService
from src.operations.local_routing import LocalRoutingService
from src.operations.local_wave_control import LocalWaveControlService


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
REVIEW_RESOLUTION_STATUSES = {"approved", "rejected", "resolved", "ignored"}
RECONCILIATION_RESOLUTION_STATUSES = {"approved", "reconciled", "rejected", "resolved", "ignored", "needs_review"}
RULE_RESOLUTION_STATUSES = VENDOR_CATEGORY_RULE_STATUSES - {"learned"}


DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FAB Operations</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --panel-soft: #f0f5f8;
      --text: #15202b;
      --muted: #5d6b78;
      --line: #d9e2ea;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --danger: #b42318;
      --warning: #a15c07;
      --ok: #166534;
      --shadow: 0 14px 36px rgba(21, 32, 43, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }
    a { color: var(--accent-dark); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .shell { max-width: 1320px; margin: 0 auto; padding: 24px; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      padding: 10px 0 22px;
    }
    h1 { margin: 0; font-size: 30px; line-height: 1.1; letter-spacing: 0; }
    h2 { margin: 0 0 14px; font-size: 18px; line-height: 1.2; letter-spacing: 0; }
    h3 { margin: 0 0 8px; font-size: 15px; line-height: 1.2; letter-spacing: 0; }
    .subtitle { margin: 8px 0 0; color: var(--muted); max-width: 720px; }
    .top-status {
      display: grid;
      gap: 8px;
      min-width: 260px;
      padding: 12px 14px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }
    .status-row { display: flex; justify-content: space-between; gap: 14px; color: var(--muted); }
    .status-row strong { color: var(--text); font-weight: 650; text-align: right; }
    nav {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 18px;
    }
    nav a {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 7px 11px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      font-size: 13px;
      font-weight: 650;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 16px;
      box-shadow: var(--shadow);
      min-height: 96px;
    }
    .metric span { display: block; color: var(--muted); font-size: 12px; font-weight: 650; text-transform: uppercase; }
    .metric strong { display: block; margin-top: 8px; font-size: 30px; line-height: 1; }
    section {
      margin: 18px 0;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
    }
    .section-head p { margin: 4px 0 0; color: var(--muted); }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 880px; }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      background: var(--panel-soft);
      white-space: nowrap;
    }
    tbody tr:hover { background: #f9fbfc; }
    .muted { color: var(--muted); }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 12px; }
    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      border: 1px solid var(--line);
      background: #edf7f4;
      color: var(--accent-dark);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .badge.failed, .badge.rejected { background: #fff1f0; color: var(--danger); }
    .badge.blocked, .badge.blocked_routing, .badge.blocked_by_review, .badge.blocked_invalid_plan, .badge.blocked_unapproved, .badge.high { background: #fff1f0; color: var(--danger); }
    .badge.pending, .badge.review, .badge.needs_review, .badge.in_review, .badge.candidate, .badge.suggested, .badge.missing_receipt, .badge.unmatched_document { background: #fff7e6; color: var(--warning); }
    .badge.attention, .badge.medium, .badge.low { background: #fff7e6; color: var(--warning); }
    .badge.needs_attention, .badge.needs_auth { background: #fff7e6; color: var(--warning); }
    .badge.safe_auto, .badge.safe_draft, .badge.read_only { background: #ecfdf3; color: var(--ok); }
    .badge.review_required, .badge.approval_required, .badge.attention_required, .badge.deferred, .badge.awaiting_approval, .badge.approved_not_submitted, .badge.approved_not_executed { background: #fff7e6; color: var(--warning); }
    .badge.completed, .badge.approved, .badge.executed, .badge.submitted, .badge.resolved, .badge.validated, .badge.routed, .badge.reconciled, .badge.ok { background: #ecfdf3; color: var(--ok); }
    .badge.ready { background: #ecfdf3; color: var(--ok); }
    .badge.not_configured, .badge.disabled { background: #f1f5f9; color: var(--muted); }
    .review-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
      padding: 14px;
    }
    .review-item {
      border: 1px solid var(--line);
      background: #fff;
      padding: 14px;
      min-height: 170px;
    }
    .review-item p { margin: 7px 0; color: var(--muted); }
    form.review-actions {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin-top: 12px;
    }
    .correction-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 8px;
    }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .inline-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
      align-items: center;
    }
    form.table-actions {
      display: inline-flex;
      margin: 0;
    }
    input[type="text"], textarea, select {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      padding: 7px 9px;
      font: inherit;
      background: #fff;
      color: var(--text);
    }
    textarea { min-height: 82px; resize: vertical; }
    button {
      min-height: 36px;
      border: 1px solid var(--accent-dark);
      background: var(--accent);
      color: #fff;
      padding: 7px 11px;
      font: inherit;
      font-size: 13px;
      font-weight: 750;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--accent-dark);
    }
    button.compact {
      min-height: 30px;
      padding: 4px 8px;
      font-size: 12px;
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      padding: 14px 18px 0;
    }
    .summary-item {
      border: 1px solid var(--line);
      background: #fff;
      padding: 10px;
    }
    .summary-item span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .summary-item strong { display: block; margin-top: 5px; font-size: 20px; }
    details {
      padding: 13px 14px;
      border-top: 1px solid var(--line);
      background: #fbfcfd;
    }
    summary { cursor: pointer; font-weight: 700; }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #0f172a;
      color: #e2e8f0;
      padding: 12px;
      margin: 10px 0 0;
      max-height: 260px;
      overflow: auto;
      font-size: 12px;
    }
    .empty { padding: 22px 18px; color: var(--muted); }
    .settings-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
      padding: 14px 18px 18px;
    }
    .setting {
      border: 1px solid var(--line);
      padding: 12px;
      background: #fff;
    }
    .setting span { display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 700; }
    .setting strong { display: block; margin-top: 6px; overflow-wrap: anywhere; }
    @media (max-width: 900px) {
      .shell { padding: 16px; }
      header { display: block; }
      .top-status { margin-top: 16px; min-width: 0; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      form.review-actions { grid-template-columns: 1fr; }
      .inline-actions { justify-content: flex-start; }
    }
    @media (max-width: 520px) {
      .metrics { grid-template-columns: 1fr; }
      h1 { font-size: 25px; }
      .section-head { display: block; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>FAB Operations</h1>
        <p class="subtitle">Local bookkeeping ledger, review queue, and audit trail for the autonomous workflow.</p>
      </div>
      <div class="top-status">
        <div class="status-row"><span>API</span><strong>{{ health.status }}</strong></div>
        <div class="status-row"><span>Auth</span><strong>{{ "required" if health.auth_required else "local" }}</strong></div>
        <div class="status-row"><span>Ledger</span><strong class="mono">{{ ledger_name }}</strong></div>
      </div>
    </header>

    <nav aria-label="FAB operations sections">
      <a href="#overview">Overview</a>
      <a href="#health">Health</a>
      <a href="#close">Close</a>
      <a href="#sources">Sources</a>
      <a href="#autonomy">Autonomy</a>
      <a href="#intake">Intake</a>
      <a href="#ledger">Ledger</a>
      <a href="#groups">Groups</a>
      <a href="#duplicates">Duplicates</a>
      <a href="#records">Records</a>
      <a href="#master-ledger">Master Ledger</a>
      <a href="#fields">Fields</a>
      <a href="#routing">Routing</a>
      <a href="#exports">Exports</a>
      <a href="#mijngeldzaken">MijnGeldzaken</a>
      <a href="#wave">Wave</a>
      <a href="#bank">Bank</a>
      <a href="#reconciliation">Reconciliation</a>
      <a href="#review">Manual Review</a>
      <a href="#rules">Rules</a>
      <a href="#audit">Audit</a>
      <a href="#backups">Backups</a>
      <a href="#settings">Settings</a>
    </nav>

    <div id="overview" class="metrics">
      {% for metric in metric_cards %}
      <div class="metric">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </div>
      {% endfor %}
    </div>

    <section id="health">
      <div class="section-head">
        <div>
          <h2>Operations Health</h2>
          <p>Current queue freshness, routing blocks, failed records, and workflow run state.</p>
        </div>
        <span class="badge {{ operations_health.status }}">{{ operations_health.status }}</span>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Open reviews</span><strong>{{ operations_health.metrics.openReviewItems }}</strong></div>
        <div class="summary-item"><span>Stale reviews</span><strong>{{ operations_health.metrics.staleReviewItems }}</strong></div>
        <div class="summary-item"><span>Stuck docs</span><strong>{{ operations_health.metrics.stuckDocuments }}</strong></div>
        <div class="summary-item"><span>Routing blocks</span><strong>{{ operations_health.metrics.routingBlocks }}</strong></div>
        <div class="summary-item"><span>Drafts waiting</span><strong>{{ operations_health.metrics.pendingRoutingDrafts }}</strong></div>
        <div class="summary-item"><span>Failed docs</span><strong>{{ operations_health.metrics.failedDocuments }}</strong></div>
      </div>
      {% if operations_health.issues %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Issue</th>
              <th>Entity</th>
              <th>Age</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
          {% for issue in operations_health.issues[:10] %}
            <tr>
              <td><span class="badge {{ issue.severity }}">{{ issue.severity }}</span></td>
              <td>{{ issue.type }}</td>
              <td>{{ issue.entityType }} {{ issue.entityId or "" }}</td>
              <td>{{ issue.ageHours if issue.ageHours is not none else "-" }}h</td>
              <td>{{ issue.message }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Recommended next actions</summary>
        <pre>{{ pretty_json(operations_health.nextActions) }}</pre>
      </details>
      {% else %}
      <div class="empty">No operational health issues detected.</div>
      {% endif %}
    </section>

    <section id="exceptions">
      <div class="section-head">
        <div>
          <h2>Exception Queue</h2>
          <p>Actionable failed, stale, blocked, and review-required operating items with safe next steps.</p>
        </div>
        <span class="badge {{ exceptions.status }}">{{ exceptions.status }}</span>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Total</span><strong>{{ exceptions.summary.total }}</strong></div>
        <div class="summary-item"><span>High</span><strong>{{ exceptions.summary.bySeverity.high }}</strong></div>
        <div class="summary-item"><span>Medium</span><strong>{{ exceptions.summary.bySeverity.medium }}</strong></div>
        <div class="summary-item"><span>Low</span><strong>{{ exceptions.summary.bySeverity.low }}</strong></div>
      </div>
      {% if exceptions.exceptions %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Type</th>
              <th>Entity</th>
              <th>Next action</th>
              <th>Safe controls</th>
            </tr>
          </thead>
          <tbody>
          {% for item in exceptions.exceptions[:12] %}
            <tr>
              <td><span class="badge {{ item.severity }}">{{ item.severity }}</span></td>
              <td>{{ item.type }}</td>
              <td>
                {{ item.entityType }} {{ item.entityId or "" }}
                {% if item.entity and item.entity.originalFilename %}
                <div class="muted">{{ item.entity.originalFilename }}</div>
                {% endif %}
              </td>
              <td>{{ item.nextAction }}</td>
              <td>
                {% if item.actions %}
                  {% for action in item.actions %}
                  {% if action.method == "GET" %}
                  <a class="button-link secondary" href="{{ action.dashboardPath or action.path }}">{{ action.id }}</a>
                  {% elif action.safety == "safe_auto" and action.dashboardPath %}
                  <form class="table-actions" method="post" action="{{ action.dashboardPath }}">
                    <button class="compact secondary" type="submit">{{ action.id }}</button>
                  </form>
                  {% else %}
                  <span class="badge {{ action.safety }}">{{ action.id }}</span>
                  {% endif %}
                  {% endfor %}
                {% else %}
                  <span class="muted">Inspect manually</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Raw exception queue</summary>
        <pre>{{ pretty_json(exceptions) }}</pre>
      </details>
      {% else %}
      <div class="empty">No operating exceptions are currently queued.</div>
      {% endif %}
    </section>

    <section id="close">
      <div class="section-head">
        <div>
          <h2>Close Readiness</h2>
          <p>Combines Wave report evidence, reconciliation, review, routing, and export gates into one close decision.</p>
        </div>
        <div class="inline-actions">
          <span class="badge {{ close_readiness.status }}">{{ close_readiness.status }}</span>
          <form class="table-actions" method="post" action="{{ url_for('prepare_close_pack_form') }}">
            <button type="submit" {% if not close_readiness.canClose %}disabled{% endif %}>Prepare pack</button>
          </form>
        </div>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Can close</span><strong>{{ "yes" if close_readiness.canClose else "no" }}</strong></div>
        <div class="summary-item"><span>Blocking gates</span><strong>{{ close_readiness.blockingCount }}</strong></div>
        <div class="summary-item"><span>Attention gates</span><strong>{{ close_readiness.attentionCount }}</strong></div>
        <div class="summary-item"><span>Report controls</span><strong>{{ close_readiness.reportControls.status }}</strong></div>
        <div class="summary-item"><span>Unreconciled bank</span><strong>{{ close_readiness.metrics.unreconciledBankTransactions }}</strong></div>
        <div class="summary-item"><span>Manual reviews</span><strong>{{ close_readiness.metrics.pendingReview }}</strong></div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Gate</th>
              <th>Status</th>
              <th>Message</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody>
          {% for gate in close_readiness.gates %}
            <tr>
              <td>{{ gate.label }}</td>
              <td><span class="badge {{ gate.status }}">{{ gate.status }}</span></td>
              <td>{{ gate.message }}</td>
              <td class="mono">{{ compact_json(gate.evidence) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Close next actions</summary>
        <pre>{{ pretty_json(close_readiness.nextActions) }}</pre>
      </details>
      {% if close_pack_summary %}
      <details open>
        <summary>Last close pack action</summary>
        <pre>{{ pretty_json(close_pack_summary) }}</pre>
      </details>
      {% endif %}
      {% if close_packs.packs %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pack</th>
              <th>Status</th>
              <th>Period</th>
              <th>Created</th>
              <th>SHA-256</th>
              <th>Size</th>
            </tr>
          </thead>
          <tbody>
          {% for pack in close_packs.packs %}
            <tr>
              <td class="mono">{{ pack.closePackFilename }}</td>
              <td><span class="badge {{ pack.status }}">{{ pack.status }}</span></td>
              <td>{{ pack.fromDate or "-" }} - {{ pack.toDate or "-" }}</td>
              <td class="mono">{{ pack.createdAt or "-" }}</td>
              <td class="mono">{{ pack.sha256[:12] if pack.sha256 else "-" }}</td>
              <td>{{ pack.sizeBytes or "-" }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No period close packs have been prepared yet.</div>
      {% endif %}
    </section>

    <section id="sources">
      <div class="section-head">
        <div>
          <h2>Sources</h2>
          <p>Configured and observed document sources with scan provenance, counts, and status.</p>
        </div>
      </div>
      {% if sources %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Type</th>
              <th>Status</th>
              <th>Seen</th>
              <th>Imported</th>
              <th>Duplicates</th>
              <th>Last scan</th>
              <th>Identifier</th>
            </tr>
          </thead>
          <tbody>
          {% for source in sources %}
            <tr>
              <td>{{ source.label }}</td>
              <td>{{ source.source_type }}</td>
              <td><span class="badge {{ source.status }}">{{ source.status }}</span></td>
              <td>{{ source.documents_seen }}</td>
              <td>{{ source.documents_imported }}</td>
              <td>{{ source.duplicates_detected }}</td>
              <td class="mono">{{ source.last_scan_at or "-" }}</td>
              <td class="mono">{{ source.source_identifier }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Raw source registry</summary>
        <pre>{{ pretty_json(sources) }}</pre>
      </details>
      {% else %}
      <div class="empty">No document sources have been observed yet. Run a folder rescan or register a source through the API.</div>
      {% endif %}
    </section>

    <section id="autonomy">
      <div class="section-head">
        <div>
          <h2>Autonomous Cycle</h2>
          <p>Runs only local, policy-gated bookkeeping work: intake, processing, draft preparation, reconciliation candidates, and read-only Wave planning.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('run_autonomy_form') }}">
          <button type="submit" {% if not autonomy_plan.canRunAutonomously %}disabled{% endif %}>Run safe cycle</button>
        </form>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Status</span><strong>{{ autonomy_plan.status }}</strong></div>
        <div class="summary-item"><span>Runnable</span><strong>{{ autonomy_plan.runnableActionIds|length }}</strong></div>
        <div class="summary-item"><span>Manual gates</span><strong>{{ autonomy_plan.manualActionIds|length }}</strong></div>
        <div class="summary-item"><span>Exceptions</span><strong>{{ autonomy_plan.exceptions.total }}</strong></div>
        <div class="summary-item"><span>Imported</span><strong>{{ autonomy_plan.counts.importedDocuments }}</strong></div>
        <div class="summary-item"><span>Routable</span><strong>{{ autonomy_plan.counts.routableDocuments }}</strong></div>
        <div class="summary-item"><span>Bank tx</span><strong>{{ autonomy_plan.counts.unreconciledBankTransactions }}</strong></div>
        <div class="summary-item"><span>External submit</span><strong>{{ autonomy_plan.externalSubmission }}</strong></div>
      </div>
      <div class="empty">{{ autonomy_plan.nextAction }}</div>
      {% if autonomy_plan.exceptions.total %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Operating exception</th>
              <th>Severity</th>
              <th>Entity</th>
              <th>Next action</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
          {% for item in autonomy_plan.exceptions.topExceptions %}
            <tr>
              <td>
                <strong>{{ item.type }}</strong>
                <div class="muted">{{ item.message }}</div>
              </td>
              <td><span class="badge {{ item.severity }}">{{ item.severity }}</span></td>
              <td>{{ item.entityType }} #{{ item.entityId }}</td>
              <td>{{ item.nextAction }}</td>
              <td>
                <div class="button-row">
                {% for action in item.actions %}
                  <a class="button-link secondary" href="{{ action.path }}">{{ action.label }}</a>
                {% endfor %}
                {% if not item.actions %}-{% endif %}
                </div>
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <div class="empty"><a href="#exceptions">Open full exception queue</a></div>
      {% endif %}
      {% if autonomy_summary %}
      <details open>
        <summary>Last autonomous cycle</summary>
        <pre>{{ pretty_json(autonomy_summary) }}</pre>
      </details>
      {% endif %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Action</th>
              <th>Stage</th>
              <th>Mode</th>
              <th>Risk</th>
              <th>Can run</th>
              <th>Evidence</th>
              <th>Gate</th>
            </tr>
          </thead>
          <tbody>
          {% for action in autonomy_plan.actions %}
            <tr>
              <td>{{ action.label }}</td>
              <td>{{ action.stage }}</td>
              <td><span class="badge {{ action.mode }}">{{ action.mode }}</span></td>
              <td><span class="badge {{ action.risk }}">{{ action.risk }}</span></td>
              <td>{{ "yes" if action.canRun else "no" }}</td>
              <td class="mono">{{ compact_json(action.evidence) }}</td>
              <td>{{ action.blockedReason or "ready" }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Raw autonomous plan</summary>
        <pre>{{ pretty_json(autonomy_plan) }}</pre>
      </details>
    </section>

    <section id="intake">
      <div class="section-head">
        <div>
          <h2>Folder Intake</h2>
          <p>Scan configured folders and process imported documents through OCR, categorization, and review gates.</p>
        </div>
        <div class="inline-actions">
          <form class="inline-actions" method="post" action="{{ url_for('rescan_intake_form') }}">
            <button type="submit" {% if not intake_paths %}disabled{% endif %}>Rescan folders</button>
          </form>
          <form class="inline-actions" method="post" action="{{ url_for('process_imported_form') }}">
            <button class="secondary" type="submit">Process imported</button>
          </form>
          <form class="inline-actions" method="post" action="{{ url_for('retry_failed_processing_form') }}">
            <button class="secondary" type="submit">Retry failed</button>
          </form>
        </div>
      </div>
      {% if intake_summary %}
      <div class="summary-grid">
        <div class="summary-item"><span>Scanned</span><strong>{{ intake_summary.scanned }}</strong></div>
        <div class="summary-item"><span>Registered</span><strong>{{ intake_summary.registered }}</strong></div>
        <div class="summary-item"><span>Duplicates</span><strong>{{ intake_summary.duplicates }}</strong></div>
        <div class="summary-item"><span>Already in ledger</span><strong>{{ intake_summary.alreadyRegistered }}</strong></div>
        <div class="summary-item"><span>Skipped</span><strong>{{ intake_summary.skipped|length }}</strong></div>
      </div>
      <details>
        <summary>Last intake run</summary>
        <pre>{{ pretty_json(intake_summary) }}</pre>
      </details>
      {% endif %}
      {% if processing_summary %}
      <div class="summary-grid">
        <div class="summary-item"><span>Requested</span><strong>{{ processing_summary.requested }}</strong></div>
        <div class="summary-item"><span>Retried</span><strong>{{ processing_summary.retried or 0 }}</strong></div>
        <div class="summary-item"><span>Processed</span><strong>{{ processing_summary.processed }}</strong></div>
        <div class="summary-item"><span>Needs review</span><strong>{{ processing_summary.needsReview }}</strong></div>
        <div class="summary-item"><span>Failed</span><strong>{{ processing_summary.failed }}</strong></div>
        <div class="summary-item"><span>Skipped</span><strong>{{ processing_summary.skipped }}</strong></div>
      </div>
      <details>
        <summary>Last processing run</summary>
        <pre>{{ pretty_json(processing_summary) }}</pre>
      </details>
      {% endif %}
      {% if intake_paths %}
      <div class="settings-grid">
        {% for path in intake_paths %}
        <div class="setting"><span>Folder {{ loop.index }}</span><strong class="mono">{{ path }}</strong></div>
        {% endfor %}
        <div class="setting"><span>Allowed extensions</span><strong class="mono">{{ intake_extensions|join(", ") }}</strong></div>
      </div>
      {% else %}
      <div class="empty">No intake folders configured. Add local_intake_paths under [operations].</div>
      {% endif %}
    </section>

    <section id="ledger">
      <div class="section-head">
        <div>
          <h2>Document Ledger</h2>
          <p>{{ documents|length }} latest documents from the local operating ledger.</p>
        </div>
      </div>
      {% if documents %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Source</th>
              <th>File</th>
              <th>Vendor</th>
              <th>Amount</th>
              <th>Date</th>
              <th>Category</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
          {% for doc in documents %}
            <tr>
              <td class="mono">#{{ doc.id }}</td>
              <td>{{ doc.source }}</td>
              <td>
                <a href="{{ url_for('document_detail_page', document_id=doc.id) }}">{{ doc.original_filename }}</a>
                <div class="muted mono">{{ doc.source_document_id or "no source id" }}</div>
              </td>
              <td>{{ doc.vendor_name or "Unknown" }}</td>
              <td>{{ format_money(doc.total_amount) }}</td>
              <td>{{ doc.transaction_date or "-" }}</td>
              <td>{{ doc.category or "Unassigned" }}</td>
              <td>{{ format_confidence(doc.confidence_score) }}</td>
              <td><span class="badge {{ doc.processing_status }}">{{ doc.processing_status }}</span></td>
              <td>
                {% if doc.processing_status == "imported" %}
                <form class="table-actions" method="post" action="{{ url_for('process_document_form', document_id=doc.id) }}">
                  <button class="compact secondary" type="submit">Process</button>
                </form>
                {% elif doc.processing_status == "failed" %}
                <form class="table-actions" method="post" action="{{ url_for('retry_document_processing_form', document_id=doc.id) }}">
                  <button class="compact secondary" type="submit">Retry</button>
                </form>
                {% elif doc.processing_status in ["processed", "reviewed", "validated", "ready_to_route"] %}
                <form class="table-actions" method="post" action="{{ url_for('route_document_form', document_id=doc.id) }}">
                  <button class="compact secondary" type="submit">Prepare Wave draft</button>
                </form>
                {% else %}
                <span class="muted">-</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No documents have been registered yet.</div>
      {% endif %}
    </section>

    <section id="groups">
      <div class="section-head">
        <div>
          <h2>Document Groups</h2>
          <p>Candidate scanner batches and manual merge/split groups before documents are routed or exported.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('detect_document_groups_form') }}">
          <button type="submit">Detect scanner groups</button>
        </form>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Groups</span><strong>{{ metrics.document_groups }}</strong></div>
        <div class="summary-item"><span>Need review</span><strong>{{ metrics.open_document_groups }}</strong></div>
      </div>
      {% if grouping_summary %}
      <details open>
        <summary>Last grouping run</summary>
        <pre>{{ pretty_json(grouping_summary) }}</pre>
      </details>
      {% endif %}
      {% if document_groups %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Group</th>
              <th>Type</th>
              <th>Members</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Reason</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
          {% for group in document_groups %}
            <tr>
              <td>
                <strong>#{{ group.id }} {{ group.title or group.group_key }}</strong>
                <div class="muted mono">{{ group.group_key }}</div>
              </td>
              <td>{{ group.group_type }}</td>
              <td>
                {{ group.member_count }}
                {% for member in group.members[:3] %}
                <div class="muted mono">#{{ member.document_id }} {{ member.document.original_filename if member.document else "" }} {{ "(" ~ member.status ~ ")" if member.status != "active" else "" }}</div>
                {% endfor %}
              </td>
              <td>{{ format_confidence(group.confidence_score) }}</td>
              <td><span class="badge {{ group.status }}">{{ group.status }}</span></td>
              <td>{{ group.reason or "-" }}</td>
              <td class="mono">{{ group.updated_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No document groups have been detected yet. Run scanner detection after importing local/scanner folders.</div>
      {% endif %}
    </section>

    <section id="duplicates">
      <div class="section-head">
        <div>
          <h2>Duplicate Candidates</h2>
          <p>Review exact and fuzzy duplicate evidence before FAB blocks, ignores, or routes documents.</p>
        </div>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Candidates</span><strong>{{ metrics.duplicate_candidates }}</strong></div>
        <div class="summary-item"><span>Open</span><strong>{{ metrics.open_duplicate_candidates }}</strong></div>
        <div class="summary-item"><span>Marked duplicate</span><strong>{{ metrics.duplicates }}</strong></div>
      </div>
      {% if duplicate_candidates %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Documents</th>
              <th>Match</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Evidence</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
          {% for candidate in duplicate_candidates %}
            <tr>
              <td class="mono">#{{ candidate.id }}</td>
              <td class="mono">#{{ candidate.document_id }} -> #{{ candidate.candidate_document_id }}</td>
              <td>{{ candidate.match_type }}</td>
              <td>{{ format_confidence(candidate.confidence_score) }}</td>
              <td><span class="badge {{ candidate.status }}">{{ candidate.status }}</span></td>
              <td class="mono">{{ compact_json(candidate.evidence) }}</td>
              <td class="mono">{{ candidate.updated_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No duplicate candidates have been recorded yet.</div>
      {% endif %}
    </section>

    <section id="records">
      <div class="section-head">
        <div>
          <h2>Bookkeeping Records</h2>
          <p>Normalized financial records that connect source evidence, review state, export readiness, and reconciliation.</p>
        </div>
        <div class="inline-actions">
          <form class="table-actions" method="post" action="{{ url_for('refresh_bookkeeping_records_form') }}">
            <input type="hidden" name="sourceType" value="document">
            <button class="compact secondary" type="submit">Refresh document records</button>
          </form>
          <form class="table-actions" method="post" action="{{ url_for('refresh_bookkeeping_records_form') }}">
            <input type="hidden" name="sourceType" value="bank_transaction">
            <button class="compact secondary" type="submit">Refresh bank records</button>
          </form>
          <form class="table-actions" method="post" action="{{ url_for('refresh_bookkeeping_records_form') }}">
            <input type="hidden" name="sourceType" value="all">
            <button class="compact" type="submit">Refresh all records</button>
          </form>
        </div>
      </div>
      {% if record_refresh_summary %}
      <details open>
        <summary>Last record refresh</summary>
        <pre>{{ pretty_json(record_refresh_summary) }}</pre>
      </details>
      {% endif %}
      <div class="summary-grid">
        <div class="summary-item"><span>Records</span><strong>{{ metrics.bookkeeping_records }}</strong></div>
        <div class="summary-item"><span>Line items</span><strong>{{ metrics.bookkeeping_record_line_items }}</strong></div>
        <div class="summary-item"><span>Need review</span><strong>{{ metrics.bookkeeping_records_needing_review }}</strong></div>
        <div class="summary-item"><span>Export ready</span><strong>{{ metrics.export_ready_records }}</strong></div>
      </div>
      {% if bookkeeping_records %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Source</th>
              <th>Vendor</th>
              <th>Amount</th>
              <th>Date</th>
              <th>Lines</th>
              <th>Account / Tax</th>
              <th>Category</th>
              <th>Target</th>
              <th>Status</th>
              <th>Export</th>
              <th>Reconciliation</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
          {% for record in bookkeeping_records %}
            <tr>
              <td class="mono"><a href="{{ url_for('bookkeeping_record_detail_page', record_id=record.id) }}">#{{ record.id }}</a></td>
              <td>
                {{ record.source_type }}
                <div class="muted mono">
                  {% if record.document_id %}doc #{{ record.document_id }}{% elif record.bank_transaction_id %}bank #{{ record.bank_transaction_id }}{% else %}-{% endif %}
                </div>
              </td>
              <td>{{ record.vendor_name or "Unknown" }}</td>
              <td>{{ format_money(record.amount) }} {{ record.currency }}</td>
              <td>{{ record.record_date or "-" }}</td>
              <td>
                {{ record.line_item_count or 0 }}
                {% if record.line_items %}
                <div class="muted">{{ record.line_items[0].description or record.line_items[0].item_name or "Line item" }}</div>
                {% endif %}
              </td>
              <td>
                {% if record.line_items %}
                {{ record.line_items[0].account_name or record.target_account or "Unmapped" }}
                <div class="muted">
                  tax {{ record.line_items[0].tax_code or "unmapped" }}
                  {% if record.line_items[0].tax_rate is not none %} / {{ record.line_items[0].tax_rate }}%{% endif %}
                </div>
                {% else %}
                {{ record.target_account or "Unmapped" }}
                {% endif %}
              </td>
              <td>{{ record.category or "Unassigned" }}</td>
              <td>{{ record.target_system }}</td>
              <td><span class="badge {{ record.status }}">{{ record.status }}</span></td>
              <td><span class="badge {{ record.export_status }}">{{ record.export_status }}</span></td>
              <td><span class="badge {{ record.reconciliation_status }}">{{ record.reconciliation_status }}</span></td>
              <td>
                {% if record.review_required or record.status in ["needs_review", "missing_receipt", "failed", "duplicate"] %}
                <form class="table-actions" method="post" action="{{ url_for('resolve_bookkeeping_record_form', record_id=record.id) }}">
                  <input type="hidden" name="status" value="approved">
                  <input type="hidden" name="resolution" value="Approved normalized bookkeeping record from dashboard.">
                  <button class="compact" type="submit">Approve</button>
                </form>
                <form class="table-actions" method="post" action="{{ url_for('resolve_bookkeeping_record_form', record_id=record.id) }}">
                  <input type="hidden" name="status" value="rejected">
                  <input type="hidden" name="resolution" value="Rejected normalized bookkeeping record from dashboard.">
                  <button class="compact secondary" type="submit">Reject</button>
                </form>
                {% elif record.status not in ["rejected", "ignored"] %}
                <form class="table-actions" method="post" action="{{ url_for('resolve_bookkeeping_record_form', record_id=record.id) }}">
                  <input type="hidden" name="status" value="needs_review">
                  <input type="hidden" name="resolution" value="Reopened normalized bookkeeping record for manual review.">
                  <button class="compact secondary" type="submit">Reopen review</button>
                </form>
                {% endif %}
                {% if record.source_type == "bank_transaction" %}
                <form class="table-actions" method="post" action="{{ url_for('route_bookkeeping_record_form', record_id=record.id) }}">
                  <button class="compact" type="submit">Prepare draft</button>
                </form>
                {% else %}
                <span class="muted">Document route</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No normalized bookkeeping records have been created yet. Process documents or import bank transactions to populate this operating layer.</div>
      {% endif %}
    </section>

    <section id="master-ledger">
      <div class="section-head">
        <div>
          <h2>Master Ledger</h2>
          <p>FAB source-of-truth projection across normalized records, Wave/MGZ downstream state, checksums, and blockers.</p>
        </div>
        <div class="inline-actions">
          <a class="button-link secondary" href="{{ url_for('master_ledger_api') }}">JSON</a>
          <a class="button-link secondary" href="{{ url_for('master_ledger_api', format='csv') }}">CSV</a>
        </div>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Rows</span><strong>{{ master_ledger.summary.totalRows }}</strong></div>
        <div class="summary-item"><span>Blocked</span><strong>{{ master_ledger.summary.blockedRows }}</strong></div>
        <div class="summary-item"><span>Ready drafts</span><strong>{{ master_ledger.summary.readyForDraft }}</strong></div>
        <div class="summary-item"><span>Need approval</span><strong>{{ master_ledger.summary.readyForApproval }}</strong></div>
        <div class="summary-item"><span>Executable</span><strong>{{ master_ledger.summary.readyForExternalExecution }}</strong></div>
        <div class="summary-item"><span>Checksum</span><strong class="mono">{{ master_ledger.ledgerChecksum[:12] if master_ledger.ledgerChecksum else "-" }}</strong></div>
      </div>
      {% if master_ledger.rows %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Record</th>
              <th>Date</th>
              <th>Vendor</th>
              <th>Amount</th>
              <th>Target</th>
              <th>Downstream</th>
              <th>Proof</th>
              <th>Blockers</th>
            </tr>
          </thead>
          <tbody>
          {% for row in master_ledger.rows[:25] %}
            <tr>
              <td class="mono">#{{ row.recordId }}<div class="muted">{{ row.sourceType }}</div></td>
              <td>{{ row.recordDate or "-" }}</td>
              <td>{{ row.vendorName or row.description or "Unknown" }}</td>
              <td>{{ format_money(row.amount) }} {{ row.currency }}</td>
              <td>{{ row.targetSystem }}<div class="muted">{{ row.targetAccount or "unmapped" }}</div></td>
              <td>
                <span class="badge {{ row.downstreamStatus }}">{{ row.downstreamStatus }}</span>
                <div class="muted">{{ row.externalSubmission }}</div>
              </td>
              <td>
                <div class="mono">{{ row.rowChecksum[:12] }}</div>
                {% if row.masterLedgerChecksum %}
                <div class="muted mono">draft {{ row.masterLedgerChecksum[:12] }}</div>
                {% endif %}
                {% if row.exportAttemptId %}
                <div class="muted mono">export #{{ row.exportAttemptId }}</div>
                {% endif %}
              </td>
              <td>
                {% if row.blockers %}
                {{ row.blockers|join(", ") }}
                {% else %}
                <span class="muted">clear</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No master-ledger rows yet. Refresh records after processing documents or importing bank transactions.</div>
      {% endif %}
      <details>
        <summary>Master ledger summary</summary>
        <pre>{{ pretty_json(master_ledger.summary) }}</pre>
      </details>
    </section>

    <section id="fields">
      <div class="section-head">
        <div>
          <h2>Extracted Fields</h2>
          <p>Structured OCR/extraction evidence with confidence and provenance for review and learning.</p>
        </div>
      </div>
      {% if extracted_fields %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Field</th>
              <th>Value</th>
              <th>Confidence</th>
              <th>Source</th>
              <th>Provenance</th>
            </tr>
          </thead>
          <tbody>
          {% for field in extracted_fields %}
            <tr>
              <td class="mono">#{{ field.document_id }}</td>
              <td>{{ field.field_name }}</td>
              <td class="mono">{{ compact_json(field.field_value) }}</td>
              <td>{{ format_confidence(field.confidence_score) }}</td>
              <td>{{ field.source }}</td>
              <td class="mono">{{ compact_json(field.provenance) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No extracted field records have been stored yet. Process an imported document to populate this evidence.</div>
      {% endif %}
    </section>

    <section id="routing">
      <div class="section-head">
        <div>
          <h2>Routing & Export Drafts</h2>
          <p>Prepare Wave draft operations from reviewed documents and bank records without submitting data externally.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('prepare_ready_routes_form') }}">
          <input type="hidden" name="sourceType" value="all">
          <button type="submit">Prepare ready drafts</button>
        </form>
      </div>
      {% if routing_summary %}
      <div class="summary-grid">
        <div class="summary-item"><span>Requested</span><strong>{{ routing_summary.requested }}</strong></div>
        <div class="summary-item"><span>Drafts</span><strong>{{ routing_summary.draftPrepared }}</strong></div>
        <div class="summary-item"><span>Already ready</span><strong>{{ routing_summary.alreadyPrepared }}</strong></div>
        <div class="summary-item"><span>Needs review</span><strong>{{ routing_summary.needsReview }}</strong></div>
        <div class="summary-item"><span>Blocked</span><strong>{{ routing_summary.blocked }}</strong></div>
      </div>
      <details>
        <summary>Last routing run</summary>
        <pre>{{ pretty_json(routing_summary) }}</pre>
      </details>
      {% endif %}
      {% if routing_attempts %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Source</th>
              <th>Target</th>
              <th>Status</th>
              <th>Wave action</th>
              <th>Message</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
          {% for attempt in routing_attempts %}
            {% set operation = attempt.metadata.operation if attempt.metadata and attempt.metadata.operation else None %}
            <tr>
              <td class="mono">#{{ attempt.id }}</td>
              <td class="mono">
                {% if attempt.document_id %}
                doc #{{ attempt.document_id }}
                {% elif attempt.bookkeeping_record_id %}
                record #{{ attempt.bookkeeping_record_id }}
                {% elif attempt.metadata and attempt.metadata.bookkeepingRecordId %}
                record #{{ attempt.metadata.bookkeepingRecordId }}
                {% else %}
                -
                {% endif %}
              </td>
              <td>{{ attempt.target }}</td>
              <td><span class="badge {{ attempt.status }}">{{ attempt.status }}</span></td>
              <td>{{ operation.action_id if operation else "-" }}</td>
              <td>{{ attempt.message or "-" }}</td>
              <td class="mono">{{ attempt.created_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No export drafts or routing blocks have been recorded yet.</div>
      {% endif %}
    </section>

    <section id="exports">
      <div class="section-head">
        <div>
          <h2>Export Attempts</h2>
          <p>FAB-owned approval and result ledger for Wave operations; approvals never submit externally by themselves.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('prepare_ready_export_attempts_form') }}">
          <button type="submit">Prepare export approvals</button>
        </form>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Attempts</span><strong>{{ metrics.export_attempts }}</strong></div>
        <div class="summary-item"><span>Need approval</span><strong>{{ metrics.export_attempts_needing_approval }}</strong></div>
        <div class="summary-item"><span>Approved</span><strong>{{ metrics.approved_export_attempts }}</strong></div>
        <div class="summary-item"><span>Needs attention</span><strong>{{ metrics.attention_export_attempts }}</strong></div>
        <div class="summary-item"><span>Deferred</span><strong>{{ metrics.deferred_export_attempts }}</strong></div>
        <div class="summary-item"><span>Needs supervision</span><strong>{{ metrics.supervised_export_attempts }}</strong></div>
        <div class="summary-item"><span>Executed</span><strong>{{ metrics.executed_export_attempts }}</strong></div>
      </div>
      {% if export_summary %}
      <details>
        <summary>Last export preparation run</summary>
        <pre>{{ pretty_json(export_summary) }}</pre>
      </details>
      {% endif %}
      {% if export_attempts %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Source</th>
              <th>Target</th>
              <th>Action</th>
              <th>Status</th>
              <th>External</th>
              <th>Approval</th>
              <th>Message</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
          {% for export in export_attempts %}
            <tr>
              <td class="mono">#{{ export.id }}</td>
              <td class="mono">
                {% if export.document_id %}
                doc #{{ export.document_id }}
                {% elif export.bookkeeping_record_id %}
                record #{{ export.bookkeeping_record_id }}
                {% else %}
                -
                {% endif %}
              </td>
              <td>
                {{ export.target_system }}
                <div class="muted">{{ export.surface or "-" }}</div>
              </td>
              <td>
                {{ export.action_id or "-" }}
                <div class="muted mono">{{ export.operation_id or "-" }}</div>
                {% if export.external_id %}
                <div class="muted">Wave ID</div>
                <div class="muted mono">{{ export.external_id }}</div>
                {% endif %}
                {% if export.metadata and export.metadata.masterLedgerDraft %}
                <div class="muted">Master ledger {{ export.metadata.masterLedgerDraft.draftType }}</div>
                <div class="muted mono">{{ export.metadata.masterLedgerChecksum[:12] if export.metadata.masterLedgerChecksum else export.metadata.masterLedgerDraft.checksum[:12] }}</div>
                <div><a href="{{ url_for('export_attempt_artifact', export_attempt_id=export.id, format='csv' if export.metadata.masterLedgerDraft.draftType == 'transaction_import' else 'json') }}">Artifact</a></div>
                {% endif %}
              </td>
              <td><span class="badge {{ export.status }}">{{ export.status }}</span></td>
              <td><span class="badge {{ export.external_submission }}">{{ export.external_submission }}</span></td>
              <td>
                {% if export.approval_required %}
                Required
                {% elif export.approved_at %}
                {{ export.approved_by or "approved" }}<div class="muted mono">{{ export.approved_at }}</div>
                {% else %}
                -
                {% endif %}
              </td>
              <td>{{ export.message or "-" }}</td>
              <td>
                {% if export.metadata and export.metadata.masterLedgerDraft and export.status != "supervision_required" and export.external_submission not in ["queued", "submitted", "executed"] %}
                <form class="table-actions" method="post" action="{{ url_for('regenerate_export_attempt_form', export_attempt_id=export.id) }}">
                  <button class="compact secondary" type="submit">Regenerate draft</button>
                </form>
                {% endif %}
                {% if export.status in ["approval_required", "prepared", "attention_required"] %}
                {% if export.status == "attention_required" %}
                <div class="muted">Resolve the linked review/configuration issue, then approve again.</div>
                {% endif %}
                <form class="table-actions" method="post" action="{{ url_for('approve_export_attempt_form', export_attempt_id=export.id) }}">
                  <input type="text" name="confirmation" placeholder="{{ export_approval_phrase }}">
                  <button class="compact" type="submit">Approve</button>
                </form>
                <form class="table-actions" method="post" action="{{ url_for('reject_export_attempt_form', export_attempt_id=export.id) }}">
                  <input type="text" name="confirmation" placeholder="{{ export_rejection_phrase }}">
                  <button class="compact secondary" type="submit">Reject</button>
                </form>
                {% elif export.status == "approved" %}
                <form class="review-actions" method="post" action="{{ url_for('execute_export_attempt_form', export_attempt_id=export.id) }}">
                  <button type="submit">Execute</button>
                </form>
                <form class="review-actions" method="post" action="{{ url_for('reject_export_attempt_form', export_attempt_id=export.id) }}">
                  <input type="text" name="confirmation" placeholder="{{ export_rejection_phrase }}">
                  <button class="compact secondary" type="submit">Cancel approval</button>
                </form>
                <form class="review-actions" method="post" action="{{ url_for('record_export_attempt_result_form', export_attempt_id=export.id) }}">
                  <select name="status" aria-label="Export result">
                    <option value="executed">Executed</option>
                    <option value="queued">Queued</option>
                    <option value="failed">Failed</option>
                  </select>
                  <input type="text" name="externalId" placeholder="External ID">
                  <input type="text" name="confirmation" placeholder="{{ export_result_confirmation_phrase }}">
                  <button class="compact secondary" type="submit">Record result</button>
                </form>
                {% elif export.status == "supervision_required" %}
                <div class="muted">Complete the stored artifact import in your MijnGeldzaken session.</div>
                <form class="review-actions" method="post" action="{{ url_for('record_export_attempt_result_form', export_attempt_id=export.id) }}">
                  <select name="status" aria-label="Supervised export result">
                    <option value="executed">Executed</option>
                    <option value="submitted">Submitted</option>
                    <option value="failed">Failed</option>
                  </select>
                  <input type="text" name="externalId" placeholder="Receipt reference">
                  <input type="text" name="confirmation" placeholder="{{ export_result_confirmation_phrase }}">
                  <button class="compact secondary" type="submit">Record supervised result</button>
                </form>
                {% else %}
                -
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No export attempts have been prepared yet. Prepare Wave drafts first, then prepare export approvals.</div>
      {% endif %}
    </section>

    <section id="mijngeldzaken">
      <div class="section-head">
        <div>
          <h2>MijnGeldzaken Control Center</h2>
          <p>Model household-bookkeeping menus, master-ledger sync, document vault, planning, and account-health actions before external execution.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('plan_mijngeldzaken_workflow_form') }}">
          <select name="workflowId" aria-label="MijnGeldzaken workflow">
            <option value="master_ledger_downstream_sync">Master ledger sync</option>
            <option value="document_vault_sync">Document vault</option>
            <option value="planning_context_read">Planning context</option>
            <option value="connection_health_check">Connection health</option>
          </select>
          <input type="text" name="fromDate" placeholder="From date">
          <input type="text" name="toDate" placeholder="To date">
          <button type="submit">Plan MGZ workflow</button>
        </form>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Surfaces</span><strong>{{ mijngeldzaken_control.summary.surfaces }}</strong></div>
        <div class="summary-item"><span>Actions</span><strong>{{ mijngeldzaken_control.summary.actions }}</strong></div>
        <div class="summary-item"><span>Features</span><strong>{{ mijngeldzaken_control.summary.feature_pages }}</strong></div>
        <div class="summary-item"><span>Read-only</span><strong>{{ mijngeldzaken_control.summary.actions_by_safety.read_only }}</strong></div>
        <div class="summary-item"><span>Safe drafts</span><strong>{{ mijngeldzaken_control.summary.actions_by_safety.safe_draft }}</strong></div>
        <div class="summary-item"><span>Confirmations</span><strong>{{ mijngeldzaken_control.summary.actions_by_safety.requires_confirmation }}</strong></div>
      </div>
      {% if mijngeldzaken_plan_summary %}
      <details open>
        <summary>Last MijnGeldzaken workflow plan</summary>
        <pre>{{ pretty_json(mijngeldzaken_plan_summary) }}</pre>
      </details>
      {% endif %}
      {% if mijngeldzaken_controls %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Master-ledger gate</th>
              <th>Status</th>
              <th>Count</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
          {% for gate in mijngeldzaken_controls.gates %}
            <tr>
              <td><strong>{{ gate.label }}</strong></td>
              <td><span class="badge {{ gate.status }}">{{ gate.status }}</span></td>
              <td>{{ gate.count }}</td>
              <td>{{ gate.description }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>MijnGeldzaken next actions</summary>
        <pre>{{ pretty_json(mijngeldzaken_controls.nextActions) }}</pre>
      </details>
      {% endif %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Feature surface</th>
              <th>Mode</th>
              <th>Controls</th>
              <th>Gate</th>
            </tr>
          </thead>
          <tbody>
          {% for feature_id, feature in mijngeldzaken_control.featureInventory.items() %}
            <tr>
              <td>
                <strong>{{ feature.surface }}</strong>
                <div class="muted">{{ feature.module }} / {{ feature_id }}</div>
              </td>
              <td><span class="badge {{ feature.automation_mode }}">{{ feature.automation_mode }}</span></td>
              <td>{{ feature.controls|length }}</td>
              <td>{{ feature.review_gate }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>MijnGeldzaken guardrails and sync contract</summary>
        <pre>{{ pretty_json({"credentials": mijngeldzaken_control.credentials, "safetyPolicy": mijngeldzaken_control.safetyPolicy, "syncContracts": mijngeldzaken_control.syncContracts}) }}</pre>
      </details>
    </section>

    <section id="wave">
      <div class="section-head">
        <div>
          <h2>Wave Control Center</h2>
          <p>Model Wave menus, reports, and actions as FAB-owned operation plans before anything is executed externally.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('plan_wave_workflow_form') }}">
          <select name="workflowId" aria-label="Wave workflow">
            <option value="daily_reconciliation_run">Daily reconciliation</option>
            <option value="period_close_pack">Period close pack</option>
          </select>
          <input type="text" name="fromDate" placeholder="From date">
          <input type="text" name="toDate" placeholder="To date">
          <button type="submit">Plan Wave workflow</button>
        </form>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Surfaces</span><strong>{{ wave_control.summary.surfaces }}</strong></div>
        <div class="summary-item"><span>Actions</span><strong>{{ wave_control.summary.actions }}</strong></div>
        <div class="summary-item"><span>Reports</span><strong>{{ wave_control.summary.reports }}</strong></div>
        <div class="summary-item"><span>Read-only</span><strong>{{ wave_control.summary.actions_by_safety.read_only }}</strong></div>
        <div class="summary-item"><span>Safe drafts</span><strong>{{ wave_control.summary.actions_by_safety.safe_draft }}</strong></div>
        <div class="summary-item"><span>Confirmations</span><strong>{{ wave_control.summary.actions_by_safety.requires_confirmation }}</strong></div>
      </div>
      <div class="section-head" style="padding: 14px 18px 0;">
        <div>
          <h3>Verified account mappings</h3>
          <p>Read Wave's chart of accounts and confirm the exact anchor and category IDs used by approved exports.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('discover_wave_accounts_form') }}">
          <select name="targetSystem" aria-label="Wave target account">
            <option value="waveapps_business">Wave Business</option>
            <option value="waveapps_personal">Wave Personal</option>
          </select>
          <button type="submit">Refresh accounts</button>
        </form>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Target</th><th>Configuration</th><th>Anchor account</th><th>Category accounts</th><th>Discovery</th></tr></thead>
          <tbody>
          {% for mapping in wave_control.accountMappings.targets %}
            <tr>
              <td><strong>{{ mapping.targetSystem }}</strong></td>
              <td><span class="badge {{ 'ready' if mapping.configured else 'blocked' }}">{{ 'configured' if mapping.configured else 'missing' }}</span><div class="muted">{{ ", ".join(mapping.requiredMissing) if mapping.requiredMissing else "All required settings present" }}</div></td>
              <td><span class="mono">{{ mapping.anchorAccount.accountId or '-' }}</span><div class="muted">verified {{ mapping.anchorAccount.verified if mapping.anchorAccount.verified is not none else 'not checked' }}</div></td>
              <td>{{ mapping.categoryAccounts|length }} mapped<div class="muted">verified {{ mapping.verified if mapping.accountsDiscovered is not none else 'not checked' }}</div></td>
              <td>{{ mapping.accountsDiscovered if mapping.accountsDiscovered is not none else '-' }} accounts</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% if wave_account_discovery_summary %}
      <details open>
        <summary>Last Wave account discovery</summary>
        <pre>{{ pretty_json(wave_account_discovery_summary) }}</pre>
      </details>
      {% endif %}
      {% if wave_plan_summary %}
      <details open>
        <summary>Last Wave workflow plan</summary>
        <pre>{{ pretty_json(wave_plan_summary) }}</pre>
      </details>
      {% endif %}
      {% if wave_report_controls %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Report control gate</th>
              <th>Required actions</th>
              <th>Planned actions</th>
              <th>Evidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
          {% for gate in wave_report_controls.gates %}
            <tr>
              <td>
                <strong>{{ gate.label }}</strong>
                <div class="muted">{{ gate.section }}</div>
              </td>
              <td>{{ ", ".join(gate.requiredActions) }}</td>
              <td>{{ ", ".join(gate.plannedActions) if gate.plannedActions else "-" }}</td>
              <td>{{ gate.snapshotCount }} snapshots{% if gate.hasResultPayload %} / result payload{% endif %}</td>
              <td><span class="badge {{ gate.status }}">{{ gate.status }}</span></td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Report control next actions</summary>
        <pre>{{ pretty_json(wave_report_controls.nextActions) }}</pre>
      </details>
      {% endif %}
      {% if wave_report_snapshots %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Report evidence</th>
              <th>Action</th>
              <th>Period</th>
              <th>Scope</th>
              <th>Result</th>
              <th>Status</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
          {% for snapshot in wave_report_snapshots %}
            <tr>
              <td>
                <strong>{{ snapshot.report_type }}</strong>
                <div class="muted">{{ snapshot.report_section or "reports" }} · {{ snapshot.export_format or "screen" }}</div>
              </td>
              <td>{{ snapshot.action_id }}</td>
              <td>{{ snapshot.from_date or snapshot.as_of_date or "-" }}{% if snapshot.to_date %} to {{ snapshot.to_date }}{% endif %}</td>
              <td>{{ snapshot.account_name or snapshot.account_option or "All Accounts" }} / {{ snapshot.contact_name or snapshot.contact_option or "All Contacts" }}</td>
              <td>
                {% if snapshot.row_count is not none %}Rows {{ snapshot.row_count }}{% endif %}
                {% if snapshot.total_amount is not none %}<div>{{ format_money(snapshot.total_amount) }}</div>{% endif %}
                {% if snapshot.total_debits is not none or snapshot.total_credits is not none %}
                  <div class="muted">Dr {{ format_money(snapshot.total_debits) }} / Cr {{ format_money(snapshot.total_credits) }}</div>
                {% endif %}
                {% if snapshot.row_count is none and snapshot.total_amount is none and snapshot.total_debits is none and snapshot.total_credits is none %}-{% endif %}
              </td>
              <td><span class="badge {{ snapshot.status }}">{{ snapshot.status }}</span></td>
              <td class="mono">{{ snapshot.updated_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No Wave report evidence snapshots have been planned yet.</div>
      {% endif %}
      {% if wave_operation_snapshots %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Operation evidence</th>
              <th>Action</th>
              <th>Surface</th>
              <th>Safety</th>
              <th>Status</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
          {% for snapshot in wave_operation_snapshots %}
            <tr>
              <td>
                <strong>{{ snapshot.operation_id }}</strong>
                <div class="muted">{{ snapshot.mode or "-" }} Â· workflow {{ snapshot.workflow_id or "-" }}</div>
              </td>
              <td>{{ snapshot.action_id }}</td>
              <td>{{ snapshot.surface or "-" }}</td>
              <td><span class="badge {{ snapshot.safety }}">{{ snapshot.safety }}</span></td>
              <td><span class="badge {{ snapshot.status }}">{{ snapshot.status }}</span></td>
              <td class="mono">{{ snapshot.updated_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No Wave operation evidence snapshots have been planned yet.</div>
      {% endif %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Report section</th>
              <th>Reports</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
          {% for section in wave_control.reportSections %}
            <tr>
              <td>{{ section.label }}</td>
              <td>{{ section.report_count }}</td>
              <td>{{ section.description }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      <details>
        <summary>Wave guardrails and report catalog</summary>
        <pre>{{ pretty_json({"credentials": wave_control.credentials, "safetyPolicy": wave_control.safetyPolicy, "reports": wave_control.reports}) }}</pre>
      </details>
    </section>

    <section id="bank">
      <div class="section-head">
        <div>
          <h2>Bank Transactions</h2>
          <p>Persist Wave account-transactions exports, bank statement rows, and imported ledger evidence before reconciliation.</p>
        </div>
      </div>
      <form method="post" action="{{ url_for('import_bank_transactions_form') }}" style="padding: 14px 18px 0;">
        <div class="correction-grid">
          <input type="text" name="accountIdentifier" value="default" placeholder="Account identifier">
          <input type="text" name="source" value="manual_upload" placeholder="Source">
          <input type="text" name="filename" placeholder="Filename or Wave export name">
          <select name="format" aria-label="Statement format">
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="camt">CAMT XML</option>
            <option value="mt940">MT940</option>
          </select>
        </div>
        <textarea name="statementText" placeholder='Paste JSON, CSV, CAMT XML, or MT940 statement rows. JSON example: [{"id":"tx-1","date":"2026-06-28","amount":-42.5,"description":"Office Shop"}]'></textarea>
        <div class="button-row" style="margin-top: 8px;">
          <button type="submit">Import bank transactions</button>
        </div>
      </form>
      {% if bank_import_summary %}
      {% if bank_import_summary.error %}
      <div class="empty">{{ bank_import_summary.error }}</div>
      {% else %}
      <div class="summary-grid">
        <div class="summary-item"><span>Rows seen</span><strong>{{ bank_import_summary.rowsSeen }}</strong></div>
        <div class="summary-item"><span>Imported</span><strong>{{ bank_import_summary.rowsImported }}</strong></div>
        <div class="summary-item"><span>Duplicates</span><strong>{{ bank_import_summary.duplicates }}</strong></div>
        <div class="summary-item"><span>Skipped</span><strong>{{ bank_import_summary.skipped }}</strong></div>
      </div>
      <details open>
        <summary>Last bank import</summary>
        <pre>{{ pretty_json(bank_import_summary) }}</pre>
      </details>
      {% endif %}
      {% endif %}
      <div class="summary-grid">
        <div class="summary-item"><span>Imported tx</span><strong>{{ metrics.bank_transactions }}</strong></div>
        <div class="summary-item"><span>Unreconciled tx</span><strong>{{ metrics.unreconciled_bank_transactions }}</strong></div>
        <div class="summary-item"><span>Imports</span><strong>{{ metrics.bank_statement_imports }}</strong></div>
      </div>
      {% if bank_statement_imports %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Import</th>
              <th>Account</th>
              <th>Format</th>
              <th>Status</th>
              <th>Rows</th>
              <th>Duplicates</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
          {% for import_row in bank_statement_imports %}
            <tr>
              <td class="mono">#{{ import_row.id }} {{ import_row.filename or import_row.source }}</td>
              <td class="mono">{{ import_row.account_identifier }}</td>
              <td>{{ import_row.format }}</td>
              <td><span class="badge {{ import_row.status }}">{{ import_row.status }}</span></td>
              <td>{{ import_row.rows_imported }} / {{ import_row.rows_seen }}</td>
              <td>{{ import_row.duplicates }}</td>
              <td class="mono">{{ import_row.updated_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}
      {% if bank_transactions %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Amount</th>
              <th>Counterparty</th>
              <th>Description</th>
              <th>Reconciliation</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
          {% for tx in bank_transactions %}
            <tr>
              <td class="mono">{{ tx.transaction_id }}</td>
              <td>{{ tx.transaction_date or "-" }}</td>
              <td>{{ format_money(tx.amount) }} {{ tx.currency }}</td>
              <td>{{ tx.counterparty or "-" }}</td>
              <td>{{ tx.description or "-" }}</td>
              <td><span class="badge {{ tx.reconciliation_status }}">{{ tx.reconciliation_status }}</span></td>
              <td>{{ tx.source }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No bank transactions imported yet. Paste a Wave account-transactions export or bank statement above.</div>
      {% endif %}
    </section>

    <section id="reconciliation">
      <div class="section-head">
        <div>
          <h2>Reconciliation</h2>
          <p>Match processed ledger documents to imported bank transactions and route uncertain evidence to review.</p>
        </div>
      </div>
      <form method="post" action="{{ url_for('run_reconciliation_form') }}" style="padding: 14px 18px 0;">
        <textarea name="bankTransactionsJson" placeholder='Optional override batch. Leave empty to use imported bank transactions. Example: [{"id":"tx-1","date":"2026-06-28","amount":-42.5,"description":"Office Shop"}]'></textarea>
        <div class="button-row" style="margin-top: 8px;">
          <button type="submit">Run matching</button>
        </div>
      </form>
      {% if reconciliation_summary %}
      {% if reconciliation_summary.error %}
      <div class="empty">{{ reconciliation_summary.error }}</div>
      {% else %}
      <div class="summary-grid">
        <div class="summary-item"><span>Transactions</span><strong>{{ reconciliation_summary.requestedTransactions }}</strong></div>
        <div class="summary-item"><span>Candidate docs</span><strong>{{ reconciliation_summary.candidateDocuments }}</strong></div>
        <div class="summary-item"><span>Matches</span><strong>{{ reconciliation_summary.matchedCandidates }}</strong></div>
        <div class="summary-item"><span>Missing receipts</span><strong>{{ reconciliation_summary.missingReceipts }}</strong></div>
        <div class="summary-item"><span>Unmatched docs</span><strong>{{ reconciliation_summary.unmatchedDocuments }}</strong></div>
        <div class="summary-item"><span>Review items</span><strong>{{ reconciliation_summary.reviewItemsCreated }}</strong></div>
      </div>
      <details>
        <summary>Last reconciliation run</summary>
        <pre>{{ pretty_json(reconciliation_summary) }}</pre>
      </details>
      {% endif %}
      {% endif %}
      {% if reconciliation_matches %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Document</th>
              <th>Bank transaction</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Difference</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
          {% for match in reconciliation_matches %}
            <tr>
              <td class="mono">#{{ match.id }}</td>
              <td class="mono">{{ "#" ~ match.document_id if match.document_id else "-" }}</td>
              <td class="mono">{{ match.bank_transaction_id }}</td>
              <td><span class="badge {{ match.status }}">{{ match.status }}</span></td>
              <td>{{ format_confidence(match.confidence_score) }}</td>
              <td>{{ match.amount_difference if match.amount_difference is not none else "-" }}</td>
              <td>
                {% if match.status in ["candidate", "unmatched_document", "missing_receipt", "needs_review"] %}
                <form class="table-actions" method="post" action="{{ url_for('resolve_reconciliation_form', reconciliation_match_id=match.id) }}">
                  {% if match.status == "candidate" %}
                  <button class="compact" type="submit" name="status" value="approved">Reconcile</button>
                  <button class="compact secondary" type="submit" name="status" value="rejected">Reject</button>
                  {% else %}
                  <button class="compact secondary" type="submit" name="status" value="resolved">Resolve</button>
                  <button class="compact secondary" type="submit" name="status" value="ignored">Ignore</button>
                  {% endif %}
                </form>
                {% else %}
                <span class="muted">-</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No reconciliation evidence has been recorded yet.</div>
      {% endif %}
    </section>

    <section id="review">
      <div class="section-head">
        <div>
          <h2>Manual Review</h2>
          <p>{{ review_items|length }} pending or in-progress review items.</p>
        </div>
      </div>
      {% if review_items %}
      <div class="review-grid">
        {% for item in review_items %}
        <article class="review-item">
          {% set doc = review_documents.get(item.document_id) if item.document_id else None %}
          <h3>{{ item.reason }}</h3>
          <span class="badge {{ item.status }}">{{ item.status }}</span>
          <p>{{ item.details or "No detail recorded." }}</p>
          <p class="mono">Document: {{ "#" ~ item.document_id if item.document_id else "not linked" }}</p>
          {% if item.reason in ["reconciliation_candidate", "missing_receipt", "unmatched_document"] %}
            {% set bank_tx = item.corrected_data.bankTransaction if item.corrected_data and item.corrected_data.bankTransaction else None %}
            {% if bank_tx %}
            <div class="empty">
              <strong>{{ bank_tx.id or bank_tx.transaction_id or item.corrected_data.bankTransactionId }}</strong>
              · {{ bank_tx.date or bank_tx.transaction_date or "-" }}
              · {{ format_money(bank_tx.amount) }}
              · {{ bank_tx.counterparty or bank_tx.description or "No description" }}
            </div>
            {% endif %}
          {% endif %}
          <form class="review-actions" method="post" action="{{ url_for('resolve_review_form', review_item_id=item.id) }}">
            <input type="text" name="resolution" value="" placeholder="Resolution note">
            <div class="correction-grid">
              <input type="text" name="vendorName" value="{{ doc.vendor_name if doc and doc.vendor_name else "" }}" placeholder="Vendor">
              <input type="text" name="category" value="{{ doc.category if doc and doc.category else "" }}" placeholder="Category">
              <input type="text" name="transactionDate" value="{{ doc.transaction_date if doc and doc.transaction_date else "" }}" placeholder="Date YYYY-MM-DD">
              <input type="text" name="totalAmount" value="{{ doc.total_amount if doc and doc.total_amount is not none else "" }}" placeholder="Total">
              <input type="text" name="vatAmount" value="{{ doc.vat_amount if doc and doc.vat_amount is not none else "" }}" placeholder="VAT">
            </div>
            <div class="button-row">
              {% if item.reason == "reconciliation_candidate" %}
              <button type="submit" name="status" value="approved">Reconcile</button>
              <button class="secondary" type="submit" name="status" value="rejected">Reject match</button>
              {% elif item.reason in ["missing_receipt", "unmatched_document"] %}
              <button type="submit" name="status" value="resolved">Resolved</button>
              <button class="secondary" type="submit" name="status" value="ignored">No receipt needed</button>
              {% else %}
              <button type="submit" name="status" value="approved">Approve</button>
              <button class="secondary" type="submit" name="status" value="rejected">Reject</button>
              <button class="secondary" type="submit" name="status" value="resolved">Resolve</button>
              {% endif %}
            </div>
          </form>
        </article>
        {% endfor %}
      </div>
      {% else %}
      <div class="empty">No pending review items.</div>
      {% endif %}
    </section>

    <section id="rules">
      <div class="section-head">
        <div>
          <h2>Vendors & Rules</h2>
          <p>{{ vendor_summaries|length }} vendors, {{ category_summaries|length }} categories, and {{ rules|length }} suggested or learned rules from ledger evidence.</p>
        </div>
      </div>
      {% if vendor_summaries %}
      <details open>
        <summary>Vendor Directory</summary>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Records</th>
                <th>Documents</th>
                <th>Categories</th>
                <th>Targets</th>
                <th>Needs attention</th>
                <th>Export ready</th>
                <th>Rules</th>
              </tr>
            </thead>
            <tbody>
            {% for vendor in vendor_summaries %}
              <tr>
                <td>{{ vendor.vendorName }}</td>
                <td>{{ vendor.recordCount }}</td>
                <td>{{ vendor.documentCount }}</td>
                <td>{{ vendor.categories[:3]|map(attribute="value")|join(", ") or "-" }}</td>
                <td>{{ vendor.targetSystems[:3]|map(attribute="value")|join(", ") or "-" }}</td>
                <td><span class="badge {{ 'needs_attention' if vendor.needsAttention else 'ok' }}">{{ vendor.reviewRequiredCount + vendor.failedCount }}</span></td>
                <td>{{ vendor.exportReadyCount }}</td>
                <td>{{ vendor.ruleCount }}{% if vendor.suggestedRuleCount %} ({{ vendor.suggestedRuleCount }} suggested){% endif %}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </details>
      {% endif %}
      {% if category_summaries %}
      <details>
        <summary>Category Directory</summary>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Records</th>
                <th>Documents</th>
                <th>Vendors</th>
                <th>Targets</th>
                <th>Needs attention</th>
                <th>Export ready</th>
                <th>Rules</th>
              </tr>
            </thead>
            <tbody>
            {% for category in category_summaries %}
              <tr>
                <td>{{ category.category }}</td>
                <td>{{ category.recordCount }}</td>
                <td>{{ category.documentCount }}</td>
                <td>{{ category.vendors[:3]|map(attribute="value")|join(", ") or "-" }}</td>
                <td>{{ category.targetSystems[:3]|map(attribute="value")|join(", ") or "-" }}</td>
                <td><span class="badge {{ 'needs_attention' if category.needsAttention else 'ok' }}">{{ category.reviewRequiredCount + category.failedCount }}</span></td>
                <td>{{ category.exportReadyCount }}</td>
                <td>{{ category.ruleCount }}{% if category.suggestedRuleCount %} ({{ category.suggestedRuleCount }} suggested){% endif %}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </details>
      {% endif %}
      {% if rules %}
      <details open>
        <summary>Rule Review</summary>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Category</th>
              <th>Target</th>
              <th>Status</th>
              <th>Uses</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
          {% for rule in rules %}
            <tr>
              <td>{{ rule.vendor_name }}</td>
              <td>{{ rule.category }}</td>
              <td>{{ rule.target_system }}</td>
              <td><span class="badge {{ rule.status }}">{{ rule.status }}</span></td>
              <td>{{ rule.usage_count }}</td>
              <td class="mono">{{ rule.updated_at }}</td>
              <td>
                {% if rule.status == "suggested" %}
                <form class="table-actions" method="post" action="{{ url_for('resolve_rule_form', rule_id=rule.id) }}">
                  <input type="hidden" name="status" value="approved">
                  <input type="hidden" name="resolution" value="Approved for future autonomous suggestions.">
                  <button class="compact" type="submit">Approve</button>
                </form>
                <form class="table-actions" method="post" action="{{ url_for('resolve_rule_form', rule_id=rule.id) }}">
                  <input type="hidden" name="status" value="rejected">
                  <input type="hidden" name="resolution" value="Rejected by operator review.">
                  <button class="compact secondary" type="submit">Reject</button>
                </form>
                {% elif rule.status == "approved" %}
                <form class="table-actions" method="post" action="{{ url_for('resolve_rule_form', rule_id=rule.id) }}">
                  <input type="hidden" name="status" value="disabled">
                  <input type="hidden" name="resolution" value="Disabled by operator review.">
                  <button class="compact secondary" type="submit">Disable</button>
                </form>
                {% elif rule.status in ["rejected", "disabled"] %}
                <form class="table-actions" method="post" action="{{ url_for('resolve_rule_form', rule_id=rule.id) }}">
                  <input type="hidden" name="status" value="suggested">
                  <input type="hidden" name="resolution" value="Returned to rule review queue.">
                  <button class="compact secondary" type="submit">Reopen</button>
                </form>
                {% else %}
                <span class="muted">No action</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      </details>
      {% else %}
      <div class="empty">No correction-based vendor rules yet.</div>
      {% endif %}
      <details>
        <summary>Recent correction history</summary>
        <pre>{{ pretty_json(corrections) }}</pre>
      </details>
    </section>

    <section id="audit">
      <div class="section-head">
        <div>
          <h2>Audit Log</h2>
          <p>{{ audit_events|length }} latest audit events.</p>
        </div>
      </div>
      {% if audit_events %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
          {% for event in audit_events %}
            <tr>
              <td class="mono">{{ event.created_at }}</td>
              <td>{{ event.action }}</td>
              <td>{{ event.entity_type }} {{ event.entity_id or "" }}</td>
              <td class="mono">{{ compact_json(event.details) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No audit events recorded yet.</div>
      {% endif %}
    </section>

    <section id="backups">
      <div class="section-head">
        <div>
          <h2>Backups</h2>
          <p>Snapshot and restore the local SQLite ledger with explicit confirmation.</p>
        </div>
        <form class="inline-actions" method="post" action="{{ url_for('create_backup_form') }}">
          <button type="submit">Create backup</button>
        </form>
      </div>
      <div class="settings-grid">
        <div class="setting"><span>Backup folder</span><strong class="mono">{{ backups.backupDir }}</strong></div>
        <div class="setting"><span>Restore phrase</span><strong class="mono">{{ backups.restoreConfirmationPhrase }}</strong></div>
      </div>
      {% if backup_summary %}
      {% if backup_summary.error %}
      <div class="empty">{{ backup_summary.error }}</div>
      {% else %}
      <details open>
        <summary>Last backup action</summary>
        <pre>{{ pretty_json(backup_summary) }}</pre>
      </details>
      {% endif %}
      {% endif %}
      {% if backups.backups %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Backup</th>
              <th>Status</th>
              <th>Created</th>
              <th>Ledger bytes</th>
              <th>Checksum</th>
              <th>Restore</th>
            </tr>
          </thead>
          <tbody>
          {% for backup in backups.backups %}
            <tr>
              <td class="mono">{{ backup.backupFilename }}</td>
              <td><span class="badge {{ backup.status }}">{{ backup.status }}</span></td>
              <td class="mono">{{ backup.createdAt or "-" }}</td>
              <td>{{ backup.ledgerBytes or "-" }}</td>
              <td class="mono">{{ backup.ledgerSha256[:12] if backup.ledgerSha256 else "-" }}</td>
              <td>
                {% if backup.status == "valid" %}
                <form method="post" action="{{ url_for('restore_backup_form') }}">
                  <input type="hidden" name="backupPath" value="{{ backup.backupPath }}">
                  <input type="text" name="confirmation" placeholder="{{ backups.restoreConfirmationPhrase }}">
                  <button class="compact secondary" type="submit">Restore</button>
                </form>
                {% else %}
                <span class="muted">{{ backup.error or "-" }}</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No local ledger backups have been created yet.</div>
      {% endif %}
    </section>

    <section id="settings">
      <div class="section-head">
        <div>
          <h2>Settings</h2>
          <p>Operational status without secret values.</p>
        </div>
        <span class="badge {{ readiness.status }}">{{ readiness.status }}</span>
      </div>
      <div class="settings-grid">
        <div class="setting"><span>Ledger path</span><strong class="mono">{{ health.ledger_path }}</strong></div>
        <div class="setting"><span>API host</span><strong class="mono">{{ health.host }}</strong></div>
        <div class="setting"><span>Remote auth</span><strong>{{ "enabled" if readiness.security.apiTokenConfigured else "not required on loopback" }}</strong></div>
        <div class="setting"><span>Remote exposure</span><strong>{{ "safe" if readiness.security.remoteExposureSafe else "blocked until API token is configured" }}</strong></div>
        <div class="setting"><span>Ready sources</span><strong>{{ readiness.sources|selectattr("status", "equalto", "ready")|list|length }}</strong></div>
        <div class="setting"><span>Secret values</span><strong>{{ "redacted" if readiness.security.secretValuesRedacted else "unsafe" }}</strong></div>
        <div class="setting"><span>Dashboard URL</span><strong class="mono">{{ readiness.localAccess.dashboardUrl }}</strong></div>
        <div class="setting"><span>API base URL</span><strong class="mono">{{ readiness.localAccess.apiBaseUrl }}</strong></div>
        <div class="setting"><span>Auth mode</span><strong>{{ readiness.localAccess.authMode }}</strong></div>
        <div class="setting"><span>Ngrok safety</span><strong>{{ readiness.localAccess.ngrokSafety }}</strong></div>
      </div>
      <details>
        <summary>Windows Local Runbook</summary>
        <div class="settings-grid">
          <div class="setting"><span>Start command</span><strong class="mono">{{ readiness.localAccess.windows.startCommand }}</strong></div>
          <div class="setting"><span>Working directory</span><strong>{{ readiness.localAccess.windows.workingDirectory }}</strong></div>
          <div class="setting"><span>Task Scheduler</span><strong>{{ readiness.localAccess.windows.taskScheduler }}</strong></div>
          <div class="setting"><span>Auth header</span><strong class="mono">{{ readiness.localAccess.authHeaderExample or "not required for loopback-only no-token mode" }}</strong></div>
        </div>
        <pre>{{ pretty_json(readiness.localAccess.safeRemoteChecklist) }}</pre>
      </details>
      {% if readiness.issues %}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Issue</th>
              <th>Message</th>
              <th>Next action</th>
            </tr>
          </thead>
          <tbody>
          {% for issue in readiness.issues[:8] %}
            <tr>
              <td><span class="badge {{ issue.severity }}">{{ issue.severity }}</span></td>
              <td>{{ issue.type }}</td>
              <td>{{ issue.message }}</td>
              <td>{{ issue.nextAction or "-" }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}
      <details open>
        <summary>Source Status</summary>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Status</th>
                <th>Configured</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
            {% for source in readiness.sources %}
              <tr>
                <td>{{ source.label }}</td>
                <td><span class="badge {{ source.status }}">{{ source.status }}</span></td>
                <td>{{ "yes" if source.configured else "no" }}</td>
                <td>{{ source.details }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Dependency Status</summary>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Dependency</th>
                <th>Status</th>
                <th>Version / command</th>
                <th>Purpose</th>
              </tr>
            </thead>
            <tbody>
            {% for dependency in readiness.dependencies %}
              <tr>
                <td>{{ dependency.label }}</td>
                <td><span class="badge {{ dependency.status }}">{{ dependency.status }}</span></td>
                <td class="mono">{{ dependency.version or dependency.command or dependency.resolved or "-" }}</td>
                <td>{{ dependency.details }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Credential Status</summary>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Credential</th>
                <th>Configured</th>
                <th>File exists</th>
                <th>Stored value</th>
              </tr>
            </thead>
            <tbody>
            {% for credential in readiness.credentials %}
              <tr>
                <td>{{ credential.label }}</td>
                <td>{{ "yes" if credential.configured else "no" }}</td>
                <td>{{ "yes" if credential.exists else "no" }}</td>
                <td>{{ "redacted" if credential.secret else "not secret" }}</td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Storage Paths</summary>
        <pre>{{ pretty_json(readiness.paths) }}</pre>
      </details>
      <details>
        <summary>Raw readiness payload</summary>
        <pre>{{ pretty_json(readiness) }}</pre>
      </details>
      <details>
        <summary>Raw dashboard payload</summary>
        <pre>{{ raw_payload }}</pre>
      </details>
    </section>
  </div>
</body>
</html>
"""


DOCUMENT_DETAIL_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FAB Document #{{ document.id }}</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --panel-soft: #f0f5f8;
      --text: #15202b;
      --muted: #5d6b78;
      --line: #d9e2ea;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --danger: #b42318;
      --warning: #a15c07;
      --ok: #166534;
      --shadow: 0 14px 36px rgba(21, 32, 43, 0.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14px; line-height: 1.45; }
    a { color: var(--accent-dark); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .shell { max-width: 1320px; margin: 0 auto; padding: 24px; }
    header, .section-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
    header { padding: 10px 0 18px; }
    h1 { margin: 0; font-size: 28px; line-height: 1.1; letter-spacing: 0; overflow-wrap: anywhere; }
    h2 { margin: 0 0 12px; font-size: 18px; line-height: 1.2; letter-spacing: 0; }
    h3 { margin: 0 0 8px; font-size: 15px; line-height: 1.2; letter-spacing: 0; }
    .subtitle { margin: 7px 0 0; color: var(--muted); overflow-wrap: anywhere; }
    .button-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    button, .button-link {
      min-height: 36px; border: 1px solid var(--accent-dark); background: var(--accent); color: #fff;
      padding: 7px 11px; font: inherit; font-size: 13px; font-weight: 750; cursor: pointer;
      display: inline-flex; align-items: center;
    }
    .button-link.secondary, button.secondary { background: #fff; color: var(--accent-dark); }
    input[type="text"], textarea, select { width: 100%; min-height: 36px; border: 1px solid var(--line); padding: 7px 9px; font: inherit; background: #fff; color: var(--text); }
    textarea { min-height: 82px; resize: vertical; }
    section { margin: 18px 0; background: var(--panel); border: 1px solid var(--line); box-shadow: var(--shadow); overflow: hidden; }
    .section-head { padding: 16px 18px; border-bottom: 1px solid var(--line); background: #fbfcfd; }
    .section-head p { margin: 4px 0 0; color: var(--muted); }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; padding: 14px 18px 0; }
    .summary-item { border: 1px solid var(--line); background: #fff; padding: 10px; min-width: 0; }
    .summary-item span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .summary-item strong { display: block; margin-top: 5px; font-size: 18px; overflow-wrap: anywhere; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 820px; }
    th, td { padding: 11px 13px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; background: var(--panel-soft); white-space: nowrap; }
    .muted { color: var(--muted); }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 12px; }
    .badge { display: inline-flex; align-items: center; min-height: 24px; padding: 3px 8px; border: 1px solid var(--line); background: #edf7f4; color: var(--accent-dark); font-size: 12px; font-weight: 700; white-space: nowrap; }
    .badge.failed, .badge.rejected, .badge.duplicate, .badge.high { background: #fff1f0; color: var(--danger); }
    .badge.pending, .badge.needs_review, .badge.in_review, .badge.candidate, .badge.needs_review, .badge.approval_required { background: #fff7e6; color: var(--warning); }
    .badge.completed, .badge.approved, .badge.processed, .badge.reviewed, .badge.ready_to_route, .badge.reconciled, .badge.resolved { background: #ecfdf3; color: var(--ok); }
    .evidence-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; padding: 14px 18px 18px; }
    .evidence { border: 1px solid var(--line); background: #fff; padding: 12px; min-width: 0; }
    .review-actions { display: grid; gap: 8px; margin-top: 10px; }
    .correction-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }
    details { padding: 13px 14px; border-top: 1px solid var(--line); background: #fbfcfd; }
    summary { cursor: pointer; font-weight: 700; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #0f172a; color: #e2e8f0; padding: 12px; margin: 10px 0 0; max-height: 360px; overflow: auto; font-size: 12px; }
    .empty { padding: 22px 18px; color: var(--muted); }
    @media (max-width: 760px) { .shell { padding: 16px; } header, .section-head { display: block; } .button-row { margin-top: 12px; } h1 { font-size: 24px; } }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <a class="button-link secondary" href="{{ url_for('dashboard_page', _anchor='ledger') }}">Back to dashboard</a>
        <h1>{{ document.original_filename }}</h1>
        <p class="subtitle">Document #{{ document.id }} from {{ document.source }} / {{ document.source_document_id or "no source id" }}</p>
      </div>
      <div class="button-row">
        {% if document.processing_status == "imported" %}
        <form method="post" action="{{ url_for('process_document_form', document_id=document.id) }}">
          <button type="submit">Process</button>
        </form>
        {% endif %}
        {% if document.processing_status in ["processed", "reviewed", "validated", "ready_to_route"] %}
        <form method="post" action="{{ url_for('route_document_form', document_id=document.id) }}">
          <button type="submit">Prepare Wave draft</button>
        </form>
        {% endif %}
      </div>
    </header>

    <section>
      <div class="section-head">
        <div>
          <h2>Review Summary</h2>
          <p>The operational state FAB will use before routing or export.</p>
        </div>
        <span class="badge {{ document.processing_status }}">{{ document.processing_status }}</span>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Vendor</span><strong>{{ document.vendor_name or "Unknown" }}</strong></div>
        <div class="summary-item"><span>Amount</span><strong>{{ format_money(document.total_amount) }}</strong></div>
        <div class="summary-item"><span>Date</span><strong>{{ document.transaction_date or "-" }}</strong></div>
        <div class="summary-item"><span>Category</span><strong>{{ document.category or "Unassigned" }}</strong></div>
        <div class="summary-item"><span>Confidence</span><strong>{{ format_confidence(document.confidence_score) }}</strong></div>
        <div class="summary-item"><span>Reconciliation</span><strong>{{ document.reconciliation_status }}</strong></div>
        <div class="summary-item"><span>Reviews</span><strong>{{ open_review_count }} open / {{ document.review_items|length }} total</strong></div>
        <div class="summary-item"><span>Groups</span><strong>{{ document.document_groups|length }}</strong></div>
      </div>
      <div class="evidence-grid">
        <div class="evidence">
          <h3>Source Provenance</h3>
          <p><strong>Path:</strong> <span class="mono">{{ document.storage_path or "-" }}</span></p>
          <p><strong>MIME:</strong> {{ document.mime_type or "-" }}</p>
          <p><strong>Type:</strong> {{ document.document_type }}</p>
          <p><strong>Created:</strong> <span class="mono">{{ document.created_at }}</span></p>
          <p><strong>Updated:</strong> <span class="mono">{{ document.updated_at }}</span></p>
        </div>
        <div class="evidence">
          <h3>Source Preview</h3>
          <p>{{ source_preview.status }}</p>
          {% if source_preview.text %}
          <pre>{{ source_preview.text }}</pre>
          {% else %}
          <p class="muted mono">{{ source_preview.path or "No local source path recorded." }}</p>
          {% endif %}
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Manual Review</h2>
          <p>Resolve only the specific review items that need a human decision.</p>
        </div>
      </div>
      {% if document.review_items %}
      <div class="evidence-grid">
        {% for item in document.review_items %}
        <article class="evidence">
          <h3>{{ item.reason }}</h3>
          <span class="badge {{ item.status }}">{{ item.status }}</span>
          <p>{{ item.details or "No detail recorded." }}</p>
          <p class="mono">{{ compact_json(item.corrected_data) }}</p>
          {% if item.status in ["pending", "in_review"] %}
          <form class="review-actions" method="post" action="{{ url_for('resolve_review_form', review_item_id=item.id) }}">
            <input type="text" name="resolution" placeholder="Resolution note">
            <div class="correction-grid">
              <input type="text" name="vendorName" value="{{ document.vendor_name or "" }}" placeholder="Vendor">
              <input type="text" name="category" value="{{ document.category or "" }}" placeholder="Category">
              <input type="text" name="transactionDate" value="{{ document.transaction_date or "" }}" placeholder="Date YYYY-MM-DD">
              <input type="text" name="totalAmount" value="{{ document.total_amount if document.total_amount is not none else "" }}" placeholder="Total">
              <input type="text" name="vatAmount" value="{{ document.vat_amount if document.vat_amount is not none else "" }}" placeholder="VAT">
              <input type="text" name="duplicateOfDocumentId" value="{{ document.duplicate_of_document_id if document.duplicate_of_document_id else "" }}" placeholder="Duplicate doc ID">
            </div>
            <div class="button-row">
              <button type="submit" name="status" value="approved">Approve</button>
              <button class="secondary" type="submit" name="status" value="rejected">Reject</button>
              <button class="secondary" type="submit" name="status" value="resolved">Resolve</button>
              <button class="secondary" type="submit" name="status" value="ignored">Ignore</button>
            </div>
          </form>
          {% endif %}
        </article>
        {% endfor %}
      </div>
      {% else %}
      <div class="empty">No review items recorded for this document.</div>
      {% endif %}
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Extracted Fields</h2>
          <p>Structured OCR/extraction evidence with confidence and provenance.</p>
        </div>
      </div>
      {% if document.extracted_fields %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Field</th><th>Value</th><th>Confidence</th><th>Source</th><th>Provenance</th></tr></thead>
          <tbody>
          {% for field in document.extracted_fields %}
            <tr>
              <td>{{ field.field_name }}</td>
              <td class="mono">{{ compact_json(field.field_value) }}</td>
              <td>{{ format_confidence(field.confidence_score) }}</td>
              <td>{{ field.source }}</td>
              <td class="mono">{{ compact_json(field.provenance) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No extracted fields have been stored yet.</div>
      {% endif %}
      <details {% if document.ocr_text %}open{% endif %}>
        <summary>OCR Text</summary>
        <pre>{{ document.ocr_text or "No OCR text stored." }}</pre>
      </details>
      <details>
        <summary>Extracted Data JSON</summary>
        <pre>{{ pretty_json(document.extracted_data) }}</pre>
      </details>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Duplicate And Group Evidence</h2>
          <p>Non-destructive duplicate and multi-page grouping signals.</p>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence">
          <h3>Duplicate Candidates</h3>
          {% if document.duplicate_candidates %}
          {% for candidate in document.duplicate_candidates %}
            <p><span class="badge {{ candidate.status }}">{{ candidate.status }}</span> #{{ candidate.document_id }} -> #{{ candidate.candidate_document_id }} {{ candidate.match_type }} {{ format_confidence(candidate.confidence_score) }}</p>
            <p class="mono">{{ compact_json(candidate.evidence) }}</p>
          {% endfor %}
          {% else %}
          <p class="muted">No duplicate candidates.</p>
          {% endif %}
        </div>
        <div class="evidence">
          <h3>Document Groups</h3>
          {% if document.document_groups %}
          {% for group in document.document_groups %}
            <p><span class="badge {{ group.status }}">{{ group.status }}</span> #{{ group.id }} {{ group.title or group.group_key }} ({{ group.member_count }} active)</p>
            {% for member in group.members %}
              <p class="mono">#{{ member.document_id }} {{ member.role }} {{ member.status }} {{ member.document.original_filename if member.document else "" }}</p>
            {% endfor %}
          {% endfor %}
          {% else %}
          <p class="muted">No document groups.</p>
          {% endif %}
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Bookkeeping, Routing, Export, Reconciliation</h2>
          <p>Downstream operating evidence tied to this document.</p>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence">
          <h3>Bookkeeping Record</h3>
          {% if document.bookkeeping_record %}
          <p><span class="badge {{ document.bookkeeping_record.status }}">{{ document.bookkeeping_record.status }}</span> {{ document.bookkeeping_record.target_system }} / {{ document.bookkeeping_record.export_status }}</p>
          <p>{{ document.bookkeeping_record.vendor_name or "Unknown" }} {{ format_money(document.bookkeeping_record.amount) }} {{ document.bookkeeping_record.currency }}</p>
          <p class="mono">{{ compact_json(document.bookkeeping_record.metadata) }}</p>
          {% else %}
          <p class="muted">No bookkeeping record yet.</p>
          {% endif %}
        </div>
        <div class="evidence">
          <h3>Reconciliation</h3>
          {% if document.reconciliation_matches %}
          {% for match in document.reconciliation_matches %}
            <p><span class="badge {{ match.status }}">{{ match.status }}</span> {{ match.bank_transaction_id }} {{ format_confidence(match.confidence_score) }}</p>
          {% endfor %}
          {% else %}
          <p class="muted">No reconciliation evidence.</p>
          {% endif %}
        </div>
      </div>
      {% if document.routing_attempts or document.export_attempts %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Type</th><th>Status</th><th>Target</th><th>Action</th><th>Message</th></tr></thead>
          <tbody>
          {% for attempt in document.routing_attempts %}
            <tr><td>Routing</td><td><span class="badge {{ attempt.status }}">{{ attempt.status }}</span></td><td>{{ attempt.target }}</td><td>{{ attempt.metadata.operation.action_id if attempt.metadata and attempt.metadata.operation else "-" }}</td><td>{{ attempt.message or "-" }}</td></tr>
          {% endfor %}
          {% for export in document.export_attempts %}
            <tr><td>Export</td><td><span class="badge {{ export.status }}">{{ export.status }}</span></td><td>{{ export.target_system }}</td><td>{{ export.action_id or "-" }}</td><td>{{ export.message or "-" }}</td></tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Audit Trail</h2>
          <p>Document-specific sensitive actions and state transitions.</p>
        </div>
      </div>
      {% if document.audit_events %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Created</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead>
          <tbody>
          {% for event in document.audit_events %}
            <tr>
              <td class="mono">{{ event.created_at }}</td>
              <td>{{ event.action }}</td>
              <td>{{ event.entity_type }} {{ event.entity_id or "" }}</td>
              <td class="mono">{{ compact_json(event.details) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No document-specific audit events recorded.</div>
      {% endif %}
      <details>
        <summary>Raw document payload</summary>
        <pre>{{ pretty_json(document) }}</pre>
      </details>
    </section>
  </div>
</body>
</html>
"""


BOOKKEEPING_RECORD_DETAIL_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FAB Bookkeeping Record #{{ record.id }}</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --panel-soft: #f0f5f8;
      --text: #15202b;
      --muted: #5d6b78;
      --line: #d9e2ea;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --danger: #b42318;
      --warning: #a15c07;
      --ok: #166534;
      --shadow: 0 14px 36px rgba(21, 32, 43, 0.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14px; line-height: 1.45; }
    a { color: var(--accent-dark); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .shell { max-width: 1320px; margin: 0 auto; padding: 24px; }
    header, .section-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
    header { padding: 10px 0 18px; }
    h1 { margin: 0; font-size: 28px; line-height: 1.1; letter-spacing: 0; overflow-wrap: anywhere; }
    h2 { margin: 0 0 12px; font-size: 18px; line-height: 1.2; letter-spacing: 0; }
    h3 { margin: 0 0 8px; font-size: 15px; line-height: 1.2; letter-spacing: 0; }
    p { margin: 6px 0; }
    .subtitle { margin: 7px 0 0; color: var(--muted); overflow-wrap: anywhere; }
    .button-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    button, .button-link {
      min-height: 36px; border: 1px solid var(--accent-dark); background: var(--accent); color: #fff;
      padding: 7px 11px; font: inherit; font-size: 13px; font-weight: 750; cursor: pointer;
      display: inline-flex; align-items: center;
    }
    .button-link.secondary, button.secondary { background: #fff; color: var(--accent-dark); }
    input[type="text"], textarea { width: 100%; min-height: 36px; border: 1px solid var(--line); padding: 7px 9px; font: inherit; background: #fff; color: var(--text); }
    textarea { min-height: 82px; resize: vertical; }
    section { margin: 18px 0; background: var(--panel); border: 1px solid var(--line); box-shadow: var(--shadow); overflow: hidden; }
    .section-head { padding: 16px 18px; border-bottom: 1px solid var(--line); background: #fbfcfd; }
    .section-head p { margin: 4px 0 0; color: var(--muted); }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; padding: 14px 18px 18px; }
    .summary-item { border: 1px solid var(--line); background: #fff; padding: 10px; min-width: 0; }
    .summary-item span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .summary-item strong { display: block; margin-top: 5px; font-size: 18px; overflow-wrap: anywhere; }
    .evidence-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; padding: 14px 18px 18px; }
    .evidence { border: 1px solid var(--line); background: #fff; padding: 12px; min-width: 0; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 820px; }
    th, td { padding: 11px 13px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; background: var(--panel-soft); white-space: nowrap; }
    .muted { color: var(--muted); }
    .mono { font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 12px; }
    .badge { display: inline-flex; align-items: center; min-height: 24px; padding: 3px 8px; border: 1px solid var(--line); background: #edf7f4; color: var(--accent-dark); font-size: 12px; font-weight: 700; white-space: nowrap; }
    .badge.failed, .badge.rejected, .badge.duplicate, .badge.high { background: #fff1f0; color: var(--danger); }
    .badge.pending, .badge.needs_review, .badge.in_review, .badge.candidate, .badge.blocked_by_review, .badge.missing_receipt { background: #fff7e6; color: var(--warning); }
    .badge.completed, .badge.approved, .badge.processed, .badge.reviewed, .badge.ready_to_route, .badge.ready, .badge.reconciled, .badge.resolved { background: #ecfdf3; color: var(--ok); }
    .review-actions { display: grid; gap: 8px; margin-top: 10px; }
    .correction-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }
    details { padding: 13px 14px; border-top: 1px solid var(--line); background: #fbfcfd; }
    summary { cursor: pointer; font-weight: 700; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #0f172a; color: #e2e8f0; padding: 12px; margin: 10px 0 0; max-height: 360px; overflow: auto; font-size: 12px; }
    .empty { padding: 22px 18px; color: var(--muted); }
    @media (max-width: 760px) { .shell { padding: 16px; } header, .section-head { display: block; } .button-row { margin-top: 12px; } h1 { font-size: 24px; } }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <a class="button-link secondary" href="{{ url_for('dashboard_page', _anchor='records') }}">Back to records</a>
        <h1>Bookkeeping Record #{{ record.id }}</h1>
        <p class="subtitle">{{ record.source_type }} source{% if record.document_id %} / document #{{ record.document_id }}{% elif record.bank_transaction_id %} / bank transaction #{{ record.bank_transaction_id }}{% endif %}</p>
      </div>
      <div class="button-row">
        <a class="button-link secondary" href="{{ url_for('bookkeeping_record_detail', record_id=record.id) }}">JSON</a>
        {% if record.source_type == "bank_transaction" or record.status in ["ready_to_route", "approved", "reviewed"] %}
        <form method="post" action="{{ url_for('route_bookkeeping_record_form', record_id=record.id) }}">
          <button type="submit">Prepare draft</button>
        </form>
        {% endif %}
      </div>
    </header>

    <section>
      <div class="section-head">
        <div>
          <h2>Operating Summary</h2>
          <p>Normalized source-of-truth state before FAB routes anything downstream.</p>
        </div>
        <span class="badge {{ record.status }}">{{ record.status }}</span>
      </div>
      <div class="summary-grid">
        <div class="summary-item"><span>Vendor</span><strong>{{ record.vendor_name or "Unknown" }}</strong></div>
        <div class="summary-item"><span>Amount</span><strong>{{ format_money(record.amount) }}</strong></div>
        <div class="summary-item"><span>Date</span><strong>{{ record.record_date or "-" }}</strong></div>
        <div class="summary-item"><span>Category</span><strong>{{ record.category or "Unassigned" }}</strong></div>
        <div class="summary-item"><span>Target</span><strong>{{ record.target_system or "-" }}</strong></div>
        <div class="summary-item"><span>Account</span><strong>{{ record.target_account or "Unmapped" }}</strong></div>
        <div class="summary-item"><span>Confidence</span><strong>{{ format_confidence(record.confidence_score) }}</strong></div>
        <div class="summary-item"><span>Review</span><strong>{{ "required" if record.review_required else "not required" }}</strong></div>
        <div class="summary-item"><span>Export</span><strong>{{ record.export_status }}</strong></div>
        <div class="summary-item"><span>Reconciliation</span><strong>{{ record.reconciliation_status }}</strong></div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Record Review</h2>
          <p>Approve, reject, or reopen this normalized row with an audited explanation.</p>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence">
          <h3>Decision</h3>
          <form class="review-actions" method="post" action="{{ url_for('resolve_bookkeeping_record_form', record_id=record.id) }}">
            <textarea name="resolution" placeholder="Resolution note">{{ record.metadata.lastResolution.resolution if record.metadata and record.metadata.lastResolution else "" }}</textarea>
            <div class="button-row">
              <button type="submit" name="status" value="approved">Approve</button>
              <button class="secondary" type="submit" name="status" value="rejected">Reject</button>
              <button class="secondary" type="submit" name="status" value="needs_review">Reopen review</button>
              <button class="secondary" type="submit" name="status" value="ignored">Ignore</button>
            </div>
          </form>
        </div>
        <div class="evidence">
          <h3>Corrections</h3>
          <form class="review-actions" method="post" action="{{ url_for('resolve_bookkeeping_record_form', record_id=record.id) }}">
            <input type="hidden" name="status" value="approved">
            <div class="correction-grid">
              <input type="text" name="vendorName" value="{{ record.vendor_name or "" }}" placeholder="Vendor">
              <input type="text" name="category" value="{{ record.category or "" }}" placeholder="Category">
              <input type="text" name="recordDate" value="{{ record.record_date or "" }}" placeholder="Date YYYY-MM-DD">
              <input type="text" name="amount" value="{{ record.amount if record.amount is not none else "" }}" placeholder="Amount">
              <input type="text" name="targetAccount" value="{{ record.target_account or "" }}" placeholder="Target account">
              <input type="text" name="targetSystem" value="{{ record.target_system or "" }}" placeholder="Target system">
            </div>
            <input type="text" name="resolution" value="Approved with dashboard corrections.">
            <button type="submit">Approve corrections</button>
          </form>
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Source Proof</h2>
          <p>Trace the normalized row back to the originating document or bank transaction.</p>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence">
          <h3>Source</h3>
          <p><strong>Type:</strong> {{ record.source_type }}</p>
          <p><strong>Record type:</strong> {{ record.record_type }}</p>
          <p><strong>Description:</strong> {{ record.description or "-" }}</p>
          {% if record.document_id %}
          <p><strong>Document:</strong> <a href="{{ url_for('document_detail_page', document_id=record.document_id) }}">#{{ record.document_id }}</a></p>
          {% endif %}
          {% if record.bank_transaction_id %}
          <p><strong>Bank transaction:</strong> <span class="mono">#{{ record.bank_transaction_id }}</span></p>
          {% endif %}
        </div>
        <div class="evidence">
          <h3>Metadata</h3>
          <pre>{{ pretty_json(record.metadata) }}</pre>
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Line Items</h2>
          <p>Posting lines FAB will use for ledger, Wave, and MGZ downstream mapping.</p>
        </div>
      </div>
      {% if record.line_items %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Description</th><th>Quantity</th><th>Unit</th><th>Amount</th><th>VAT</th><th>Account</th><th>Tax</th></tr></thead>
          <tbody>
          {% for item in record.line_items %}
            <tr>
              <td class="mono">{{ item.line_index }}</td>
              <td>{{ item.description or item.item_name or "-" }}</td>
              <td>{{ item.quantity if item.quantity is not none else "-" }}</td>
              <td>{{ format_money(item.unit_price if item.unit_price is defined else none) }}</td>
              <td>{{ format_money(item.amount if item.amount is defined else none) }}</td>
              <td>{{ format_money(item.vat_amount if item.vat_amount is defined else none) }}</td>
              <td>{{ item.account_name or "Unmapped" }}</td>
              <td>{{ item.tax_code or "-" }}{% if item.tax_rate is not none %} / {{ item.tax_rate }}%{% endif %}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No line items are attached to this bookkeeping record.</div>
      {% endif %}
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Reconciliation Evidence</h2>
          <p>Bank/document matches tied to this record, with approval-gated close controls.</p>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence">
          <h3>Bank Transaction</h3>
          {% if bank_transaction %}
          <p><strong>Account:</strong> {{ bank_transaction.account_identifier }}</p>
          <p><strong>Transaction:</strong> <span class="mono">{{ bank_transaction.transaction_id }}</span></p>
          <p><strong>Date:</strong> {{ bank_transaction.transaction_date or "-" }}</p>
          <p><strong>Amount:</strong> {{ format_money(bank_transaction.amount) }} {{ bank_transaction.currency or "" }}</p>
          <p><strong>Description:</strong> {{ bank_transaction.description or "-" }}</p>
          <p><strong>Status:</strong> <span class="badge {{ bank_transaction.reconciliation_status }}">{{ bank_transaction.reconciliation_status }}</span></p>
          {% else %}
          <p class="muted">No persisted bank transaction is linked to this bookkeeping record.</p>
          {% endif %}
        </div>
        <div class="evidence">
          <h3>Latest Match State</h3>
          {% if reconciliation_matches %}
          {% set latest_match = reconciliation_matches[0] %}
          <p><strong>Match:</strong> #{{ latest_match.id }} <span class="badge {{ latest_match.status }}">{{ latest_match.status }}</span></p>
          <p><strong>Confidence:</strong> {{ format_confidence(latest_match.confidence_score) }}</p>
          <p><strong>Amount difference:</strong> {{ latest_match.amount_difference if latest_match.amount_difference is not none else "-" }}</p>
          <p><strong>Bank transaction:</strong> <span class="mono">{{ latest_match.bank_transaction_id }}</span></p>
          {% else %}
          <p class="muted">No reconciliation match evidence is attached to this record.</p>
          {% endif %}
        </div>
      </div>
      {% if reconciliation_matches %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Match</th><th>Document</th><th>Bank transaction</th><th>Status</th><th>Confidence</th><th>Amount diff</th><th>Actions</th></tr></thead>
          <tbody>
          {% for match in reconciliation_matches %}
            <tr>
              <td class="mono">#{{ match.id }}</td>
              <td class="mono">{{ "#" ~ match.document_id if match.document_id else "-" }}</td>
              <td class="mono">{{ match.bank_transaction_id }}</td>
              <td><span class="badge {{ match.status }}">{{ match.status }}</span></td>
              <td>{{ format_confidence(match.confidence_score) }}</td>
              <td>{{ match.amount_difference if match.amount_difference is not none else "-" }}</td>
              <td>
                {% if match.status in ["candidate", "unmatched_document", "missing_receipt", "needs_review"] %}
                <form class="review-actions" method="post" action="{{ url_for('resolve_reconciliation_form', reconciliation_match_id=match.id) }}">
                  {% if match.status == "candidate" %}
                  <button type="submit" name="status" value="approved">Reconcile</button>
                  <button class="secondary" type="submit" name="status" value="rejected">Reject match</button>
                  {% else %}
                  <button type="submit" name="status" value="resolved">Resolve</button>
                  <button class="secondary" type="submit" name="status" value="ignored">Ignore</button>
                  {% endif %}
                  <input type="text" name="resolution" value="Resolved from bookkeeping record #{{ record.id }}.">
                </form>
                {% else %}
                <span class="muted">closed</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% endif %}
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Routing And Export Evidence</h2>
          <p>Prepared downstream operations and approval/submission state.</p>
        </div>
      </div>
      {% if routing_attempts or export_attempts %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Type</th><th>Status</th><th>Target</th><th>Action</th><th>Submission</th><th>Message</th><th>Updated</th></tr></thead>
          <tbody>
          {% for attempt in routing_attempts %}
            <tr>
              <td>Routing</td>
              <td><span class="badge {{ attempt.status }}">{{ attempt.status }}</span></td>
              <td>{{ attempt.target }}</td>
              <td>{{ attempt.metadata.operation.action_id if attempt.metadata and attempt.metadata.operation else "-" }}</td>
              <td>not_executed</td>
              <td>{{ attempt.message or "-" }}</td>
              <td class="mono">{{ attempt.updated_at or attempt.created_at }}</td>
            </tr>
          {% endfor %}
          {% for export in export_attempts %}
            <tr>
              <td>Export</td>
              <td><span class="badge {{ export.status }}">{{ export.status }}</span></td>
              <td>{{ export.target_system }}</td>
              <td>{{ export.action_id or "-" }}</td>
              <td>{{ export.external_submission }}</td>
              <td>{{ export.message or "-" }}</td>
              <td class="mono">{{ export.updated_at or export.created_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No routing or export attempts are attached to this record yet.</div>
      {% endif %}
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Audit Trail</h2>
          <p>Record-specific actions FAB has logged locally.</p>
        </div>
      </div>
      {% if audit_events %}
      <div class="table-wrap">
        <table>
          <thead><tr><th>Created</th><th>Action</th><th>Actor</th><th>Details</th></tr></thead>
          <tbody>
          {% for event in audit_events %}
            <tr>
              <td class="mono">{{ event.created_at }}</td>
              <td>{{ event.action }}</td>
              <td>{{ event.actor or "-" }}</td>
              <td class="mono">{{ compact_json(event.details) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <div class="empty">No record-specific audit events recorded.</div>
      {% endif %}
      <details>
        <summary>Raw bookkeeping record payload</summary>
        <pre>{{ pretty_json(record) }}</pre>
      </details>
    </section>
  </div>
</body>
</html>
"""


LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FAB Operations Login</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f6f8fb; color: #15202b; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    form { width: min(420px, calc(100vw - 32px)); background: #fff; border: 1px solid #d9e2ea; padding: 22px; box-shadow: 0 14px 36px rgba(21, 32, 43, 0.08); }
    h1 { margin: 0 0 8px; font-size: 24px; letter-spacing: 0; }
    p { margin: 0 0 16px; color: #5d6b78; }
    input { width: 100%; min-height: 40px; border: 1px solid #d9e2ea; padding: 8px 10px; font: inherit; }
    button { width: 100%; min-height: 40px; margin-top: 12px; border: 1px solid #115e59; background: #0f766e; color: #fff; font: inherit; font-weight: 750; cursor: pointer; }
    .error { color: #b42318; }
  </style>
</head>
<body>
  <form method="post" action="{{ url_for('login') }}">
    <h1>FAB Operations</h1>
    <p>Enter the local API token.</p>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <input type="password" name="token" autofocus autocomplete="current-password">
    <button type="submit">Open dashboard</button>
  </form>
</body>
</html>
"""


def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    config = config or {}
    host = str(
        config.get("fab_local_api_host")
        or config.get("operations_api_host")
        or "127.0.0.1"
    )
    token = str(
        config.get("fab_local_api_token")
        or config.get("fab_operations_api_token")
        or config.get("operations_api_token")
        or ""
    )
    if host not in LOOPBACK_HOSTS and not token:
        raise ValueError("Refusing to expose FAB local API beyond loopback without an API token.")

    ledger_path = str(
        config.get("fab_local_ledger_path")
        or config.get("operations_ledger_path")
        or default_ledger_path()
    )
    intake_paths = _list_config(
        config,
        "fab_local_intake_paths",
        "operations_local_intake_paths",
        "operations_intake_paths",
        "operations_scanner_folder",
        "operations_scanner_watch_folder",
        "scanner_folder",
        "scanner_watch_folder",
    )
    intake_extensions = _list_config(
        config,
        "fab_local_intake_extensions",
        "operations_local_intake_extensions",
        "operations_intake_extensions",
    ) or sorted(DEFAULT_ALLOWED_EXTENSIONS)
    ledger = LocalOperationsLedger(ledger_path)
    app = Flask(__name__)
    app.config["FAB_LOCAL_LEDGER_PATH"] = ledger_path
    app.config["FAB_LOCAL_API_HOST"] = host
    app.config["FAB_LOCAL_INTAKE_PATHS"] = intake_paths
    app.config["FAB_LOCAL_INTAKE_EXTENSIONS"] = intake_extensions
    app.secret_key = hashlib.sha256((token or f"fab-local:{ledger_path}").encode("utf-8")).hexdigest()

    @app.before_request
    def require_token():
        if not token:
            return None
        if request.endpoint == "login":
            return None
        if request.headers.get("Authorization") != f"Bearer {token}":
            if session.get("fab_local_api_authenticated"):
                return None
            if not request.path.startswith("/api/"):
                return redirect(url_for("login"))
            return jsonify({"error": "Unauthorized"}), 401
        return None

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not token:
            return redirect(url_for("dashboard_page"))
        if request.method == "POST":
            submitted = request.form.get("token", "")
            if submitted == token:
                session["fab_local_api_authenticated"] = True
                return redirect(url_for("dashboard_page"))
            return render_template_string(LOGIN_TEMPLATE, error="Invalid token."), 401
        return render_template_string(LOGIN_TEMPLATE, error=None)

    @app.get("/api/health")
    def health():
        operations_health = LocalOperationsHealth(ledger, config).summarize()
        readiness = _readiness_service(config, ledger_path, host, bool(token), intake_paths, intake_extensions).compact()
        return jsonify({
            "status": operations_health["status"],
            "ledgerPath": app.config["FAB_LOCAL_LEDGER_PATH"],
            "authRequired": bool(token),
            "intakePaths": app.config["FAB_LOCAL_INTAKE_PATHS"],
            "intakeExtensions": app.config["FAB_LOCAL_INTAKE_EXTENSIONS"],
            "operations": operations_health,
            "readiness": readiness,
        })

    @app.get("/")
    def dashboard_page():
        metrics = ledger.dashboard_metrics()
        operations_health = LocalOperationsHealth(ledger, config).summarize()
        exceptions = LocalExceptionQueueService(ledger, config).list_exceptions(limit=50)
        readiness_service = _readiness_service(config, ledger_path, host, bool(token), intake_paths, intake_extensions)
        readiness = readiness_service.summarize()
        autonomy_plan = _autonomy_service(
            ledger,
            config,
            readiness_service,
            intake_paths,
            intake_extensions,
        ).plan()
        documents = ledger.list_documents(limit=25)
        sources = ledger.list_source_accounts(limit=25)
        document_groups = ledger.list_document_groups(limit=25)
        extracted_fields = ledger.list_extracted_fields(limit=40)
        duplicate_candidates = ledger.list_duplicate_candidates(limit=25)
        review_items = ledger.list_review_items(status=("pending", "in_review"), limit=12)
        review_documents = {
            item["document_id"]: ledger.get_document(int(item["document_id"]))
            for item in review_items
            if item.get("document_id")
        }
        routing_attempts = ledger.list_routing_attempts(limit=20)
        export_attempts = ledger.list_export_attempts(limit=20)
        reconciliation_matches = ledger.list_reconciliation_matches(limit=20)
        bank_transactions = ledger.list_bank_transactions(limit=25)
        bank_statement_imports = ledger.list_bank_statement_imports(limit=10)
        bookkeeping_records = ledger.list_bookkeeping_records(limit=25)
        master_ledger = LocalMasterLedgerService(ledger, config).project(limit=100)
        backups = LocalBackupService(ledger, config).list_backups(limit=10)
        mijngeldzaken_service = LocalMijngeldzakenControlService(config)
        mijngeldzaken_control = mijngeldzaken_service.overview(ledger)
        mijngeldzaken_controls = mijngeldzaken_control.get("masterLedgerControls")
        wave_service = LocalWaveControlService(config)
        wave_control = wave_service.overview()
        wave_report_snapshots = ledger.list_wave_report_snapshots(limit=20)
        wave_operation_snapshots = ledger.list_wave_operation_snapshots(limit=20)
        wave_report_controls = wave_service.evaluate_report_controls(ledger)
        close_readiness = LocalCloseReadinessService(ledger, config).assess()
        close_packs = LocalClosePackService(ledger, config).list_packs(limit=10)
        rules = ledger.list_vendor_category_rules(limit=25)
        vendor_summaries = ledger.list_vendor_summaries(limit=25)
        category_summaries = ledger.list_category_summaries(limit=25)
        corrections = ledger.list_review_corrections(limit=25)
        audit_events = ledger.list_audit_events(limit=15)
        last_intake_summary = session.pop("fab_last_intake_summary", None)
        last_processing_summary = session.pop("fab_last_processing_summary", None)
        last_routing_summary = session.pop("fab_last_routing_summary", None)
        last_export_summary = session.pop("fab_last_export_summary", None)
        last_mijngeldzaken_plan = session.pop("fab_last_mijngeldzaken_plan", None)
        last_wave_plan = session.pop("fab_last_wave_plan", None)
        last_reconciliation_summary = session.pop("fab_last_reconciliation_summary", None)
        last_bank_import_summary = session.pop("fab_last_bank_import_summary", None)
        last_record_refresh_summary = session.pop("fab_last_record_refresh_summary", None)
        last_autonomy_summary = session.pop("fab_last_autonomy_summary", None)
        last_backup_summary = session.pop("fab_last_backup_summary", None)
        last_close_pack_summary = session.pop("fab_last_close_pack_summary", None)
        health_payload = {
            "status": operations_health["status"],
            "ledger_path": app.config["FAB_LOCAL_LEDGER_PATH"],
            "auth_required": bool(token),
            "host": app.config["FAB_LOCAL_API_HOST"],
            "intake_paths": app.config["FAB_LOCAL_INTAKE_PATHS"],
            "operations": operations_health,
            "readiness": readiness,
        }
        raw_payload = {
            "metrics": metrics,
            "operationsHealth": operations_health,
            "exceptions": exceptions,
            "readiness": readiness,
            "autonomyPlan": autonomy_plan,
            "sources": sources,
            "documents": documents,
            "documentGroups": document_groups,
            "extractedFields": extracted_fields,
            "duplicateCandidates": duplicate_candidates,
            "reviewItems": review_items,
            "routingAttempts": routing_attempts,
            "exportAttempts": export_attempts,
            "bookkeepingRecords": bookkeeping_records,
            "masterLedger": master_ledger,
            "bankTransactions": bank_transactions,
            "bankStatementImports": bank_statement_imports,
            "mijngeldzakenControl": mijngeldzaken_control,
            "mijngeldzakenControls": mijngeldzaken_controls,
            "waveControl": wave_control,
            "waveReportSnapshots": wave_report_snapshots,
            "waveOperationSnapshots": wave_operation_snapshots,
            "waveReportControls": wave_report_controls,
            "closeReadiness": close_readiness,
            "closePacks": close_packs,
            "reconciliationMatches": reconciliation_matches,
            "backups": backups,
            "rules": rules,
            "vendors": vendor_summaries,
            "categories": category_summaries,
            "corrections": corrections,
            "auditEvents": audit_events,
            "health": health_payload,
            "lastIntakeSummary": last_intake_summary,
            "lastProcessingSummary": last_processing_summary,
            "lastGroupingSummary": session.get("fab_last_grouping_summary"),
            "lastRoutingSummary": last_routing_summary,
            "lastExportSummary": last_export_summary,
            "lastMijngeldzakenPlan": last_mijngeldzaken_plan,
            "lastWavePlan": last_wave_plan,
            "lastReconciliationSummary": last_reconciliation_summary,
            "lastBankImportSummary": last_bank_import_summary,
            "lastRecordRefreshSummary": last_record_refresh_summary,
            "lastAutonomySummary": last_autonomy_summary,
            "lastBackupSummary": last_backup_summary,
            "lastClosePackSummary": last_close_pack_summary,
        }
        return render_template_string(
            DASHBOARD_TEMPLATE,
            autonomy_plan=autonomy_plan,
            autonomy_summary=last_autonomy_summary,
            audit_events=audit_events,
            backup_summary=last_backup_summary,
            backups=backups,
            bank_import_summary=last_bank_import_summary,
            bank_statement_imports=bank_statement_imports,
            bank_transactions=bank_transactions,
            bookkeeping_records=bookkeeping_records,
            compact_json=_compact_json,
            close_pack_summary=last_close_pack_summary,
            close_packs=close_packs,
            close_readiness=close_readiness,
            documents=documents,
            document_groups=document_groups,
            duplicate_candidates=duplicate_candidates,
            export_approval_phrase=EXPORT_APPROVAL_PHRASE,
            export_attempts=export_attempts,
            export_rejection_phrase=EXPORT_REJECTION_PHRASE,
            export_result_confirmation_phrase=EXPORT_RESULT_CONFIRMATION_PHRASE,
            export_summary=last_export_summary,
            exceptions=exceptions,
            extracted_fields=extracted_fields,
            format_confidence=_format_confidence,
            format_money=_format_money,
            grouping_summary=session.pop("fab_last_grouping_summary", None),
            health=health_payload,
            intake_extensions=app.config["FAB_LOCAL_INTAKE_EXTENSIONS"],
            intake_paths=app.config["FAB_LOCAL_INTAKE_PATHS"],
            intake_summary=last_intake_summary,
            ledger_name=os.path.basename(app.config["FAB_LOCAL_LEDGER_PATH"]),
            metric_cards=[
                {"label": "Documents", "value": metrics["documents"]},
                {"label": "Sources", "value": len(sources)},
                {"label": "Pending Review", "value": metrics["pending_review"]},
                {"label": "Duplicates", "value": metrics["duplicates"]},
                {"label": "Dupe Review", "value": metrics["open_duplicate_candidates"]},
                {"label": "Group Review", "value": metrics["open_document_groups"]},
                {"label": "Rule Review", "value": metrics["suggested_vendor_rules"]},
                {"label": "Unreconciled", "value": metrics["unreconciled_documents"]},
                {"label": "Bank Tx", "value": metrics["bank_transactions"]},
                {"label": "Records", "value": metrics["bookkeeping_records"]},
                {"label": "Master Rows", "value": master_ledger["summary"]["totalRows"]},
                {"label": "Export Ready", "value": metrics["export_ready_records"]},
                {"label": "Export Approvals", "value": metrics["export_attempts_needing_approval"]},
                {"label": "MGZ Rows", "value": mijngeldzaken_controls["rowCount"]},
                {"label": "MGZ Blocked", "value": mijngeldzaken_controls["blockingCount"]},
                {"label": "Unmatched Bank", "value": metrics["unreconciled_bank_transactions"]},
                {"label": "Failed", "value": metrics["failed_documents"]},
                {"label": "Wave Reports", "value": metrics["wave_report_snapshots"]},
                {"label": "Wave Ops", "value": metrics["wave_operation_snapshots"]},
                {"label": "Audit Events", "value": metrics["audit_events"]},
            ],
            metrics=metrics,
            master_ledger=master_ledger,
            mijngeldzaken_control=mijngeldzaken_control,
            mijngeldzaken_controls=mijngeldzaken_controls,
            mijngeldzaken_plan_summary=last_mijngeldzaken_plan,
            pretty_json=_pretty_json,
            processing_summary=last_processing_summary,
            operations_health=operations_health,
            readiness=readiness,
            raw_payload=_pretty_json(raw_payload),
            record_refresh_summary=last_record_refresh_summary,
            corrections=corrections,
            review_documents=review_documents,
            review_items=review_items,
            reconciliation_matches=reconciliation_matches,
            reconciliation_summary=last_reconciliation_summary,
            routing_attempts=routing_attempts,
            routing_summary=last_routing_summary,
            rules=rules,
            vendor_summaries=vendor_summaries,
            category_summaries=category_summaries,
            sources=sources,
            wave_control=wave_control,
            wave_account_discovery_summary=session.pop("fab_last_wave_account_discovery", None),
            wave_plan_summary=last_wave_plan,
            wave_report_snapshots=wave_report_snapshots,
            wave_operation_snapshots=wave_operation_snapshots,
            wave_report_controls=wave_report_controls,
        )

    @app.get("/api/dashboard")
    def dashboard():
        return jsonify(ledger.dashboard_metrics())

    @app.get("/api/exceptions")
    def exceptions_api():
        include_entities = _bool_value(request.args.get("includeEntities"), default=True)
        return jsonify(LocalExceptionQueueService(ledger, config).list_exceptions(
            limit=_limit_arg(),
            include_entities=include_entities,
        ))

    @app.get("/api/close-readiness")
    def close_readiness_api():
        workflow_id = request.args.get("workflowId") or request.args.get("workflow_id") or "daily_reconciliation_run"
        return jsonify(LocalCloseReadinessService(ledger, config).assess(
            workflow_id=workflow_id,
            from_date=request.args.get("fromDate") or request.args.get("from_date"),
            to_date=request.args.get("toDate") or request.args.get("to_date"),
        ))

    @app.get("/api/close-packs")
    def close_packs_api():
        return jsonify(LocalClosePackService(ledger, config).list_packs(limit=_limit_arg()))

    @app.post("/api/close-packs")
    def prepare_close_pack_api():
        payload = request.get_json(silent=True) or {}
        result = LocalClosePackService(ledger, config).prepare(
            workflow_id=payload.get("workflowId") or payload.get("workflow_id") or "daily_reconciliation_run",
            from_date=payload.get("fromDate") or payload.get("from_date"),
            to_date=payload.get("toDate") or payload.get("to_date"),
            actor=payload.get("actor") or "local_api",
            require_ready=_bool_value(payload.get("requireReady"), default=True),
        )
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    @app.get("/api/close-packs/inspect")
    def inspect_close_pack_api():
        close_pack_path = request.args.get("closePackPath") or request.args.get("closePackFilename")
        try:
            return jsonify(LocalClosePackService(ledger, config).inspect_pack(str(close_pack_path or "")))
        except Exception as exc:
            return jsonify({"success": False, "status": "invalid", "error": str(exc)}), 400

    @app.post("/close-packs/prepare")
    def prepare_close_pack_form():
        session["fab_last_close_pack_summary"] = LocalClosePackService(ledger, config).prepare(
            actor="dashboard",
        )
        return redirect(url_for("dashboard_page", _anchor="close"))

    @app.get("/api/document-groups")
    def document_groups_api():
        document_id = request.args.get("documentId") or request.args.get("document_id")
        try:
            parsed_document_id = int(document_id) if document_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid documentId"}), 400
        return jsonify({
            "documentGroups": ledger.list_document_groups(
                status=request.args.get("status"),
                group_type=request.args.get("groupType") or request.args.get("group_type"),
                document_id=parsed_document_id,
                limit=_limit_arg(),
            )
        })

    @app.post("/api/document-groups/detect")
    def detect_document_groups_api():
        payload = request.get_json(silent=True) or {}
        return jsonify(LocalDocumentGroupingService(ledger, config).detect_scanner_groups(
            limit=_bounded_positive_int(payload.get("limit"), default=100, maximum=500),
        ))

    @app.post("/document-groups/detect")
    def detect_document_groups_form():
        session["fab_last_grouping_summary"] = LocalDocumentGroupingService(ledger, config).detect_scanner_groups(limit=100)
        return redirect(url_for("dashboard_page", _anchor="groups"))

    @app.post("/api/document-groups/merge")
    def merge_document_group_api():
        payload = request.get_json(silent=True) or {}
        result = LocalDocumentGroupingService(ledger, config).merge_documents(
            payload.get("documentIds") or payload.get("document_ids") or [],
            title=payload.get("title"),
            reason=payload.get("reason"),
            actor=payload.get("actor") or "api",
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.post("/api/document-groups/<int:group_id>/split")
    def split_document_group_api(group_id: int):
        payload = request.get_json(silent=True) or {}
        try:
            document_id = int(payload.get("documentId") or payload.get("document_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "documentId is required"}), 400
        result = LocalDocumentGroupingService(ledger, config).split_document_from_group(
            group_id,
            document_id,
            reason=payload.get("reason"),
            actor=payload.get("actor") or "api",
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.get("/api/sources")
    def sources():
        return jsonify({
            "sources": ledger.list_source_accounts(
                source_type=request.args.get("sourceType") or request.args.get("source_type"),
                status=request.args.get("status"),
                limit=_limit_arg(),
            )
        })

    @app.post("/api/sources")
    def upsert_source():
        payload = request.get_json(silent=True) or {}
        try:
            source_account_id = ledger.upsert_source_account(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        ledger.record_audit_event({
            "action": "local_api.source.upsert",
            "entityType": "source_account",
            "entityId": str(source_account_id),
            "details": {
                "sourceType": payload.get("sourceType") or payload.get("source_type"),
                "sourceIdentifier": payload.get("sourceIdentifier") or payload.get("source_identifier"),
                "status": payload.get("status") or "active",
                "metadataKeys": sorted((payload.get("metadata") or {}).keys())
                if isinstance(payload.get("metadata"), dict)
                else [],
            },
        })
        return jsonify({"success": True, "sourceAccountId": source_account_id})

    @app.get("/api/settings")
    def settings():
        return jsonify(_readiness_service(
            config,
            ledger_path,
            host,
            bool(token),
            intake_paths,
            intake_extensions,
        ).summarize())

    @app.get("/api/autonomy/plan")
    def autonomy_plan():
        limit = _bounded_positive_int(request.args.get("limit"), default=25, maximum=100)
        include_wave_plan = _bool_value(request.args.get("includeWavePlan"), default=True)
        return jsonify(_autonomy_service(
            ledger,
            config,
            _readiness_service(config, ledger_path, host, bool(token), intake_paths, intake_extensions),
            intake_paths,
            intake_extensions,
        ).plan(limit=limit, include_wave_plan=include_wave_plan))

    @app.post("/api/autonomy/run")
    def run_autonomy():
        payload = request.get_json(silent=True) or {}
        bank_transactions = payload.get("bankTransactions") if "bankTransactions" in payload else None
        if bank_transactions is not None and not isinstance(bank_transactions, list):
            return jsonify({"error": "bankTransactions must be a list"}), 400
        result = _autonomy_service(
            ledger,
            config,
            _readiness_service(config, ledger_path, host, bool(token), intake_paths, intake_extensions),
            intake_paths,
            intake_extensions,
        ).run_cycle(
            limit=_bounded_positive_int(payload.get("limit"), default=25, maximum=100),
            bank_transactions=bank_transactions,
            include_wave_plan=_bool_value(payload.get("includeWavePlan"), default=True),
            dry_run=bool(payload.get("dryRun", False)),
        )
        status_code = 400 if result.get("status") == "blocked" else 200
        return jsonify(result), status_code

    @app.post("/autonomy/run")
    def run_autonomy_form():
        session["fab_last_autonomy_summary"] = _autonomy_service(
            ledger,
            config,
            _readiness_service(config, ledger_path, host, bool(token), intake_paths, intake_extensions),
            intake_paths,
            intake_extensions,
        ).run_cycle(limit=25, include_wave_plan=True)
        return redirect(url_for("dashboard_page", _anchor="autonomy"))

    @app.get("/api/wave")
    def wave_overview():
        return jsonify(LocalWaveControlService(config).overview())

    @app.get("/api/wave/actions")
    def wave_actions():
        return jsonify(LocalWaveControlService(config).actions(
            surface=request.args.get("surface"),
            safety=request.args.get("safety"),
            mode=request.args.get("mode"),
        ))

    @app.get("/api/wave/account-mappings")
    def wave_account_mappings():
        return jsonify(WaveappsAccountDiscoveryService(config).mapping_status(
            request.args.get("targetSystem") or request.args.get("target_system"),
        ))

    def run_wave_account_discovery(target_system: str) -> Dict[str, Any]:
        result = WaveappsAccountDiscoveryService(config).discover(target_system)
        operation = result.get("operation") if isinstance(result.get("operation"), dict) else None
        if operation:
            operation["metadata"] = {
                "accountDiscovery": {
                    "targetSystem": result.get("targetSystem"),
                    "business": result.get("business"),
                    "accounts": result.get("accounts"),
                    "mapping": result.get("mapping"),
                    "externalSubmission": "not_executed",
                },
            }
            LocalWaveControlService(config).record_operation_snapshot(
                ledger,
                operation,
                workflow_id="wave_account_discovery",
                status=result.get("status") or "read_result_captured",
            )
        ledger.record_audit_event({
            "action": "local_wave.account_discovery_read",
            "entityType": "wave_account_discovery",
            "entityId": str((operation or {}).get("operation_id") or target_system),
            "details": {
                "targetSystem": target_system,
                "success": result.get("success"),
                "status": result.get("status"),
                "accountCount": len(result.get("accounts") or []),
                "externalSubmission": "not_executed",
            },
        })
        return result

    @app.post("/api/wave/accounts/discover")
    def discover_wave_accounts():
        payload = request.get_json(silent=True) or {}
        target_system = str(payload.get("targetSystem") or payload.get("target_system") or "waveapps_business")
        result = run_wave_account_discovery(target_system)
        status_code = 200 if result.get("success") else 400
        if result.get("status") in {"rate_limited", "quota_exhausted"}:
            status_code = 429
        elif result.get("status") == "provider_error":
            status_code = 502
        return jsonify(result), status_code

    @app.post("/wave/accounts/discover")
    def discover_wave_accounts_form():
        target_system = str(request.form.get("targetSystem") or "waveapps_business")
        result = run_wave_account_discovery(target_system)
        session["fab_last_wave_account_discovery"] = {
            "success": result.get("success"),
            "status": result.get("status"),
            "targetSystem": target_system,
            "business": result.get("business"),
            "accounts": result.get("accounts"),
            "mapping": result.get("mapping"),
            "message": result.get("message"),
            "externalSubmission": "not_executed",
        }
        return redirect(url_for("dashboard_page", _anchor="wave"))

    @app.get("/api/wave/reports")
    def wave_reports():
        return jsonify(LocalWaveControlService(config).reports(section=request.args.get("section")))

    @app.get("/api/wave/report-snapshots")
    def wave_report_snapshots():
        return jsonify({
            "waveReportSnapshots": ledger.list_wave_report_snapshots(
                report_type=request.args.get("reportType") or request.args.get("report_type"),
                workflow_id=request.args.get("workflowId") or request.args.get("workflow_id"),
                status=request.args.get("status"),
                limit=_limit_arg(),
            )
        })

    @app.get("/api/wave/report-controls")
    def wave_report_controls():
        workflow_id = request.args.get("workflowId") or request.args.get("workflow_id") or "daily_reconciliation_run"
        return jsonify(LocalWaveControlService(config).evaluate_report_controls(
            ledger,
            workflow_id=workflow_id,
            limit=_limit_arg(),
        ))

    @app.post("/api/wave/report-results")
    def record_wave_report_result():
        payload = request.get_json(silent=True) or {}
        service = LocalWaveControlService(config)
        result = service.record_report_result(ledger, payload)
        snapshot = result.get("waveReportSnapshot") or {}
        ledger.record_audit_event({
            "action": "local_wave.report_result_captured",
            "entityType": "wave_report_snapshot",
            "entityId": str(result.get("waveReportSnapshotId") or payload.get("snapshotId") or payload.get("operationId")),
            "details": {
                "status": result.get("status"),
                "success": result.get("success"),
                "reportType": snapshot.get("report_type") or payload.get("reportType"),
                "actionId": snapshot.get("action_id") or payload.get("actionId"),
                "workflowId": snapshot.get("workflow_id") or payload.get("workflowId"),
                "rowCount": (snapshot.get("row_count") if snapshot else (payload.get("result") or {}).get("rowCount")),
                "externalSubmission": result.get("externalSubmission"),
            },
        })
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.get("/api/wave/operations")
    def wave_operation_snapshots():
        return jsonify({
            "waveOperationSnapshots": ledger.list_wave_operation_snapshots(
                surface=request.args.get("surface"),
                workflow_id=request.args.get("workflowId") or request.args.get("workflow_id"),
                action_id=request.args.get("actionId") or request.args.get("action_id"),
                safety=request.args.get("safety"),
                status=request.args.get("status"),
                operation_id=request.args.get("operationId") or request.args.get("operation_id"),
                limit=_limit_arg(),
            )
        })

    @app.get("/api/mijngeldzaken")
    def mijngeldzaken_overview():
        include_controls = _bool_value(request.args.get("includeControls"), default=True)
        return jsonify(LocalMijngeldzakenControlService(config).overview(ledger if include_controls else None))

    @app.get("/api/mijngeldzaken/actions")
    def mijngeldzaken_actions():
        return jsonify(LocalMijngeldzakenControlService(config).actions(
            surface=request.args.get("surface"),
            safety=request.args.get("safety"),
            mode=request.args.get("mode"),
        ))

    @app.post("/api/mijngeldzaken/plan")
    def mijngeldzaken_plan():
        payload = request.get_json(silent=True) or {}
        result = LocalMijngeldzakenControlService(config).plan_action(payload)
        operation = result.get("operation") or {}
        ledger.record_audit_event({
            "action": "local_mijngeldzaken.action_plan_prepared",
            "entityType": "mijngeldzaken_operation",
            "entityId": operation.get("operation_id"),
            "details": {
                "surface": operation.get("surface"),
                "actionId": operation.get("action_id"),
                "safety": operation.get("safety"),
                "planStatus": (operation.get("plan") or {}).get("status"),
                "externalSubmission": "not_executed",
            },
        })
        status_code = 400 if result.get("status") in {"unsupported", "invalid_payload"} else 200
        return jsonify(result), status_code

    @app.post("/api/mijngeldzaken/workflows/plan")
    def plan_mijngeldzaken_workflow():
        payload = request.get_json(silent=True) or {}
        service = LocalMijngeldzakenControlService(config)
        result = service.plan_workflow(payload)
        controls = service.evaluate_master_ledger_controls(ledger)
        result["masterLedgerControls"] = controls
        workflow_plan = result.get("workflowPlan") or {}
        ledger.record_audit_event({
            "action": "local_mijngeldzaken.workflow_plan_prepared",
            "entityType": "mijngeldzaken_workflow",
            "entityId": workflow_plan.get("workflowId"),
            "details": {
                "status": result.get("status"),
                "workflowId": workflow_plan.get("workflowId"),
                "operationCount": result.get("operationCount"),
                "masterLedgerControls": {
                    "status": controls.get("status"),
                    "rowCount": controls.get("rowCount"),
                    "blockingCount": controls.get("blockingCount"),
                    "readyForDraft": controls.get("readyForDraft"),
                    "readyForApproval": controls.get("readyForApproval"),
                    "readyForExternalExecution": controls.get("readyForExternalExecution"),
                },
                "externalSubmission": result.get("externalSubmission"),
            },
        })
        status_code = 400 if result.get("status") in {"unsupported", "invalid_payload"} else 200
        return jsonify(result), status_code

    @app.post("/mijngeldzaken/workflows/plan")
    def plan_mijngeldzaken_workflow_form():
        payload = {
            "workflowId": request.form.get("workflowId") or "master_ledger_downstream_sync",
            "fromDate": request.form.get("fromDate") or None,
            "toDate": request.form.get("toDate") or None,
            "actor": "dashboard",
        }
        service = LocalMijngeldzakenControlService(config)
        result = service.plan_workflow(payload)
        controls = service.evaluate_master_ledger_controls(ledger)
        result["masterLedgerControls"] = controls
        session["fab_last_mijngeldzaken_plan"] = _compact_mijngeldzaken_plan_summary(result)
        workflow_plan = result.get("workflowPlan") or {}
        ledger.record_audit_event({
            "action": "local_mijngeldzaken.workflow_plan_prepared",
            "entityType": "mijngeldzaken_workflow",
            "entityId": workflow_plan.get("workflowId"),
            "details": {
                "status": result.get("status"),
                "workflowId": workflow_plan.get("workflowId"),
                "operationCount": result.get("operationCount"),
                "masterLedgerControls": {
                    "status": controls.get("status"),
                    "rowCount": controls.get("rowCount"),
                    "blockingCount": controls.get("blockingCount"),
                    "readyForDraft": controls.get("readyForDraft"),
                    "readyForApproval": controls.get("readyForApproval"),
                    "readyForExternalExecution": controls.get("readyForExternalExecution"),
                },
                "externalSubmission": result.get("externalSubmission"),
            },
        })
        return redirect(url_for("dashboard_page", _anchor="mijngeldzaken"))

    @app.post("/api/wave/reports/plan")
    def plan_wave_report():
        payload = request.get_json(silent=True) or {}
        service = LocalWaveControlService(config)
        result = service.plan_report_action(
            str(payload.get("reportType") or payload.get("report_type") or "account-transactions"),
            from_date=payload.get("fromDate") or payload.get("from_date"),
            to_date=payload.get("toDate") or payload.get("to_date"),
            as_of_date=payload.get("asOfDate") or payload.get("as_of_date"),
            action_id=str(payload.get("actionId") or payload.get("action_id") or "report_table_read"),
            export_format=payload.get("format") or payload.get("exportFormat") or payload.get("export_format"),
            basis=str(payload.get("basis") or "accrual"),
            account_option=str(payload.get("accountOption") or payload.get("account_option") or "-1"),
            account_name=str(payload.get("accountName") or payload.get("account_name") or "All Accounts"),
            contact_option=str(payload.get("contactOption") or payload.get("contact_option") or "0"),
            contact_name=str(payload.get("contactName") or payload.get("contact_name") or "All Contacts"),
            cash_mode=str(payload.get("cashMode") or payload.get("cash_mode") or "1"),
        )
        operation = result.get("operation") or {}
        snapshot_id = None
        operation_snapshot_id = None
        if result.get("status") == "planned":
            snapshot_id = service.record_report_operation_snapshot(
                ledger,
                operation,
                workflow_id=payload.get("workflowId") or payload.get("workflow_id") or "ad_hoc_report_plan",
            )
            operation_snapshot_id = service.record_operation_snapshot(
                ledger,
                operation,
                workflow_id=payload.get("workflowId") or payload.get("workflow_id") or "ad_hoc_report_plan",
            )
        result["waveReportSnapshotId"] = snapshot_id
        result["waveOperationSnapshotId"] = operation_snapshot_id
        ledger.record_audit_event({
            "action": "local_wave.report_plan_prepared",
            "entityType": "wave_report_snapshot",
            "entityId": str(snapshot_id) if snapshot_id is not None else operation.get("operation_id"),
            "details": {
                "status": result.get("status"),
                "reportType": (operation.get("payload") or {}).get("reportType"),
                "actionId": operation.get("action_id"),
                "operationId": operation.get("operation_id"),
                "waveOperationSnapshotId": operation_snapshot_id,
                "externalSubmission": result.get("externalSubmission"),
            },
        })
        status_code = 400 if result.get("status") in {"unsupported", "invalid_payload"} else 200
        return jsonify(result), status_code

    @app.post("/api/wave/plan")
    def plan_wave_action():
        payload = request.get_json(silent=True) or {}
        service = LocalWaveControlService(config)
        result = service.plan_action(payload)
        operation = result.get("operation") or {}
        snapshot_id = None
        operation_snapshot_id = None
        if result.get("status") == "planned":
            operation_snapshot_id = service.record_operation_snapshot(
                ledger,
                operation,
                workflow_id=payload.get("workflowId") or payload.get("workflow_id") or "ad_hoc_action_plan",
            )
            if operation.get("surface") == "reports":
                snapshot_id = service.record_report_operation_snapshot(
                    ledger,
                    operation,
                    workflow_id=payload.get("workflowId") or payload.get("workflow_id") or "ad_hoc_action_plan",
                )
        if snapshot_id is not None:
            result["waveReportSnapshotId"] = snapshot_id
        if operation_snapshot_id is not None:
            result["waveOperationSnapshotId"] = operation_snapshot_id
        ledger.record_audit_event({
            "action": "local_wave.action_plan_prepared",
            "entityType": "wave_operation",
            "entityId": operation.get("operation_id"),
            "details": {
                "status": result.get("status"),
                "actionId": operation.get("action_id") or payload.get("actionId"),
                "surface": operation.get("surface") or payload.get("surface"),
                "safety": operation.get("safety"),
                "waveReportSnapshotId": snapshot_id,
                "waveOperationSnapshotId": operation_snapshot_id,
                "externalSubmission": result.get("externalSubmission"),
            },
        })
        status_code = 400 if result.get("status") in {"unsupported", "invalid_payload"} else 200
        return jsonify(result), status_code

    @app.post("/api/wave/workflows/plan")
    def plan_wave_workflow():
        payload = request.get_json(silent=True) or {}
        service = LocalWaveControlService(config)
        result = service.plan_workflow(payload)
        snapshot_summary = service.record_workflow_report_snapshots(ledger, result)
        operation_snapshot_summary = service.record_workflow_operation_snapshots(ledger, result)
        report_controls = service.evaluate_report_controls(
            ledger,
            workflow_id=(result.get("workflow_plan") or {}).get("workflow_id") or "daily_reconciliation_run",
        )
        result["waveReportSnapshots"] = snapshot_summary
        result["waveOperationSnapshots"] = operation_snapshot_summary
        result["waveReportControls"] = report_controls
        ledger.record_audit_event({
            "action": "local_wave.workflow_plan_prepared",
            "entityType": "wave_workflow",
            "entityId": result.get("workflow_plan", {}).get("workflow_id"),
            "details": {
                "status": result.get("status"),
                "workflowId": result.get("workflow_plan", {}).get("workflow_id"),
                "operationCount": result.get("operationCount"),
                "waveReportSnapshots": snapshot_summary,
                "waveOperationSnapshots": operation_snapshot_summary,
                "waveReportControls": {
                    "status": report_controls.get("status"),
                    "requiredReportCount": report_controls.get("requiredReportCount"),
                    "coveredReportCount": report_controls.get("coveredReportCount"),
                    "resultGapCount": report_controls.get("resultGapCount"),
                    "blockingCount": report_controls.get("blockingCount"),
                },
                "externalSubmission": result.get("externalSubmission"),
            },
        })
        return jsonify(result)

    @app.post("/wave/workflows/plan")
    def plan_wave_workflow_form():
        payload = {
            "workflowId": request.form.get("workflowId") or "daily_reconciliation_run",
            "fromDate": request.form.get("fromDate"),
            "toDate": request.form.get("toDate"),
        }
        service = LocalWaveControlService(config)
        wave_plan = service.plan_workflow(payload)
        snapshot_summary = service.record_workflow_report_snapshots(ledger, wave_plan)
        operation_snapshot_summary = service.record_workflow_operation_snapshots(ledger, wave_plan)
        report_controls = service.evaluate_report_controls(
            ledger,
            workflow_id=(wave_plan.get("workflow_plan") or {}).get("workflow_id") or "daily_reconciliation_run",
        )
        wave_plan["waveReportSnapshots"] = snapshot_summary
        wave_plan["waveOperationSnapshots"] = operation_snapshot_summary
        wave_plan["waveReportControls"] = report_controls
        session["fab_last_wave_plan"] = _compact_wave_plan_summary(wave_plan)
        workflow_plan = wave_plan.get("workflow_plan", {})
        ledger.record_audit_event({
            "action": "local_wave.workflow_plan_prepared",
            "entityType": "wave_workflow",
            "entityId": workflow_plan.get("workflow_id"),
            "details": {
                "status": wave_plan.get("status"),
                "workflowId": workflow_plan.get("workflow_id"),
                "operationCount": wave_plan.get("operationCount"),
                "waveReportSnapshots": snapshot_summary,
                "waveOperationSnapshots": operation_snapshot_summary,
                "waveReportControls": {
                    "status": report_controls.get("status"),
                    "requiredReportCount": report_controls.get("requiredReportCount"),
                    "coveredReportCount": report_controls.get("coveredReportCount"),
                    "resultGapCount": report_controls.get("resultGapCount"),
                    "blockingCount": report_controls.get("blockingCount"),
                },
                "externalSubmission": wave_plan.get("externalSubmission"),
            },
        })
        return redirect(url_for("dashboard_page", _anchor="wave"))

    @app.get("/api/documents")
    def documents():
        return jsonify({
            "documents": ledger.list_documents(
                status=request.args.get("status"),
                limit=_limit_arg(),
            )
        })

    @app.get("/documents/<int:document_id>")
    def document_detail_page(document_id: int):
        document = ledger.get_document(document_id)
        if not document:
            return render_template_string(
                "<h1>Document not found</h1><p>No local FAB document exists for this id.</p>"
            ), 404
        open_review_count = len([
            item
            for item in document.get("review_items") or []
            if item.get("status") in {"pending", "in_review"}
        ])
        return render_template_string(
            DOCUMENT_DETAIL_TEMPLATE,
            compact_json=_compact_json,
            document=document,
            format_confidence=_format_confidence,
            format_money=_format_money,
            open_review_count=open_review_count,
            pretty_json=_pretty_json,
            source_preview=_document_source_preview(document),
        )

    @app.get("/api/documents/<int:document_id>")
    def document_detail(document_id: int):
        document = ledger.get_document(document_id)
        if not document:
            return jsonify({"error": "Document not found"}), 404
        return jsonify(document)

    @app.get("/api/duplicates")
    def duplicate_candidates_api():
        document_id = request.args.get("documentId") or request.args.get("document_id")
        candidate_document_id = request.args.get("candidateDocumentId") or request.args.get("candidate_document_id")
        try:
            parsed_document_id = int(document_id) if document_id else None
            parsed_candidate_document_id = int(candidate_document_id) if candidate_document_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid duplicate candidate document id"}), 400
        return jsonify({
            "duplicateCandidates": ledger.list_duplicate_candidates(
                status=request.args.get("status"),
                document_id=parsed_document_id,
                candidate_document_id=parsed_candidate_document_id,
                limit=_limit_arg(),
            )
        })

    @app.get("/api/extracted-fields")
    def extracted_fields():
        document_id = request.args.get("documentId")
        try:
            parsed_document_id = int(document_id) if document_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid documentId"}), 400
        return jsonify({
            "extractedFields": ledger.list_extracted_fields(
                document_id=parsed_document_id,
                field_name=request.args.get("fieldName") or request.args.get("field_name"),
                limit=_limit_arg(),
            )
        })

    @app.get("/api/bookkeeping-records")
    def bookkeeping_records():
        return jsonify({
            "bookkeepingRecords": ledger.list_bookkeeping_records(
                status=request.args.get("status"),
                export_status=request.args.get("exportStatus") or request.args.get("export_status"),
                reconciliation_status=request.args.get("reconciliationStatus") or request.args.get("reconciliation_status"),
                target_system=request.args.get("targetSystem") or request.args.get("target_system"),
                source_type=request.args.get("sourceType") or request.args.get("source_type"),
                limit=_limit_arg(),
            )
        })

    @app.get("/api/master-ledger")
    def master_ledger_api():
        service = LocalMasterLedgerService(ledger, config)
        target_system = request.args.get("targetSystem") or request.args.get("target_system")
        export_format = str(request.args.get("format") or "json").strip().lower()
        limit = _bounded_positive_int(request.args.get("limit"), default=500, maximum=1000)
        if export_format == "csv":
            artifact = service.csv_artifact(target_system=target_system, limit=limit)
            response = Response(artifact["content"], mimetype=artifact["contentType"])
            response.headers["Content-Disposition"] = f"attachment; filename={artifact['filename']}"
            response.headers["X-FAB-External-Submission"] = artifact["externalSubmission"]
            response.headers["X-FAB-Master-Ledger-Checksum"] = artifact["ledgerChecksum"]
            response.headers["X-FAB-Master-Ledger-Rows"] = str(artifact["rowCount"])
            return response
        if export_format != "json":
            return jsonify({
                "success": False,
                "status": "unsupported_format",
                "supportedFormats": ["json", "csv"],
            }), 400
        projection = service.project(target_system=target_system, limit=limit)
        if _bool_value(request.args.get("audit"), default=False):
            service.record_projection_audit(projection, actor=request.args.get("actor") or "local_api")
        return jsonify(projection)

    @app.get("/api/bookkeeping-records/<int:record_id>")
    def bookkeeping_record_detail(record_id: int):
        record = ledger.get_bookkeeping_record(record_id)
        if not record:
            return jsonify({"error": "Bookkeeping record not found"}), 404
        record["routing_attempts"] = ledger.list_routing_attempts(
            bookkeeping_record_id=record_id,
            limit=_limit_arg(),
        )
        record["export_attempts"] = ledger.list_export_attempts(
            bookkeeping_record_id=record_id,
            limit=_limit_arg(),
        )
        return jsonify(record)

    @app.get("/bookkeeping-records/<int:record_id>")
    def bookkeeping_record_detail_page(record_id: int):
        record = ledger.get_bookkeeping_record(record_id)
        if not record:
            return render_template_string(
                "<h1>Bookkeeping record not found</h1><p>No local FAB bookkeeping record exists for this id.</p>"
            ), 404
        routing_attempts = ledger.list_routing_attempts(
            bookkeeping_record_id=record_id,
            limit=_limit_arg(),
        )
        export_attempts = ledger.list_export_attempts(
            bookkeeping_record_id=record_id,
            limit=_limit_arg(),
        )
        bank_transaction = None
        if record.get("bank_transaction_id"):
            bank_transaction = ledger.get_bank_transaction(int(record["bank_transaction_id"]))
        reconciliation_matches = _reconciliation_matches_for_record(
            ledger,
            record,
            bank_transaction=bank_transaction,
            limit=_limit_arg(),
        )
        audit_events = [
            event
            for event in ledger.list_audit_events(limit=500)
            if event.get("entity_type") == "bookkeeping_record"
            and str(event.get("entity_id") or "") == str(record_id)
        ]
        return render_template_string(
            BOOKKEEPING_RECORD_DETAIL_TEMPLATE,
            audit_events=audit_events,
            bank_transaction=bank_transaction,
            compact_json=_compact_json,
            export_attempts=export_attempts,
            format_confidence=_format_confidence,
            format_money=_format_money,
            pretty_json=_pretty_json,
            record=record,
            reconciliation_matches=reconciliation_matches,
            routing_attempts=routing_attempts,
        )

    @app.post("/api/bookkeeping-records/<int:record_id>/resolve")
    def resolve_bookkeeping_record(record_id: int):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status") or payload.get("resolutionStatus") or "resolved")
        if status not in BOOKKEEPING_RECORD_RESOLUTION_STATUSES:
            return jsonify({"error": "Invalid bookkeeping record resolution status"}), 400
        result = LocalBookkeepingRecordService(ledger, config).resolve_record(
            record_id,
            status=status,
            resolution=payload.get("resolution"),
            corrections=payload.get("corrections") or _bookkeeping_record_corrections_from_mapping(payload),
            actor=str(payload.get("actor") or "fab_local_api"),
        )
        status_code = 404 if result.get("status") == "not_found" else 200
        return jsonify(result), status_code

    @app.post("/bookkeeping-records/<int:record_id>/resolve")
    def resolve_bookkeeping_record_form(record_id: int):
        status = str(request.form.get("status") or "resolved")
        if status not in BOOKKEEPING_RECORD_RESOLUTION_STATUSES:
            status = "resolved"
        LocalBookkeepingRecordService(ledger, config).resolve_record(
            record_id,
            status=status,
            resolution=request.form.get("resolution") or None,
            corrections=_bookkeeping_record_corrections_from_mapping(request.form),
            actor="fab_dashboard",
        )
        return redirect(url_for("dashboard_page", _anchor="records"))

    @app.get("/api/bookkeeping-records/<int:record_id>/line-items")
    def bookkeeping_record_line_items(record_id: int):
        if not ledger.get_bookkeeping_record(record_id):
            return jsonify({"error": "Bookkeeping record not found"}), 404
        return jsonify({
            "lineItems": ledger.list_bookkeeping_record_line_items(
                bookkeeping_record_id=record_id,
                limit=_limit_arg(),
            )
        })

    @app.post("/api/bookkeeping-records/refresh")
    def refresh_bookkeeping_records():
        payload = request.get_json(silent=True) or {}
        limit = _bounded_positive_int(payload.get("limit"), default=100, maximum=500)
        source_type = payload.get("sourceType") or payload.get("source_type") or "document"
        try:
            result = _refresh_bookkeeping_records(ledger, config, source_type=source_type, limit=limit)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/bookkeeping-records/refresh")
    def refresh_bookkeeping_records_form():
        source_type = request.form.get("sourceType") or request.form.get("source_type") or "document"
        try:
            session["fab_last_record_refresh_summary"] = _refresh_bookkeeping_records(
                ledger,
                config,
                source_type=source_type,
                limit=100,
            )
        except ValueError as exc:
            session["fab_last_record_refresh_summary"] = {
                "success": False,
                "status": "failed",
                "error": str(exc),
                "externalSubmission": "not_executed",
            }
        return redirect(url_for("dashboard_page", _anchor="records"))

    @app.post("/api/documents/<int:document_id>/process")
    def process_document(document_id: int):
        result = LocalDocumentProcessor(ledger, config).process_document(document_id)
        if result.get("status") == "not_found":
            return jsonify(result), 404
        return jsonify(result)

    @app.post("/api/documents/<int:document_id>/retry-processing")
    def retry_document_processing(document_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalDocumentProcessor(ledger, config).retry_document(
            document_id,
            actor=str(payload.get("actor") or "fab_local_api"),
        )
        if result.get("status") == "not_found":
            return jsonify(result), 404
        return jsonify(result)

    @app.post("/documents/<int:document_id>/process")
    def process_document_form(document_id: int):
        session["fab_last_processing_summary"] = {
            "requested": 1,
            "processed": 0,
            "needsReview": 0,
            "failed": 0,
            "skipped": 0,
            "documents": [LocalDocumentProcessor(ledger, config).process_document(document_id)],
        }
        status = session["fab_last_processing_summary"]["documents"][0].get("status")
        if status == "processed":
            session["fab_last_processing_summary"]["processed"] = 1
        elif status == "failed":
            session["fab_last_processing_summary"]["failed"] = 1
        elif session["fab_last_processing_summary"]["documents"][0].get("skipped"):
            session["fab_last_processing_summary"]["skipped"] = 1
        else:
            session["fab_last_processing_summary"]["needsReview"] = 1
        return redirect(url_for("dashboard_page", _anchor="ledger"))

    @app.post("/api/documents/process-imported")
    def process_imported_documents():
        payload = request.get_json(silent=True) or {}
        limit = _bounded_positive_int(payload.get("limit"), default=25, maximum=100)
        return jsonify(LocalDocumentProcessor(ledger, config).process_imported(limit=limit))

    @app.post("/documents/process-imported")
    def process_imported_form():
        session["fab_last_processing_summary"] = LocalDocumentProcessor(ledger, config).process_imported(limit=25)
        return redirect(url_for("dashboard_page", _anchor="intake"))

    @app.post("/api/documents/retry-failed")
    def retry_failed_processing():
        payload = request.get_json(silent=True) or {}
        limit = _bounded_positive_int(payload.get("limit"), default=25, maximum=100)
        actor = str(payload.get("actor") or "fab_local_api")
        return jsonify(LocalDocumentProcessor(ledger, config).retry_failed(limit=limit, actor=actor))

    @app.post("/documents/retry-failed")
    def retry_failed_processing_form():
        session["fab_last_processing_summary"] = LocalDocumentProcessor(ledger, config).retry_failed(
            limit=25,
            actor="fab_dashboard",
        )
        return redirect(url_for("dashboard_page", _anchor="intake"))

    @app.post("/documents/<int:document_id>/retry-processing")
    def retry_document_processing_form(document_id: int):
        result = LocalDocumentProcessor(ledger, config).retry_document(
            document_id,
            actor="fab_dashboard",
        )
        session["fab_last_processing_summary"] = _single_processing_summary(result, retried=bool(result.get("retry")))
        return redirect(url_for("dashboard_page", _anchor="ledger"))

    @app.get("/api/routing")
    def routing_attempts():
        document_id = request.args.get("documentId")
        bookkeeping_record_id = request.args.get("bookkeepingRecordId") or request.args.get("bookkeeping_record_id")
        try:
            parsed_document_id = int(document_id) if document_id else None
            parsed_bookkeeping_record_id = int(bookkeeping_record_id) if bookkeeping_record_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid routing source id"}), 400
        return jsonify({
            "routingAttempts": ledger.list_routing_attempts(
                status=request.args.get("status"),
                target=request.args.get("target"),
                document_id=parsed_document_id,
                bookkeeping_record_id=parsed_bookkeeping_record_id,
                limit=_limit_arg(),
            )
        })

    @app.post("/api/documents/<int:document_id>/route")
    def route_document(document_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalRoutingService(ledger, config).prepare_document_route(
            document_id,
            target_system=payload.get("targetSystem"),
            workflow_run_id=payload.get("workflowRunId"),
        )
        status_code = 404 if result.get("status") == "not_found" else 200
        return jsonify(result), status_code

    @app.post("/documents/<int:document_id>/route")
    def route_document_form(document_id: int):
        session["fab_last_routing_summary"] = {
            "requested": 1,
            "draftPrepared": 0,
            "alreadyPrepared": 0,
            "needsReview": 0,
            "blocked": 0,
            "documents": [LocalRoutingService(ledger, config).prepare_document_route(document_id)],
        }
        status = session["fab_last_routing_summary"]["documents"][0].get("status")
        if status == "draft_prepared":
            session["fab_last_routing_summary"]["draftPrepared"] = 1
        elif status == "already_prepared":
            session["fab_last_routing_summary"]["alreadyPrepared"] = 1
        elif status == "needs_review":
            session["fab_last_routing_summary"]["needsReview"] = 1
        else:
            session["fab_last_routing_summary"]["blocked"] = 1
        return redirect(url_for("dashboard_page", _anchor="routing"))

    @app.post("/api/bookkeeping-records/<int:record_id>/route")
    def route_bookkeeping_record(record_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalRoutingService(ledger, config).prepare_bookkeeping_record_route(
            record_id,
            target_system=payload.get("targetSystem"),
            workflow_run_id=payload.get("workflowRunId"),
        )
        status_code = 404 if result.get("status") == "not_found" else 200
        return jsonify(result), status_code

    @app.post("/bookkeeping-records/<int:record_id>/route")
    def route_bookkeeping_record_form(record_id: int):
        result = LocalRoutingService(ledger, config).prepare_bookkeeping_record_route(record_id)
        session["fab_last_routing_summary"] = _single_record_routing_summary(result)
        return redirect(url_for("dashboard_page", _anchor="routing"))

    @app.post("/api/routing/prepare-ready")
    def prepare_ready_routes():
        payload = request.get_json(silent=True) or {}
        limit = _bounded_positive_int(payload.get("limit"), default=25, maximum=100)
        source_type = payload.get("sourceType") or payload.get("source_type") or "all"
        try:
            result = _prepare_ready_routes(ledger, config, source_type=source_type, limit=limit)
        except ValueError as exc:
            return jsonify({"success": False, "status": "invalid_source_type", "error": str(exc)}), 400
        return jsonify(result)

    @app.post("/routing/prepare-ready")
    def prepare_ready_routes_form():
        source_type = request.form.get("sourceType") or request.form.get("source_type") or "all"
        try:
            session["fab_last_routing_summary"] = _prepare_ready_routes(
                ledger,
                config,
                source_type=source_type,
                limit=25,
            )
        except ValueError as exc:
            session["fab_last_routing_summary"] = {
                "success": False,
                "status": "invalid_source_type",
                "error": str(exc),
                "externalSubmission": "not_executed",
            }
        return redirect(url_for("dashboard_page", _anchor="routing"))

    @app.get("/api/export-attempts")
    def export_attempts_api():
        document_id = request.args.get("documentId")
        bookkeeping_record_id = request.args.get("bookkeepingRecordId") or request.args.get("bookkeeping_record_id")
        try:
            parsed_document_id = int(document_id) if document_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid documentId"}), 400
        try:
            parsed_bookkeeping_record_id = int(bookkeeping_record_id) if bookkeeping_record_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid bookkeepingRecordId"}), 400
        return jsonify({
            "exportAttempts": ledger.list_export_attempts(
                status=request.args.get("status"),
                external_submission=request.args.get("externalSubmission") or request.args.get("external_submission"),
                target_system=request.args.get("targetSystem") or request.args.get("target_system"),
                document_id=parsed_document_id,
                bookkeeping_record_id=parsed_bookkeeping_record_id,
                limit=_limit_arg(),
            ),
            "approvalPhrase": EXPORT_APPROVAL_PHRASE,
            "rejectionPhrase": EXPORT_REJECTION_PHRASE,
            "resultConfirmationPhrase": EXPORT_RESULT_CONFIRMATION_PHRASE,
        })

    @app.get("/api/export-attempts/<int:export_attempt_id>")
    def export_attempt_detail(export_attempt_id: int):
        attempt = ledger.get_export_attempt(export_attempt_id)
        if not attempt:
            return jsonify({"error": "Export attempt not found"}), 404
        return jsonify(attempt)

    @app.get("/api/export-attempts/<int:export_attempt_id>/artifact")
    def export_attempt_artifact(export_attempt_id: int):
        result = LocalExportAttemptService(ledger, config).artifact_for_attempt(
            export_attempt_id,
            export_format=request.args.get("format") or "json",
            actor=request.args.get("actor") or "api",
        )
        if not result.get("success"):
            status_code = 404 if result.get("status") == "not_found" else 400
            return jsonify(result), status_code
        artifact = result["artifact"]
        if artifact.get("format") == "json":
            return jsonify({
                "status": result["status"],
                "artifact": {
                    key: value
                    for key, value in artifact.items()
                    if key != "content"
                },
                "content": json.loads(artifact["content"]),
            })
        return Response(
            artifact["content"],
            mimetype=artifact["contentType"],
            headers={
                "Content-Disposition": f"attachment; filename={artifact['filename']}",
                "X-FAB-External-Submission": artifact["externalSubmission"],
                "X-FAB-Master-Ledger-Checksum": artifact.get("checksum") or "",
            },
        )

    @app.post("/api/routing/<int:routing_attempt_id>/export-attempt")
    def prepare_export_attempt_from_route(routing_attempt_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalExportAttemptService(ledger, config).prepare_from_routing_attempt(
            routing_attempt_id,
            actor=payload.get("actor") or "api",
        )
        status_code = 404 if result.get("status") == "not_found" else 200
        return jsonify(result), status_code

    @app.post("/api/export-attempts/prepare-ready")
    def prepare_ready_export_attempts():
        payload = request.get_json(silent=True) or {}
        limit = _bounded_positive_int(payload.get("limit"), default=25, maximum=100)
        return jsonify(LocalExportAttemptService(ledger, config).prepare_ready_exports(limit=limit))

    @app.post("/exports/prepare-ready")
    def prepare_ready_export_attempts_form():
        session["fab_last_export_summary"] = LocalExportAttemptService(ledger, config).prepare_ready_exports(limit=25)
        return redirect(url_for("dashboard_page", _anchor="exports"))

    @app.post("/api/export-attempts/<int:export_attempt_id>/approve")
    def approve_export_attempt(export_attempt_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalExportAttemptService(ledger, config).approve_attempt(
            export_attempt_id,
            actor=payload.get("actor") or "api",
            confirmation=payload.get("confirmation"),
            resolution=payload.get("resolution"),
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.post("/export-attempts/<int:export_attempt_id>/approve")
    def approve_export_attempt_form(export_attempt_id: int):
        session["fab_last_export_summary"] = LocalExportAttemptService(ledger, config).approve_attempt(
            export_attempt_id,
            actor="dashboard",
            confirmation=request.form.get("confirmation"),
            resolution="Approved from local FAB dashboard.",
        )
        return redirect(url_for("dashboard_page", _anchor="exports"))

    @app.post("/api/export-attempts/<int:export_attempt_id>/reject")
    def reject_export_attempt(export_attempt_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalExportAttemptService(ledger, config).reject_attempt(
            export_attempt_id,
            actor=payload.get("actor") or "api",
            confirmation=payload.get("confirmation"),
            resolution=payload.get("resolution"),
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.post("/export-attempts/<int:export_attempt_id>/reject")
    def reject_export_attempt_form(export_attempt_id: int):
        session["fab_last_export_summary"] = LocalExportAttemptService(ledger, config).reject_attempt(
            export_attempt_id,
            actor="dashboard",
            confirmation=request.form.get("confirmation"),
            resolution=request.form.get("resolution") or "Rejected from local FAB dashboard.",
        )
        return redirect(url_for("dashboard_page", _anchor="exports"))

    @app.post("/api/export-attempts/<int:export_attempt_id>/regenerate")
    def regenerate_export_attempt(export_attempt_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalExportAttemptService(ledger, config).regenerate_attempt(
            export_attempt_id,
            actor=payload.get("actor") or "api",
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.post("/export-attempts/<int:export_attempt_id>/regenerate")
    def regenerate_export_attempt_form(export_attempt_id: int):
        session["fab_last_export_summary"] = LocalExportAttemptService(ledger, config).regenerate_attempt(
            export_attempt_id,
            actor="dashboard",
        )
        return redirect(url_for("dashboard_page", _anchor="exports"))

    @app.post("/api/export-attempts/<int:export_attempt_id>/execute")
    def execute_export_attempt(export_attempt_id: int):
        result = LocalExportAttemptService(ledger, config).execute_attempt(
            export_attempt_id,
            actor="api",
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.post("/export-attempts/<int:export_attempt_id>/execute")
    def execute_export_attempt_form(export_attempt_id: int):
        session["fab_last_export_summary"] = LocalExportAttemptService(ledger, config).execute_attempt(
            export_attempt_id,
            actor="dashboard",
        )
        return redirect(url_for("dashboard_page", _anchor="exports"))

    @app.post("/api/export-attempts/<int:export_attempt_id>/result")
    def record_export_attempt_result(export_attempt_id: int):
        payload = request.get_json(silent=True) or {}
        result = LocalExportAttemptService(ledger, config).record_result(
            export_attempt_id,
            status=payload.get("status"),
            external_id=payload.get("externalId") or payload.get("external_id"),
            result=payload.get("result"),
            actor=payload.get("actor") or "api",
            confirmation=payload.get("confirmation"),
        )
        status_code = 200 if result.get("success") else 400
        if result.get("status") == "not_found":
            status_code = 404
        return jsonify(result), status_code

    @app.post("/export-attempts/<int:export_attempt_id>/result")
    def record_export_attempt_result_form(export_attempt_id: int):
        session["fab_last_export_summary"] = LocalExportAttemptService(ledger, config).record_result(
            export_attempt_id,
            status=request.form.get("status") or "executed",
            external_id=request.form.get("externalId") or None,
            result={"source": "dashboard"},
            actor="dashboard",
            confirmation=request.form.get("confirmation"),
        )
        return redirect(url_for("dashboard_page", _anchor="exports"))

    @app.get("/api/bank-transactions")
    def bank_transactions():
        return jsonify({
            "bankTransactions": ledger.list_bank_transactions(
                account_identifier=request.args.get("accountIdentifier") or request.args.get("account_identifier"),
                status=request.args.get("status"),
                reconciliation_status=request.args.get("reconciliationStatus") or request.args.get("reconciliation_status"),
                limit=_limit_arg(),
            ),
            "bankStatementImports": ledger.list_bank_statement_imports(
                account_identifier=request.args.get("accountIdentifier") or request.args.get("account_identifier"),
                limit=25,
            ),
        })

    @app.post("/api/bank-transactions/import")
    def import_bank_transactions():
        payload = request.get_json(silent=True) or {}
        service = LocalBankTransactionImportService(ledger, config)
        account_identifier = payload.get("accountIdentifier") or payload.get("account_identifier") or "default"
        source = payload.get("source") or "api_import"
        filename = payload.get("filename")
        format_name = payload.get("format") or "json"
        try:
            if payload.get("statementText") or payload.get("statement_text"):
                result = service.import_statement_text(
                    payload.get("statementText") or payload.get("statement_text") or "",
                    format=format_name,
                    account_identifier=account_identifier,
                    source=source,
                    filename=filename,
                )
            else:
                transactions = payload.get("bankTransactions") or payload.get("transactions") or []
                if not isinstance(transactions, list):
                    return jsonify({"error": "bankTransactions must be a list"}), 400
                result = service.import_transactions(
                    transactions,
                    account_identifier=account_identifier,
                    source=source,
                    filename=filename,
                    format=format_name,
                )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/bank-transactions/import")
    def import_bank_transactions_form():
        service = LocalBankTransactionImportService(ledger, config)
        try:
            session["fab_last_bank_import_summary"] = service.import_statement_text(
                request.form.get("statementText") or "",
                format=request.form.get("format") or "json",
                account_identifier=request.form.get("accountIdentifier") or "default",
                source=request.form.get("source") or "manual_upload",
                filename=request.form.get("filename") or None,
            )
        except Exception as exc:
            session["fab_last_bank_import_summary"] = {
                "success": False,
                "status": "failed",
                "error": f"Could not import bank transactions: {exc}",
                "rowsSeen": 0,
                "rowsImported": 0,
                "duplicates": 0,
                "skipped": 0,
                "externalSubmission": "not_executed",
            }
        return redirect(url_for("dashboard_page", _anchor="bank"))

    @app.get("/api/reconciliation")
    def reconciliation_matches():
        document_id = request.args.get("documentId")
        try:
            parsed_document_id = int(document_id) if document_id else None
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid documentId"}), 400
        return jsonify({
            "reconciliationMatches": ledger.list_reconciliation_matches(
                status=request.args.get("status"),
                document_id=parsed_document_id,
                bank_transaction_id=request.args.get("bankTransactionId"),
                limit=_limit_arg(),
            )
        })

    @app.post("/api/reconciliation/run")
    def run_reconciliation():
        payload = request.get_json(silent=True) or {}
        if "bankTransactions" in payload:
            bank_transactions = payload.get("bankTransactions") or []
        else:
            bank_transactions = LocalBankTransactionImportService(ledger, config).transactions_for_reconciliation(
                limit=_bounded_positive_int(payload.get("limit"), default=100, maximum=500),
            )
        if not isinstance(bank_transactions, list):
            return jsonify({"error": "bankTransactions must be a list"}), 400
        try:
            result = LocalReconciliationService(ledger, config).run(
                bank_transactions,
                document_ids=payload.get("documentIds"),
                limit=_bounded_positive_int(payload.get("limit"), default=100, maximum=500),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.post("/reconciliation/run")
    def run_reconciliation_form():
        raw_transactions = request.form.get("bankTransactionsJson") or ""
        try:
            if raw_transactions.strip():
                bank_transactions = json.loads(raw_transactions)
                if not isinstance(bank_transactions, list):
                    raise ValueError("Bank transactions JSON must be a list.")
            else:
                bank_transactions = LocalBankTransactionImportService(ledger, config).transactions_for_reconciliation(limit=100)
            session["fab_last_reconciliation_summary"] = LocalReconciliationService(ledger, config).run(
                bank_transactions,
                limit=100,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            session["fab_last_reconciliation_summary"] = {
                "error": f"Could not run reconciliation: {exc}",
                "requestedTransactions": 0,
                "candidateDocuments": 0,
                "matchedCandidates": 0,
                "missingReceipts": 0,
                "unmatchedDocuments": 0,
                "matchesRecorded": 0,
                "reviewItemsCreated": 0,
                "results": [],
            }
        return redirect(url_for("dashboard_page", _anchor="reconciliation"))

    @app.post("/api/reconciliation/<int:reconciliation_match_id>/resolve")
    def resolve_reconciliation(reconciliation_match_id: int):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status") or "resolved")
        if status not in RECONCILIATION_RESOLUTION_STATUSES:
            return jsonify({"error": "Invalid reconciliation resolution status"}), 400
        result = LocalReconciliationService(ledger, config).resolve_match(
            reconciliation_match_id,
            status=status,
            resolution=payload.get("resolution"),
        )
        status_code = 404 if result.get("status") == "not_found" else 200
        if result.get("status") == "invalid_status":
            status_code = 400
        return jsonify(result), status_code

    @app.post("/reconciliation/<int:reconciliation_match_id>/resolve")
    def resolve_reconciliation_form(reconciliation_match_id: int):
        status = str(request.form.get("status") or "resolved")
        if status not in RECONCILIATION_RESOLUTION_STATUSES:
            status = "resolved"
        LocalReconciliationService(ledger, config).resolve_match(
            reconciliation_match_id,
            status=status,
            resolution=f"Resolved from FAB dashboard as {status}.",
        )
        return redirect(url_for("dashboard_page", _anchor="reconciliation"))

    @app.get("/api/backups")
    def list_backups():
        return jsonify(LocalBackupService(ledger, config).list_backups(limit=_limit_arg()))

    @app.post("/api/backups")
    def create_backup():
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(LocalBackupService(ledger, config).create_backup(note=payload.get("note")))
        except Exception as exc:
            return jsonify({"success": False, "status": "failed", "error": str(exc)}), 500

    @app.post("/backups/create")
    def create_backup_form():
        try:
            session["fab_last_backup_summary"] = LocalBackupService(ledger, config).create_backup(
                note="Created from FAB dashboard.",
            )
        except Exception as exc:
            session["fab_last_backup_summary"] = {
                "success": False,
                "status": "failed",
                "error": str(exc),
            }
        return redirect(url_for("dashboard_page", _anchor="backups"))

    @app.get("/api/backups/inspect")
    def inspect_backup():
        backup_path = request.args.get("backupPath") or request.args.get("backupFilename")
        try:
            return jsonify(LocalBackupService(ledger, config).inspect_backup(str(backup_path or "")))
        except Exception as exc:
            return jsonify({"success": False, "status": "invalid", "error": str(exc)}), 400

    @app.post("/api/backups/restore")
    def restore_backup():
        payload = request.get_json(silent=True) or {}
        try:
            result = LocalBackupService(ledger, config).restore_backup(
                str(payload.get("backupPath") or payload.get("backupFilename") or ""),
                str(payload.get("confirmation") or ""),
            )
        except Exception as exc:
            return jsonify({"success": False, "status": "failed", "error": str(exc)}), 400
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    @app.post("/backups/restore")
    def restore_backup_form():
        try:
            session["fab_last_backup_summary"] = LocalBackupService(ledger, config).restore_backup(
                str(request.form.get("backupPath") or ""),
                str(request.form.get("confirmation") or ""),
            )
        except Exception as exc:
            session["fab_last_backup_summary"] = {
                "success": False,
                "status": "failed",
                "error": str(exc),
            }
        return redirect(url_for("dashboard_page", _anchor="backups"))

    @app.post("/api/intake/rescan")
    def rescan_intake():
        paths = app.config["FAB_LOCAL_INTAKE_PATHS"]
        if not paths:
            return jsonify({
                "error": "No intake folders configured",
                "intakePaths": [],
            }), 400
        summary = LocalFolderIntake(
            ledger,
            allowed_extensions=app.config["FAB_LOCAL_INTAKE_EXTENSIONS"],
        ).rescan(paths)
        return jsonify(summary)

    @app.post("/intake/rescan")
    def rescan_intake_form():
        paths = app.config["FAB_LOCAL_INTAKE_PATHS"]
        if paths:
            session["fab_last_intake_summary"] = LocalFolderIntake(
                ledger,
                allowed_extensions=app.config["FAB_LOCAL_INTAKE_EXTENSIONS"],
            ).rescan(paths)
        else:
            session["fab_last_intake_summary"] = {
                "folders": [],
                "allowedExtensions": app.config["FAB_LOCAL_INTAKE_EXTENSIONS"],
                "scanned": 0,
                "registered": 0,
                "duplicates": 0,
                "alreadyRegistered": 0,
                "skipped": [{"reason": "no_intake_folders_configured"}],
                "documents": [],
            }
        return redirect(url_for("dashboard_page", _anchor="intake"))

    @app.get("/api/review")
    def review_queue():
        return jsonify({
            "reviewItems": ledger.list_review_items(
                status=request.args.get("status"),
                limit=_limit_arg(),
            )
        })

    @app.post("/api/review/<int:review_item_id>/resolve")
    def resolve_review(review_item_id: int):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status") or "resolved")
        if status not in REVIEW_RESOLUTION_STATUSES:
            return jsonify({"error": "Invalid review resolution status"}), 400
        resolution = payload.get("resolution")
        result = LocalReviewService(ledger).resolve_review_item(
            review_item_id,
            status=status,
            resolution=str(resolution) if resolution is not None else None,
            corrections=payload.get("corrections") or _corrections_from_mapping(payload),
            learn_rule=bool(payload.get("learnRule", True)),
        )
        status_code = 404 if result.get("status") == "not_found" else 200
        return jsonify(result), status_code

    @app.post("/review/<int:review_item_id>/resolve")
    def resolve_review_form(review_item_id: int):
        status = str(request.form.get("status") or "resolved")
        if status not in REVIEW_RESOLUTION_STATUSES:
            status = "resolved"
        resolution = request.form.get("resolution") or None
        LocalReviewService(ledger).resolve_review_item(
            review_item_id,
            status=status,
            resolution=resolution,
            corrections=_corrections_from_mapping(request.form),
            learn_rule=True,
        )
        return redirect(url_for("dashboard_page", _anchor="review"))

    @app.get("/api/rules")
    def rules():
        return jsonify({
            "vendorCategoryRules": ledger.list_vendor_category_rules(
                vendor_name=request.args.get("vendorName"),
                status=request.args.get("status"),
                limit=_limit_arg(),
            )
        })

    @app.get("/api/vendors")
    def vendors():
        return jsonify({
            "vendors": ledger.list_vendor_summaries(limit=_limit_arg()),
            "externalSubmission": "not_executed",
        })

    @app.get("/api/categories")
    def categories():
        return jsonify({
            "categories": ledger.list_category_summaries(limit=_limit_arg()),
            "externalSubmission": "not_executed",
        })

    @app.post("/api/rules")
    def upsert_rule():
        payload = request.get_json(silent=True) or {}
        payload.setdefault("status", "suggested")
        try:
            rule_id = ledger.upsert_vendor_category_rule(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        ledger.record_audit_event({
            "action": "local_api.vendor_category_rule.upsert",
            "entityType": "vendor_category_rule",
            "entityId": str(rule_id),
            "details": {
                "vendorName": payload.get("vendorName"),
                "category": payload.get("category"),
                "status": payload.get("status", "suggested"),
            },
        })
        return jsonify({"success": True, "ruleId": rule_id})

    @app.post("/api/rules/<int:rule_id>/resolve")
    def resolve_rule(rule_id: int):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get("status") or "").strip()
        if status not in RULE_RESOLUTION_STATUSES:
            return jsonify({"error": "Unsupported rule status"}), 400
        try:
            rule = ledger.update_vendor_category_rule_status(
                rule_id,
                status,
                resolution=payload.get("resolution"),
                actor=payload.get("actor") or "local_api",
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if not rule:
            return jsonify({"error": "Vendor category rule not found"}), 404
        ledger.record_audit_event({
            "action": "local_api.vendor_category_rule.status_changed",
            "entityType": "vendor_category_rule",
            "entityId": str(rule_id),
            "details": {
                "status": status,
                "resolution": payload.get("resolution"),
                "actor": payload.get("actor") or "local_api",
            },
        })
        return jsonify({"success": True, "rule": rule})

    @app.post("/rules/<int:rule_id>/resolve")
    def resolve_rule_form(rule_id: int):
        status = str(request.form.get("status") or "").strip()
        if status not in RULE_RESOLUTION_STATUSES:
            status = "suggested"
        rule = ledger.update_vendor_category_rule_status(
            rule_id,
            status,
            resolution=request.form.get("resolution") or None,
            actor="local_dashboard",
        )
        if rule:
            ledger.record_audit_event({
                "action": "local_dashboard.vendor_category_rule.status_changed",
                "entityType": "vendor_category_rule",
                "entityId": str(rule_id),
                "details": {
                    "status": status,
                    "resolution": request.form.get("resolution") or None,
                    "actor": "local_dashboard",
                },
            })
        return redirect(url_for("dashboard_page", _anchor="rules"))

    @app.get("/api/corrections")
    def corrections():
        document_id = request.args.get("documentId")
        return jsonify({
            "reviewCorrections": ledger.list_review_corrections(
                document_id=int(document_id) if document_id else None,
                limit=_limit_arg(),
            )
        })

    @app.get("/api/audit")
    def audit_events():
        return jsonify({"auditEvents": ledger.list_audit_events(limit=_limit_arg())})

    def _limit_arg() -> int:
        try:
            return int(request.args.get("limit", 100))
        except (TypeError, ValueError):
            return 100

    return app


def _format_money(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"EUR {float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _format_confidence(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return str(value)


def _reconciliation_matches_for_record(
    ledger: LocalOperationsLedger,
    record: Dict[str, Any],
    bank_transaction: Optional[Dict[str, Any]] = None,
    limit: int = 100,
) -> list:
    matches: list = []
    seen_ids = set()

    def add_rows(rows: list) -> None:
        for row in rows:
            row_id = row.get("id")
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
            matches.append(row)

    if record.get("document_id"):
        add_rows(ledger.list_reconciliation_matches(
            document_id=int(record["document_id"]),
            limit=limit,
        ))

    bank_transaction_id = None
    if bank_transaction:
        bank_transaction_id = bank_transaction.get("transaction_id")
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    latest = metadata.get("latestReconciliation") if isinstance(metadata.get("latestReconciliation"), dict) else {}
    if not bank_transaction_id:
        bank_transaction_id = latest.get("bankTransactionId")
    if bank_transaction_id:
        add_rows(ledger.list_reconciliation_matches(
            bank_transaction_id=str(bank_transaction_id),
            limit=limit,
        ))

    return matches[: _bounded_positive_int(limit, default=100, maximum=500)]


def _document_source_preview(document: Dict[str, Any], character_limit: int = 5000) -> Dict[str, Any]:
    path = document.get("storage_path")
    if not path:
        return {"status": "No source file path is recorded.", "path": None, "text": None}
    normalized_path = os.path.abspath(os.path.expandvars(os.path.expanduser(str(path))))
    if not os.path.exists(normalized_path):
        return {"status": "Source file is missing from disk.", "path": normalized_path, "text": None}
    extension = os.path.splitext(normalized_path)[1].lower()
    mime_type = str(document.get("mime_type") or "").lower()
    file_size = os.path.getsize(normalized_path)
    if extension in {".txt", ".csv", ".json", ".xml"} or mime_type.startswith("text/"):
        try:
            with open(normalized_path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read(character_limit + 1)
        except OSError as exc:
            return {"status": f"Could not read source preview: {exc}", "path": normalized_path, "text": None}
        truncated = len(text) > character_limit
        if truncated:
            text = text[:character_limit] + "\n... truncated ..."
        return {
            "status": f"Text preview from local source file ({file_size} bytes).",
            "path": normalized_path,
            "text": text,
        }
    return {
        "status": f"Binary source file recorded ({file_size} bytes). Open from local path if visual inspection is needed.",
        "path": normalized_path,
        "text": None,
    }


def _compact_json(value: Any) -> str:
    if value is None:
        return "-"
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _pretty_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, indent=2)


def _readiness_service(
    config: Dict[str, Any],
    ledger_path: str,
    host: str,
    token_configured: bool,
    intake_paths: list,
    intake_extensions: list,
) -> LocalReadinessService:
    return LocalReadinessService(
        config,
        ledger_path=ledger_path,
        api_host=host,
        api_token_configured=token_configured,
        intake_paths=intake_paths,
        intake_extensions=intake_extensions,
    )


def _autonomy_service(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    readiness: LocalReadinessService,
    intake_paths: list,
    intake_extensions: list,
) -> LocalAutonomousService:
    return LocalAutonomousService(
        ledger,
        config,
        readiness=readiness,
        intake_paths=intake_paths,
        intake_extensions=intake_extensions,
    )


def _compact_wave_plan_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
    workflow_plan = plan.get("workflow_plan") or {}
    operations = plan.get("operations") or []
    return {
        "status": plan.get("status"),
        "canRunAutonomously": plan.get("can_run_autonomously"),
        "workflowId": workflow_plan.get("workflow_id"),
        "operationCount": plan.get("operationCount"),
        "waveReportSnapshots": (plan.get("waveReportSnapshots") or {}).get("snapshotCount"),
        "waveOperationSnapshots": (plan.get("waveOperationSnapshots") or {}).get("snapshotCount"),
        "waveReportControls": {
            "status": (plan.get("waveReportControls") or {}).get("status"),
            "requiredReportCount": (plan.get("waveReportControls") or {}).get("requiredReportCount"),
            "coveredReportCount": (plan.get("waveReportControls") or {}).get("coveredReportCount"),
            "resultGapCount": (plan.get("waveReportControls") or {}).get("resultGapCount"),
            "blockingCount": (plan.get("waveReportControls") or {}).get("blockingCount"),
        },
        "externalSubmission": plan.get("externalSubmission"),
        "guardrail": plan.get("guardrail"),
        "missingSignals": workflow_plan.get("missing_signals", []),
        "reviewGates": workflow_plan.get("review_gates", []),
        "actions": [
            {
                "operationId": operation.get("operation_id"),
                "actionId": operation.get("action_id"),
                "surface": operation.get("surface"),
                "safety": operation.get("safety"),
                "planStatus": (operation.get("plan") or {}).get("status"),
            }
            for operation in operations[:25]
        ],
    }


def _compact_mijngeldzaken_plan_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
    workflow_plan = plan.get("workflowPlan") or {}
    controls = plan.get("masterLedgerControls") or {}
    operations = plan.get("operations") or []
    return {
        "status": plan.get("status"),
        "workflowId": workflow_plan.get("workflowId"),
        "operationCount": plan.get("operationCount"),
        "blockingOperations": len(plan.get("blockingOperations") or []),
        "masterLedgerControls": {
            "status": controls.get("status"),
            "rowCount": controls.get("rowCount"),
            "blockingCount": controls.get("blockingCount"),
            "readyForDraft": controls.get("readyForDraft"),
            "readyForApproval": controls.get("readyForApproval"),
            "readyForExternalExecution": controls.get("readyForExternalExecution"),
            "staleDrafts": controls.get("staleDrafts"),
        },
        "externalSubmission": plan.get("externalSubmission"),
        "guardrail": plan.get("guardrail"),
        "actions": [
            {
                "operationId": operation.get("operation_id"),
                "actionId": operation.get("action_id"),
                "surface": operation.get("surface"),
                "safety": operation.get("safety"),
                "planStatus": (operation.get("plan") or {}).get("status"),
            }
            for operation in operations[:25]
        ],
    }


def _refresh_bookkeeping_records(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    source_type: str = "document",
    limit: int = 100,
) -> Dict[str, Any]:
    service = LocalBookkeepingRecordService(ledger, config)
    normalized_source = str(source_type or "document").strip().lower()
    if normalized_source in {"document", "documents"}:
        result = service.refresh_documents(limit=limit)
        result["sourceType"] = "document"
        result["externalSubmission"] = "not_executed"
        return result
    if normalized_source in {"bank_transaction", "bank_transactions", "bank", "transactions"}:
        result = service.refresh_bank_transactions(limit=limit)
        result["sourceType"] = "bank_transaction"
        result["externalSubmission"] = "not_executed"
        return result
    if normalized_source == "all":
        document_refresh = service.refresh_documents(limit=limit)
        bank_refresh = service.refresh_bank_transactions(limit=limit)
        return {
            "success": True,
            "status": "completed",
            "sourceType": "all",
            "externalSubmission": "not_executed",
            "documentRefresh": document_refresh,
            "bankTransactionRefresh": bank_refresh,
            "requested": int(document_refresh.get("requested", 0)) + int(bank_refresh.get("requested", 0)),
            "updated": int(document_refresh.get("updated", 0)) + int(bank_refresh.get("updated", 0)),
            "failed": int(document_refresh.get("failed", 0)) + int(bank_refresh.get("failed", 0)),
        }
    raise ValueError("sourceType must be one of: document, bank_transaction, all")


def _prepare_ready_routes(
    ledger: LocalOperationsLedger,
    config: Dict[str, Any],
    source_type: str = "all",
    limit: int = 25,
) -> Dict[str, Any]:
    service = LocalRoutingService(ledger, config)
    normalized_source = str(source_type or "all").strip().lower()
    if normalized_source in {"document", "documents"}:
        result = service.prepare_ready_documents(limit=limit)
        result["sourceType"] = "document"
        result["externalSubmission"] = "not_executed"
        return result
    if normalized_source in {"bookkeeping_record", "bookkeeping_records", "bank_transaction", "bank_transactions", "bank", "transactions"}:
        result = service.prepare_ready_bookkeeping_records(limit=limit)
        result["sourceType"] = "bank_transaction"
        result["externalSubmission"] = "not_executed"
        return result
    if normalized_source == "all":
        document_routing = service.prepare_ready_documents(limit=limit)
        bank_record_routing = service.prepare_ready_bookkeeping_records(limit=limit)
        return _combined_routing_summary(
            document_routing,
            bank_record_routing,
            source_type="all",
        )
    raise ValueError("sourceType must be one of: document, bank_transaction, all")


def _combined_routing_summary(
    document_routing: Dict[str, Any],
    bank_record_routing: Dict[str, Any],
    source_type: str = "all",
) -> Dict[str, Any]:
    return {
        "success": True,
        "status": "completed",
        "sourceType": source_type,
        "externalSubmission": "not_executed",
        "documentRouting": document_routing,
        "bankRecordRouting": bank_record_routing,
        "requested": int(document_routing.get("requested", 0)) + int(bank_record_routing.get("requested", 0)),
        "draftPrepared": int(document_routing.get("draftPrepared", 0)) + int(bank_record_routing.get("draftPrepared", 0)),
        "alreadyPrepared": int(document_routing.get("alreadyPrepared", 0)) + int(bank_record_routing.get("alreadyPrepared", 0)),
        "needsReview": int(document_routing.get("needsReview", 0)) + int(bank_record_routing.get("needsReview", 0)),
        "blocked": int(document_routing.get("blocked", 0)) + int(bank_record_routing.get("blocked", 0)),
    }


def _single_record_routing_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    status = result.get("status")
    summary = {
        "sourceType": "bank_transaction",
        "externalSubmission": "not_executed",
        "requested": 1,
        "draftPrepared": 0,
        "alreadyPrepared": 0,
        "needsReview": 0,
        "blocked": 0,
        "bookkeepingRecords": [result],
    }
    if status == "draft_prepared":
        summary["draftPrepared"] = 1
    elif status == "already_prepared":
        summary["alreadyPrepared"] = 1
    elif status == "needs_review":
        summary["needsReview"] = 1
    else:
        summary["blocked"] = 1
    return summary


def _single_processing_summary(result: Dict[str, Any], retried: bool = False) -> Dict[str, Any]:
    status = result.get("status")
    summary = {
        "requested": 1,
        "retried": 1 if retried else 0,
        "processed": 0,
        "needsReview": 0,
        "failed": 0,
        "skipped": 0,
        "documents": [result],
    }
    if result.get("skipped"):
        summary["skipped"] = 1
    elif status == "processed":
        summary["processed"] = 1
    elif status in {"failed", "not_found"}:
        summary["failed"] = 1
    else:
        summary["needsReview"] = 1
    return summary


def _bounded_positive_int(value: Any, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _bool_value(value: Any, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _corrections_from_mapping(values: Any) -> Dict[str, Any]:
    keys = (
        "vendorName",
        "category",
        "transactionDate",
        "totalAmount",
        "vatAmount",
        "targetSystem",
        "duplicateOfDocumentId",
    )
    corrections = {}
    for key in keys:
        value = values.get(key) if hasattr(values, "get") else None
        if value not in (None, ""):
            corrections[key] = value
    return corrections


def _bookkeeping_record_corrections_from_mapping(values: Any) -> Dict[str, Any]:
    keys = (
        "vendorName",
        "category",
        "recordDate",
        "transactionDate",
        "amount",
        "totalAmount",
        "vatAmount",
        "currency",
        "description",
        "targetSystem",
        "targetAccount",
        "recordType",
        "confidenceScore",
    )
    corrections = {}
    for key in keys:
        value = values.get(key) if hasattr(values, "get") else None
        if value not in (None, ""):
            corrections[key] = value
    return corrections


def _list_config(config: Dict[str, Any], *keys: str) -> list:
    value = _config_value(config, *keys)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = str(value).replace("\n", ",").replace(";", ",").split(",")
    return [str(item).strip() for item in raw_items if str(item).strip()]


def _config_value(config: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = config.get(key)
        if value not in (None, ""):
            return value
    for key in keys:
        if "_" not in key:
            continue
        section, option = key.split("_", 1)
        section_values = config.get(section)
        if isinstance(section_values, dict):
            value = section_values.get(option)
            if value not in (None, ""):
                return value
    return None


def run(config: Optional[Dict[str, Any]] = None):
    config = config or ConfigLoader(config_file="config/config.ini").get_all_config()
    app = create_app(config)
    host = str(config.get("fab_local_api_host") or config.get("operations_api_host") or "127.0.0.1")
    port = int(config.get("fab_local_api_port") or config.get("operations_api_port") or 5001)
    app.run(host=host, port=port)


if __name__ == "__main__":
    run()
