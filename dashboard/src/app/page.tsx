'use client';

import { DollarSign, Zap, GitBranch, Package } from 'lucide-react';
import KPICard from '@/components/KPICard';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

// ─── Mock Data ───────────────────────────────────────────────────────────────

const DAILY_SAVINGS = [
  { day: 'May 8',  without: 1124, with: 421, savings: 703 },
  { day: 'May 9',  without: 987,  with: 368, savings: 619 },
  { day: 'May 10', without: 1203, with: 451, savings: 752 },
  { day: 'May 11', without: 843,  with: 312, savings: 531 },
  { day: 'May 12', without: 762,  with: 284, savings: 478 },
  { day: 'May 13', without: 934,  with: 347, savings: 587 },
  { day: 'May 14', without: 1089, with: 402, savings: 687 },
  { day: 'May 15', without: 1178, with: 441, savings: 737 },
  { day: 'May 16', without: 1034, with: 384, savings: 650 },
  { day: 'May 17', without: 1267, with: 472, savings: 795 },
  { day: 'May 18', without: 1312, with: 489, savings: 823 },
  { day: 'May 19', without: 1098, with: 408, savings: 690 },
  { day: 'May 20', without: 823,  with: 306, savings: 517 },
  { day: 'May 21', without: 791,  with: 295, savings: 496 },
  { day: 'May 22', without: 1143, with: 426, savings: 717 },
  { day: 'May 23', without: 1289, with: 480, savings: 809 },
  { day: 'May 24', without: 1356, with: 505, savings: 851 },
  { day: 'May 25', without: 1201, with: 448, savings: 753 },
  { day: 'May 26', without: 1089, with: 405, savings: 684 },
  { day: 'May 27', without: 912,  with: 340, savings: 572 },
  { day: 'May 28', without: 878,  with: 327, savings: 551 },
  { day: 'May 29', without: 1234, with: 460, savings: 774 },
  { day: 'May 30', without: 1390, with: 518, savings: 872 },
  { day: 'May 31', without: 1423, with: 530, savings: 893 },
  { day: 'Jun 1',  without: 1567, with: 584, savings: 983 },
  { day: 'Jun 2',  without: 1489, with: 555, savings: 934 },
  { day: 'Jun 3',  without: 1623, with: 605, savings: 1018 },
  { day: 'Jun 4',  without: 1534, with: 572, savings: 962 },
  { day: 'Jun 5',  without: 1712, with: 638, savings: 1074 },
  { day: 'Jun 6',  without: 1687, with: 629, savings: 1058 },
];

const PIE_DATA = [
  { name: 'Semantic Cache',       value: 45, color: '#6366F1' },
  { name: 'Model Routing',        value: 38, color: '#10B981' },
  { name: 'Context Compression',  value: 17, color: '#F59E0B' },
];

const RECENT_REQUESTS = [
  { time: '15:21:44', modelReq: 'GPT-4o',          modelUsed: 'gpt-3.5-turbo',  tokens: 1842, cost: 0.0028, savings: 78, cacheHit: true  },
  { time: '15:21:38', modelReq: 'Claude 3 Opus',   modelUsed: 'Claude 3 Haiku', tokens: 3210, cost: 0.0014, savings: 83, cacheHit: false },
  { time: '15:21:31', modelReq: 'GPT-4o',          modelUsed: 'GPT-4o',         tokens: 8941, cost: 0.0448, savings: 0,  cacheHit: false },
  { time: '15:21:19', modelReq: 'GPT-4 Turbo',     modelUsed: 'gpt-3.5-turbo',  tokens: 512,  cost: 0.0003, savings: 94, cacheHit: true  },
  { time: '15:21:07', modelReq: 'Claude 3 Sonnet', modelUsed: 'Claude 3 Haiku', tokens: 2134, cost: 0.0009, savings: 71, cacheHit: false },
  { time: '15:20:58', modelReq: 'GPT-4o',          modelUsed: 'gpt-3.5-turbo',  tokens: 1023, cost: 0.0015, savings: 81, cacheHit: true  },
  { time: '15:20:44', modelReq: 'Gemini Ultra',    modelUsed: 'Gemini Flash',    tokens: 4567, cost: 0.0018, savings: 76, cacheHit: false },
  { time: '15:20:33', modelReq: 'GPT-4 Turbo',     modelUsed: 'gpt-3.5-turbo',  tokens: 789,  cost: 0.0006, savings: 89, cacheHit: true  },
  { time: '15:20:21', modelReq: 'Claude 3 Opus',   modelUsed: 'Claude 3 Haiku', tokens: 1456, cost: 0.0006, savings: 85, cacheHit: false },
  { time: '15:20:09', modelReq: 'GPT-4o',          modelUsed: 'GPT-4o-mini',    tokens: 2341, cost: 0.0007, savings: 65, cacheHit: false },
];

