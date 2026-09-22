import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext'
import { api } from '../lib/api'
import { LoadingSpinner, ErrorBanner } from './UIComponents'
import { pct, fmt } from '../lib/utils'

const SYNOPTIC_REGIMES = [
  'quiescent_clear',
  'monsoon_trough',
  'cyclonic_disturbance',
  'western_disturbance',
  'pre_monsoon_convective',
  'dry_continental',
]

const TERRAIN_TYPES = [
  { value: 'Northern_Plains', label: 'Northern Plains' },
  { value: 'Himalayan', label: 'Himalayan' },
  { value: 'Western_Ghats', label: 'Western Ghats' },
  { value: 'Eastern_Ghats', label: 'Eastern Ghats' },
  { value: 'Coastal_Peninsula', label: 'Coastal Peninsula' },
  { value: 'Deccan_Plateau', label: 'Deccan Plateau' },
  { value: 'Northeast', label: 'Northeast' },
  { value: 'Andaman_Nicobar', label: 'Andaman & Nicobar' },
]

const REGIONS_SUBSET = [
  'Jammu & Kashmir and Ladakh',
  'Haryana, Chandigarh & Delhi',
  'Uttar Pradesh',
  'Bihar',
  'West Bengal & Sikkim',
  'Odisha',
  'Gangetic West Bengal',
  'Jharkhand',
  'Chhattisgarh',
  'Vidarbha',
  'Konkan & Goa',
  'Madhya Maharashtra',
  'Marathwada',
  'Gujarat Region',
  'Saurashtra & Kutch',
  'Rajasthan',
  'Punjab',
  'Himachal Pradesh',
  'Uttarakhand',
  'Sub-Himalayan West Bengal & Sikkim',
  'Assam & Meghalaya',
  'Nagaland, Manipur, Mizoram & Tripura',
  'Arunachal Pradesh',
  'Coastal Andhra Pradesh',
  'Rayalaseema',
  'Tamil Nadu, Puducherry & Karaikal',
  'South Interior Karnataka',
  'North Interior Karnataka',
  'Coastal Karnataka',
  'Kerala & Mahe',
  'Lakshadweep',
  'Andaman & Nicobar Islands',
]

interface WhatIfLabProps {
  initialRegion?: string
}

interface PredictResponse {
  bust_probability: number
  predicted_error_mm: number
  error_interval_90_lower: number | null
  error_interval_90_upper: number | null
  conformal_interval_mm: [number, number] | null
  confidence_score: number
  risk_tier: string
  evidence_agreement: number
  contradiction_flag: boolean
  plain_language_summary: string
  operational_bulletin: Record<string, string> | null
}

const defaultForm = {
  lead_day: 1,
  region: 'Konkan & Goa',
  terrain: 'Western_Ghats',
  terrain_difficulty: 0.78,
  synoptic_regime: 'quiescent_clear',
  fcst_rainfall_mm: 10.0,
  ens_spread_rainfall: 4.5,
  ens_spread_mslp: 1.2,
  fcst_mslp_hpa: 1010.0,
  vertical_wind_shear: 8.0,
  fcst_rh_700_pct: 65.0,
  fcst_cape_jkg: 500.0,
  recent_error_mae_30d: 5.0,
}

