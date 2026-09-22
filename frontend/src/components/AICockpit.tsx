import React, { useState } from 'react'
import { IndiaMap } from './IndiaMap'
import { RegionDetail } from './RegionDetail'
import { ExplainPanel } from './ExplainPanel'
import { WhatIfLab } from './WhatIfLab'
import { EmptyState } from './UIComponents'
import { useAppContext } from '../context/AppContext'

type Tab = 'detail' | 'explain' | 'whatif'

export function AICockpit() {
  const { today } = useAppContext()
  const [selectedRegion, setSelectedRegion] = useState<string | null>('East Rajasthan')
  const [selectedLat, setSelectedLat] = useState<number | null>(26.9)
  const [selectedLon, setSelectedLon] = useState<number | null>(75.8)
  const [activeTab, setActiveTab] = useState<Tab>('detail')

  // Sidebar control states
  const [initDate, setInitDate] = useState('2024-12-30')
  const [leadTime, setLeadTime] = useState(5)
  const [mapMetric, setMapMetric] = useState<'confidence' | 'prob' | 'error'>('confidence')
  const [subdivisionFilter, setSubdivisionFilter] = useState('all')

  const handleRegionSelect = (region: string, lat: number, lon: number) => {
    setSelectedRegion(region)
    setSelectedLat(lat)
    setSelectedLon(lon)
  }

  return (
    <div
      style={{
        display: 'flex',
        minHeight: 'calc(100vh - 120px)',
        background: '#ffffff',
        color: '#0f172a',
        fontFamily: 'var(--font-family-sans)',
      }}
    >
      {/* ── 1. LEFT SIDEBAR: FORECAST CONTROLS ─────────────────────────────── */}
      <aside
        style={{
          width: '260px',
          background: '#f8fafc',
          borderRight: '1px solid #cbd5e1',
          padding: '1.25rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
          flexShrink: 0,
        }}
      >
        {/* Department Emblem */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
          <div style={{ width: 40, height: 40, background: '#0b4c8c', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff', fontWeight: 800, fontSize: '0.85rem' }}>
            MoES
          </div>
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 800, color: '#0b4c8c', lineHeight: 1.2 }}>NCMRWF / MoES</div>
            <div style={{ fontSize: '0.68rem', color: '#64748b' }}>Ministry of Earth Sciences, Govt. of India</div>
          </div>
        </div>

        {/* Section Title */}
        <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span>⚙️</span> Forecast Controls
        </div>

        {/* Control 1: NWP Initialization Date */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>📅 NWP Initialization Date</span>
            <span style={{ fontSize: '0.65rem', color: '#64748b', cursor: 'help' }}>ⓘ</span>
          </label>
          <select
            value={initDate}
            onChange={(e) => setInitDate(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '0.8rem',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              background: '#ffffff',
              color: '#0f172a',
              fontWeight: 600,
              outline: 'none',
            }}
          >
            <option value="2024-12-30">2024-12-30</option>
            <option value="2024-12-29">2024-12-29</option>
            <option value="2024-12-28">2024-12-28</option>
            <option value="2024-12-25">2024-12-25</option>
          </select>
        </div>

        {/* Control 2: Forecast Lead Time Slider */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 700, color: '#334155' }}>
            <span>⏱️ Forecast Lead Time</span>
            <span style={{ color: '#dc2626', fontWeight: 800 }}>Day {leadTime}</span>
          </div>
          <input
            type="range"
            min={1}
            max={10}
            value={leadTime}
            onChange={(e) => setLeadTime(Number(e.target.value))}
            style={{ width: '100%', accentColor: '#dc2626', cursor: 'pointer' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#64748b' }}>
            <span>Day 1</span>
            <span>Day 5</span>
            <span>Day 10</span>
          </div>
        </div>

        {/* Control 3: Map Layer Metric Radio Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#334155' }}>
            🗺️ Map Layer Metric
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', cursor: 'pointer', color: '#0f172a' }}>
            <input
              type="radio"
              name="mapMetric"
              checked={mapMetric === 'confidence'}
              onChange={() => setMapMetric('confidence')}
              style={{ accentColor: '#dc2626' }}
            />
            Confidence Score
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', cursor: 'pointer', color: '#0f172a' }}>
            <input
              type="radio"
              name="mapMetric"
              checked={mapMetric === 'prob'}
              onChange={() => setMapMetric('prob')}
              style={{ accentColor: '#dc2626' }}
            />
            Bust Probability
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', cursor: 'pointer', color: '#0f172a' }}>
            <input
              type="radio"
              name="mapMetric"
              checked={mapMetric === 'error'}
              onChange={() => setMapMetric('error')}
              style={{ accentColor: '#dc2626' }}
            />
            Expected Error Magnitude
          </label>
        </div>

        {/* Control 4: Filter Subdivision View */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#334155' }}>
            📌 Filter Subdivision View
          </label>
          <select
            value={subdivisionFilter}
            onChange={(e) => setSubdivisionFilter(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '0.8rem',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              background: '#ffffff',
              color: '#0f172a',
              fontWeight: 600,
              outline: 'none',
            }}
          >
            <option value="all">All Subdivisions (32)</option>
            <option value="bust">Bust Alert Subdivisions Only</option>
            <option value="north">North India Region</option>
            <option value="south">South Peninsula Region</option>
          </select>
        </div>
      </aside>

      {/* ── 2. MAIN COCKPIT WORKSPACE (WHITE BACKGROUND) ────────────────────── */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          padding: '1.25rem',
          gap: '1.25rem',
          background: '#ffffff',
          overflowY: 'auto',
        }}
      >
        {/* Top Header Card */}
        <div
          style={{
            background: 'linear-gradient(135deg, #0b4c8c 0%, #002b5c 100%)',
            color: '#ffffff',
            borderRadius: '10px',
            padding: '1.25rem 1.5rem',
            boxShadow: '0 4px 15px rgba(0, 51, 102, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              🌩️ AI-Based Forecast Bust Detection System
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#93c5fd', margin: '4px 0 0 0' }}>
              National Centre for Medium Range Weather Forecasting (NCMRWF) • Ministry of Earth Sciences (MoES)
            </p>
          </div>
          <div
            style={{
              background: 'rgba(16, 185, 129, 0.2)',
              border: '1px solid #10b981',
              borderRadius: '99px',
              padding: '0.3rem 0.85rem',
              fontSize: '0.72rem',
              fontWeight: 800,
              color: '#34d399',
              letterSpacing: '0.04em',
            }}
          >
            🟢 INFERENCE ENGINE ONLINE • 00Z RUN
          </div>
        </div>

        {/* 4 KPI Indicator Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          {/* Card 1 */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', boxShadow: '0 2px 6px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>⚠️ Subdivisions Under Bust Alert</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#b91c1c', marginTop: '0.2rem' }}>4 / 32 Reg...</div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#dc2626', marginTop: '0.25rem' }}>↑ 12.5% of Country Affected</div>
          </div>

          {/* Card 2 */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', boxShadow: '0 2px 6px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>🛡️ National Mean Forecast Conf...</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0369a1', marginTop: '0.2rem' }}>88.9%</div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#15803d', marginTop: '0.25rem' }}>↑ Day 5 Lead Horizon</div>
          </div>

          {/* Card 3 */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', boxShadow: '0 2px 6px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>🔥 Maximum Bust Hazard</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#c2410c', marginTop: '0.2rem' }}>East Raja...</div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#c2410c', marginTop: '0.25rem' }}>↑ Bust Likelihood: 98%</div>
          </div>

          {/* Card 4 */}
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', boxShadow: '0 2px 6px rgba(0,0,0,0.04)' }}>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>🌪️ Prevailing Synoptic Pattern</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#15803d', marginTop: '0.2rem' }}>Quiescent...</div>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#15803d', marginTop: '0.25rem' }}>↑ Terrain: Central Plateau</div>
          </div>
        </div>

        {/* 2-Column Cockpit Workspace: Map Left, Inspector Right */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 440px', gap: '1.25rem', flex: 1 }}>
          {/* Left Column: Regional Forecast Confidence Map */}
          <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0b4c8c', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              🇮🇳 Regional Forecast Confidence Map • Day {leadTime} ({initDate})
            </h3>
            <div style={{ flex: 1, minHeight: '400px' }}>
              <IndiaMap
                selectedRegion={selectedRegion}
                onRegionSelect={handleRegionSelect}
                locationResult={null}
              />
            </div>
          </div>

          {/* Right Column: Subdivision Diagnostic Inspector Tabs & Details */}
          <div style={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '8px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Tab Header */}
            <div style={{ display: 'flex', borderBottom: '2px solid #e2e8f0', background: '#f8fafc' }}>
              {[
                { id: 'detail', label: 'Operational Confidence Map & Inspector' },
                { id: 'explain', label: 'Synoptic SHAP Explanation' },
                { id: 'whatif', label: 'What-If Simulation Lab' },
              ].map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as Tab)}
                  style={{
                    flex: 1,
                    padding: '0.75rem 0.5rem',
                    border: 'none',
                    background: activeTab === id ? '#ffffff' : 'transparent',
                    color: activeTab === id ? '#0b4c8c' : '#64748b',
                    fontWeight: activeTab === id ? 800 : 600,
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    borderBottom: activeTab === id ? '3px solid #0b4c8c' : '3px solid transparent',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Tab Panels */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
              {activeTab === 'detail' && selectedRegion && (
                <RegionDetail region={selectedRegion} />
              )}
              {activeTab === 'explain' && selectedRegion && (
                <ExplainPanel region={selectedRegion} />
              )}
              {activeTab === 'whatif' && (
                <WhatIfLab initialRegion={selectedRegion ?? undefined} />
              )}
              {!selectedRegion && (
                <EmptyState message="Select a subdivision on the map to inspect." />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
