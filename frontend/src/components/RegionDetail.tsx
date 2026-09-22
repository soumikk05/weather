import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { api } from '../lib/api'
import { useAppContext } from '../context/AppContext'
import { VerdictBadge, RiskPill, EvidenceBar, LoadingSpinner, EmptyState, ErrorBanner } from './UIComponents'
import { fmt, pct, fmtDate } from '../lib/utils'

interface RegionDetailProps {
  region: string
}

export function RegionDetail({ region }: RegionDetailProps) {
  const { today } = useAppContext()
  const [leadDay, setLeadDay] = React.useState(1)

  const { data: forecast, isLoading: fLoading, error: fErr } = useQuery({
    queryKey: ['forecast', region, today?.today],
    queryFn: () => api.regionForecast(region, today?.today),
    enabled: !!region,
    staleTime: 5 * 60 * 1000,
  })

  const { data: history, isLoading: hLoading, error: hErr } = useQuery({
    queryKey: ['history', region, today?.today, leadDay],
    queryFn: () => api.regionHistory(region, 10, today?.today, leadDay),
    enabled: !!region,
    staleTime: 5 * 60 * 1000,
  })

  const { data: summary } = useQuery({
    queryKey: ['history_summary', region, today?.today, leadDay],
    queryFn: () => api.regionHistorySummary(region, 10, today?.today, leadDay),
    enabled: !!region,
    staleTime: 5 * 60 * 1000,
  })

  const forecastChartData = React.useMemo(() => {
    return forecast?.map((f) => ({
      day: `D+${f.lead_day}`,
      lead_day: f.lead_day,
      bust_prob: +(f.bust_probability * 100).toFixed(1),
      confidence: +(f.confidence_score * 100).toFixed(1),
      error_lower: f.error_interval_90_lower ?? 0,
      error_upper: f.error_interval_90_upper ?? 0,
      predicted_error: f.predicted_error_mm,
      risk_tier: f.risk_tier,
    })) ?? []
  }, [forecast])

  if (!region) return <EmptyState message="Select a region on the map or search above." />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem', height: '100%', overflowY: 'auto' }}>
      {/* Region header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-gov-blue-800)', lineHeight: 1.25 }}>
            {region}
          </h2>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
            IMD Meteorological Subdivision · {forecast?.[0]?.terrain?.replace('_', ' ')}
          </div>
        </div>
        {forecast?.[0] && (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <RiskPill tier={forecast[0].risk_tier} />
            <EvidenceBar
              agreement={forecast[0].evidence_agreement}
              contradiction={forecast[0].contradiction_flag}
            />
          </div>
        )}
      </div>

      {/* 10-Day Bust Probability Chart */}
      <div className="card" style={{ padding: '0.875rem' }}>
        <h3 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-surface-700)', marginBottom: '0.5rem' }}>
          10-Day Bust Probability Trajectory
        </h3>
        {fLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem' }}>
            <LoadingSpinner />
          </div>
        ) : fErr ? (
          <ErrorBanner message="Could not load forecast profile." />
        ) : forecastChartData.length === 0 ? (
          <EmptyState message="No forecast profile data." />
        ) : (
          <ResponsiveContainer width="100%" height={140}>
            <AreaChart data={forecastChartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="bustGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#b45309" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#b45309" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-surface-200)" />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 10, fill: 'var(--color-surface-500)' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: 'var(--color-surface-500)' }}
                axisLine={false}
                tickLine={false}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  fontSize: '0.72rem',
                  background: 'var(--color-gov-blue-900)',
                  border: 'none',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-gov-blue-100)',
                }}
                labelStyle={{ fontWeight: 700 }}
                formatter={(val: unknown) => [`${+(val as number)}%`, 'Bust Prob.']}
              />
              <ReferenceLine y={50} stroke="#b45309" strokeDasharray="4 3" strokeWidth={1} />
              <Area
                type="monotone"
                dataKey="bust_prob"
                stroke="#b45309"
                strokeWidth={2}
                fill="url(#bustGrad)"
                dot={{ r: 3, fill: '#b45309', stroke: 'white', strokeWidth: 1 }}
                activeDot={{ r: 4 }}
                name="Bust Prob."
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Lead day picker for history */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--color-surface-600)', fontWeight: 600 }}>
          Verification Lead Day:
        </span>
        {[1, 2, 3, 5, 7, 10].map((d) => (
          <button
            key={d}
            onClick={() => setLeadDay(d)}
            aria-pressed={leadDay === d}
            style={{
              padding: '0.15rem 0.45rem',
              border: '1px solid',
              borderColor: leadDay === d ? 'var(--color-gov-blue-500)' : 'var(--color-surface-300)',
              background: leadDay === d ? 'var(--color-gov-blue-500)' : 'transparent',
              color: leadDay === d ? 'white' : 'var(--color-surface-700)',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: leadDay === d ? 700 : 400,
            }}
          >
            D+{d}
          </button>
        ))}
      </div>

      {/* History summary */}
      {summary && (
        <div className="card" style={{ padding: '0.75rem' }}>
          <p style={{ fontSize: '0.76rem', color: 'var(--color-surface-700)', lineHeight: 1.55 }}>
            {summary.summary_sentence}
          </p>
          <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <Stat label="Bust Rate" value={pct(summary.overall_bust_rate)} />
            <Stat label="Mean MAE" value={`${summary.mean_abs_error.toFixed(2)} mm`} />
            <Stat label="Days analysed" value={String(summary.days)} />
            {(Object.entries(summary.counts_per_calibration_verdict) as [string, number][])
              .filter(([, n]) => n > 0)
              .map(([v, n]) => (
                <div key={v} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <VerdictBadge verdict={v as never} />
                  <span style={{ fontSize: '0.72rem', color: 'var(--color-surface-600)' }}>×{n}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* History table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '0.625rem 0.875rem', borderBottom: '1px solid var(--color-surface-100)' }}>
          <h3 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-surface-700)' }}>
            10-Day Verification History (Lead Day {leadDay})
          </h3>
        </div>
        {hLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '1.5rem' }}>
            <LoadingSpinner />
          </div>
        ) : hErr ? (
          <div style={{ padding: '0.75rem' }}>
            <ErrorBanner message="Could not load history." />
          </div>
        ) : !history || history.length === 0 ? (
          <EmptyState message="No history data for this region / lead day." />
        ) : (
          <table className="data-table" aria-label="Verification history">
            <thead>
              <tr>
                <th>Date</th>
                <th>Fcst Rain</th>
                <th>Obs Rain</th>
                <th>MAE</th>
                <th>Bust</th>
                <th>Verdict</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.date}>
                  <td style={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {fmtDate(h.date)}
                  </td>
                  <td className="tabnum">{fmt(h.forecast_rainfall_mm, 1, ' mm')}</td>
                  <td className="tabnum">{fmt(h.observed_rainfall_mm, 1, ' mm')}</td>
                  <td className="tabnum">{fmt(h.abs_error_mm, 1, ' mm')}</td>
                  <td>
                    {h.was_bust ? (
                      <span style={{ color: 'var(--color-risk-low)', fontWeight: 700, fontSize: '0.72rem' }}>
                        BUST
                      </span>
                    ) : (
                      <span style={{ color: 'var(--color-chakra-600)', fontSize: '0.72rem' }}>—</span>
                    )}
                  </td>
                  <td>
                    <VerdictBadge verdict={h.calibration_verdict} />
                  </td>
                  <td>
                    <EvidenceBar
                      agreement={h.evidence_agreement}
                      contradiction={h.contradiction_flag}
                      compact
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
      <span style={{ fontSize: '0.6rem', color: 'var(--color-surface-500)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
        {label}
      </span>
      <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-gov-blue-800)', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </span>
    </div>
  )
}