export function WhatIfLab({ initialRegion }: WhatIfLabProps) {
  const [form, setForm] = useState({ ...defaultForm, region: initialRegion || defaultForm.region })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const setField = <K extends keyof typeof form>(key: K, val: typeof form[K]) => {
    setForm((f) => ({ ...f, [key]: val }))
    setResult(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.detail?.[0]?.msg ?? `HTTP ${res.status}`)
      }
      setResult(await res.json())
    } catch (err: unknown) {
      setError((err as Error).message ?? 'Prediction failed.')
    } finally {
      setLoading(false)
    }
  }

  const riskColor = result
    ? result.risk_tier === 'High Confidence'
      ? '#0369a1'
      : result.risk_tier === 'Moderate Confidence'
      ? '#b45309'
      : '#9f1239'
    : undefined

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
      <div>
        <h3 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-gov-blue-800)' }}>
          What-If Synoptic Scenario Lab
        </h3>
        <p style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
          Adjust synoptic parameters and evaluate real-time calibrated bust probability via{' '}
          <code style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.68rem' }}>POST /predict</code>.
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
        {/* Grid of sliders + inputs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.5rem' }}>
          {/* Region */}
          <FormField label="Region">
            <select
              value={form.region}
              onChange={(e) => setField('region', e.target.value)}
              aria-label="Select region"
              style={selectStyle}
            >
              {REGIONS_SUBSET.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </FormField>

          {/* Lead day */}
          <FormField label="Lead Day">
            <input
              type="number"
              min={1}
              max={10}
              value={form.lead_day}
              onChange={(e) => setField('lead_day', +e.target.value)}
              aria-label="Lead day"
              style={inputStyle}
            />
          </FormField>

          {/* Terrain */}
          <FormField label="Terrain">
            <select
              value={form.terrain}
              onChange={(e) => setField('terrain', e.target.value)}
              aria-label="Select terrain"
              style={selectStyle}
            >
              {TERRAIN_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </FormField>

          {/* Terrain difficulty */}
          <FormField label={`Terrain Difficulty: ${form.terrain_difficulty.toFixed(2)}`}>
            <input
              type="range" min={0} max={1} step={0.01}
              value={form.terrain_difficulty}
              onChange={(e) => setField('terrain_difficulty', +e.target.value)}
              aria-label="Terrain difficulty"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* Synoptic regime */}
          <FormField label="Synoptic Regime">
            <select
              value={form.synoptic_regime}
              onChange={(e) => setField('synoptic_regime', e.target.value)}
              aria-label="Synoptic regime"
              style={selectStyle}
            >
              {SYNOPTIC_REGIMES.map((r) => (
                <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </FormField>

          {/* Forecast rainfall */}
          <FormField label={`Fcst Rainfall: ${fmt(form.fcst_rainfall_mm, 1, ' mm')}`}>
            <input type="range" min={0} max={200} step={0.5}
              value={form.fcst_rainfall_mm}
              onChange={(e) => setField('fcst_rainfall_mm', +e.target.value)}
              aria-label="Forecast rainfall mm"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* Ensemble spread rainfall */}
          <FormField label={`Ens Spread Rain: ${fmt(form.ens_spread_rainfall, 1, ' mm')}`}>
            <input type="range" min={0} max={40} step={0.5}
              value={form.ens_spread_rainfall}
              onChange={(e) => setField('ens_spread_rainfall', +e.target.value)}
              aria-label="Ensemble spread rainfall"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* MSLP */}
          <FormField label={`MSLP: ${fmt(form.fcst_mslp_hpa, 1, ' hPa')}`}>
            <input type="range" min={970} max={1025} step={0.5}
              value={form.fcst_mslp_hpa}
              onChange={(e) => setField('fcst_mslp_hpa', +e.target.value)}
              aria-label="Forecast MSLP hPa"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* Vertical wind shear */}
          <FormField label={`Wind Shear: ${fmt(form.vertical_wind_shear, 1, ' m/s')}`}>
            <input type="range" min={0} max={40} step={0.5}
              value={form.vertical_wind_shear}
              onChange={(e) => setField('vertical_wind_shear', +e.target.value)}
              aria-label="Vertical wind shear m/s"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* RH 700 hPa */}
          <FormField label={`RH 700 hPa: ${fmt(form.fcst_rh_700_pct, 0, '%')}`}>
            <input type="range" min={0} max={100} step={1}
              value={form.fcst_rh_700_pct}
              onChange={(e) => setField('fcst_rh_700_pct', +e.target.value)}
              aria-label="Forecast RH 700 hPa"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* CAPE */}
          <FormField label={`CAPE: ${fmt(form.fcst_cape_jkg, 0, ' J/kg')}`}>
            <input type="range" min={0} max={4000} step={50}
              value={form.fcst_cape_jkg}
              onChange={(e) => setField('fcst_cape_jkg', +e.target.value)}
              aria-label="Forecast CAPE J/kg"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>

          {/* Recent MAE 30d */}
          <FormField label={`Recent MAE 30d: ${fmt(form.recent_error_mae_30d, 1, ' mm')}`}>
            <input type="range" min={0} max={30} step={0.5}
              value={form.recent_error_mae_30d}
              onChange={(e) => setField('recent_error_mae_30d', +e.target.value)}
              aria-label="Recent error MAE 30d mm"
              style={{ width: '100%', accentColor: 'var(--color-gov-blue-500)' }}
            />
          </FormField>
        </div>

        <button
          type="submit"
          disabled={loading}
          id="whatif-submit-btn"
          style={{
            alignSelf: 'flex-start',
            padding: '0.5rem 1.25rem',
            background: loading ? 'var(--color-surface-300)' : 'var(--color-gov-blue-600)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '0.82rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {loading && <LoadingSpinner size={16} />}
          {loading ? 'Evaluating…' : 'Evaluate Scenario →'}
        </button>
      </form>

      {error && <ErrorBanner message={error} />}

      {result && (
        <div
          className="card animate-fade-in"
          style={{
            border: `2px solid ${riskColor}`,
            background: result.risk_tier === 'Low Confidence - Bust Risk' ? '#fff1f2' : 'var(--color-surface-0)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: riskColor, fontVariantNumeric: 'tabular-nums' }}>
              {pct(result.bust_probability)}
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: riskColor }}>{result.risk_tier}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--color-surface-500)' }}>Bust Probability</div>
            </div>
            <div style={{ flex: 1 }} />
            <div style={{ fontSize: '0.78rem', color: 'var(--color-surface-600)' }}>
              Confidence: <strong>{pct(result.confidence_score)}</strong>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--color-surface-600)' }}>
              Pred. Error: <strong>{fmt(result.predicted_error_mm, 2, ' mm')}</strong>
            </div>
          </div>

          {result.conformal_interval_mm && (
            <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-600)', marginBottom: '0.5rem' }}>
              90% CI: [{result.conformal_interval_mm[0].toFixed(1)}, {result.conformal_interval_mm[1].toFixed(1)}] mm
            </div>
          )}

          <p style={{ fontSize: '0.76rem', color: 'var(--color-surface-700)', lineHeight: 1.55 }}>
            {result.plain_language_summary}
          </p>

          {result.operational_bulletin && (
            <div style={{ marginTop: '0.625rem', padding: '0.625rem', background: 'rgba(0,0,0,0.04)', borderRadius: 'var(--radius-sm)' }}>
              {Object.entries(result.operational_bulletin).map(([k, v]) => (
                <div key={k} style={{ fontSize: '0.72rem', marginBottom: '0.2rem' }}>
                  <span style={{ fontWeight: 700, color: 'var(--color-surface-600)', textTransform: 'uppercase', letterSpacing: '0.04em', fontSize: '0.62rem' }}>
                    {k.replace(/_/g, ' ')}:{' '}
                  </span>
                  <span style={{ color: 'var(--color-surface-800)' }}>{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
      <label style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--color-surface-600)', letterSpacing: '0.03em' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '0.3rem 0.5rem',
  fontSize: '0.8rem',
  border: '1px solid var(--color-surface-300)',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--color-surface-0)',
  color: 'var(--color-surface-900)',
  width: '100%',
}

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: 'pointer',
}
