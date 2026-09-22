// API base — uses Vite proxy (/api -> localhost:8000)
export const API_BASE = '/api'

// ── Types ──────────────────────────────────────────────────────────────────

export interface SystemToday {
  today: string
  is_synthetic_or_replay: boolean
  data_source: string
  earliest_date: string
  latest_date: string
  note: string
}

export interface HealthResponse {
  status: string
  service: string
  version: string
  subdivisions_count: number
  available_dates_count: number
  models_loaded: boolean
  current_data_date: string
  data_recency_note: string
}

export interface RegionMeta {
  name: string
  lat: number
  lon: number
  terrain: string
  terrain_difficulty: number
}

export interface ConfidenceMapItem {
  date: string
  region: string
  lat: number
  lon: number
  terrain: string
  terrain_difficulty: number
  synoptic_regime: string
  lead_day: number
  bust_probability: number
  predicted_error_mm: number
  error_interval_90_lower: number | null
  error_interval_90_upper: number | null
  conformal_interval_mm: [number, number] | null
  confidence_score: number
  risk_tier: string
  evidence_agreement: number
  contradiction_flag: boolean
  top_drivers: string[]
  top_families: unknown[] | null
  operational_bulletin: Record<string, string> | null
  plain_language_summary: string
}

export interface ForecastProfileItem {
  lead_day: number
  date: string
  region: string
  terrain: string
  synoptic_regime: string
  ens_spread_rainfall: number
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
  top_drivers: unknown[]
  top_families: unknown[] | null
  operational_bulletin: Record<string, string> | null
}

export type CalibrationVerdict =
  | 'confident_correct'
  | 'confident_but_busted'
  | 'flagged_risky_and_busted'
  | 'flagged_risky_no_bust'

export interface HistoryItem {
  date: string
  initialization_time: string | null
  lead_day: number
  region: string
  forecast_rainfall_mm: number
  forecast_temp_2m_c: number
  observed_rainfall_mm: number
  observed_temp_2m_c: number
  forecast_error_mm: number
  abs_error_mm: number
  bust_threshold_mm: number
  was_bust: boolean
  confidence_at_issue_time: number
  bust_probability: number
  predicted_error_mm: number | null
  conformal_interval_mm: [number, number] | null
  risk_tier: string
  calibration_verdict: CalibrationVerdict
  evidence_agreement: number
  contradiction_flag: boolean
  top_drivers: string[] | null
}

export interface HistorySummary {
  region: string
  days: number
  as_of: string
  lead_day: number
  counts_per_calibration_verdict: {
    confident_correct: number
    confident_but_busted: number
    flagged_risky_and_busted: number
    flagged_risky_no_bust: number
  }
  overall_bust_rate: number
  mean_abs_error: number
  summary_sentence: string
}

export interface LocationSearchResult {
  query: string
  resolved_subdivision: string
  subdivision_lat: number
  subdivision_lon: number
  match_confidence: 'exact_subdivision' | 'resolved_from_city'
  matched_name: string | null
  distance_km: number | null
  note: string
}

export interface HourlyCurvePoint {
  hour: number
  time_utc: string
  temp_c: number
  rainfall_mm: number
  is_illustrative: true
}

export interface DayDetail {
  date: string
  region: string
  lead_day: number
  initialization_time: string
  granularity: 'daily'
  note: string
  bust_probability: number
  confidence_score: number
  predicted_error_mm: number
  error_interval_90_lower: number | null
  error_interval_90_upper: number | null
  conformal_interval_mm: [number, number] | null
  risk_tier: string
  evidence_agreement: number
  contradiction_flag: boolean
  forecast_rainfall_mm: number
  forecast_temp_2m_c: number
  observed_rainfall_mm: number | null
  observed_temp_2m_c: number | null
  forecast_error_mm: number | null
  abs_error_mm: number | null
  bust_threshold_mm: number | null
  was_bust: boolean | null
  era5_diagnostics: Record<string, number | null>
  top_drivers: string[]
  top_families: unknown[] | null
  operational_bulletin: Record<string, string> | null
  plain_language_summary: string
  illustrative_hourly_curve: HourlyCurvePoint[]
  is_illustrative: true
  illustrative_note: string
}

// ── API helpers ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error(`API ${res.status}: ${res.url}`)
    ;(err as Error & { status: number; detail: unknown }).status = res.status
    ;(err as Error & { status: number; detail: unknown }).detail = body?.detail
    throw err
  }
  return res.json() as Promise<T>
}

export const api = {
  systemToday: () => apiFetch<SystemToday>('/system/today'),
  health: () => apiFetch<HealthResponse>('/health'),
  regions: () => apiFetch<RegionMeta[]>('/regions'),
  dates: () => apiFetch<string[]>('/dates'),
  confidenceMap: (date?: string, lead_day = 1) =>
    apiFetch<ConfidenceMapItem[]>(
      `/confidence_map?lead_day=${lead_day}${date ? `&date=${date}` : ''}`
    ),
  regionForecast: (region: string, date?: string) =>
    apiFetch<ForecastProfileItem[]>(
      `/region/${encodeURIComponent(region)}/forecast${date ? `?date=${date}` : ''}`
    ),
  regionHistory: (region: string, days = 10, as_of?: string, lead_day = 1) =>
    apiFetch<HistoryItem[]>(
      `/region/${encodeURIComponent(region)}/history?days=${days}&lead_day=${lead_day}${as_of ? `&as_of=${as_of}` : ''}`
    ),
  regionHistorySummary: (region: string, days = 10, as_of?: string, lead_day = 1) =>
    apiFetch<HistorySummary>(
      `/region/${encodeURIComponent(region)}/history/summary?days=${days}&lead_day=${lead_day}${as_of ? `&as_of=${as_of}` : ''}`
    ),
  dayDetail: (region: string, date?: string, lead_day = 1) =>
    apiFetch<DayDetail>(
      `/region/${encodeURIComponent(region)}/day_detail?lead_day=${lead_day}${date ? `&date=${date}` : ''}`
    ),
  locationsSearch: (q: string) =>
    apiFetch<LocationSearchResult>(`/locations/search?q=${encodeURIComponent(q)}`),
  explain: (region: string, lead_day = 1, date?: string) =>
    apiFetch<unknown>(
      `/explain/${encodeURIComponent(region)}?lead_day=${lead_day}${date ? `&date=${date}` : ''}`
    ),
}
