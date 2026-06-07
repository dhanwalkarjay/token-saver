'use client';

import { useState } from 'react';
import { ScrollText, Search, Filter, Download, CheckCircle, AlertTriangle, Info, Shield, User } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

type EventType = 'request' | 'cache' | 'routing' | 'auth' | 'admin' | 'billing';
type Severity = 'info' | 'success' | 'warning' | 'error';

interface AuditEvent {
  id: string;
  timestamp: string;
  eventType: EventType;
  severity: Severity;
  actor: string;
  team: string;
  action: string;
  detail: string;
  model?: string;
  tokens?: number;
  cost?: number;
  savings?: number;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

const AUDIT_EVENTS: AuditEvent[] = [
  { id: 'evt-001', timestamp: '2026-06-07 15:21:44', eventType: 'request',  severity: 'success', actor: 'api-key-goog-search',  team: 'Google Search AI',    action: 'LLM Request Completed',   detail: 'Request routed to gpt-3.5-turbo (down from GPT-4o)',  model: 'gpt-3.5-turbo',  tokens: 1842, cost: 0.0028, savings: 78 },
  { id: 'evt-002', timestamp: '2026-06-07 15:21:38', eventType: 'cache',    severity: 'success', actor: 'api-key-ms-copilot',   team: 'Microsoft Copilot',   action: 'L2 Cache Hit',             detail: 'Semantic similarity 0.97 — returned cached response', model: undefined, tokens: 3210, cost: 0, savings: 100 },
  { id: 'evt-003', timestamp: '2026-06-07 15:21:31', eventType: 'request',  severity: 'info',    actor: 'api-key-amz-alexa',   team: 'Amazon Alexa AI',     action: 'LLM Request Completed',   detail: 'Premium request: no cheaper alternative found',       model: 'GPT-4o',          tokens: 8941, cost: 0.0448, savings: 0 },
  { id: 'evt-004', timestamp: '2026-06-07 15:21:19', eventType: 'cache',    severity: 'success', actor: 'api-key-goog-dm',     team: 'Google DeepMind',     action: 'L1 Cache Hit',             detail: 'Exact match — returned in 0ms',                       model: undefined, tokens: 512,  cost: 0, savings: 100 },
  { id: 'evt-005', timestamp: '2026-06-07 15:20:58', eventType: 'routing',  severity: 'success', actor: 'routing-engine-v3',   team: 'System',              action: 'Routing Decision Made',   detail: 'Complexity 42 — assigned to Tier 1 (gpt-3.5-turbo)', model: 'gpt-3.5-turbo',  tokens: 1023, cost: 0.0015, savings: 81 },
  { id: 'evt-006', timestamp: '2026-06-07 15:20:44', eventType: 'request',  severity: 'success', actor: 'api-key-meta-ai',     team: 'Meta Content AI',     action: 'LLM Request Completed',   detail: 'Routed from Gemini Ultra to Gemini Flash',            model: 'Gemini Flash',    tokens: 4567, cost: 0.0018, savings: 76 },
  { id: 'evt-007', timestamp: '2026-06-07 15:20:33', eventType: 'admin',    severity: 'warning', actor: 'admin@tokensaver.io',  team: 'Admin',               action: 'Budget Alert Triggered',  detail: 'Meta Content AI at 82% of monthly budget ($15,000)',  model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-008', timestamp: '2026-06-07 15:20:21', eventType: 'auth',     severity: 'info',    actor: 'sarah.chen@meta.com', team: 'Meta Content AI',     action: 'API Key Rotated',          detail: 'Key ending in ...8f3a rotated by user request',       model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-009', timestamp: '2026-06-07 15:20:09', eventType: 'request',  severity: 'success', actor: 'api-key-goog-search',  team: 'Google Search AI',    action: 'LLM Request Completed',   detail: 'Context compressed by 34% before routing',           model: 'GPT-4o-mini',     tokens: 2341, cost: 0.0007, savings: 65 },
  { id: 'evt-010', timestamp: '2026-06-07 15:19:57', eventType: 'billing',  severity: 'info',    actor: 'billing-service',     team: 'System',              action: 'Invoice Generated',        detail: 'May 2026 invoice: $47,832 saved vs projected spend',  model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-011', timestamp: '2026-06-07 15:19:43', eventType: 'cache',    severity: 'warning', actor: 'cache-service',       team: 'System',              action: 'Cache Eviction',           detail: 'L1 cache 89% full — evicting 12,420 stale entries',   model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-012', timestamp: '2026-06-07 15:19:31', eventType: 'request',  severity: 'success', actor: 'api-key-amz-aws',    team: 'Amazon AWS AI',       action: 'LLM Request Completed',   detail: 'Batch request: 23 items processed at Tier 2',         model: 'Claude 3 Sonnet', tokens: 12340, cost: 0.0394, savings: 71 },
  { id: 'evt-013', timestamp: '2026-06-07 15:19:18', eventType: 'auth',     severity: 'error',   actor: 'unknown@external.io', team: 'Unknown',             action: 'Auth Failure',             detail: 'Invalid API key used — IP 203.0.113.42 blocked',      model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-014', timestamp: '2026-06-07 15:18:55', eventType: 'routing',  severity: 'info',    actor: 'routing-engine-v3',   team: 'System',              action: 'Model Unavailable',        detail: 'Claude 3 Opus rate limited — fallback to Sonnet',    model: 'Claude 3 Sonnet', tokens: 3456, cost: 0.0111, savings: 45 },
  { id: 'evt-015', timestamp: '2026-06-07 15:18:33', eventType: 'admin',    severity: 'info',    actor: 'admin@tokensaver.io',  team: 'Admin',               action: 'Config Updated',           detail: 'Semantic similarity threshold changed: 0.90 → 0.88',  model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-016', timestamp: '2026-06-07 15:18:12', eventType: 'request',  severity: 'success', actor: 'api-key-ms-copilot',   team: 'Microsoft Copilot',   action: 'LLM Request Completed',   detail: 'High-confidence routing: complexity 28 → Tier 1',    model: 'gpt-3.5-turbo',  tokens: 987, cost: 0.0015, savings: 84 },
  { id: 'evt-017', timestamp: '2026-06-07 15:17:49', eventType: 'cache',    severity: 'success', actor: 'api-key-goog-dm',     team: 'Google DeepMind',     action: 'L2 Cache Hit',             detail: 'Semantic match 0.93 for code review query',           model: undefined, tokens: 4523, cost: 0, savings: 100 },
  { id: 'evt-018', timestamp: '2026-06-07 15:17:28', eventType: 'billing',  severity: 'warning', actor: 'billing-service',     team: 'System',              action: 'Overage Warning',          detail: 'Amazon Alexa AI 95% of $15k monthly budget reached',  model: undefined, tokens: undefined, cost: undefined, savings: undefined },
  { id: 'evt-019', timestamp: '2026-06-07 15:17:01', eventType: 'request',  severity: 'success', actor: 'api-key-meta-ai',     team: 'Meta Content AI',     action: 'LLM Request Completed',   detail: 'Translation task: 45 languages, compression saved 41%', model: 'GPT-4o-mini', tokens: 6780, cost: 0.0020, savings: 79 },
  { id: 'evt-020', timestamp: '2026-06-07 15:16:44', eventType: 'admin',    severity: 'success', actor: 'admin@tokensaver.io',  team: 'Admin',               action: 'New Team Created',         detail: 'Team "Amazon AWS AI" added with $12k budget, T2 limit', model: undefined, tokens: undefined, cost: undefined, savings: undefined },
];

const EVENT_TYPE_LABELS: Record<EventType, string> = {
  request: 'Request',
  cache: 'Cache',
  routing: 'Routing',
  auth: 'Auth',
  admin: 'Admin',
  billing: 'Billing',
};

const SEVERITY_COLORS: Record<Severity, string> = {
  info: '#6366F1',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
};

const SEVERITY_BG: Record<Severity, string> = {
  info: 'rgba(99,102,241,0.12)',
  success: 'rgba(16,185,129,0.12)',
  warning: 'rgba(245,158,11,0.12)',
  error: 'rgba(239,68,68,0.12)',
};

function SeverityIcon({ sev }: { sev: Severity }) {
  const size = 14;
  const color = SEVERITY_COLORS[sev];
  if (sev === 'success') return <CheckCircle size={size} color={color} />;
  if (sev === 'warning') return <AlertTriangle size={size} color={color} />;
  if (sev === 'error') return <Shield size={size} color={color} />;
  return <Info size={size} color={color} />;
}

function EventTypeBadge({ type }: { type: EventType }) {
  const colors: Record<EventType, [string, string]> = {
    request:  ['rgba(99,102,241,0.12)',  '#818CF8'],
    cache:    ['rgba(16,185,129,0.12)',  '#10B981'],
    routing:  ['rgba(168,85,247,0.12)',  '#A855F7'],
    auth:     ['rgba(245,158,11,0.12)',  '#F59E0B'],
    admin:    ['rgba(20,184,166,0.12)',  '#14B8A6'],
    billing:  ['rgba(239,68,68,0.12)',   '#EF4444'],
  };
  const [bg, color] = colors[type];
  return (
    <span className="badge" style={{ background: bg, color, border: 'none', fontSize: 9 }}>
      {EVENT_TYPE_LABELS[type]}
    </span>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function AuditLogPage() {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<EventType | 'all'>('all');
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'all'>('all');

  const filtered = AUDIT_EVENTS.filter(ev => {
    const matchSearch = search === '' ||
      ev.action.toLowerCase().includes(search.toLowerCase()) ||
      ev.detail.toLowerCase().includes(search.toLowerCase()) ||
      ev.actor.toLowerCase().includes(search.toLowerCase()) ||
      ev.team.toLowerCase().includes(search.toLowerCase());
    const matchType = filterType === 'all' || ev.eventType === filterType;
    const matchSev = filterSeverity === 'all' || ev.severity === filterSeverity;
    return matchSearch && matchType && matchSev;
  });

  const summaryStats = {
    total: AUDIT_EVENTS.length,
    success: AUDIT_EVENTS.filter(e => e.severity === 'success').length,
    warnings: AUDIT_EVENTS.filter(e => e.severity === 'warning').length,
    errors: AUDIT_EVENTS.filter(e => e.severity === 'error').length,
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Audit Log</h1>
          <p className="page-subtitle">
            Complete immutable event log · {AUDIT_EVENTS.length} events today{' '}
            <span className="dot-live" style={{ marginLeft: 6 }} />
          </p>
        </div>
        <button className="btn-ghost" style={{ fontSize: 13 }}>
          <Download size={14} />
          Export JSONL
        </button>
      </div>

      {/* Summary chips */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { label: 'Total Events', value: summaryStats.total, color: '#6366F1', bg: 'rgba(99,102,241,0.1)' },
          { label: 'Successful', value: summaryStats.success, color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
          { label: 'Warnings', value: summaryStats.warnings, color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
          { label: 'Errors', value: summaryStats.errors, color: '#EF4444', bg: 'rgba(239,68,68,0.1)' },
        ].map((s, i) => (
          <div
            key={s.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              background: s.bg,
              border: `1px solid ${s.color}30`,
              borderRadius: 10,
              animation: `fadeInUp 0.4s ease ${i * 50 + 50}ms both`,
            }}
          >
            <span style={{ fontSize: 16, fontWeight: 800, color: s.color }}>{s.value}</span>
            <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div
        className="card"
        style={{
          marginBottom: 20,
          padding: '14px 20px',
          animation: 'fadeInUp 0.4s ease 0.2s both',
          display: 'flex',
          gap: 12,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        {/* Search */}
        <div style={{ flex: 1, minWidth: 200, position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
          <input
            className="input"
            style={{ paddingLeft: 32, fontSize: 13 }}
            placeholder="Search events, actors, teams…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Event type filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Filter size={12} color="var(--text-muted)" />
          <select className="input" style={{ width: 'auto', fontSize: 12, padding: '8px 32px 8px 10px' }} value={filterType} onChange={e => setFilterType(e.target.value as EventType | 'all')}>
            <option value="all">All Types</option>
            {Object.entries(EVENT_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>

        {/* Severity filter */}
        <select className="input" style={{ width: 'auto', fontSize: 12, padding: '8px 32px 8px 10px' }} value={filterSeverity} onChange={e => setFilterSeverity(e.target.value as Severity | 'all')}>
          <option value="all">All Severities</option>
          <option value="success">Success</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
        </select>

        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          Showing {filtered.length} of {AUDIT_EVENTS.length}
        </span>
      </div>

      {/* Events Table */}
      <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.25s both' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Type</th>
                <th>Team</th>
                <th>Action</th>
                <th>Detail</th>
                <th>Model</th>
                <th>Tokens</th>
                <th>Savings</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ev) => (
                <tr key={ev.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{ev.timestamp}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <SeverityIcon sev={ev.severity} />
                      <span style={{ fontSize: 11, color: SEVERITY_COLORS[ev.severity], fontWeight: 600, textTransform: 'capitalize' }}>{ev.severity}</span>
                    </div>
                  </td>
                  <td><EventTypeBadge type={ev.eventType} /></td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{ev.team}</td>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', fontSize: 12 }}>{ev.action}</td>
                  <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={ev.detail}>
                    {ev.detail}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--accent-light)' }}>{ev.model ?? '—'}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{ev.tokens != null ? ev.tokens.toLocaleString() : '—'}</td>
                  <td>
                    {ev.savings != null ? (
                      <span style={{ fontWeight: 700, fontSize: 12, color: ev.savings > 0 ? 'var(--success)' : 'var(--text-muted)' }}>
                        {ev.savings > 0 ? `↓ ${ev.savings}%` : '—'}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                    No events match your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)', fontSize: 11, color: 'var(--text-muted)' }}>
          <span>Audit logs retained for 90 days · End-to-end immutable</span>
          <button className="btn-ghost" style={{ fontSize: 11, padding: '6px 12px' }}>Load more events</button>
        </div>
      </div>
    </div>
  );
}
