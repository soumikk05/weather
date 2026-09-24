import React, { useState } from 'react'
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from 'react-simple-maps'


interface IMDHomePortalProps {
  onOpenAICockpit: () => void
  onOpenLogin: () => void
}

const STATE_TEMPERATURES: Record<string, { temp: number; color: string }> = {
  'Jammu and Kashmir': { temp: 15, color: '#fef9c3' },
  'Himachal Pradesh': { temp: 18, color: '#fef08a' },
  'Punjab': { temp: 27, color: '#fcd34d' },
  'Haryana': { temp: 28, color: '#fbbf24' },
  'Delhi': { temp: 28, color: '#fbbf24' },
  'Uttaranchal': { temp: 20, color: '#fef08a' },
  'Rajasthan': { temp: 34, color: '#b91c1c' },
  'Uttar Pradesh': { temp: 30, color: '#d97706' },
  'Bihar': { temp: 29, color: '#f59e0b' },
  'Gujarat': { temp: 33, color: '#c2410c' },
  'Madhya Pradesh': { temp: 32, color: '#ea580c' },
  'Chhattisgarh': { temp: 30, color: '#d97706' },
  'Jharkhand': { temp: 28, color: '#f59e0b' },
  'West Bengal': { temp: 29, color: '#f59e0b' },
  'Orissa': { temp: 30, color: '#d97706' },
  'Maharashtra': { temp: 31, color: '#ea580c' },
  'Telangana': { temp: 31, color: '#c2410c' },
  'Andhra Pradesh': { temp: 32, color: '#b91c1c' },
  'Karnataka': { temp: 28, color: '#f59e0b' },
  'Goa': { temp: 29, color: '#f59e0b' },
  'Tamil Nadu': { temp: 33, color: '#b91c1c' },
  'Kerala': { temp: 29, color: '#f59e0b' },
  'Sikkim': { temp: 16, color: '#fef9c3' },
  'Assam': { temp: 25, color: '#fde047' },
  'Arunachal Pradesh': { temp: 21, color: '#fef08a' },
  'Meghalaya': { temp: 22, color: '#fde047' },
  'Nagaland': { temp: 23, color: '#fde047' },
  'Manipur': { temp: 24, color: '#fde047' },
  'Mizoram': { temp: 24, color: '#fde047' },
  'Tripura': { temp: 26, color: '#fbbf24' },
  'Andaman and Nicobar': { temp: 28, color: '#f59e0b' },
  'Lakshadweep': { temp: 30, color: '#d97706' },
}

