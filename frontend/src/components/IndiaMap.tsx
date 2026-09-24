import React, { useState, useCallback, useEffect } from 'react'
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps'
import { useQuery } from '@tanstack/react-query'
import { api, type RegionMeta, type LocationSearchResult } from '../lib/api'
import { probToFill } from '../lib/utils'
import { useAppContext } from '../context/AppContext'
import { LoadingSpinner, ErrorBanner } from './UIComponents'

interface IndiaMapProps {
  selectedRegion: string | null
  onRegionSelect: (region: string, lat: number, lon: number) => void
  locationResult: LocationSearchResult | null
}

const MAP_CENTER: [number, number] = [82.0, 22.0]

export function IndiaMap({ selectedRegion, onRegionSelect, locationResult }: IndiaMapProps) {
  const { today } = useAppContext()
  const [leadDay, setLeadDay] = useState(1)
  const [hoveredRegion, setHoveredRegion] = useState<string | null>(null)
  const [searchQ, setSearchQ] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchResult, setSearchResult] = useState<LocationSearchResult | null>(locationResult)
  const [zoom, setZoom] = useState<number>(1)
  const [center, setCenter] = useState<[number, number]>(MAP_CENTER)

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

  // If external locationResult changes, zoom to it
  useEffect(() => {
    if (locationResult) {
      setSearchResult(locationResult)
      setCenter([locationResult.subdivision_lon, locationResult.subdivision_lat])
      setZoom(2.8)
    }
  }, [locationResult])

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    const q = searchQ.trim()
    if (!q) return
    setSearchLoading(true)
    setSearchError(null)
    try {
      const result = await api.locationsSearch(q)
      setSearchResult(result)
      setCenter([result.subdivision_lon, result.subdivision_lat])
      setZoom(2.8)
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

  const handleSelectMarker = (regionName: string, lat: number, lon: number) => {
    setCenter([lon, lat])
    setZoom(2.4)
    onRegionSelect(regionName, lat, lon)
  }

  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.4, 4))
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.4, 0.8))
  const handleReset = () => {
    setZoom(1)
    setCenter(MAP_CENTER)
    setSearchResult(null)
  }

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
              placeholder="Search city or subdivision (e.g. Bengaluru, Odisha, Jaipur)"
              aria-label="Search location"
              style={{
                flex: 1,
                padding: '0.45rem 0.65rem',
                fontSize: '0.82rem',
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
                padding: '0.45rem 0.85rem',
                background: '#0b4c8c',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: searchLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.82rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
              }}
            >
              {searchLoading ? <LoadingSpinner size={14} /> : '🔍 Search'}
            </button>
          </div>
          {searchError && (
            <div style={{ marginTop: '0.375rem', fontSize: '0.72rem', color: '#be123c', fontWeight: 600 }}>
              {searchError}
            </div>
          )}
        </form>

        {/* Lead day selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flexShrink: 0, flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.68rem', color: 'var(--color-surface-600)', fontWeight: 700 }}>Day:</span>
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
                borderColor: leadDay === d ? '#0b4c8c' : 'var(--color-surface-300)',
                background: leadDay === d ? '#0b4c8c' : 'transparent',
                color: leadDay === d ? 'white' : 'var(--color-surface-700)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '0.68rem',
                fontWeight: leadDay === d ? 700 : 500,
              }}
            >
              {d}
            </button>
          ))}
          {cmLoading && <LoadingSpinner size={14} />}
        </div>
      </div>

      {/* City resolution disclosure / Active searched banner */}
      {searchResult && (
        <div
          role="status"
          style={{
            padding: '0.4rem 0.65rem',
            background: '#e0f2fe',
            border: '1px solid #7dd3fc',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.75rem',
            color: '#0369a1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <strong>📍 {searchResult.matched_name || searchResult.query}</strong> resolved to{' '}
            <strong>{searchResult.resolved_subdivision}</strong>
            {searchResult.distance_km ? ` (${searchResult.distance_km.toFixed(0)} km from center)` : ''} · Zoomed
          </div>
          <button
            onClick={handleReset}
            style={{
              background: '#ffffff',
              border: '1px solid #7dd3fc',
              borderRadius: '4px',
              padding: '0.15rem 0.4rem',
              fontSize: '0.68rem',
              cursor: 'pointer',
              fontWeight: 700,
              color: '#0369a1',
            }}
          >
            Reset View
          </button>
        </div>
      )}

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.65rem', color: 'var(--color-surface-600)', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700 }}>Bust Risk (D+{leadDay}):</span>
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

      {/* Map Viewport */}
      {cmError ? (
        <ErrorBanner message="Could not load confidence map. Is the backend running on :8000?" />
      ) : (
        <div
          style={{
            flex: 1,
            minHeight: '480px',
            position: 'relative',
            border: '1px solid #cbd5e1',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            background: '#e0f2fe',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {/* Zoom controls */}
          <div
            style={{
              position: 'absolute',
              top: '10px',
              left: '10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              zIndex: 10,
            }}
          >
            <button
              onClick={handleReset}
              title="Reset View"
              style={{
                width: 26,
                height: 26,
                background: '#ffffff',
                border: '1px solid #94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 700,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              🏠
            </button>
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              style={{
                width: 26,
                height: 26,
                background: '#ffffff',
                border: '1px solid #94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 700,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              +
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              style={{
                width: 26,
                height: 26,
                background: '#ffffff',
                border: '1px solid #94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 700,
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              -
            </button>
          </div>

          <ComposableMap
            projection="geoMercator"
            projectionConfig={{
              scale: 1050,
              center: MAP_CENTER,
            }}
            width={800}
            height={580}
            style={{ width: '100%', height: '100%' }}
          >
            <ZoomableGroup
              zoom={zoom}
              center={center}
              minZoom={0.8}
              maxZoom={5}
              onMoveEnd={({ coordinates, zoom: z }: any) => {
                if (
                  coordinates &&
                  Array.isArray(coordinates) &&
                  typeof coordinates[0] === 'number' &&
                  typeof coordinates[1] === 'number' &&
                  !isNaN(coordinates[0]) &&
                  !isNaN(coordinates[1])
                ) {
                  setCenter(coordinates as [number, number])
                }
                if (typeof z === 'number' && !isNaN(z) && z > 0) {
                  setZoom(z)
                }
              }}
            >
              {/* State boundaries */}
              <Geographies geography="/india-states.geojson">
                {({ geographies }) =>
                  geographies.map((geo) => (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill="#fef08a"
                      stroke="#ca8a04"
                      strokeWidth={0.6}
                      style={{
                        default: { outline: 'none' },
                        hover: { fill: '#fde047', outline: 'none' },
                        pressed: { outline: 'none' },
                      }}
                    />
                  ))
                }
              </Geographies>

              {/* Subdivision Markers */}
              {regions?.map((r: RegionMeta) => {
                const prob = probLookup[r.name]
                const color = prob !== undefined ? probToFill(prob) : '#334155'
                const isSelected = r.name === selectedRegion
                const isHovered = r.name === hoveredRegion
                const radius = isSelected ? 10 : isHovered ? 8 : 6

                return (
                  <Marker
                    key={r.name}
                    coordinates={[r.lon, r.lat]}
                    onClick={() => handleSelectMarker(r.name, r.lat, r.lon)}
                    onMouseEnter={() => setHoveredRegion(r.name)}
                    onMouseLeave={() => setHoveredRegion(null)}
                  >
                    <g style={{ cursor: 'pointer' }}>
                      {isSelected && (
                        <circle
                          cx={0} cy={0} r={radius + 5}
                          fill="none"
                          stroke="#dc2626"
                          strokeWidth={2.5}
                          opacity={0.9}
                        />
                      )}
                      <circle
                        cx={0} cy={0} r={radius}
                        fill={color}
                        stroke={isSelected ? '#dc2626' : isHovered ? 'white' : 'rgba(255,255,255,0.6)'}
                        strokeWidth={isSelected ? 2.5 : isHovered ? 1.5 : 0.75}
                        opacity={0.95}
                      />
                      {prob !== undefined && (
                        <text
                          x={0} y={3}
                          textAnchor="middle"
                          fontSize={5.5}
                          fontWeight={700}
                          fill="white"
                          style={{ pointerEvents: 'none', userSelect: 'none' }}
                        >
                          {(prob * 100).toFixed(0)}%
                        </text>
                      )}
                    </g>
                  </Marker>
                )
              })}

              {/* Highlight Pin for Searched Location */}
              {searchResult && (
                <Marker coordinates={[searchResult.subdivision_lon, searchResult.subdivision_lat]}>
                  <g style={{ pointerEvents: 'none' }}>
                    <circle cx={0} cy={0} r={18} fill="rgba(220, 38, 38, 0.2)" />
                    <circle cx={0} cy={0} r={6} fill="#dc2626" stroke="#ffffff" strokeWidth={2} />
                    <text
                      x={0}
                      y={-12}
                      textAnchor="middle"
                      fontSize={7.5}
                      fontWeight={800}
                      fill="#0b4c8c"
                      stroke="#ffffff"
                      strokeWidth={2}
                      paintOrder="stroke fill"
                    >
                      📍 {searchResult.matched_name || searchResult.resolved_subdivision}
                    </text>
                  </g>
                </Marker>
              )}
            </ZoomableGroup>
          </ComposableMap>

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
