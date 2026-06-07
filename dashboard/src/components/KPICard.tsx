'use client';

import { useEffect, useState, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string;
  rawValue?: number;
  change: number;
  changeLabel?: string;
  icon: React.ReactNode;
  color: string;
  colorDim: string;
  trend?: 'up' | 'down' | 'neutral';
  /** If true, "up" is bad (e.g., error rate) */
  invertTrend?: boolean;
  animationDelay?: number;
}

function useCountUp(target: number, duration: number = 1200, started: boolean = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!started) return;
    let start: number | null = null;
    const step = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.floor(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, started]);
  return value;
}

export default function KPICard({
  title,
  value,
  rawValue,
  change,
  changeLabel,
  icon,
  color,
  colorDim,
  trend = 'up',
  invertTrend = false,
  animationDelay = 0,
}: KPICardProps) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.1 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  // Determine trend color
  const isPositive = invertTrend ? trend === 'down' : trend === 'up';
  const trendColor = isPositive ? 'var(--success)' : trend === 'neutral' ? 'var(--text-muted)' : 'var(--danger)';
  const trendBg = isPositive ? 'var(--success-dim)' : trend === 'neutral' ? 'rgba(255,255,255,0.05)' : 'var(--danger-dim)';

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <div
      ref={ref}
      className="card"
      style={{
        animationDelay: `${animationDelay}ms`,
        animation: `fadeInUp 0.5s ease ${animationDelay}ms both`,
      }}
    >
      {/* Gradient background accent */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 120,
          height: 120,
          borderRadius: '0 16px 0 100%',
          background: `radial-gradient(circle at top right, ${colorDim}, transparent 70%)`,
          pointerEvents: 'none',
        }}
      />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.01em' }}>
          {title}
        </span>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: colorDim,
            border: `1px solid ${color}30`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color,
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
      </div>

      {/* Value */}
      <div
        style={{
          fontSize: 30,
          fontWeight: 800,
          color: 'var(--text-primary)',
          letterSpacing: '-1px',
          lineHeight: 1,
          marginBottom: 12,
          animation: visible ? 'countUp 0.4s ease both' : 'none',
          animationDelay: `${animationDelay + 200}ms`,
        }}
      >
        {value}
      </div>

      {/* Change badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 8px',
            background: trendBg,
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 600,
            color: trendColor,
          }}
        >
          <TrendIcon size={11} strokeWidth={2.5} />
          {change > 0 ? '+' : ''}{change}%
        </div>
        {changeLabel && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{changeLabel}</span>
        )}
      </div>
    </div>
  );
}
