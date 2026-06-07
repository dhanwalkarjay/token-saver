'use client';

import { useState } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { Users, Plus, X, DollarSign, Zap, BarChart2, TrendingUp } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Team {
  id: string;
  name: string;
  initials: string;
  color: string;
  saved: number;
  hitRate: number;
  requests: number;
  avgLatency: string;
  tier: string;
  budget: number;
  sparkline: Array<{ v: number }>;
  createdAt: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────

function makeSparkline(base: number, len = 12): Array<{ v: number }> {
  let v = base;
  return Array.from({ length: len }, () => {
    v = Math.max(0, v + (Math.random() - 0.45) * (base * 0.15));
    return { v: Math.round(v) };
  });
}

const TEAMS: Team[] = [
  {
    id: 'team-1',
    name: 'Google Search AI',
    initials: 'GS',
    color: '#6366F1',
    saved: 12430,
    hitRate: 43,
    requests: 23412,
    avgLatency: '148ms',
    tier: 'Enterprise',
    budget: 25000,
    sparkline: makeSparkline(400),
    createdAt: 'Jan 12, 2025',
  },
  {
    id: 'team-2',
    name: 'Microsoft Copilot',
    initials: 'MC',
    color: '#10B981',
    saved: 8921,
    hitRate: 51,
    requests: 18934,
    avgLatency: '122ms',
    tier: 'Enterprise',
    budget: 20000,
    sparkline: makeSparkline(310),
    createdAt: 'Feb 3, 2025',
  },
  {
    id: 'team-3',
    name: 'Amazon Alexa AI',
    initials: 'AA',
    color: '#F59E0B',
    saved: 7340,
    hitRate: 38,
    requests: 15201,
    avgLatency: '167ms',
    tier: 'Professional',
    budget: 15000,
    sparkline: makeSparkline(250),
    createdAt: 'Jan 28, 2025',
  },
  {
    id: 'team-4',
    name: 'Meta Content AI',
    initials: 'MC',
    color: '#A855F7',
    saved: 6123,
    hitRate: 29,
    requests: 12876,
    avgLatency: '195ms',
    tier: 'Professional',
    budget: 15000,
    sparkline: makeSparkline(200),
    createdAt: 'Mar 1, 2025',
  },
  {
    id: 'team-5',
    name: 'Google DeepMind',
    initials: 'GD',
    color: '#14B8A6',
    saved: 5891,
    hitRate: 44,
    requests: 11203,
    avgLatency: '134ms',
    tier: 'Enterprise',
    budget: 12000,
    sparkline: makeSparkline(190),
    createdAt: 'Feb 14, 2025',
  },
  {
    id: 'team-6',
    name: 'Amazon AWS AI',
    initials: 'AW',
    color: '#EF4444',
    saved: 5234,
    hitRate: 35,
    requests: 10982,
    avgLatency: '178ms',
    tier: 'Professional',
    budget: 12000,
    sparkline: makeSparkline(170),
    createdAt: 'Mar 15, 2025',
  },
];

// ─── Team Card ────────────────────────────────────────────────────────────────

function TeamCard({ team, rank, delay }: { team: Team; rank: number; delay: number }) {
  const budgetUsed = ((team.budget - team.saved) / team.budget) * 100;
  const actualBudgetUsedPct = Math.min(95, Math.round(budgetUsed));

  return (
    <div
      className="card"
      style={{
        animation: `fadeInUp 0.5s ease ${delay}ms both`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Top accent line */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: `linear-gradient(90deg, ${team.color}, ${team.color}50)` }} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, marginTop: 4 }}>
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: `${team.color}20`,
            border: `1.5px solid ${team.color}50`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            fontWeight: 800,
            color: team.color,
            flexShrink: 0,
          }}
        >
          {team.initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {team.name}
          </div>
          <span
            className="badge"
            style={{
              background: team.tier === 'Enterprise' ? 'var(--accent-dim)' : 'var(--warning-dim)',
              color: team.tier === 'Enterprise' ? 'var(--accent-light)' : 'var(--warning)',
              border: `1px solid ${team.tier === 'Enterprise' ? 'rgba(99,102,241,0.2)' : 'rgba(245,158,11,0.2)'}`,
              fontSize: 9,
            }}
          >
            {team.tier}
          </span>
        </div>
        <div style={{
          width: 24,
          height: 24,
          borderRadius: 6,
          background: 'rgba(255,255,255,0.05)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 10,
          fontWeight: 800,
          color: rank <= 3 ? ['#F59E0B','#94A3B8','#CD7C2F'][rank-1] : 'var(--text-muted)',
        }}>
          #{rank}
        </div>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
        {[
          { label: 'Saved', value: `$${team.saved.toLocaleString()}`, color: 'var(--success)', icon: <DollarSign size={11} /> },
          { label: 'Hit Rate', value: `${team.hitRate}%`, color: 'var(--accent-light)', icon: <Zap size={11} /> },
          { label: 'Requests', value: team.requests.toLocaleString(), color: 'var(--text-primary)', icon: <BarChart2 size={11} /> },
          { label: 'Avg Latency', value: team.avgLatency, color: 'var(--text-secondary)', icon: <TrendingUp size={11} /> },
        ].map(stat => (
          <div key={stat.label} style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 8, padding: '8px 10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 3, color: 'var(--text-muted)' }}>
              {stat.icon}
              <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.05em' }}>{stat.label}</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: stat.color }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Sparkline */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600 }}>SAVINGS TREND (12 days)</span>
        </div>
        <ResponsiveContainer width="100%" height={48}>
          <LineChart data={team.sparkline}>
            <Line type="monotone" dataKey="v" stroke={team.color} strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Budget bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
          <span>Budget Utilization</span>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
            ${(team.budget * actualBudgetUsedPct / 100 / 1000).toFixed(1)}k / ${(team.budget / 1000).toFixed(0)}k
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${actualBudgetUsedPct}%`,
              background: actualBudgetUsedPct > 80
                ? 'linear-gradient(90deg, #EF4444, #F59E0B)'
                : `linear-gradient(90deg, ${team.color}, ${team.color}80)`,
            }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

function CreateTeamModal({ onClose }: { onClose: () => void }) {
  const [formData, setFormData] = useState({
    name: '',
    tier: 'Professional',
    budget: '',
    tierLimit: 'Tier 2',
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // In a real app, this would POST to the API
    alert(`Team "${formData.name}" created! (Demo mode)`);
    onClose();
  }

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal-box">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>Create New Team</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>Set up a new team with budget limits and tier access</div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', borderRadius: 8, padding: '6px 8px', cursor: 'pointer', color: 'var(--text-secondary)' }}
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label className="input-label">Team Name</label>
            <input
              className="input"
              placeholder="e.g. Platform Engineering"
              value={formData.name}
              onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
              required
            />
          </div>

          <div>
            <label className="input-label">Subscription Tier</label>
            <select className="input" value={formData.tier} onChange={e => setFormData(p => ({ ...p, tier: e.target.value }))}>
              <option>Starter</option>
              <option>Professional</option>
              <option>Enterprise</option>
            </select>
          </div>

          <div>
            <label className="input-label">Model Tier Limit</label>
            <select className="input" value={formData.tierLimit} onChange={e => setFormData(p => ({ ...p, tierLimit: e.target.value }))}>
              <option>Tier 1 (Cheap only)</option>
              <option>Tier 2 (Balanced — recommended)</option>
              <option>Tier 3 (All models)</option>
            </select>
          </div>

          <div>
            <label className="input-label">Monthly Budget (USD)</label>
            <input
              className="input"
              type="number"
              placeholder="e.g. 5000"
              value={formData.budget}
              onChange={e => setFormData(p => ({ ...p, budget: e.target.value }))}
              required
              min="100"
            />
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button type="button" className="btn-ghost" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" style={{ flex: 1, justifyContent: 'center' }}>
              <Plus size={15} />
              Create Team
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function TeamsPage() {
  const [showModal, setShowModal] = useState(false);

  const totalSaved = TEAMS.reduce((a, t) => a + t.saved, 0);
  const totalRequests = TEAMS.reduce((a, t) => a + t.requests, 0);
  const avgHitRate = Math.round(TEAMS.reduce((a, t) => a + t.hitRate, 0) / TEAMS.length);

  return (
    <div>
      {showModal && <CreateTeamModal onClose={() => setShowModal(false)} />}

      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Teams</h1>
          <p className="page-subtitle">Manage teams, budgets, and model access tiers</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={15} />
          New Team
        </button>
      </div>

      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Total Teams', value: TEAMS.length.toString(), sub: 'Active workspaces', color: '#6366F1', icon: <Users size={16} /> },
          { label: 'Combined Savings', value: `$${totalSaved.toLocaleString()}`, sub: 'This month across all teams', color: '#10B981', icon: <DollarSign size={16} /> },
          { label: 'Avg Cache Hit Rate', value: `${avgHitRate}%`, sub: `${totalRequests.toLocaleString()} total requests`, color: '#F59E0B', icon: <Zap size={16} /> },
        ].map((s, i) => (
          <div className="card" key={s.label} style={{ animation: `fadeInUp 0.5s ease ${i * 50 + 50}ms both`, padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>{s.label}</span>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: `${s.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: s.color }}>{s.icon}</div>
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 3 }}>{s.value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Team Cards Grid */}
      <div className="grid-3" style={{ marginBottom: 24 }}>
        {TEAMS.map((team, i) => (
          <TeamCard key={team.id} team={team} rank={i + 1} delay={i * 60 + 100} />
        ))}
      </div>

      {/* Full Table */}
      <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.5s both' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <div className="section-title">All Teams — Monthly Statistics</div>
            <div className="section-subtitle" style={{ marginBottom: 0 }}>Detailed breakdown for the current billing period</div>
          </div>
          <button className="btn-ghost" style={{ fontSize: 12 }}>Export CSV</button>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Team</th>
                <th>Tier</th>
                <th>Total Saved</th>
                <th>Cache Hit Rate</th>
                <th>Requests</th>
                <th>Avg Latency</th>
                <th>Budget Used</th>
                <th>Since</th>
              </tr>
            </thead>
            <tbody>
              {TEAMS.map((team, i) => {
                const budgetUsedPct = Math.min(95, Math.round(((team.budget - team.saved) / team.budget) * 100));
                return (
                  <tr key={team.id}>
                    <td style={{ color: 'var(--text-muted)', fontWeight: 700 }}>#{i+1}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 26, height: 26, borderRadius: 7, background: `${team.color}20`, border: `1px solid ${team.color}40`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 800, color: team.color, flexShrink: 0 }}>{team.initials}</div>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{team.name}</span>
                      </div>
                    </td>
                    <td>
                      <span className="badge" style={{ background: team.tier === 'Enterprise' ? 'var(--accent-dim)' : 'var(--warning-dim)', color: team.tier === 'Enterprise' ? 'var(--accent-light)' : 'var(--warning)', border: 'none', fontSize: 9 }}>{team.tier}</span>
                    </td>
                    <td style={{ fontWeight: 700, color: 'var(--success)' }}>${team.saved.toLocaleString()}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ width: 50, display: 'inline-block' }}>
                          <div className="progress-fill" style={{ width: `${team.hitRate}%`, background: team.hitRate > 40 ? 'var(--success)' : 'var(--warning)' }} />
                        </div>
                        <span style={{ fontSize: 11, fontWeight: 600 }}>{team.hitRate}%</span>
                      </div>
                    </td>
                    <td style={{ fontFamily: 'monospace' }}>{team.requests.toLocaleString()}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{team.avgLatency}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ width: 50, display: 'inline-block' }}>
                          <div className="progress-fill" style={{ width: `${budgetUsedPct}%`, background: budgetUsedPct > 80 ? 'var(--danger)' : 'var(--accent)' }} />
                        </div>
                        <span style={{ fontSize: 11 }}>{budgetUsedPct}%</span>
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{team.createdAt}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
