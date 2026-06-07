'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Database,
  GitBranch,
  Users,
  ScrollText,
  Settings,
  Zap,
  ChevronRight,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview',       href: '/',        icon: LayoutDashboard },
  { label: 'Cache Analytics', href: '/cache',   icon: Database,    badge: 'Live' },
  { label: 'Model Routing',  href: '/models',  icon: GitBranch },
  { label: 'Teams',          href: '/teams',   icon: Users },
  { label: 'Audit Log',      href: '/audit',   icon: ScrollText },
  { label: 'Settings',       href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: 'var(--sidebar-width)',
        height: '100vh',
        background: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        overflow: 'hidden',
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: '28px 20px 24px',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #6366F1, #4F46E5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 14,
              fontWeight: 800,
              color: '#fff',
              flexShrink: 0,
              boxShadow: '0 4px 14px rgba(99,102,241,0.4)',
            }}
          >
            TS
          </div>
          <div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                background: 'linear-gradient(135deg, #818CF8, #6366F1)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                lineHeight: 1.2,
              }}
            >
              TokenSaver
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 500, letterSpacing: '0.05em' }}>
              ENTERPRISE
            </div>
          </div>
        </div>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            padding: '3px 8px',
            background: 'var(--accent-dim)',
            border: '1px solid var(--border-accent)',
            borderRadius: 999,
            fontSize: 10,
            color: 'var(--accent-light)',
            fontWeight: 600,
          }}
        >
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--success)', display: 'inline-block', boxShadow: '0 0 5px var(--success)' }} />
          v1.0.0 · All systems normal
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '16px 12px', overflowY: 'auto' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.12em', padding: '0 8px', marginBottom: 8 }}>
          NAVIGATION
        </div>
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 12px',
                    borderRadius: 10,
                    textDecoration: 'none',
                    fontSize: 13.5,
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? '#fff' : 'var(--text-secondary)',
                    background: isActive
                      ? 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(79,70,229,0.15))'
                      : 'transparent',
                    borderLeft: isActive
                      ? '2px solid var(--accent)'
                      : '2px solid transparent',
                    transition: 'all 0.18s ease',
                    position: 'relative',
                  }}
                  onMouseEnter={e => {
                    if (!isActive) {
                      (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
                      (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                      (e.currentTarget as HTMLElement).style.transform = 'translateX(2px)';
                    }
                  }}
                  onMouseLeave={e => {
                    if (!isActive) {
                      (e.currentTarget as HTMLElement).style.background = 'transparent';
                      (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                      (e.currentTarget as HTMLElement).style.transform = 'translateX(0)';
                    }
                  }}
                >
                  <Icon
                    size={16}
                    strokeWidth={isActive ? 2.5 : 2}
                  />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {item.badge && (
                    <span
                      style={{
                        fontSize: 9,
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: 999,
                        background: 'var(--success-dim)',
                        color: 'var(--success)',
                        border: '1px solid rgba(16,185,129,0.2)',
                        letterSpacing: '0.05em',
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                  {isActive && (
                    <ChevronRight size={12} style={{ opacity: 0.5 }} />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom section */}
      <div style={{ padding: '16px 12px', borderTop: '1px solid var(--border)' }}>
        {/* Plan badge */}
        <div
          style={{
            padding: '10px 12px',
            background: 'var(--accent-dim)',
            border: '1px solid var(--border-accent)',
            borderRadius: 10,
            marginBottom: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <Sparkles size={12} color="var(--accent-light)" />
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-light)', letterSpacing: '0.05em' }}>
              ENTERPRISE EDITION
            </span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Unlimited seats · Priority support
          </div>
        </div>

        {/* Upgrade CTA */}
        <button
          className="btn-primary"
          style={{ width: '100%', justifyContent: 'center', fontSize: 12 }}
        >
          <Zap size={13} />
          Upgrade to Strategic
        </button>
      </div>
    </aside>
  );
}
