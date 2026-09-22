import React from 'react'
import { VERDICT_CONFIG, RISK_TIER_CONFIG } from '../lib/utils'
import type { CalibrationVerdict as VerdictType } from '../lib/api'

// ── VerdictBadge ─────────────────────────────────────────────────────────

interface VerdictBadgeProps {
  verdict: VerdictType
  expanded?: boolean
}

export function VerdictBadge({ verdict, expanded = false }: VerdictBadgeProps) {
  const cfg = VERDICT_CONFIG[verdict]
  if (!cfg) return <span className="verdict-badge" style={{ color: 'var(--color-surface-500)' }}>{verdict}</span>

  return (
    <div>
      <span
        className="verdict-badge"
        title={expanded ? undefined : cfg.explanation}
        style={{
          color: cfg.colorClass.replace('text-', '').replace('[', '').replace(']', ''),
          // Use inline style since Tailwind v4 arbitrary values
          backgroundColor: verdict === 'confident_correct' ? '#eff6ff' :
                           verdict === 'confident_but_busted' ? '#fffbeb' :
                           verdict === 'flagged_risky_and_busted' ? '#f0fdf4' :
                           '#f5f3ff',
          border: `1px solid currentColor`,
          opacity: 0.95,
        }}
      >
        <span aria-hidden="true">{cfg.icon}</span>
        {cfg.shortLabel}
      </span>
      {expanded && (
        <p style={{ fontSize: '0.72rem', color: 'var(--color-surface-600)', marginTop: '0.375rem', lineHeight: 1.5 }}>
          {cfg.explanation}
        </p>
      )}
    </div>
  )
}

// ── RiskPill ──────────────────────────────────────────────────────────────

interface RiskPillProps {
  tier: string
}

export function RiskPill({ tier }: RiskPillProps) {
  const cfg = RISK_TIER_CONFIG[tier] ?? {
    color: 'text-gray-600',
    bg: 'bg-gray-100',
    label: tier.toUpperCase(),
  }
  const bgColor = tier === 'High Confidence'
    ? '#eff6ff'
    : tier === 'Moderate Confidence'
    ? '#fffbeb'
    : '#fff1f2'
  const color = tier === 'High Confidence'
    ? 'var(--color-risk-high)'
    : tier === 'Moderate Confidence'
    ? 'var(--color-risk-mod)'
    : 'var(--color-risk-low)'

  return (
    <span
      className="risk-pill"
      style={{ background: bgColor, color }}
    >
      {cfg.label}
    </span>
  )
}

// ── EvidenceBar ───────────────────────────────────────────────────────────

interface EvidenceBarProps {
  agreement: number
  contradiction: boolean
  compact?: boolean
}

export function EvidenceBar({ agreement, contradiction, compact = false }: EvidenceBarProps) {
  const pct = Math.round(agreement * 100)
  return (
    <div
      title={`Evidence agreement: ${pct}%${contradiction ? ' — Contradiction detected: opposing dynamical forces' : ''}`}
      style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'help' }}
    >
      {!compact && (
        <span style={{ fontSize: '0.68rem', color: 'var(--color-surface-500)', whiteSpace: 'nowrap' }}>
          Agreement
        </span>
      )}
      <div
        style={{
          width: compact ? 36 : 52,
          height: 4,
          background: 'var(--color-surface-200)',
          borderRadius: 2,
          overflow: 'hidden',
        }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Evidence agreement ${pct}%`}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: agreement >= 0.75
              ? 'var(--color-chakra-500)'
              : agreement >= 0.55
              ? 'var(--color-saffron-400)'
              : 'var(--color-risk-low)',
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <span style={{ fontSize: '0.68rem', color: 'var(--color-surface-600)', fontVariantNumeric: 'tabular-nums' }}>
        {pct}%
      </span>
      {contradiction && (
        <span
          title="Contradiction: opposing dynamical forces"
          style={{ fontSize: '0.68rem', color: 'var(--color-saffron-500)', fontWeight: 700 }}
          aria-label="Contradiction flag"
        >
          ⚡
        </span>
      )}
    </div>
  )
}

// ── LoadingSpinner ────────────────────────────────────────────────────────

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Loading"
      style={{ animation: 'spin 0.8s linear infinite' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle
        cx="12" cy="12" r="10"
        stroke="var(--color-gov-blue-200)"
        strokeWidth="3"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="var(--color-gov-blue-500)"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  )
}

// ── EmptyState ────────────────────────────────────────────────────────────

export function EmptyState({ message }: { message: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2.5rem 1rem',
        color: 'var(--color-surface-500)',
        textAlign: 'center',
        gap: '0.5rem',
      }}
    >
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" />
        <path d="M16 10v7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <circle cx="16" cy="21" r="1.5" fill="currentColor" />
      </svg>
      <span style={{ fontSize: '0.82rem', fontWeight: 500 }}>{message}</span>
    </div>
  )
}

// ── ErrorBanner ────────────────────────────────────────────────────────────

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      style={{
        padding: '0.625rem 0.875rem',
        background: '#fff1f2',
        border: '1px solid #fda4af',
        borderRadius: 'var(--radius-md)',
        fontSize: '0.78rem',
        color: '#be123c',
        display: 'flex',
        gap: '0.5rem',
        alignItems: 'flex-start',
      }}
    >
      <span aria-hidden="true" style={{ flexShrink: 0, marginTop: '0.05rem' }}>⚠</span>
      <span>{message}</span>
    </div>
  )
}