const TEAMS = [
  { name: 'Google Search AI',    initials: 'GS', color: '#6366F1', saved: 12430, hitRate: 43, requests: 23412 },
  { name: 'Microsoft Copilot',   initials: 'MC', color: '#10B981', saved: 8921,  hitRate: 51, requests: 18934 },
  { name: 'Amazon Alexa AI',     initials: 'AA', color: '#F59E0B', saved: 7340,  hitRate: 38, requests: 15201 },
  { name: 'Meta Content AI',     initials: 'MC', color: '#A855F7', saved: 6123,  hitRate: 29, requests: 12876 },
  { name: 'Google DeepMind',     initials: 'GD', color: '#14B8A6', saved: 5891,  hitRate: 44, requests: 11203 },
];

// Custom recharts tooltip
function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#16161F',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 10,
      padding: '10px 14px',
      fontSize: 12,
    }}>
      <div style={{ color: '#94A3B8', marginBottom: 6, fontWeight: 600 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          <span style={{ color: '#94A3B8' }}>{p.name}:</span>
          <span style={{ color: '#F8FAFC', fontWeight: 600 }}>${p.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function CustomPieTooltip({ active, payload }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: { color: string } }>;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#16161F',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 10,
      padding: '10px 14px',
      fontSize: 12,
    }}>
      <div style={{ color: '#F8FAFC', fontWeight: 600 }}>{payload[0].name}</div>
      <div style={{ color: payload[0].payload.color, fontWeight: 700, fontSize: 16 }}>{payload[0].value}%</div>
    </div>
  );
}

