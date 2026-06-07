'use client';

import { useState } from 'react';
import {
  Settings, Key, Bell, Shield, Globe, Sliders,
  Copy, RefreshCw, Eye, EyeOff, Check, AlertTriangle,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

type Tab = 'general' | 'api-keys' | 'routing' | 'alerts' | 'security';

// ─── Mock API Keys ─────────────────────────────────────────────────────────────

interface ApiKey {
  id: string;
  name: string;
  key: string;
  team: string;
  created: string;
  lastUsed: string;
  requests: number;
  active: boolean;
}

const API_KEYS: ApiKey[] = [
  { id: 'k1', name: 'Google Search AI Key',    key: 'tsk_live_Gx7kJm9NpQr2vY8wLsAeHdTb4...', team: 'Google Search AI',    created: 'Jan 12, 2025', lastUsed: '2 min ago',  requests: 234120, active: true  },
  { id: 'k2', name: 'Microsoft Copilot Key',   key: 'tsk_live_Mv3pRn6QsWx1uZ5tKcFiGjYo8...', team: 'Microsoft Copilot',   created: 'Feb 3, 2025',  lastUsed: '8 min ago',  requests: 189340, active: true  },
  { id: 'k3', name: 'Amazon Alexa Key',        key: 'tsk_live_Hp9mKs4WtNq7rX2dBvEaLfCj1...', team: 'Amazon Alexa AI',     created: 'Jan 28, 2025', lastUsed: '15 min ago', requests: 152010, active: true  },
  { id: 'k4', name: 'Meta Content AI Key',     key: 'tsk_live_Rc5aYn8MtGz3kL7wJeQsPbVx2...', team: 'Meta Content AI',     created: 'Mar 1, 2025',  lastUsed: '1 hr ago',   requests: 128760, active: true  },
  { id: 'k5', name: 'Legacy Integration Key',  key: 'tsk_live_Zj2fXo7NsRp4eW6dHbQvMtKa9...', team: 'Admin',               created: 'Nov 15, 2024', lastUsed: '7 days ago', requests: 4230,   active: false },
];

// ─── Routing Config ────────────────────────────────────────────────────────────

interface RoutingConfig {
  complexityThreshold1: number;
  complexityThreshold2: number;
  semanticSimilarity: number;
  maxCacheAge: number;
  enableCompression: boolean;
  compressionTarget: number;
  fallbackEnabled: boolean;
  rateLimitBuffer: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

function TabButton({ id, label, icon, active, onClick }: {
  id: Tab; label: string; icon: React.ReactNode; active: boolean; onClick: (id: Tab) => void;
}) {
  return (
    <button
      onClick={() => onClick(id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 16px',
        background: active ? 'var(--accent-dim)' : 'transparent',
        border: active ? '1px solid var(--border-accent)' : '1px solid transparent',
        borderRadius: 10,
        color: active ? 'var(--accent-light)' : 'var(--text-secondary)',
        fontSize: 13,
        fontWeight: active ? 600 : 500,
        fontFamily: 'Inter, sans-serif',
        cursor: 'pointer',
        transition: 'all 0.18s ease',
        whiteSpace: 'nowrap',
      }}
      onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; }}
      onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
    >
      {icon}
      {label}
    </button>
  );
}

function ToggleSwitch({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div
      onClick={() => onChange(!value)}
      style={{
        width: 44,
        height: 24,
        borderRadius: 999,
        background: value ? 'var(--accent)' : 'rgba(255,255,255,0.1)',
        padding: 3,
        cursor: 'pointer',
        transition: 'background 0.2s',
        flexShrink: 0,
        position: 'relative',
      }}
    >
      <div style={{
        width: 18,
        height: 18,
        borderRadius: '50%',
        background: '#fff',
        transform: value ? 'translateX(20px)' : 'translateX(0)',
        transition: 'transform 0.2s ease',
        boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
      }} />
    </div>
  );
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, padding: '16px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{label}</div>
        {description && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{description}</div>}
      </div>
      {children}
    </div>
  );
}

