import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppContext } from './context/AppContext'
import { api } from './lib/api'
import { Header } from './components/Header'
import { IndiaMap } from './components/IndiaMap'
import { RegionDetail } from './components/RegionDetail'
import { ExplainPanel } from './components/ExplainPanel'
import { WhatIfLab } from './components/WhatIfLab'
import { LoadingSpinner, EmptyState } from './components/UIComponents'

type Tab = 'detail' | 'explain' | 'whatif'

export default function App() {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [selectedLat, setSelectedLat] = useState<number | null>(null)
  const [selectedLon, setSelectedLon] = useState<number | null>(null)
  const [locationResult, setLocationResult] = useState(null)
  const [activeTab, setActiveTab] = useState<Tab>('detail')

  const { data: today, isLoading } = useQuery({
    queryKey: ['system_today'],
    queryFn: api.systemToday,
    staleTime: Infinity,
    retry: 3,
  })

  const handleRegionSelect = (region: string, lat: number, lon: number) => {
    setSelectedRegion(region)
    setSelectedLat(lat)
    setSelectedLon(lon)
    setActiveTab('detail')
  }

  return (
    <AppContext.Provider value={{ today: today ?? null, isLoading }}>
      <div
        style={{
          height: '100dvh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: 'var(--color-surface-50)',
        }}
      >
        <Header />

        {/* System banner if backend not reachable */}
        {!isLoading && !today && (
          <div
            role="alert"
            style={{
              padding: '0.5rem 1.25rem',
              background: '#fff1f2',
              borderBottom: '1px solid #fda4af',
              fontSize: '0.78rem',
              color: '#be123c',
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'center',
            }}
          >
            <span aria-hidden="true">⚠</span>
            Backend API not reachable at{' '}
            <code style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.72rem' }}>
              http://localhost:8000
            </code>
            . Start with{' '}
            <code style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.72rem' }}>
              uvicorn api.main:app
            </code>
            .
          </div>
        )}

        {/* Main layout: map left, detail right */}
        <main
          id="main-content"
          style={{
            flex: 1,
            display: 'grid',
            gridTemplateColumns: '1fr 440px',
            gridTemplateRows: '1fr',
            gap: 0,
            overflow: 'hidden',
          }}
        >
          {/* Left: India Map */}
          <section
            aria-label="India confidence map"
            style={{
              padding: '0.875rem',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              borderRight: '1px solid var(--color-surface-200)',
            }}
          >
            <IndiaMap
              selectedRegion={selectedRegion}
              onRegionSelect={handleRegionSelect}
              locationResult={locationResult}
            />
          </section>

          {/* Right: Tabs panel */}
          <aside
            aria-label="Region analysis panel"
            style={{
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Tab bar */}
            <div
              role="tablist"
              aria-label="Analysis view tabs"
              style={{
                display: 'flex',
                borderBottom: '1px solid var(--color-surface-200)',
                background: 'var(--color-surface-0)',
                padding: '0 0.875rem',
                flexShrink: 0,
              }}
            >
              {([
                { id: 'detail', label: 'Verification', disabled: !selectedRegion },
                { id: 'explain', label: 'Explanation', disabled: !selectedRegion },
                { id: 'whatif', label: 'What-If Lab', disabled: false },
              ] as { id: Tab; label: string; disabled: boolean }[]).map(({ id, label, disabled }) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={activeTab === id}
                  aria-controls={`panel-${id}`}
                  id={`tab-${id}`}
                  disabled={disabled}
                  onClick={() => setActiveTab(id)}
                  style={{
                    padding: '0.625rem 0.875rem',
                    border: 'none',
                    borderBottom: activeTab === id ? '2px solid var(--color-gov-blue-500)' : '2px solid transparent',
                    background: 'transparent',
                    cursor: disabled ? 'not-allowed' : 'pointer',
                    fontSize: '0.78rem',
                    fontWeight: activeTab === id ? 700 : 500,
                    color: activeTab === id
                      ? 'var(--color-gov-blue-700)'
                      : disabled
                      ? 'var(--color-surface-400)'
                      : 'var(--color-surface-600)',
                    letterSpacing: '0.02em',
                    marginBottom: '-1px',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Tab panels */}
            <div
              id="panel-detail"
              role="tabpanel"
              aria-labelledby="tab-detail"
              hidden={activeTab !== 'detail'}
              style={{ flex: 1, overflowY: 'auto', padding: '0.875rem', display: activeTab === 'detail' ? 'flex' : 'none', flexDirection: 'column' }}
            >
              {selectedRegion ? (
                <RegionDetail region={selectedRegion} />
              ) : (
                <EmptyState message="Select a subdivision on the map or search above to view verification data." />
              )}
            </div>

            <div
              id="panel-explain"
              role="tabpanel"
              aria-labelledby="tab-explain"
              hidden={activeTab !== 'explain'}
              style={{ flex: 1, overflowY: 'auto', padding: '0.875rem', display: activeTab === 'explain' ? 'flex' : 'none', flexDirection: 'column' }}
            >
              {selectedRegion ? (
                <ExplainPanel region={selectedRegion} />
              ) : (
                <EmptyState message="Select a region to view SHAP explanations and duty forecaster bulletin." />
              )}
            </div>

            <div
              id="panel-whatif"
              role="tabpanel"
              aria-labelledby="tab-whatif"
              hidden={activeTab !== 'whatif'}
              style={{ flex: 1, overflowY: 'auto', padding: '0.875rem', display: activeTab === 'whatif' ? 'flex' : 'none', flexDirection: 'column' }}
            >
              <WhatIfLab initialRegion={selectedRegion ?? undefined} />
            </div>
          </aside>
        </main>
      </div>
    </AppContext.Provider>
  )
}
