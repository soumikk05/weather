import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { api, type DayDetail } from '../lib/api'
import { VerdictBadge, RiskPill, EvidenceBar, LoadingSpinner, EmptyState, ErrorBanner } from './UIComponents'
import { fmt, pct, fmtDate, advisoryColor, advisoryBg, era5Label } from '../lib/utils'
import { useAppContext } from '../context/AppContext'

interface DayDetailModalProps {
  region: string
  date: string
  leadDay: number
  onClose: () => void
}

export function DayDetailModal({ region, date, leadDay, onClose }: DayDetailModalProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['day_detail', region, date, leadDay],
    queryFn: () => api.dayDetail(region, date, leadDay),
    staleTime: 5 * 60 * 1000,
  })

  // Close on Escape
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={`Day detail: ${region} — ${fmtDate(date)}`}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="card animate-fade-in"
        style={{
          maxWidth: 720,
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {/* Modal header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-gov-blue-800)' }}>
              {region} — {fmtDate(date)}
            </h2>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
              Lead Day {leadDay} · Daily Verification Record
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close detail"
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-surface-500)', fontSize: '1.2rem', lineHeight: 1, padding: '0.25rem' }}
          >
            ✕
          </button>
        </div>

        {isLoading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
            <LoadingSpinner />
          </div>
        )}

        {error && (
          <ErrorBanner message="Could not load daily detail. Check backend availability." />
        )}

        {data && <DayDetailContent data={data} />}
      </div>
    </div>
  )
}

function DayDetailContent({ data }: { data: DayDetail }) {
  const bullAdvisoryKey = data.operational_bulletin
    ? Object.keys(data.operational_bulletin).find((k) => k.toLowerCase().includes('advisory'))
    : undefined
  const bulletinLevel = bullAdvisoryKey ? data.operational_bulletin![bullAdvisoryKey] : null

  // Diurnal chart data
  const chartData = data.illustrative_hourly_curve.map((h) => ({
    hour: h.time_utc,
    temp: +h.temp_c.toFixed(1),
    rain: +h.rainfall_mm.toFixed(2),
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
      {/* Status row */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <RiskPill tier={data.risk_tier} />
        <EvidenceBar agreement={data.evidence_agreement} contradiction={data.contradiction_flag} />
        {data.was_bust !== null && (
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '0.15rem 0.5rem',
              borderRadius: 99,
              background: data.was_bust ? '#fff1f2' : '#f0fdf4',
              color: data.was_bust ? 'var(--color-risk-low)' : 'var(--color-chakra-600)',
              border: `1px solid ${data.was_bust ? '#fda4af' : '#86efac'}`,
            }}
          >
            {data.was_bust ? '⚡ BUST VERIFIED' : '✓ No Bust'}
          </span>
        )}
      </div>

      {/* Confidence + Error metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
          gap: '0.5rem',
        }}
      >
        {[
          { label: 'Confidence', value: pct(data.confidence_score), highlight: true },
          { label: 'Bust Prob.', value: pct(data.bust_probability) },
          { label: 'Pred. Error', value: fmt(data.predicted_error_mm, 2, ' mm') },
          { label: '90% CI', value: data.conformal_interval_mm ? `[${data.conformal_interval_mm[0].toFixed(1)}, ${data.conformal_interval_mm[1].toFixed(1)}] mm` : '—' },
          { label: 'Fcst Rain', value: fmt(data.forecast_rainfall_mm, 1, ' mm') },
          { label: 'Obs Rain', value: fmt(data.observed_rainfall_mm, 1, ' mm') },
          { label: 'MAE', value: fmt(data.abs_error_mm, 2, ' mm') },
          { label: 'Bust Thresh.', value: fmt(data.bust_threshold_mm, 2, ' mm') },
        ].map(({ label, value, highlight }) => (
          <div
            key={label}
            style={{
              padding: '0.5rem 0.625rem',
              background: highlight ? 'var(--color-gov-blue-50)' : 'var(--color-surface-50)',
              border: `1px solid ${highlight ? 'var(--color-gov-blue-200)' : 'var(--color-surface-200)'}`,
              borderRadius: 'var(--radius-md)',
            }}
          >
            <div style={{ fontSize: '0.62rem', color: 'var(--color-surface-500)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              {label}
            </div>
            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-gov-blue-800)', fontVariantNumeric: 'tabular-nums' }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Operational bulletin */}
      {data.operational_bulletin && (
        <div
          style={{
            padding: '0.75rem',
            border: '1px solid',
            borderRadius: 'var(--radius-md)',
            borderColor: bulletinLevel
              ? (bulletinLevel.toUpperCase().startsWith('RED') ? '#fda4af' :
                 bulletinLevel.toUpperCase().startsWith('AMBER') ? '#fcd34d' : '#86efac')
              : 'var(--color-surface-200)',
            background: bulletinLevel
              ? (bulletinLevel.toUpperCase().startsWith('RED') ? '#fff1f2' :
                 bulletinLevel.toUpperCase().startsWith('AMBER') ? '#fffbeb' : '#f0fdf4')
              : 'var(--color-surface-50)',
          }}
        >
          {Object.entries(data.operational_bulletin).map(([k, v]) => (
            <div key={k} style={{ marginBottom: '0.25rem' }}>
              <span style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--color-surface-500)', fontWeight: 700 }}>
                {k.replace(/_/g, ' ')}:{' '}
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--color-surface-800)' }}>{v}</span>
            </div>
          ))}
        </div>
      )}

      {/* Plain language summary */}
      <div style={{ fontSize: '0.78rem', color: 'var(--color-surface-700)', lineHeight: 1.55, padding: '0.625rem', background: 'var(--color-surface-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-surface-200)' }}>
        {data.plain_language_summary}
      </div>

      {/* ERA5 diagnostics */}
      {data.era5_diagnostics && Object.keys(data.era5_diagnostics).length > 0 && (
        <div>
          <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-surface-600)', marginBottom: '0.375rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            ERA5 Diagnostics
          </h4>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {Object.entries(data.era5_diagnostics).map(([k, v]) => (
              <div
                key={k}
                style={{
                  padding: '0.375rem 0.625rem',
                  background: 'var(--color-surface-50)',
                  border: '1px solid var(--color-surface-200)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <div style={{ fontSize: '0.6rem', color: 'var(--color-surface-500)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {era5Label(k)}
                </div>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-surface-800)', fontVariantNumeric: 'tabular-nums' }}>
                  {v != null ? v.toFixed(2) : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SHAP drivers */}
      {data.top_drivers.length > 0 && (
        <div>
          <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-surface-600)', marginBottom: '0.375rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Top Bust Drivers (SHAP)
          </h4>
          <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            {data.top_drivers.slice(0, 5).map((d, i) => (
              <li key={i} style={{ fontSize: '0.76rem', color: 'var(--color-surface-700)', display: 'flex', gap: '0.375rem' }}>
                <span style={{ color: 'var(--color-saffron-500)', fontWeight: 700, flexShrink: 0 }}>#{i + 1}</span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Illustrative diurnal chart */}
      {chartData.length > 0 && (
        <div className="illustrative-chart-wrapper">
          <h4 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-surface-600)', marginBottom: '0.375rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Diurnal Temperature Curve
          </h4>
          <div
            style={{
              padding: '0.5rem',
              border: '2px dashed var(--color-saffron-400)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-saffron-100)',
            }}
          >
            <p style={{ fontSize: '0.68rem', color: 'var(--color-saffron-600)', marginBottom: '0.5rem', fontWeight: 600 }}>
              ⚠ The curve below is a SYNTHETIC DIURNAL INTERPOLATION. It is NOT observed or forecast hourly data.{' '}
              {data.illustrative_note}
            </p>
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={chartData} margin={{ top: 0, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-200)" />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 9, fill: 'var(--color-surface-500)' }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis
                  yAxisId="temp"
                  tick={{ fontSize: 9, fill: 'var(--color-surface-500)' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ fontSize: '0.68rem' }}
                  formatter={(val: unknown, name: unknown) => [
                    name === 'temp' ? `${val}°C` : `${val} mm`,
                    name === 'temp' ? 'Temp.' : 'Rain',
                  ]}
                />
                <Line
                  yAxisId="temp"
                  dataKey="temp"
                  stroke="#b45309"
                  strokeWidth={1.5}
                  dot={false}
                  name="temp"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Granularity note */}
      <p style={{ fontSize: '0.68rem', color: 'var(--color-surface-500)', lineHeight: 1.5, marginTop: '-0.25rem' }}>
        <strong>Granularity note:</strong> {data.note}
      </p>
    </div>
  )
}
