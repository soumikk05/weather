import React, { useState } from 'react'

interface GovtNavBarProps {
  activeTab?: string
  onTabChange?: (tab: string) => void
}

export function GovtNavBar({ activeTab = 'HOME', onTabChange }: GovtNavBarProps) {
  const [selectedNav, setSelectedNav] = useState(activeTab)

  const navItems = [
    { label: 'HOME', icon: '🏠' },
    { label: 'DEPARTMENTAL WEBSITES', hasDropdown: true },
    { label: 'ABOUT IMD', hasDropdown: true },
    { label: 'PEOPLE', hasDropdown: true },
    { label: 'PUBLICATIONS', hasDropdown: true },
    { label: 'SOP', hasDropdown: true },
    { label: 'SERVICES', hasDropdown: true },
    { label: 'PRESS RELEASE' },
    { label: 'CONTACTS' },
    { label: 'LOCAL FORECAST', hasDropdown: true },
    { label: 'IMD@150' },
    { label: 'IMD API' },
    { label: 'SPECIALIZED AI FORECAST', badge: 'AI-ENGINE' },
  ]

  const handleSelect = (label: string) => {
    setSelectedNav(label)
    if (onTabChange) onTabChange(label)
  }

  return (
    <nav role="navigation" aria-label="Main Government Navigation" style={{ width: '100%', flexShrink: 0 }}>
      {/* 1. Primary Royal Blue Navigation Bar (Matching mausam.imd.gov.in) */}
      <div
        style={{
          background: '#0b4c8c',
          borderBottom: '1px solid #073461',
          padding: '0 0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.15rem',
          overflowX: 'auto',
          whiteSpace: 'nowrap',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        {navItems.map((item) => {
          const isActive = selectedNav === item.label
          return (
            <button
              key={item.label}
              onClick={() => handleSelect(item.label)}
              style={{
                background: isActive ? '#073461' : 'transparent',
                border: 'none',
                color: '#ffffff',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.72rem',
                padding: '0.5rem 0.65rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                letterSpacing: '0.01em',
                transition: 'background 0.15s ease',
                borderBottom: isActive ? '3px solid #ff9933' : '3px solid transparent',
              }}
            >
              {item.icon && <span>{item.icon}</span>}
              {item.label}
              {item.hasDropdown && <span style={{ fontSize: '0.55rem', opacity: 0.8 }}>▾</span>}
              {item.badge && (
                <span
                  style={{
                    background: '#ff9933',
                    color: '#073461',
                    fontSize: '0.58rem',
                    fontWeight: 800,
                    padding: '0.1rem 0.3rem',
                    borderRadius: '3px',
                    marginLeft: '0.2rem',
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* 2. Category Action Bar (Red - Orange - Green - Yellow) matching mausam.imd.gov.in */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr 1.2fr',
          fontSize: '0.8rem',
          fontWeight: 700,
          color: '#ffffff',
          textAlign: 'center',
          boxShadow: '0 2px 5px rgba(0,0,0,0.08)',
        }}
      >
        {/* Red: Warnings */}
        <div
          onClick={() => handleSelect('HOME')}
          style={{
            background: 'linear-gradient(90deg, #dc2626 0%, #b91c1c 100%)',
            padding: '0.5rem 0.75rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            borderRight: '1px solid rgba(255,255,255,0.2)',
            cursor: 'pointer',
          }}
        >
          <div style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            Warnings
          </div>
          <div style={{ fontSize: '0.68rem', fontWeight: 500, opacity: 0.95 }}>
            Subdivisionwise &nbsp;|&nbsp; Districtwise
          </div>
        </div>

        {/* Orange: Nowcast */}
        <div
          onClick={() => handleSelect('HOME')}
          style={{
            background: 'linear-gradient(90deg, #ea580c 0%, #c2410c 100%)',
            padding: '0.5rem 0.75rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            borderRight: '1px solid rgba(255,255,255,0.2)',
            cursor: 'pointer',
          }}
        >
          <div style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            Nowcast
          </div>
          <div style={{ fontSize: '0.68rem', fontWeight: 500, opacity: 0.95 }}>
            Districtwise &nbsp;|&nbsp; Stationwise
          </div>
        </div>

        {/* Green: Public Observation */}
        <div
          onClick={() => handleSelect('HOME')}
          style={{
            background: 'linear-gradient(90deg, #059669 0%, #047857 100%)',
            padding: '0.5rem 0.75rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            borderRight: '1px solid rgba(255,255,255,0.2)',
            cursor: 'pointer',
          }}
        >
          <div style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            Public Observation
          </div>
          <div style={{ fontSize: '0.68rem', fontWeight: 500, opacity: 0.95 }}>
            (Multi Indian Languages) &nbsp;|&nbsp; Weather Realized
          </div>
        </div>

        {/* Yellow/Gold: Specialized Forecast */}
        <div
          onClick={() => handleSelect('SPECIALIZED AI FORECAST')}
          style={{
            background: selectedNav === 'SPECIALIZED AI FORECAST'
              ? 'linear-gradient(90deg, #b45309 0%, #78350f 100%)'
              : 'linear-gradient(90deg, #d97706 0%, #b45309 100%)',
            padding: '0.5rem 0.75rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            cursor: 'pointer',
          }}
        >
          <div style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            Specialized Forecast ⇄
          </div>
          <div style={{ fontSize: '0.68rem', fontWeight: 500, opacity: 0.95 }}>
            Bust Detection & AI Confidence Engine
          </div>
        </div>
      </div>

      {/* 3. Press Release Ticker Bar */}
      <div
        style={{
          background: '#fefce8',
          borderBottom: '1px solid #fef08a',
          padding: '0.35rem 1rem',
          fontSize: '0.72rem',
          color: '#854d0e',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          overflow: 'hidden',
        }}
      >
        <span
          style={{
            background: '#ca8a04',
            color: '#ffffff',
            fontWeight: 800,
            padding: '0.1rem 0.4rem',
            borderRadius: '3px',
            fontSize: '0.65rem',
            flexShrink: 0,
          }}
        >
          PRESS RELEASE
        </span>
        <div style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600 }}>
          <div style={{ display: 'inline-block', paddingLeft: '100%', animation: 'marquee 25s linear infinite' }}>
            📢 Press Release Date: 22nd September 2026 — A Depression lay centered over Bay of Bengal • Operational AI Bulletin: High Forecast Bust Risk detected in East Rajasthan (Day 5 Lead Horizon) • RECRUITMENT TO THE POST OF SCIENTIFIC ASSISTANT IN IMD THROUGH SSC JE EXAMINATION
          </div>
        </div>
      </div>
    </nav>
  )
}
