import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext'
import { DataSourcesPanel } from './DataSourcesPanel'
import { fmtDate } from '../lib/utils'

export function Header() {
  const { today } = useAppContext()
  const [dsOpen, setDsOpen] = useState(false)

  return (
    <>
      <header
        role="banner"
        style={{
          background: 'var(--color-gov-blue-900)',
          borderBottom: '1px solid var(--color-gov-blue-700)',
          padding: '0 1.25rem',
          height: 52,
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          flexShrink: 0,
        }}
      >
        {/* Emblem / wordmark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexShrink: 0 }}>
          {/* Stylised Ashoka-chakra-adjacent emblem */}
          <svg
            aria-hidden="true"
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
          >
            <circle cx="14" cy="14" r="12" stroke="#5e8fdb" strokeWidth="1.5" />
            <circle cx="14" cy="14" r="4" fill="#3369c4" />
            {/* 24 spokes like Ashoka Chakra (simplified to 12 for clarity) */}
            {Array.from({ length: 12 }).map((_, i) => {
              const angle = (i * 30 * Math.PI) / 180
              const x1 = 14 + 5 * Math.cos(angle)
              const y1 = 14 + 5 * Math.sin(angle)
              const x2 = 14 + 10 * Math.cos(angle)
              const y2 = 14 + 10 * Math.sin(angle)
              return (
                <line
                  key={i}
                  x1={x1} y1={y1} x2={x2} y2={y2}
                  stroke="#3369c4"
                  strokeWidth="1"
                />
              )
            })}
          </svg>
          <div>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#d4e3f7', letterSpacing: '0.01em', lineHeight: 1.2 }}>
              NCMRWF · MoES
            </div>
            <div style={{ fontSize: '0.68rem', color: '#5e8fdb', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Forecast Reliability Engine
            </div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 28, background: 'var(--color-gov-blue-700)', flexShrink: 0 }} />

        {/* System name */}
        <div style={{ fontSize: '0.78rem', color: 'var(--color-gov-blue-200)', flexShrink: 0 }}>
          Bust Detection & Confidence Mapping — Day 1–10
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Replay/Synthetic mode badge */}
        {today?.is_synthetic_or_replay && (
          <div
            title={today.note}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              background: 'rgba(217, 119, 6, 0.18)',
              border: '1px solid rgba(217, 119, 6, 0.45)',
              borderRadius: 99,
              padding: '0.2rem 0.625rem',
              fontSize: '0.68rem',
              fontWeight: 700,
              color: 'var(--color-saffron-400)',
              letterSpacing: '0.04em',
              flexShrink: 0,
              cursor: 'help',
            }}
            aria-label={`Replay mode: data through ${today.latest_date}`}
          >
            <span aria-hidden="true">▶</span>
            Replay Mode &nbsp;·&nbsp; Data through{' '}
            {today.latest_date ? fmtDate(today.latest_date) : '…'}
          </div>
        )}

        {/* Data Sources button */}
        <button
          onClick={() => setDsOpen(true)}
          aria-label="Open data sources panel"
          style={{
            background: 'none',
            border: '1px solid var(--color-gov-blue-600)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--color-gov-blue-300)',
            fontSize: '0.72rem',
            fontWeight: 600,
            padding: '0.25rem 0.625rem',
            cursor: 'pointer',
            letterSpacing: '0.03em',
            flexShrink: 0,
          }}
        >
          Data Sources
        </button>

        {/* Disabled login placeholder */}
        <button
          disabled
          aria-label="Forecaster login — coming soon"
          title="Forecaster login — coming soon"
          style={{
            background: 'none',
            border: '1px solid var(--color-gov-blue-700)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--color-gov-blue-600)',
            fontSize: '0.72rem',
            fontWeight: 600,
            padding: '0.25rem 0.625rem',
            cursor: 'not-allowed',
            letterSpacing: '0.03em',
            flexShrink: 0,
            opacity: 0.6,
          }}
        >
          Forecaster Login
        </button>
      </header>

      <DataSourcesPanel open={dsOpen} onClose={() => setDsOpen(false)} />
    </>
  )
}
