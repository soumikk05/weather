import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { api } from '../lib/api'
import { useAppContext } from '../context/AppContext'
import { LoadingSpinner, EmptyState, ErrorBanner, RiskPill, EvidenceBar } from './UIComponents'
import { fmt, pct } from '../lib/utils'

interface ExplainPanelProps {
  region: string
}

export function ExplainPanel({ region }: ExplainPanelProps) {
  const { today } = useAppContext()
  const [leadDay, setLeadDay] = useState(1)

  const { data, isLoading, error } = useQuery({
    queryKey: ['explain', region, leadDay, today?.today],
    queryFn: () => api.explain(region, leadDay, today?.today),
    enabled: !!region,
    staleTime: 5 * 60 * 1000,
  }) as { data: Record<string, unknown> | undefined; isLoading: boolean; error: unknown }

  const topDrivers = (data?.top_drivers as string[] | undefined) ?? []
  const shapData = topDrivers.map((d, i) => ({ name: `#${i + 1}`, label: d, value: topDrivers.length - i }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h3 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-gov-blue-800)' }}>
          Explanation — {region}
        </h3>
        <div style={{ display: 'flex', gap: '0.375rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.68rem', color: 'var(--color-surface-600)', fontWeight: 600 }}>Lead:</span>
          {[1, 3, 5, 7, 10].map((d) => (
            <button
              key={d}
              onClick={() => setLeadDay(d)}
              aria-pressed={leadDay === d}
              style={{
                padding: '0.1rem 0.35rem',
                border: '1px solid',
                borderColor: leadDay === d ? 'var(--color-gov-blue-500)' : 'var(--color-surface-300)',
                background: leadDay === d ? 'var(--color-gov-blue-500)' : 'transparent',
                color: leadDay === d ? 'white' : 'var(--color-surface-700)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '0.7rem',
              }}
            >
              D+{d}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem' }}>
          <LoadingSpinner />
        </div>
      )}

      {!!error && <ErrorBanner message="Could not load explanation data." />}

      {data && (
        <>
          {/* Confidence metrics */}
          <div style={{ display: 'flex', gap: '0.625rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <RiskPill tier={data.risk_tier as string} />
            <span style={{ fontSize: '0.78rem', color: 'var(--color-surface-600)' }}>
              Confidence: <strong>{pct(data.confidence_score as number)}</strong> ·
              Bust prob: <strong>{pct(data.bust_probability as number)}</strong>
            </span>
            <EvidenceBar
              agreement={data.evidence_agreement as number}
              contradiction={data.contradiction_flag as boolean}
            />
          </div>

          {/* Synoptic regime */}
          {data.synoptic_regime && (
            <div style={{ fontSize: '0.75rem', color: 'var(--color-surface-700)' }}>
              Synoptic regime:{' '}
              <strong style={{ textTransform: 'capitalize' }}>
                {(data.synoptic_regime as string).replace(/_/g, ' ')}
              </strong>
            </div>
          )}

          {/* Top drivers bar chart */}
          {topDrivers.length > 0 && (
            <div>
              <h4 style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-surface-500)', marginBottom: '0.375rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                SHAP Feature Importance (Top {topDrivers.length})
              </h4>
              <ResponsiveContainer width="100%" height={topDrivers.length * 28 + 16}>
                <BarChart
                  layout="vertical"
                  data={shapData}
                  margin={{ top: 0, right: 8, bottom: 0, left: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-100)" horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 10, fill: 'var(--color-surface-600)' }}
                    axisLine={false}
                    tickLine={false}
                    width={28}
                  />
                  <Tooltip
                    content={({ payload }) => {
                      if (!payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div style={{ background: 'var(--color-gov-blue-900)', color: 'var(--color-gov-blue-100)', padding: '0.375rem 0.625rem', borderRadius: 'var(--radius-sm)', fontSize: '0.7rem', maxWidth: 240 }}>
                          {d.label}
                        </div>
                      )
                    }}
                  />
                  <Bar
                    dataKey="value"
                    fill="var(--color-gov-blue-400)"
                    radius={[0, 3, 3, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
              <ul style={{ listStyle: 'none', padding: 0, marginTop: '0.375rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                {topDrivers.map((d, i) => (
                  <li key={i} style={{ fontSize: '0.72rem', color: 'var(--color-surface-700)', display: 'flex', gap: '0.375rem' }}>
                    <span style={{ color: 'var(--color-saffron-500)', fontWeight: 700, flexShrink: 0, minWidth: 20 }}>#{i + 1}</span>
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Operational bulletin */}
          {data.operational_bulletin && (
            <div
              style={{
                padding: '0.75rem',
                background: 'var(--color-gov-blue-50)',
                border: '1px solid var(--color-gov-blue-200)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <h4 style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-gov-blue-700)', marginBottom: '0.375rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                Duty Forecaster Bulletin
              </h4>
              {Object.entries(data.operational_bulletin as Record<string, string>).map(([k, v]) => (
                <div key={k} style={{ marginBottom: '0.25rem' }}>
                  <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-surface-500)', fontWeight: 700 }}>
                    {k.replace(/_/g, ' ')}:{' '}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-surface-800)' }}>{v}</span>
                </div>
              ))}
            </div>
          )}

          {/* Plain language summary */}
          {data.plain_language_summary && (
            <div style={{ fontSize: '0.76rem', color: 'var(--color-surface-700)', lineHeight: 1.55, padding: '0.625rem', background: 'var(--color-surface-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-surface-200)' }}>
              {data.plain_language_summary as string}
            </div>
          )}
        </>
      )}
    </div>
  )
}
