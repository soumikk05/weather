import React, { useState } from 'react'

interface IMDHomePortalProps {
  onOpenAICockpit: () => void
  onOpenLogin: () => void
}

export function IMDHomePortal({ onOpenAICockpit, onOpenLogin }: IMDHomePortalProps) {
  const [activeTab, setActiveTab] = useState<'satellite' | 'radar' | 'lightning'>('satellite')

  const weatherStations = [
    { name: 'Leh', temp: '14°C', icon: '☀️', top: '15%', left: '32%' },
    { name: 'New Delhi', temp: '27°C', icon: '🌤️', top: '30%', left: '35%' },
    { name: 'Jaipur', temp: '30°C', icon: '☀️', top: '36%', left: '26%' },
    { name: 'Gangtok', temp: '19°C', icon: '🌧️', top: '38%', left: '74%' },
    { name: 'Diu', temp: '31°C', icon: '☀️', top: '50%', left: '16%' },
    { name: 'Mumbai', temp: '30°C', icon: '🌤️', top: '56%', left: '22%' },
    { name: 'Panjim', temp: '29°C', icon: '☀️', top: '65%', left: '24%' },
    { name: 'Bengaluru', temp: '26°C', icon: '⛅', top: '72%', left: '32%' },
    { name: 'Puducherry', temp: '32°C', icon: '🌤️', top: '75%', left: '44%' },
    { name: 'Port Blair', temp: '28°C', icon: '⛈️', top: '75%', left: '85%' },
  ]

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1.1fr 1.2fr 1fr',
        gap: '1rem',
        padding: '1rem',
        background: '#e0f2fe',
        minHeight: 'calc(100vh - 160px)',
        overflowY: 'auto',
      }}
    >
      {/* ── COLUMN 1: CURRENT WEATHER (Clean Vector Outline Map) ──────────────── */}
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
          CURRENT WEATHER
        </div>

        {/* Clean Vector India Outline Map Container */}
        <div
          style={{
            flex: 1,
            position: 'relative',
            background: 'linear-gradient(180deg, #bae6fd 0%, #7dd3fc 100%)',
            minHeight: '400px',
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

          {/* Clean Vector India Outline Map (No text watermarks/political headers) */}
          <svg
            viewBox="0 0 500 550"
            style={{ width: '92%', height: '92%', filter: 'drop-shadow(0 4px 8px rgba(0, 51, 102, 0.15))' }}
          >
            {/* Ocean Wave lines */}
            <path d="M20 400 Q60 390 100 400" stroke="#0284c7" strokeWidth="1" fill="none" opacity="0.4" />
            <path d="M350 420 Q400 410 450 420" stroke="#0284c7" strokeWidth="1" fill="none" opacity="0.4" />

            {/* India Mainland Outline Path */}
            <g fill="#fef08a" stroke="#0369a1" strokeWidth="2.5" strokeLinejoin="round">
              <path d="
                M 190,45 
                L 210,35 L 230,42 L 245,65 L 235,90 
                L 260,110 L 275,100 L 295,115 L 340,125 
                L 380,120 L 420,135 L 440,150 L 420,170 
                L 390,175 L 375,160 L 350,165 L 320,180 
                L 330,205 L 305,225 L 320,255 L 290,290 
                L 260,340 L 240,410 L 225,450 L 210,480 
                L 190,440 L 165,370 L 150,330 L 140,290 
                L 125,270 L 95,250 L 75,230 L 90,200 
                L 110,195 L 120,175 L 150,170 L 160,135 
                L 175,115 L 165,85 L 180,60 Z
              " />
            </g>

            {/* Sub-region state border grid lines inside India */}
            <path d="M190,45 L175,115 L260,110 M260,110 L320,180 M160,135 L120,175 M120,175 L150,270 M150,270 L260,340 M260,340 L225,450 M140,290 L240,410" stroke="#ca8a04" strokeWidth="1.2" strokeDasharray="3 3" fill="none" opacity="0.7" />

            {/* Neighboring Lands silhouette */}
            <path d="M 60,80 L 140,80 L 165,85 L 175,115 L 120,175 L 90,200 L 60,170 Z" fill="#dcfce7" stroke="#166534" strokeWidth="1.5" opacity="0.8" />
            <path d="M 245,65 L 380,50 L 440,150 L 380,120 L 340,125 L 295,115 Z" fill="#dcfce7" stroke="#166534" strokeWidth="1.5" opacity="0.8" />
            <path d="M 215,505 C 230,490 240,510 230,525 C 220,535 205,520 215,505 Z" fill="#dcfce7" stroke="#166534" strokeWidth="1.5" />
          </svg>

          {/* Weather Station Pins */}
          {weatherStations.map((st) => (
            <div
              key={st.name}
              style={{
                position: 'absolute',
                top: st.top,
                left: st.left,
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                background: 'rgba(255,255,255,0.96)',
                padding: '3px 8px',
                borderRadius: '12px',
                border: '1.5px solid #0369a1',
                boxShadow: '0 3px 8px rgba(0,51,102,0.2)',
                fontSize: '0.7rem',
                fontWeight: 800,
                color: '#0369a1',
                cursor: 'pointer',
                zIndex: 5,
              }}
            >
              <span>{st.icon}</span>
              <span>{st.name}</span>
              <span style={{ color: '#0f172a' }}>{st.temp}</span>
            </div>
          ))}
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
  )
}
