import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { DataSourcesPanel } from './DataSourcesPanel'

export function Header() {
  const { today } = useAppContext()
  const { user, isLoggedIn, isAdmin, setLoginModalOpen, logout } = useAuth()
  const [dsOpen, setDsOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <>
      {/* Topmost Social & Utilities Bar */}
      <div
        style={{
          background: '#073461',
          padding: '0.2rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: '0.75rem',
          fontSize: '0.72rem',
          color: '#ffffff',
        }}
      >
        {/* Social Icons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ cursor: 'pointer' }} title="Facebook">📘</span>
          <span style={{ cursor: 'pointer' }} title="YouTube">🔴</span>
          <span style={{ cursor: 'pointer' }} title="Twitter / X">🐦</span>
          <span style={{ cursor: 'pointer' }} title="Instagram">📷</span>
          <span style={{ cursor: 'pointer' }} title="Feedback">💬</span>
        </div>

        {/* Language Toggle */}
        <button
          style={{
            background: '#dc2626',
            color: '#ffffff',
            border: 'none',
            borderRadius: '3px',
            padding: '0.15rem 0.5rem',
            fontSize: '0.68rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          हिंदी वेबसाइट
        </button>

        {/* Data Sources Trigger */}
        <button
          onClick={() => setDsOpen(true)}
          style={{
            background: 'rgba(255,255,255,0.15)',
            border: '1px solid rgba(255,255,255,0.3)',
            borderRadius: '3px',
            color: '#ffffff',
            fontSize: '0.68rem',
            fontWeight: 600,
            padding: '0.15rem 0.5rem',
            cursor: 'pointer',
          }}
        >
          Data Sources
        </button>
      </div>

      {/* Main Government Banner (matching mausam.imd.gov.in) */}
      <header
        role="banner"
        style={{
          background: '#0b4c8c',
          color: '#ffffff',
          padding: '0.5rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          borderBottom: '1px solid #073461',
        }}
      >
        {/* Left: Golden State Emblem & Official Titles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <img
            src="/emblem.png"
            alt="State Emblem of India"
            style={{ height: '54px', width: 'auto', objectFit: 'contain' }}
          />

          <div>
            <h1 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, lineHeight: 1.2, color: '#ffffff', letterSpacing: '0.01em' }}>
              India Meteorological Department
            </h1>
            <h2 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0, lineHeight: 1.2, color: '#ffffff' }}>
              Ministry Of Earth Sciences
            </h2>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 500, margin: 0, lineHeight: 1.2, color: '#ffffff' }}>
              Government Of India
            </h3>
          </div>
        </div>

        {/* Center: Search Bar */}
        <div style={{ flex: 1, maxWidth: '380px', display: 'flex', gap: 0 }}>
          <input
            type="text"
            placeholder="Search here..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              padding: '0.45rem 0.75rem',
              fontSize: '0.82rem',
              border: '1px solid #ffffff',
              borderRight: 'none',
              borderRadius: '4px 0 0 4px',
              outline: 'none',
              color: '#0f172a',
              background: '#ffffff',
            }}
          />
          <button
            style={{
              padding: '0.45rem 0.85rem',
              background: '#073461',
              border: '1px solid #ffffff',
              borderRadius: '0 4px 4px 0',
              color: '#ffffff',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            🔍
          </button>
        </div>

        {/* Right Logos & User / Admin Login Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* Top Right Golden State Emblem of India */}
          <img
            src="/emblem.png"
            alt="State Emblem of India"
            style={{ height: '50px', width: 'auto', objectFit: 'contain', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))' }}
          />

          {/* Government Emblem / 150 Years Emblem Badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#ffffff', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>
            <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#0b4c8c' }}>150 YEARS</span>
            <span style={{ width: 1, height: 18, background: '#cbd5e1' }} />
            <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#006699' }}>ESSO</span>
            <span style={{ width: 1, height: 18, background: '#cbd5e1' }} />
            <span style={{ fontSize: '0.65rem', fontWeight: 800, color: '#b45309' }}>MoES</span>
          </div>

          {/* TOP RIGHT LOGIN BUTTON */}
          {!isLoggedIn ? (
            <button
              onClick={() => setLoginModalOpen(true)}
              style={{
                background: 'linear-gradient(135deg, #ff9933 0%, #e67e22 100%)',
                border: '1px solid #ffffff',
                borderRadius: '4px',
                color: '#002b5c',
                fontSize: '0.82rem',
                fontWeight: 800,
                padding: '0.45rem 0.95rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                whiteSpace: 'nowrap',
              }}
            >
              <span>🔑</span> Login (User / Admin)
            </button>
          ) : (
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                style={{
                  background: isAdmin ? '#b45309' : '#1e3f7f',
                  border: '1px solid #ffffff',
                  borderRadius: '4px',
                  color: '#ffffff',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  padding: '0.4rem 0.8rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>{isAdmin ? '🛡️' : '👤'}</span>
                <span>{isAdmin ? 'Admin' : 'User'}: {user?.name.split(' ')[0]}</span>
                <span>▾</span>
              </button>

              {userMenuOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: '110%',
                    right: 0,
                    width: '230px',
                    background: '#ffffff',
                    color: '#0f172a',
                    borderRadius: '6px',
                    boxShadow: '0 10px 25px rgba(0,0,0,0.25)',
                    border: '1px solid #cbd5e1',
                    padding: '0.75rem',
                    zIndex: 200,
                  }}
                >
                  <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#0b4c8c' }}>{user?.name}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{user?.department}</div>
                    <span
                      style={{
                        display: 'inline-block',
                        marginTop: '4px',
                        padding: '0.15rem 0.4rem',
                        background: isAdmin ? '#fef3c7' : '#dbeafe',
                        color: isAdmin ? '#92400e' : '#1e40af',
                        borderRadius: '3px',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                      }}
                    >
                      ROLE: {user?.role.toUpperCase()}
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      logout()
                      setUserMenuOpen(false)
                    }}
                    style={{
                      width: '100%',
                      padding: '0.4rem',
                      background: '#fef2f2',
                      border: '1px solid #fca5a5',
                      color: '#b91c1c',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Log Out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      <DataSourcesPanel open={dsOpen} onClose={() => setDsOpen(false)} />
    </>
  )
}
