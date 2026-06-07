'use client';

import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Database, Zap, Clock, HardDrive, Search } from 'lucide-react';

// ─── Mock Data ────────────────────────────────────────────────────────────────

const CACHE_HIT_RATE_30D = [
  { day: 'May 8',  l1: 18.2, l2: 21.3, total: 39.5 },
  { day: 'May 9',  l1: 19.1, l2: 22.1, total: 41.2 },
  { day: 'May 10', l1: 20.4, l2: 23.8, total: 44.2 },
  { day: 'May 11', l1: 18.9, l2: 21.5, total: 40.4 },
  { day: 'May 12', l1: 19.3, l2: 22.4, total: 41.7 },
  { day: 'May 13', l1: 20.1, l2: 23.1, total: 43.2 },
  { day: 'May 14', l1: 21.2, l2: 24.0, total: 45.2 },
  { day: 'May 15', l1: 20.8, l2: 23.7, total: 44.5 },
  { day: 'May 16', l1: 21.5, l2: 24.3, total: 45.8 },
  { day: 'May 17', l1: 22.1, l2: 25.1, total: 47.2 },
  { day: 'May 18', l1: 21.8, l2: 24.8, total: 46.6 },
  { day: 'May 19', l1: 22.4, l2: 25.6, total: 48.0 },
  { day: 'May 20', l1: 21.2, l2: 23.9, total: 45.1 },
  { day: 'May 21', l1: 20.9, l2: 23.4, total: 44.3 },
  { day: 'May 22', l1: 22.7, l2: 25.9, total: 48.6 },
  { day: 'May 23', l1: 23.1, l2: 26.2, total: 49.3 },
  { day: 'May 24', l1: 23.8, l2: 27.0, total: 50.8 },
  { day: 'May 25', l1: 23.2, l2: 26.4, total: 49.6 },
  { day: 'May 26', l1: 22.9, l2: 26.0, total: 48.9 },
  { day: 'May 27', l1: 22.3, l2: 25.2, total: 47.5 },
  { day: 'May 28', l1: 21.8, l2: 24.5, total: 46.3 },
  { day: 'May 29', l1: 23.4, l2: 26.7, total: 50.1 },
  { day: 'May 30', l1: 24.1, l2: 27.5, total: 51.6 },
  { day: 'May 31', l1: 24.7, l2: 28.1, total: 52.8 },
  { day: 'Jun 1',  l1: 25.3, l2: 28.9, total: 54.2 },
  { day: 'Jun 2',  l1: 24.8, l2: 28.3, total: 53.1 },
  { day: 'Jun 3',  l1: 25.6, l2: 29.1, total: 54.7 },
  { day: 'Jun 4',  l1: 25.1, l2: 28.7, total: 53.8 },
  { day: 'Jun 5',  l1: 26.2, l2: 29.8, total: 56.0 },
  { day: 'Jun 6',  l1: 25.8, l2: 29.4, total: 55.2 },
];

const TOP_CATEGORIES = [
  { name: 'Code Review',       hits: 52341 },
  { name: 'Documentation',     hits: 47821 },
  { name: 'Summarization',     hits: 43190 },
  { name: 'Translation',       hits: 38012 },
  { name: 'Q&A / Support',     hits: 31456 },
  { name: 'Data Extraction',   hits: 27834 },
  { name: 'Sentiment Analysis',hits: 23102 },
  { name: 'Classification',    hits: 18765 },
  { name: 'Entity Recognition',hits: 14321 },
  { name: 'Text Generation',   hits: 9890  },
];

// Heatmap: hour (0-23) × day (Mon-Sun)
const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function generateHeatmapData(): number[][] {
  // Returns [day][hour] = activity level 0-100
  return DAYS_OF_WEEK.map((_, dayIdx) => {
    const isWeekend = dayIdx >= 5;
    return HOURS.map((hour) => {
      // Business hours peak
      let base = 0;
      if (!isWeekend) {
        if (hour >= 9 && hour <= 17) base = 60 + Math.random() * 40;
        else if (hour >= 7 && hour <= 19) base = 30 + Math.random() * 30;
        else base = Math.random() * 15;
      } else {
        if (hour >= 10 && hour <= 15) base = 20 + Math.random() * 25;
        else base = Math.random() * 12;
      }
      return Math.round(base);
    });
  });
}

const HEATMAP_DATA = generateHeatmapData();