function SliderInput({ value, min, max, step, unit, onChange }: {
  value: number; min: number; max: number; step: number; unit: string; onChange: (v: number) => void;
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: 160, accentColor: 'var(--accent)', cursor: 'pointer' }}
      />
      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-light)', minWidth: 60, textAlign: 'right' }}>
        {value}{unit}
      </span>
    </div>
  );
}

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>('general');
  const [savedMsg, setSavedMsg] = useState(false);
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const [routing, setRouting] = useState<RoutingConfig>({
    complexityThreshold1: 50,
    complexityThreshold2: 80,
    semanticSimilarity: 88,
    maxCacheAge: 72,
    enableCompression: true,
    compressionTarget: 30,
    fallbackEnabled: true,
    rateLimitBuffer: 15,
  });

  const [alerts, setAlerts] = useState({
    budgetAlert: true,
    budgetPct: 80,
    errorRateAlert: true,
    errorThreshold: 2,
    cacheDropAlert: true,
    cacheDropPct: 10,
    weeklyReport: true,
    slackWebhook: 'https://hooks.slack.com/services/T04ABC/B05DEF/xxxxxxxxxxxxx',
    emailAlerts: 'alerts@yourcompany.com',
  });

  function handleSave() {
    setSavedMsg(true);
    setTimeout(() => setSavedMsg(false), 2500);
  }

  function copyKey(key: string, id: string) {
    navigator.clipboard.writeText(key).catch(() => {});
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 1800);
  }

  const TABS: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    { id: 'general',  label: 'General',    icon: <Settings size={14} /> },
    { id: 'api-keys', label: 'API Keys',   icon: <Key size={14} /> },
    { id: 'routing',  label: 'Routing',    icon: <Sliders size={14} /> },
    { id: 'alerts',   label: 'Alerts',     icon: <Bell size={14} /> },
    { id: 'security', label: 'Security',   icon: <Shield size={14} /> },
  ];

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure TokenSaver Enterprise for your organization</p>
        </div>
        <button className="btn-primary" onClick={handleSave} style={{ fontSize: 13 }}>
          {savedMsg ? <><Check size={14} /> Saved!</> : 'Save Changes'}
        </button>
      </div>

      {savedMsg && (
        <div style={{ marginBottom: 16, padding: '10px 16px', background: 'var(--success-dim)', border: '1px solid var(--border-success)', borderRadius: 10, color: 'var(--success)', fontSize: 13, fontWeight: 600, animation: 'fadeInUp 0.3s ease both', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Check size={14} /> Settings saved successfully
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 24, flexWrap: 'wrap', animation: 'fadeInUp 0.4s ease 0.1s both' }}>
        {TABS.map(t => (
          <TabButton key={t.id} id={t.id} label={t.label} icon={t.icon} active={tab === t.id} onClick={setTab} />
        ))}
      </div>

      {/* ── General ── */}
      {tab === 'general' && (
        <div className="card" style={{ animation: 'fadeInUp 0.4s ease 0.15s both' }}>
          <div className="section-title" style={{ marginBottom: 0 }}>General Settings</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>Organization-wide configuration</div>

          <SettingRow label="Organization Name" description="Shown in invoices and reports">
            <input className="input" style={{ width: 240, fontSize: 13 }} defaultValue="Acme Corp — AI Division" />
          </SettingRow>

          <SettingRow label="Default Timezone" description="Used for reports and audit log timestamps">
            <select className="input" style={{ width: 200, fontSize: 13 }}>
              <option>UTC</option>
              <option>America/New_York</option>
              <option>America/Los_Angeles</option>
              <option>Europe/London</option>
              <option>Asia/Tokyo</option>
            </select>
          </SettingRow>

          <SettingRow label="Data Retention" description="How long logs and cache entries are kept">
            <select className="input" style={{ width: 200, fontSize: 13 }}>
              <option>30 days</option>
              <option>60 days</option>
              <option selected>90 days</option>
              <option>180 days</option>
              <option>1 year</option>
            </select>
          </SettingRow>

          <SettingRow label="API Base URL" description="Endpoint for all LLM proxy requests">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input className="input" style={{ width: 280, fontSize: 12, fontFamily: 'monospace' }} defaultValue="https://api.tokensaver.io/v1" readOnly />
              <button className="btn-ghost" style={{ padding: '8px 10px' }}><Copy size={13} /></button>
            </div>
          </SettingRow>

          <SettingRow label="Webhook URL" description="Receive real-time event notifications">
            <input className="input" style={{ width: 280, fontSize: 12, fontFamily: 'monospace' }} defaultValue="https://your-app.com/webhooks/ts" />
          </SettingRow>

          <SettingRow label="Dashboard Theme" description="UI appearance preference">
            <div style={{ display: 'flex', gap: 8 }}>
              {['Dark (Current)', 'System'].map(opt => (
                <button key={opt} className={opt === 'Dark (Current)' ? 'btn-primary' : 'btn-ghost'} style={{ fontSize: 12, padding: '8px 14px' }}>{opt}</button>
              ))}
            </div>
          </SettingRow>
        </div>
      )}

      {/* ── API Keys ── */}
      {tab === 'api-keys' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, animation: 'fadeInUp 0.4s ease 0.15s both' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>API Keys</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{API_KEYS.filter(k => k.active).length} active keys · Keys provide full API access</div>
            </div>
            <button className="btn-primary" style={{ fontSize: 12 }}>
              <Key size={13} />
              Generate New Key
            </button>
          </div>

          {API_KEYS.map((apiKey) => (
            <div key={apiKey.id} className="card" style={{ padding: '16px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{apiKey.name}</div>
                    <span className={`badge ${apiKey.active ? 'badge-success' : 'badge-muted'}`}>
                      {apiKey.active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <code style={{
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: 'var(--text-secondary)',
                      background: 'rgba(255,255,255,0.04)',
                      padding: '4px 10px',
                      borderRadius: 6,
                      border: '1px solid var(--border)',
                      flex: 1,
                      maxWidth: 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'block',
                    }}>
                      {showKey[apiKey.id] ? apiKey.key.replace('...', 'xRtGhJkLmNp') : apiKey.key}
                    </code>
                    <button
                      className="btn-ghost"
                      style={{ padding: '5px 8px', fontSize: 11 }}
                      onClick={() => setShowKey(p => ({ ...p, [apiKey.id]: !p[apiKey.id] }))}
                    >
                      {showKey[apiKey.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                    </button>
                    <button
                      className="btn-ghost"
                      style={{ padding: '5px 8px', fontSize: 11 }}
                      onClick={() => copyKey(apiKey.key, apiKey.id)}
                    >
                      {copiedKey === apiKey.id ? <Check size={13} color="var(--success)" /> : <Copy size={13} />}
                    </button>
                  </div>

                  <div style={{ display: 'flex', gap: 20, fontSize: 11, color: 'var(--text-muted)' }}>
                    <span>Team: <strong style={{ color: 'var(--text-secondary)' }}>{apiKey.team}</strong></span>
                    <span>Created: <strong style={{ color: 'var(--text-secondary)' }}>{apiKey.created}</strong></span>
                    <span>Last used: <strong style={{ color: 'var(--text-secondary)' }}>{apiKey.lastUsed}</strong></span>
                    <span>Requests: <strong style={{ color: 'var(--accent-light)' }}>{apiKey.requests.toLocaleString()}</strong></span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button className="btn-ghost" style={{ fontSize: 11, padding: '6px 10px' }}>
                    <RefreshCw size={12} /> Rotate
                  </button>
                  <button
                    className="btn-ghost"
                    style={{ fontSize: 11, padding: '6px 10px', color: 'var(--danger)', borderColor: 'rgba(239,68,68,0.3)' }}
                    onClick={() => {}}
                  >
                    Revoke
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Routing ── */}
      {tab === 'routing' && (
        <div className="card" style={{ animation: 'fadeInUp 0.4s ease 0.15s both' }}>
          <div className="section-title">Routing Configuration</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
            Tune how requests are classified and routed across model tiers
          </div>

          <SettingRow
            label="Tier 1 → Tier 2 Complexity Threshold"
            description="Requests with complexity above this are routed to Tier 2"
          >
            <SliderInput value={routing.complexityThreshold1} min={20} max={70} step={1} unit="" onChange={v => setRouting(p => ({ ...p, complexityThreshold1: v }))} />
          </SettingRow>

          <SettingRow
            label="Tier 2 → Tier 3 Complexity Threshold"
            description="Requests above this are routed to premium models"
          >
            <SliderInput value={routing.complexityThreshold2} min={60} max={99} step={1} unit="" onChange={v => setRouting(p => ({ ...p, complexityThreshold2: v }))} />
          </SettingRow>

          <SettingRow
            label="Semantic Cache Similarity Threshold"
            description="Minimum similarity score (%) to serve a cached response"
          >
            <SliderInput value={routing.semanticSimilarity} min={70} max={99} step={1} unit="%" onChange={v => setRouting(p => ({ ...p, semanticSimilarity: v }))} />
          </SettingRow>

          <SettingRow
            label="Max Cache Entry Age"
            description="How long (hours) a cached response is considered valid"
          >
            <SliderInput value={routing.maxCacheAge} min={1} max={168} step={1} unit="h" onChange={v => setRouting(p => ({ ...p, maxCacheAge: v }))} />
          </SettingRow>

          <SettingRow
            label="Enable Context Compression"
            description="Automatically compress large prompts before routing"
          >
            <ToggleSwitch value={routing.enableCompression} onChange={v => setRouting(p => ({ ...p, enableCompression: v }))} />
          </SettingRow>

          {routing.enableCompression && (
            <SettingRow
              label="Compression Target Reduction"
              description="Target % token reduction for compressed prompts"
            >
              <SliderInput value={routing.compressionTarget} min={10} max={60} step={5} unit="%" onChange={v => setRouting(p => ({ ...p, compressionTarget: v }))} />
            </SettingRow>
          )}

          <SettingRow
            label="Model Fallback on Rate Limit"
            description="Automatically fall back to a lower tier if rate limited"
          >
            <ToggleSwitch value={routing.fallbackEnabled} onChange={v => setRouting(p => ({ ...p, fallbackEnabled: v }))} />
          </SettingRow>

          <SettingRow
            label="Rate Limit Safety Buffer"
            description="Stop using a model at this % of its rate limit to prevent errors"
          >
            <SliderInput value={routing.rateLimitBuffer} min={5} max={40} step={5} unit="%" onChange={v => setRouting(p => ({ ...p, rateLimitBuffer: v }))} />
          </SettingRow>
        </div>
      )}

      {/* ── Alerts ── */}
      {tab === 'alerts' && (
        <div className="card" style={{ animation: 'fadeInUp 0.4s ease 0.15s both' }}>
          <div className="section-title">Alert Configuration</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
            Set up proactive notifications for budget, errors, and performance changes
          </div>

          <SettingRow label="Budget Threshold Alert" description="Alert when a team reaches this % of monthly budget">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <ToggleSwitch value={alerts.budgetAlert} onChange={v => setAlerts(p => ({ ...p, budgetAlert: v }))} />
              {alerts.budgetAlert && <SliderInput value={alerts.budgetPct} min={50} max={100} step={5} unit="%" onChange={v => setAlerts(p => ({ ...p, budgetPct: v }))} />}
            </div>
          </SettingRow>

          <SettingRow label="Error Rate Alert" description="Alert when API error rate exceeds threshold">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <ToggleSwitch value={alerts.errorRateAlert} onChange={v => setAlerts(p => ({ ...p, errorRateAlert: v }))} />
              {alerts.errorRateAlert && <SliderInput value={alerts.errorThreshold} min={0.5} max={10} step={0.5} unit="%" onChange={v => setAlerts(p => ({ ...p, errorThreshold: v }))} />}
            </div>
          </SettingRow>

          <SettingRow label="Cache Hit Rate Drop Alert" description="Alert when cache hit rate drops more than this">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <ToggleSwitch value={alerts.cacheDropAlert} onChange={v => setAlerts(p => ({ ...p, cacheDropAlert: v }))} />
              {alerts.cacheDropAlert && <SliderInput value={alerts.cacheDropPct} min={5} max={30} step={5} unit="%" onChange={v => setAlerts(p => ({ ...p, cacheDropPct: v }))} />}
            </div>
          </SettingRow>

          <SettingRow label="Weekly Savings Report" description="Automated weekly summary email with savings breakdown">
            <ToggleSwitch value={alerts.weeklyReport} onChange={v => setAlerts(p => ({ ...p, weeklyReport: v }))} />
          </SettingRow>

          <div style={{ height: 1, background: 'var(--border)', margin: '8px 0' }} />

          <SettingRow label="Slack Webhook URL" description="Post alerts to your Slack workspace">
            <input className="input" style={{ width: 320, fontSize: 11, fontFamily: 'monospace' }} value={alerts.slackWebhook} onChange={e => setAlerts(p => ({ ...p, slackWebhook: e.target.value }))} />
          </SettingRow>

          <SettingRow label="Alert Email" description="Send email alerts to this address">
            <input className="input" style={{ width: 240, fontSize: 13 }} type="email" value={alerts.emailAlerts} onChange={e => setAlerts(p => ({ ...p, emailAlerts: e.target.value }))} />
          </SettingRow>
        </div>
      )}

      {/* ── Security ── */}
      {tab === 'security' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, animation: 'fadeInUp 0.4s ease 0.15s both' }}>
          <div className="card" style={{ background: 'var(--warning-dim)', border: '1px solid rgba(245,158,11,0.2)' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <AlertTriangle size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--warning)', marginBottom: 3 }}>Security Recommendations</div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  Enable MFA, rotate API keys every 90 days, and restrict key permissions to minimum required scopes. You have 1 inactive key that should be revoked.
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="section-title">Access Control</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>Authentication and authorization settings</div>

            <SettingRow label="Two-Factor Authentication" description="Require MFA for all admin users">
              <ToggleSwitch value={true} onChange={() => {}} />
            </SettingRow>

            <SettingRow label="SSO / SAML 2.0" description="Integrate with your identity provider">
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="badge badge-success">Configured</span>
                <button className="btn-ghost" style={{ fontSize: 12, padding: '6px 12px' }}>Configure</button>
              </div>
            </SettingRow>

            <SettingRow label="IP Allowlist" description="Restrict dashboard and API access to trusted IPs">
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="input" style={{ width: 200, fontSize: 12, fontFamily: 'monospace' }} placeholder="0.0.0.0/0 (all)" />
                <button className="btn-ghost" style={{ fontSize: 12, padding: '8px 12px' }}>Add IP</button>
              </div>
            </SettingRow>

            <SettingRow label="Session Timeout" description="Automatically log out inactive sessions">
              <select className="input" style={{ width: 160, fontSize: 13 }}>
                <option>30 minutes</option>
                <option selected>2 hours</option>
                <option>8 hours</option>
                <option>Never</option>
              </select>
            </SettingRow>
          </div>

          <div className="card">
            <div className="section-title">Data Privacy</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>Control how your data is stored and processed</div>

            <SettingRow label="PII Masking" description="Automatically redact PII from cached requests and logs">
              <ToggleSwitch value={true} onChange={() => {}} />
            </SettingRow>

            <SettingRow label="Request Logging" description="Store full request/response content for audit purposes">
              <select className="input" style={{ width: 200, fontSize: 13 }}>
                <option>Metadata only</option>
                <option selected>Headers + metadata</option>
                <option>Full content (PII masked)</option>
                <option>Disabled</option>
              </select>
            </SettingRow>

            <SettingRow label="Data Residency" description="Geographic region for all stored data">
              <select className="input" style={{ width: 200, fontSize: 13 }}>
                <option selected>US East (us-east-1)</option>
                <option>US West (us-west-2)</option>
                <option>EU West (eu-west-1)</option>
                <option>AP Southeast</option>
              </select>
            </SettingRow>
          </div>
        </div>
      )}
    </div>
  );
}