const RADIAN = Math.PI / 180;
function renderCustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }: {
  cx: number; cy: number; midAngle: number; innerRadius: number; outerRadius: number; percent: number;
}) {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={700}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const maxSaved = Math.max(...TEAMS.map(t => t.saved));

  return (
    <div>
      {/* Page Header */}
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-title">Overview</h1>
          <p className="page-subtitle">
            Real-time LLM cost intelligence · Updated just now{' '}
            <span className="dot-live" style={{ marginLeft: 6 }} />
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <select className="input" style={{ width: 'auto', padding: '8px 32px 8px 12px', fontSize: 13 }}>
            <option>Last 30 days</option>
            <option>Last 7 days</option>
            <option>Last 90 days</option>
            <option>This month</option>
          </select>
          <button className="btn-primary" style={{ fontSize: 13 }}>Export Report</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-4 animate-children" style={{ marginBottom: 24 }}>
        <KPICard
          title="Total Saved This Month"
          value="$47,832"
          change={23}
          changeLabel="vs last month"
          icon={<DollarSign size={18} />}
          color="#10B981"
          colorDim="rgba(16,185,129,0.12)"
          trend="up"
          animationDelay={50}
        />
        <KPICard
          title="Cache Hit Rate"
          value="43.7%"
          change={5.2}
          changeLabel="vs last month"
          icon={<Zap size={18} />}
          color="#6366F1"
          colorDim="rgba(99,102,241,0.12)"
          trend="up"
          animationDelay={100}
        />
        <KPICard
          title="Requests Routed Cheaper"
          value="68.3%"
          change={11.1}
          changeLabel="vs last month"
          icon={<GitBranch size={18} />}
          color="#A855F7"
          colorDim="rgba(168,85,247,0.12)"
          trend="up"
          animationDelay={150}
        />
        <KPICard
          title="Tokens Compressed"
          value="31.2% reduction"
          change={3.4}
          changeLabel="vs last month"
          icon={<Package size={18} />}
          color="#14B8A6"
          colorDim="rgba(20,184,166,0.12)"
          trend="up"
          animationDelay={200}
        />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 20, marginBottom: 24 }}>
        {/* Area Chart */}
        <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.25s both' }}>
          <div className="section-title">Cost Savings Over Time</div>
          <div className="section-subtitle">Daily API spend: with vs. without TokenSaver (last 30 days)</div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={DAILY_SAVINGS} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="gradWithout" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#EF4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="gradWith" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fill: '#475569', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval={4}
              />
              <YAxis
                tick={{ fill: '#475569', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="without"
                name="Without TokenSaver"
                stroke="#EF4444"
                strokeWidth={2}
                fill="url(#gradWithout)"
                dot={false}
                activeDot={{ r: 4, fill: '#EF4444' }}
              />
              <Area
                type="monotone"
                dataKey="with"
                name="With TokenSaver"
                stroke="#10B981"
                strokeWidth={2}
                fill="url(#gradWith)"
                dot={false}
                activeDot={{ r: 4, fill: '#10B981' }}
              />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 12, height: 3, background: '#EF4444', borderRadius: 2 }} />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Without TokenSaver (avg $1,185/day)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 12, height: 3, background: '#10B981', borderRadius: 2 }} />
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>With TokenSaver (avg $441/day)</span>
            </div>
          </div>
        </div>

        {/* Donut Chart */}
        <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.3s both' }}>
          <div className="section-title">Savings by Source</div>
          <div className="section-subtitle">Breakdown of how savings are achieved</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={PIE_DATA}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                labelLine={false}
                label={renderCustomLabel}
              >
                {PIE_DATA.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip content={<CustomPieTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Donut center label */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            {PIE_DATA.map((d) => (
              <div key={d.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 3, background: d.color, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{d.name}</span>
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: d.color }}>{d.value}%</span>
              </div>
            ))}
          </div>
          {/* Total savings callout */}
          <div style={{
            marginTop: 16,
            padding: '10px 14px',
            background: 'var(--success-dim)',
            border: '1px solid var(--border-success)',
            borderRadius: 10,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 10, color: 'var(--success)', fontWeight: 700, letterSpacing: '0.08em' }}>TOTAL MONTHLY SAVINGS</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--success)', letterSpacing: '-0.5px' }}>$47,832</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>62.8% avg cost reduction</div>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>
        {/* Recent Requests Table */}
        <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.35s both' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div className="section-title">Recent Requests</div>
              <div className="section-subtitle" style={{ marginBottom: 0 }}>Live request stream — last 10 events</div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--success)' }}>
              <span className="dot-live" />
              Live
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Requested</th>
                  <th>Routed To</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                  <th>Savings</th>
                  <th>Cache</th>
                </tr>
              </thead>
              <tbody>
                {RECENT_REQUESTS.map((req, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>{req.time}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{req.modelReq}</td>
                    <td>
                      <span style={{
                        padding: '2px 8px',
                        background: req.modelUsed === req.modelReq ? 'rgba(239,68,68,0.1)' : 'rgba(99,102,241,0.1)',
                        color: req.modelUsed === req.modelReq ? 'var(--danger)' : 'var(--accent-light)',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {req.modelUsed}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{req.tokens.toLocaleString()}</td>
                    <td style={{ fontFamily: 'monospace' }}>${req.cost.toFixed(4)}</td>
                    <td>
                      {req.savings > 0 ? (
                        <span style={{ color: 'var(--success)', fontWeight: 700, fontSize: 12 }}>↓ {req.savings}%</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>—</span>
                      )}
                    </td>
                    <td>
                      {req.cacheHit ? (
                        <span className="badge badge-success">HIT</span>
                      ) : (
                        <span className="badge badge-muted">MISS</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Teams Leaderboard */}
        <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.4s both' }}>
          <div className="section-title">Top Teams by Savings</div>
          <div className="section-subtitle">This month's leaderboard</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {TEAMS.map((team, i) => (
              <div key={team.name}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  {/* Rank */}
                  <div style={{
                    width: 20,
                    fontSize: 11,
                    fontWeight: 800,
                    color: i === 0 ? '#F59E0B' : i === 1 ? '#94A3B8' : i === 2 ? '#CD7C2F' : 'var(--text-muted)',
                    flexShrink: 0,
                    textAlign: 'center',
                  }}>
                    #{i + 1}
                  </div>
                  {/* Avatar */}
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    background: `${team.color}20`,
                    border: `1px solid ${team.color}40`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 10,
                    fontWeight: 800,
                    color: team.color,
                    flexShrink: 0,
                  }}>
                    {team.initials}
                  </div>
                  {/* Name & stats */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {team.name}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                      {team.requests.toLocaleString()} requests · {team.hitRate}% hit rate
                    </div>
                  </div>
                  {/* Savings */}
                  <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--success)', flexShrink: 0 }}>
                    ${team.saved.toLocaleString()}
                  </div>
                </div>
                {/* Progress bar */}
                <div style={{ paddingLeft: 30 }}>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${(team.saved / maxSaved) * 100}%`,
                        background: `linear-gradient(90deg, ${team.color}, ${team.color}99)`,
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
              <span>5 active teams</span>
              <a href="/teams" style={{ color: 'var(--accent-light)', textDecoration: 'none', fontWeight: 600 }}>
                View all teams →
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
