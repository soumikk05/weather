import { type CalibrationVerdict } from './api'

// Verdict display metadata (4 distinct, colorblind-safe identities)
export const VERDICT_CONFIG: Record<
  CalibrationVerdict,
  { label: string; shortLabel: string; colorClass: string; bgClass: string; borderClass: string; icon: string; explanation: string }
> = {
  confident_correct: {
    label: 'Confident & Correct',
    shortLabel: 'CC',
    colorClass: 'text-[var(--color-verdict-cc)]',
    bgClass: 'bg-blue-50',
    borderClass: 'border-[var(--color-verdict-cc)]',
    icon: '◆',
    explanation:
      'Model expressed high or moderate confidence — forecast verified with no bust. Calibration was well-placed (True Negative).',
  },
  confident_but_busted: {
    label: 'Confident — Bust Missed',
    shortLabel: 'CB',
    colorClass: 'text-[var(--color-verdict-cb)]',
    bgClass: 'bg-amber-50',
    borderClass: 'border-[var(--color-verdict-cb)]',
    icon: '▲',
    explanation:
      'Model was confident, but the forecast busted anyway. A missed alert worth reviewing — potential calibration gap (False Negative).',
  },
  flagged_risky_and_busted: {
    label: 'Risk Flagged & Verified',
    shortLabel: 'RV',
    colorClass: 'text-[var(--color-verdict-rab)]',
    bgClass: 'bg-emerald-50',
    borderClass: 'border-[var(--color-verdict-rab)]',
    icon: '●',
    explanation:
      'Model correctly issued a bust-risk alert, and the forecast did bust. Confidence was well-calibrated (True Positive Alert).',
  },
  flagged_risky_no_bust: {
    label: 'Alert Issued — No Bust',
    shortLabel: 'AN',
    colorClass: 'text-[var(--color-verdict-rnb)]',
    bgClass: 'bg-violet-50',
    borderClass: 'border-[var(--color-verdict-rnb)]',
    icon: '■',
    explanation:
      'Model issued a bust-risk alert, but the forecast verified safely. A conservative false alarm — better than a miss for operational safety (False Alarm).',
  },
}

// Risk tier display metadata
export const RISK_TIER_CONFIG: Record<
  string,
  { color: string; bg: string; label: string }
> = {
  'High Confidence': {
    color: 'text-[var(--color-risk-high)]',
    bg: 'bg-blue-50',
    label: 'HIGH',
  },
  'Moderate Confidence': {
    color: 'text-[var(--color-risk-mod)]',
    bg: 'bg-amber-50',
    label: 'MOD',
  },
  'Low Confidence - Bust Risk': {
    color: 'text-[var(--color-risk-low)]',
    bg: 'bg-rose-50',
    label: 'BUST RISK',
  },
}

// Map bust probability to choropleth fill color
export function probToFill(prob: number): string {
  if (prob >= 0.65) return '#9f1239'   // rose-800
  if (prob >= 0.50) return '#be185d'   // rose-700
  if (prob >= 0.35) return '#b45309'   // amber-700
  if (prob >= 0.20) return '#d97706'   // amber-500
  if (prob >= 0.10) return '#0369a1'   // sky-700
  return '#1d4ed8'                     // blue-700 (very low prob)
}

// Format a number as percentage
export function pct(v: number, decimals = 1): string {
  return `${(v * 100).toFixed(decimals)}%`
}

// Format a number with fixed decimals
export function fmt(v: number | null | undefined, dec = 2, unit = ''): string {
  if (v == null) return '—'
  return `${v.toFixed(dec)}${unit}`
}

// Format date as "DD MMM YYYY"
export function fmtDate(d: string): string {
  return new Date(d).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

// Advisory level -> color class
export function advisoryColor(level: string): string {
  const l = level.toUpperCase()
  if (l.startsWith('RED')) return 'text-rose-700'
  if (l.startsWith('AMBER')) return 'text-amber-600'
  return 'text-emerald-700'
}
export function advisoryBg(level: string): string {
  const l = level.toUpperCase()
  if (l.startsWith('RED')) return 'bg-rose-50 border-rose-200'
  if (l.startsWith('AMBER')) return 'bg-amber-50 border-amber-200'
  return 'bg-emerald-50 border-emerald-200'
}

// ERA5 field label prettifier
export function era5Label(key: string): string {
  return key
    .replace('era5_', '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
