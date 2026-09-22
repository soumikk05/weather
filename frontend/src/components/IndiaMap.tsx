import React, { useState, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type RegionMeta, type LocationSearchResult } from '../lib/api'
import { probToFill } from '../lib/utils'
import { useAppContext } from '../context/AppContext'
import { LoadingSpinner, ErrorBanner } from './UIComponents'

// ── Bounding box for India: lat 8–37, lon 68–97 ─────────────────────────
const LAT_MIN = 6, LAT_MAX = 38, LON_MIN = 67, LON_MAX = 98

function projectLon(lon: number, w: number) {
  return ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * w
}
function projectLat(lat: number, h: number) {
  // Invert: higher lat = top
  return ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * h
}

interface IndiaMapProps {
  selectedRegion: string | null
  onRegionSelect: (region: string, lat: number, lon: number) => void
  locationResult: LocationSearchResult | null
}

export function IndiaMap({ selectedRegion, onRegionSelect, locationResult }: IndiaMapProps) {
  const { today } = useAppContext()
  const [leadDay, setLeadDay] = useState(1)
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null)
  const [searchQ, setSearchQ] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchResult, setSearchResult] = useState<LocationSearchResult | null>(locationResult)
  const svgRef = useRef<SVGSVGElement>(null)

  const { data: regions } = useQuery({
    queryKey: ['regions'],
    queryFn: api.regions,
    staleTime: Infinity,
  })

  const { data: confidenceMap, isLoading: cmLoading, error: cmError } = useQuery({
    queryKey: ['confidence_map', today?.today, leadDay],
    queryFn: () => api.confidenceMap(today?.today, leadDay),
    enabled: !!today?.today,
    staleTime: 5 * 60 * 1000,
  })

  // Build lookup: region name -> bust_probability
  const probLookup = React.useMemo(() => {
    const m: Record<string, number> = {}
    confidenceMap?.forEach((item) => { m[item.region] = item.bust_probability })
    return m
  }, [confidenceMap])

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    const q = searchQ.trim()
    if (!q) return
    setSearchLoading(true)
    setSearchError(null)
    setSearchResult(null)
    try {
      const result = await api.locationsSearch(q)
      setSearchResult(result)
      onRegionSelect(
        result.resolved_subdivision,
        result.subdivision_lat,
        result.subdivision_lon,
      )
    } catch (err: unknown) {
      const e = err as Error & { status?: number }
      if (e.status === 404) {
        setSearchError(`No match found for "${q}". Try a state name, subdivision, or major Indian city.`)
      } else {
        setSearchError('Search temporarily unavailable. Please try again.')
      }
    } finally {
      setSearchLoading(false)
    }
  }, [searchQ, onRegionSelect])

  // SVG viewport
  const W = 380, H = 480

  const hovered = confidenceMap?.find((c) => c.region === hoveredRegion) ?? null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem', height: '100%' }}>
      {/* Controls row */}
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Search bar */}
        <form onSubmit={handleSearch} style={{ flex: 1, minWidth: 240 }}>
          <div style={{ display: 'flex', gap: '0.375rem' }}>
            <input
              type="search"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Search city or subdivision (e.g. Bengaluru, Odisha)"
              aria-label="Search location"
              style={{
                flex: 1,
                padding: '0.375rem 0.625rem',
                fontSize: '0.8rem',
                border: '1px solid var(--color-surface-300)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--color-surface-0)',
                color: 'var(--color-surface-900)',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={searchLoading || !searchQ.trim()}
              aria-label="Submit location search"
              style={{
                padding: '0.375rem 0.75rem',
                background: 'var(--color-gov-blue-600)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: searchLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
              }}
            >
              {searchLoading ? <LoadingSpinner size={14} /> : '↵'}
            </button>
          </div>
          {searchError && (
            <div style={{ marginTop: '0.375rem', fontSize: '0.72rem', color: '#be123c' }}>
              {searchError}
            </div>
          )}
        </form>

        {/* Lead day selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flexShrink: 0, flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.68rem', color: 'var(--color-surface-600)', fontWeight: 600 }}>Day:</span>
          {Array.from({ length: 10 }, (_, i) => i + 1).map((d) => (
            <button
              key={d}
              onClick={() => setLeadDay(d)}
              aria-pressed={leadDay === d}
              aria-label={`Lead day ${d}`}
              style={{
                width: 24,
                height: 24,
                border: '1px solid',
                borderColor: leadDay === d ? 'var(--color-gov-blue-500)' : 'var(--color-surface-300)',
                background: leadDay === d ? 'var(--color-gov-blue-500)' : 'transparent',
                color: leadDay === d ? 'white' : 'var(--color-surface-700)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '0.68rem',
                fontWeight: leadDay === d ? 700 : 400,
              }}
            >
              {d}
            </button>
          ))}
          {cmLoading && <LoadingSpinner size={14} />}
        </div>
      </div>

      {/* City resolution disclosure */}
      {searchResult?.match_confidence === 'resolved_from_city' && (
        <div
          role="status"
          style={{
            padding: '0.375rem 0.625rem',
            background: 'var(--color-gov-blue-50)',
            border: '1px solid var(--color-gov-blue-200)',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.72rem',
            color: 'var(--color-gov-blue-800)',
          }}
        >
          <strong>{searchResult.resolved_subdivision}</strong> subdivision ·
          nearest to <em>{searchResult.matched_name}</em>
          {searchResult.distance_km && `, ${searchResult.distance_km.toFixed(0)} km`} ·{' '}
          <span style={{ color: 'var(--color-surface-500)', fontSize: '0.68rem' }}>
            City-level resolution is a known MVP limitation.
          </span>
        </div>
      )}

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.65rem', color: 'var(--color-surface-600)', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600 }}>Bust Risk (D+{leadDay}):</span>
        {[
          ['#1d4ed8', '<10%'],
          ['#0369a1', '10–20%'],
          ['#d97706', '20–35%'],
          ['#b45309', '35–50%'],
          ['#be185d', '50–65%'],
          ['#9f1239', '>65%'],
        ].map(([color, label]) => (
          <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.175rem', marginLeft: '0.25rem' }}>
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: color, display: 'inline-block' }} aria-hidden="true" />
            {label}
          </span>
        ))}
      </div>

      {/* Tooltip for hovered region */}
      {hovered && (
        <div
          aria-live="polite"
          style={{
            padding: '0.375rem 0.625rem',
            background: 'var(--color-gov-blue-900)',
            color: 'var(--color-gov-blue-100)',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.72rem',
            pointerEvents: 'none',
          }}
        >
          <strong>{hovered.region}</strong> ·{' '}
          Bust prob: <strong style={{ color: probToFill(hovered.bust_probability) }}>
            {(hovered.bust_probability * 100).toFixed(1)}%
          </strong> ·{' '}
          <span style={{ color: 'var(--color-gov-blue-300)' }}>{hovered.risk_tier}</span>
          {hovered.plain_language_summary && (
            <div style={{ marginTop: '0.2rem', fontSize: '0.65rem', color: 'var(--color-gov-blue-200)', maxWidth: 320 }}>
              {hovered.plain_language_summary}
            </div>
          )}
        </div>
      )}

      {/* SVG Bubble Map */}
      {cmError ? (
        <ErrorBanner message="Could not load confidence map. Is the backend running on :8000?" />
      ) : (
        <div
          style={{
            flex: 1,
            minHeight: 0,
            position: 'relative',
            border: '1px solid var(--color-surface-200)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            background: 'var(--color-gov-blue-950)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: '100%', height: '100%' }}
            aria-label="India forecast reliability map"
            role="img"
          >
            <defs>
              <radialGradient id="bgGrad" cx="50%" cy="50%">
                <stop offset="0%" stopColor="#122348" />
                <stop offset="100%" stopColor="#050d1f" />
              </radialGradient>
            </defs>
            <rect width={W} height={H} fill="url(#bgGrad)" />

            {/* Grid lines */}
            {Array.from({ length: 7 }, (_, i) => {
              const lon = 68 + i * 5
              const x = projectLon(lon, W)
              return (
                <g key={`vg${i}`}>
                  <line x1={x} y1={0} x2={x} y2={H} stroke="#1a3468" strokeWidth={0.5} strokeDasharray="4 4" />
                  <text x={x + 2} y={H - 4} fill="#1e3f7f" fontSize={7}>{lon}°E</text>
                </g>
              )
            })}
            {Array.from({ length: 7 }, (_, i) => {
              const lat = 8 + i * 5
              const y = projectLat(lat, H)
              return (
                <g key={`hg${i}`}>
                  <line x1={0} y1={y} x2={W} y2={y} stroke="#1a3468" strokeWidth={0.5} strokeDasharray="4 4" />
                  <text x={2} y={y - 2} fill="#1e3f7f" fontSize={7}>{lat}°N</text>
                </g>
              )
            })}

            {/* Region bubbles */}
            {regions?.map((r: RegionMeta) => {
              const prob = probLookup[r.name]
              const x = projectLon(r.lon, W)
              const y = projectLat(r.lat, H)
              const color = prob !== undefined ? probToFill(prob) : '#334155'
              const isSelected = r.name === selectedRegion
              const isHovered = r.name === hoveredRegion
              const radius = isSelected ? 10 : isHovered ? 9 : 7

              return (
                <g
                  key={r.name}
                  onClick={() => onRegionSelect(r.name, r.lat, r.lon)}
                  onMouseEnter={() => setHoveredRegion(r.name)}
                  onMouseLeave={() => setHoveredRegion(null)}
                  role="button"
                  tabIndex={0}
                  aria-label={`${r.name}: ${prob !== undefined ? (prob * 100).toFixed(1) + '% bust risk' : 'loading'}`}
                  aria-pressed={isSelected}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') onRegionSelect(r.name, r.lat, r.lon)
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer ring for selected */}
                  {isSelected && (
                    <circle
                      cx={x} cy={y} r={radius + 4}
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      opacity={0.8}
                    />
                  )}
                  {/* Main bubble */}
                  <circle
                    cx={x} cy={y} r={radius}
                    fill={color}
                    stroke={isSelected ? '#f59e0b' : isHovered ? 'white' : 'rgba(255,255,255,0.3)'}
                    strokeWidth={isSelected ? 2 : isHovered ? 1.5 : 0.75}
                    opacity={0.9}
                    style={{ transition: 'r 0.15s ease, stroke-width 0.15s ease' }}
                  />
                  {/* Probability label */}
                  {prob !== undefined && (
                    <text
                      x={x} y={y + 3.5}
                      textAnchor="middle"
                      fontSize={6}
                      fontWeight={700}
                      fill="white"
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      {(prob * 100).toFixed(0)}%
                    </text>
                  )}
                </g>
              )
            })}

            {/* Title overlay */}
            <text x={8} y={18} fontSize={9} fill="#5e8fdb" fontWeight={700} letterSpacing={1}>
              INDIA FORECAST RELIABILITY — {32} SUBDIVISIONS
            </text>
          </svg>

          {/* No data overlay */}
          {!cmLoading && !confidenceMap?.length && (
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-gov-blue-300)',
              fontSize: '0.78rem',
              gap: '0.5rem',
            }}>
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <circle cx="14" cy="14" r="12" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" />
                <text x="14" y="18" textAnchor="middle" fill="currentColor" fontSize="10">?</text>
              </svg>
              Backend not connected. Start the API server.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