const RECENT_CACHED = [
  { query: 'Summarize the following quarterly earnings report for Q3 FY2024...', similarity: 0.98, hits: 2341, lastAccessed: '2 min ago', saved: '1,248ms' },
  { query: 'Review this Python code for security vulnerabilities and suggest...', similarity: 0.95, hits: 1876, lastAccessed: '4 min ago', saved: '1,190ms' },
  { query: 'Translate the following product description from English to Spanish...', similarity: 1.00, hits: 3012, lastAccessed: '1 min ago', saved: '1,340ms' },
  { query: 'Extract all named entities from the following news article...', similarity: 0.92, hits: 987,  lastAccessed: '7 min ago', saved: '980ms'  },
  { query: 'Generate a professional email response to the customer complaint...', similarity: 0.89, hits: 743,  lastAccessed: '11 min ago', saved: '1,100ms' },
  { query: 'Analyze the sentiment of these 50 customer reviews and categorize...', similarity: 0.96, hits: 1234, lastAccessed: '3 min ago', saved: '1,220ms' },
  { query: 'Write unit tests for the following TypeScript class...', similarity: 0.91, hits: 567,  lastAccessed: '15 min ago', saved: '1,050ms' },
];

function getHeatColor(value: number): string {
  if (value === 0) return 'rgba(255,255,255,0.03)';
  if (value < 20)  return 'rgba(99,102,241,0.15)';
  if (value < 40)  return 'rgba(99,102,241,0.30)';
  if (value < 60)  return 'rgba(99,102,241,0.50)';
  if (value < 80)  return 'rgba(99,102,241,0.70)';
  return 'rgba(99,102,241,0.90)';
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#16161F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, padding: '10px 14px', fontSize: 12 }}>
      <div style={{ color: '#94A3B8', marginBottom: 6, fontWeight: 600 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          <span style={{ color: '#94A3B8' }}>{p.name}:</span>
          <span style={{ color: '#F8FAFC', fontWeight: 600 }}>{p.value.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, color, colorDim, delay }: {
  icon: React.ReactNode; label: string; value: string; sub: string;
  color: string; colorDim: string; delay: number;
}) {
  return (
    <div className="card" style={{ animation: `fadeInUp 0.5s ease ${delay}ms both` }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.01em' }}>{label}</span>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: colorDim, display: 'flex', alignItems: 'center', justifyContent: 'center', color, flexShrink: 0 }}>{icon}</div>
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px', marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function CacheAnalyticsPage() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Cache Analytics</h1>
        <p className="page-subtitle">
          Semantic and exact-match cache performance · Updated in real-time{' '}
          <span className="dot-live" style={{ marginLeft: 6 }} />
        </p>
      </div>

      {/* Top Stats */}
      <div className="grid-4 animate-children" style={{ marginBottom: 24 }}>
        <StatCard icon={<Database size={16} />} label="Total Cache Hits" value="284,732" sub="All time since deployment" color="#6366F1" colorDim="rgba(99,102,241,0.15)" delay={50} />
        <StatCard icon={<Zap size={16} />} label="L1 Exact Hits" value="127,483" sub="44.8% of all hits" color="#10B981" colorDim="rgba(16,185,129,0.15)" delay={100} />
        <StatCard icon={<Search size={16} />} label="L2 Semantic Hits" value="157,249" sub="55.2% of all hits" color="#A855F7" colorDim="rgba(168,85,247,0.15)" delay={150} />
        <StatCard icon={<Clock size={16} />} label="Avg Latency Saved" value="1,240ms" sub="Per cache hit event" color="#F59E0B" colorDim="rgba(245,158,11,0.15)" delay={200} />
      </div>

      {/* Storage stat */}
      <div className="card" style={{ marginBottom: 24, padding: '16px 24px', animation: 'fadeInUp 0.5s ease 0.25s both' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(20,184,166,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--teal)' }}>
              <HardDrive size={18} />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Storage Used: 2.4 GB / 10 GB</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Vector embeddings + raw response cache · Redis cluster</div>
            </div>
          </div>
          <div style={{ flex: 1, maxWidth: 300 }}>
            <div className="progress-bar" style={{ height: 8 }}>
              <div className="progress-fill" style={{ width: '24%', background: 'linear-gradient(90deg, #14B8A6, #6366F1)' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 10, color: 'var(--text-muted)' }}>
              <span>24% used</span>
              <span>7.6 GB remaining</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-ghost" style={{ fontSize: 12, padding: '8px 14px' }}>Flush L1</button>
            <button className="btn-ghost" style={{ fontSize: 12, padding: '8px 14px' }}>Flush L2</button>
            <button className="btn-primary" style={{ fontSize: 12, padding: '8px 14px' }}>Expand Storage</button>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Line Chart */}
        <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.3s both' }}>
          <div className="section-title">Cache Hit Rate Over Time</div>
          <div className="section-subtitle">L1 (exact) and L2 (semantic) hit rates — 30 day trend</div>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={CACHE_HIT_RATE_30D} margin={{ top: 5, right: 5, left: -15, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="day" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} interval={4} />
              <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} domain={[0, 65]} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="l1" name="L1 Exact" stroke="#10B981" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line type="monotone" dataKey="l2" name="L2 Semantic" stroke="#6366F1" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              <Line type="monotone" dataKey="total" name="Total" stroke="#F59E0B" strokeWidth={1.5} strokeDasharray="4 2" dot={false} activeDot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
            {[{ color: '#10B981', label: 'L1 Exact' }, { color: '#6366F1', label: 'L2 Semantic' }, { color: '#F59E0B', label: 'Total' }].map(l => (
              <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <div style={{ width: 10, height: 3, background: l.color, borderRadius: 2 }} />
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bar Chart */}
        <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.35s both' }}>
          <div className="section-title">Top 10 Cached Query Categories</div>
          <div className="section-subtitle">All-time hit count by query type</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={TOP_CATEGORIES} layout="vertical" margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} width={110} />
              <Tooltip
                formatter={(v: number) => [v.toLocaleString(), 'Cache Hits']}
                contentStyle={{ background: '#16161F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 12 }}
                labelStyle={{ color: '#94A3B8' }}
                itemStyle={{ color: '#F8FAFC' }}
              />
              <Bar dataKey="hits" fill="#6366F1" radius={[0, 4, 4, 0]} barSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Heatmap */}
      <div className="card" style={{ marginBottom: 24, animation: 'fadeInUp 0.5s ease 0.4s both' }}>
        <div className="section-title">Cache Activity Heatmap</div>
        <div className="section-subtitle">Request volume by hour of day × day of week (darker = more activity)</div>
        <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: `50px repeat(24, 1fr)`, gap: 3, minWidth: 700 }}>
            {/* Hour labels */}
            <div />
            {HOURS.map(h => (
              <div key={h} style={{ textAlign: 'center', fontSize: 9, color: 'var(--text-muted)', paddingBottom: 4, fontWeight: 600 }}>
                {h === 0 ? '12a' : h < 12 ? `${h}a` : h === 12 ? '12p' : `${h-12}p`}
              </div>
            ))}
            {/* Rows */}
            {DAYS_OF_WEEK.map((day, di) => (
              <>
                <div key={`day-${day}`} style={{ fontSize: 10, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', fontWeight: 600 }}>{day}</div>
                {HOURS.map(h => (
                  <div
                    key={`${di}-${h}`}
                    title={`${day} ${h}:00 — ${HEATMAP_DATA[di][h]}% activity`}
                    style={{
                      height: 22,
                      borderRadius: 4,
                      background: getHeatColor(HEATMAP_DATA[di][h]),
                      border: '1px solid rgba(255,255,255,0.04)',
                      cursor: 'default',
                      transition: 'opacity 0.15s',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = '0.7'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                  />
                ))}
              </>
            ))}
          </div>
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 12, fontSize: 10, color: 'var(--text-muted)' }}>
          <span>Less</span>
          {['rgba(99,102,241,0.10)', 'rgba(99,102,241,0.25)', 'rgba(99,102,241,0.45)', 'rgba(99,102,241,0.65)', 'rgba(99,102,241,0.90)'].map((c, i) => (
            <div key={i} style={{ width: 16, height: 16, background: c, borderRadius: 3, border: '1px solid rgba(255,255,255,0.06)' }} />
          ))}
          <span>More</span>
        </div>
      </div>

      {/* Recently Cached Queries */}
      <div className="card" style={{ animation: 'fadeInUp 0.5s ease 0.45s both' }}>
        <div className="section-title">Recently Cached Queries</div>
        <div className="section-subtitle">Newest entries added to the semantic cache</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Query (truncated)</th>
                <th>Similarity</th>
                <th>Hit Count</th>
                <th>Last Accessed</th>
                <th>Time Saved</th>
              </tr>
            </thead>
            <tbody>
              {RECENT_CACHED.map((row, i) => (
                <tr key={i}>
                  <td style={{ maxWidth: 380, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 11, color: 'var(--text-secondary)' }}>
                    {row.query}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="progress-bar" style={{ width: 60, display: 'inline-block' }}>
                        <div className="progress-fill" style={{ width: `${row.similarity * 100}%`, background: row.similarity >= 0.95 ? 'var(--success)' : 'var(--warning)' }} />
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: row.similarity >= 0.95 ? 'var(--success)' : 'var(--warning)' }}>
                        {(row.similarity * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-light)' }}>{row.hits.toLocaleString()}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{row.lastAccessed}</td>
                  <td>
                    <span className="badge badge-success">{row.saved}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