export function IMDHomePortal({ onOpenAICockpit }: IMDHomePortalProps) {
  const [activeTab, setActiveTab] = useState<'satellite' | 'radar' | 'lightning'>('satellite')
  const [hoveredState, setHoveredState] = useState<{ name: string; temp?: number } | null>(null)
  const [zoom, setZoom] = useState<number>(1)
  const [center, setCenter] = useState<[number, number]>([78.9629, 22.5937])

  const weatherStations = [
    { name: 'Leh', temp: '14°C', icon: '☀️', coordinates: [77.5771, 34.1526] as [number, number] },
    { name: 'New Delhi', temp: '27°C', icon: '🌤️', coordinates: [77.2090, 28.6139] as [number, number] },
    { name: 'Jaipur', temp: '30°C', icon: '☀️', coordinates: [75.7873, 26.9124] as [number, number] },
    { name: 'Gangtok', temp: '19°C', icon: '🌧️', coordinates: [88.6138, 27.3389] as [number, number] },
    { name: 'Diu', temp: '31°C', icon: '☀️', coordinates: [70.9871, 20.7144] as [number, number] },
    { name: 'Mumbai', temp: '30°C', icon: '🌤️', coordinates: [72.8777, 19.0760] as [number, number] },
    { name: 'Panjim', temp: '29°C', icon: '☀️', coordinates: [73.8278, 15.4909] as [number, number] },
    { name: 'Bengaluru', temp: '26°C', icon: '⛅', coordinates: [77.5946, 12.9716] as [number, number] },
    { name: 'Puducherry', temp: '32°C', icon: '🌤️', coordinates: [79.8083, 11.9416] as [number, number] },
    { name: 'Port Blair', temp: '28°C', icon: '⛈️', coordinates: [92.7265, 11.6234] as [number, number] },
  ]

  const handleZoomIn = () => setZoom((z) => Math.min((z || 1) * 1.3, 4))
  const handleZoomOut = () => setZoom((z) => Math.max((z || 1) / 1.3, 0.8))
  const handleReset = () => {
    setZoom(1)
    setCenter([78.9629, 22.5937])
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
        padding: '1.25rem',
        background: '#e0f2fe',
        minHeight: 'calc(100vh - 160px)',
        overflowY: 'auto',
      }}
    >


      {/* ── 3-COLUMN PORTAL GRID BELOW ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.2fr 1.2fr 1fr',
          gap: '1rem',
          flex: 1,
        }}
      >
        {/* ── COLUMN 1: CURRENT WEATHER (State Map of India) ──────────────── */}
        <div
          style={{
            background: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #bae6fd',
          boxShadow: '0 4px 12px rgba(0, 51, 102, 0.08)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            background: '#0b4c8c',
            color: '#ffffff',
            padding: '0.6rem 1rem',
            fontWeight: 700,
            fontSize: '0.88rem',
            letterSpacing: '0.04em',
            textAlign: 'center',
            textTransform: 'uppercase',
          }}
        >
          CURRENT WEATHER (STATE MAP)
        </div>

        {/* State Map Container */}
        <div
          style={{
            flex: 1,
            position: 'relative',
            background: '#bae6fd',
            minHeight: '420px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
        >
          {/* Zoom controls */}
          <div
            style={{
              position: 'absolute',
              top: '12px',
              left: '12px',
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
                width: 28,
                height: 28,
                background: '#ffffff',
                border: '1px solid #94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 700,
                boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
              }}
            >
              🏠
            </button>
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              style={{
                width: 28,
                height: 28,
                background: '#ffffff',
                border: '1px solid #94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 700,
                boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
              }}
            >
              +
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              style={{
                width: 28,
                height: 28,
                background: '#ffffff',
                border: '1px solid #94a3b8',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 700,
                boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
              }}
            >
              -
            </button>
          </div>

          {/* Hover Tooltip */}
          {hoveredState && (
            <div
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'rgba(15, 23, 42, 0.92)',
                color: '#ffffff',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                zIndex: 10,
                pointerEvents: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              }}
            >
              {hoveredState.name}
              {hoveredState.temp !== undefined ? `: ${hoveredState.temp}°C` : ''}
            </div>
          )}

          {/* React Simple Maps - India States GeoJSON */}
          <ComposableMap
            projection="geoMercator"
            projectionConfig={{
              scale: 850,
              center: [78.9629, 22.5937],
            }}
            width={800}
            height={520}
            style={{ width: '100%', height: '100%' }}
          >
            <ZoomableGroup
              zoom={zoom}
              center={center}
              minZoom={0.8}
              maxZoom={4}
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
              <Geographies geography="/india-states.geojson">
                {({ geographies }) =>
                  geographies && geographies.length > 0 ? (
                    geographies.map((geo) => {
                      const stateName = geo.properties?.NAME_1 || geo.properties?.ST_NM || geo.properties?.name || ''
                      const stateInfo = STATE_TEMPERATURES[stateName]
                      const fillColor = stateInfo?.color || '#fde047'
                      const isHovered = hoveredState?.name === stateName

                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          fill={isHovered ? '#7f1d1d' : fillColor}
                          stroke="#78350f"
                          strokeWidth={0.7}
                          onMouseEnter={() => setHoveredState({ name: stateName, temp: stateInfo?.temp })}
                          onMouseLeave={() => setHoveredState(null)}
                          style={{
                            outline: 'none',
                            transition: 'fill 0.15s ease',
                            cursor: 'pointer',
                          }}
                        />
                      )
                    })
                  ) : null
                }
              </Geographies>

              {/* Weather Station Pins with crisp SVG elements */}
              {weatherStations.map((st) => (
                <Marker key={st.name} coordinates={st.coordinates}>
                  <g style={{ cursor: 'pointer' }}>
                    <circle r={6} fill="#0369a1" stroke="#ffffff" strokeWidth={2} />
                    <circle r={2.5} fill="#ffffff" />
                    <rect
                      x={-42}
                      y={-24}
                      width={84}
                      height={18}
                      rx={5}
                      fill="rgba(255, 255, 255, 0.95)"
                      stroke="#0369a1"
                      strokeWidth={1}
                      filter="drop-shadow(0 2px 4px rgba(0,0,0,0.25))"
                    />
                    <text
                      x={0}
                      y={-12}
                      textAnchor="middle"
                      fontSize={8.5}
                      fontWeight={800}
                      fill="#0369a1"
                      fontFamily="system-ui, sans-serif"
                    >
                      {st.name} {st.temp}
                    </text>
                  </g>
                </Marker>
              ))}
            </ZoomableGroup>
          </ComposableMap>
        </div>

        {/* Temperature Legend */}
        <div style={{ padding: '0.5rem 0.75rem', background: '#f8fafc', borderTop: '1px solid #bae6fd', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.68rem', color: '#334155' }}>
          <span style={{ fontWeight: 700 }}>Mean Temp (°C):</span>
          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            {[
              { label: '<18°', color: '#fef9c3' },
              { label: '18–24°', color: '#fde047' },
              { label: '25–28°', color: '#f59e0b' },
              { label: '29–31°', color: '#ea580c' },
              { label: '32–34°', color: '#c2410c' },
              { label: '>34°', color: '#b91c1c' },
            ].map((item) => (
              <span key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                <span style={{ width: 10, height: 10, borderRadius: '2px', background: item.color, border: '1px solid #78350f', display: 'inline-block' }} />
                {item.label}
              </span>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ padding: '0.75rem', background: '#ffffff', borderTop: '1px solid #bae6fd', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            onClick={onOpenAICockpit}
            style={{
              width: '100%',
              padding: '0.6rem',
              background: 'linear-gradient(135deg, #0b4c8c 0%, #002b5c 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 800,
              fontSize: '0.82rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
            }}
          >
            <span>⚡</span> Open AI Forecast Bust Cockpit
          </button>
        </div>
      </div>

      {/* ── COLUMN 2: SATELLITE | RADAR | LIGHTNING ──────────────────────────── */}
      <div
        style={{
          background: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #bae6fd',
          boxShadow: '0 4px 12px rgba(0, 51, 102, 0.08)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Tab Header Bar */}
        <div style={{ display: 'flex', borderBottom: '2px solid #0b4c8c', background: '#f8fafc' }}>
          {(['satellite', 'radar', 'lightning'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1,
                padding: '0.6rem 0.5rem',
                border: 'none',
                background: activeTab === tab ? '#ffffff' : 'transparent',
                color: activeTab === tab ? '#0b4c8c' : '#64748b',
                fontWeight: activeTab === tab ? 800 : 600,
                fontSize: '0.82rem',
                cursor: 'pointer',
                textTransform: 'uppercase',
                borderBottom: activeTab === tab ? '3px solid #0b4c8c' : '3px solid transparent',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Subheader */}
        <div style={{ padding: '0.4rem', textAlign: 'center', fontWeight: 700, fontSize: '0.78rem', color: '#0b4c8c', borderBottom: '1px solid #e2e8f0' }}>
          SATELLITE (INSAT-3DS THERMAL INFRARED)
        </div>

        {/* Satellite Imagery Viewport */}
        <div style={{ flex: 1, background: '#000000', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
          <img
            src="/satellite.jpg"
            alt="INSAT-3DS Satellite Weather Map"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>
      </div>

      {/* ── COLUMN 3: DAILY WEATHER BRIEFING & NEWS ─────────────────────────── */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        {/* Weather Briefing Video Card */}
        <div
          style={{
            background: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #bae6fd',
            boxShadow: '0 4px 12px rgba(0, 51, 102, 0.08)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              background: '#0b4c8c',
              color: '#ffffff',
              padding: '0.5rem 0.75rem',
              fontWeight: 700,
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span>DAILY WEATHER BRIEFING</span>
            <span style={{ background: '#059669', padding: '0.1rem 0.4rem', borderRadius: '3px', fontSize: '0.65rem' }}>
              ENGLISH
            </span>
          </div>

          <div style={{ position: 'relative', width: '100%', aspectRatio: '16/9', overflow: 'hidden' }}>
            <img
              src="/src/assets/briefing_thumb.jpg"
              alt="Dainik Mausam Paricharcha"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: 'rgba(0,0,0,0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: '50%',
                  background: '#dc2626',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  fontSize: '1.4rem',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                }}
              >
                ▶
              </div>
            </div>

            <div
              style={{
                position: 'absolute',
                bottom: 8,
                left: 8,
                background: 'rgba(0,0,0,0.75)',
                color: '#ffffff',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.68rem',
                fontWeight: 700,
              }}
            >
              🗓️ 22-09-2026
            </div>
          </div>
        </div>

        {/* News & Events Card */}
        <div
          style={{
            flex: 1,
            background: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #bae6fd',
            boxShadow: '0 4px 12px rgba(0, 51, 102, 0.08)',
            padding: '0.85rem',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ fontWeight: 800, fontSize: '0.85rem', color: '#0b4c8c', marginBottom: '0.65rem', borderBottom: '2px solid #0b4c8c', paddingBottom: '0.35rem' }}>
            NEWS & EVENTS
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', fontSize: '0.75rem', color: '#334155' }}>
            <div style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '0.4rem' }}>
              <div style={{ color: '#0284c7', fontWeight: 700 }}>22 SEP 2026</div>
              <div>Press Release: Weather summary and forecast for next 5 days issued by IMD RMC.</div>
            </div>
            <div style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '0.4rem' }}>
              <div style={{ color: '#0284c7', fontWeight: 700 }}>20 SEP 2026</div>
              <div>150 Years of Service to Nation Celebration & Special Weather Bulletin.</div>
            </div>
            <div>
              <div style={{ color: '#d97706', fontWeight: 700 }}>OPERATIONAL AI NOTICE</div>
              <div>NCMRWF Medium Range AI Bust Hazard System deployment online. Sign in to access full controls.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  )
}
