import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppContext } from './context/AppContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import { api } from './lib/api'
import { Header } from './components/Header'
import { GovtNavBar } from './components/GovtNavBar'
import { LoginModal } from './components/LoginModal'
import { IMDHomePortal } from './components/IMDHomePortal'
import { AICockpit } from './components/AICockpit'

type MainView = 'HOME' | 'SPECIALIZED AI FORECAST'

function MainLayout() {
  const [activeMainView, setActiveMainView] = useState<MainView>('HOME')
  const { user, isLoggedIn, isAdmin, setLoginModalOpen } = useAuth()

  // Automatically switch to full AI Cockpit when user or admin logs in
  useEffect(() => {
    if (isLoggedIn) {
      setActiveMainView('SPECIALIZED AI FORECAST')
    }
  }, [isLoggedIn])

  const { data: today, isLoading } = useQuery({
    queryKey: ['system_today'],
    queryFn: api.systemToday,
    staleTime: Infinity,
    retry: 3,
  })

  const handleNavTabChange = (navLabel: string) => {
    if (navLabel === 'SPECIALIZED AI FORECAST') {
      setActiveMainView('SPECIALIZED AI FORECAST')
    } else if (navLabel === 'HOME') {
      setActiveMainView('HOME')
    }
  }

  return (
    <AppContext.Provider value={{ today: today ?? null, isLoading }}>
      <div
        style={{
          minHeight: '100dvh',
          display: 'flex',
          flexDirection: 'column',
          background: '#ffffff',
          color: '#0f172a',
        }}
      >
        {/* 1. Official Govt Header */}
        <Header />

        {/* 2. Official Govt Navigation Bar & Category Ticker */}
        <GovtNavBar activeTab={activeMainView} onTabChange={handleNavTabChange} />

        {/* 3. Login Dialog */}
        <LoginModal />

        {/* User / Admin Session Notification Banner */}
        {isLoggedIn && (
          <div
            style={{
              background: isAdmin
                ? 'linear-gradient(90deg, #7c2d12 0%, #9a3412 100%)'
                : 'linear-gradient(90deg, #075985 0%, #0369a1 100%)',
              color: '#ffffff',
              padding: '0.4rem 1.25rem',
              fontSize: '0.78rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>{isAdmin ? '🛡️' : '👤'}</span>
              <span>
                <strong>AUTHENTICATED SESSION:</strong> Welcome {user?.name} ({user?.department}).
                All AI Forecast Bust Detection & Diagnostic features unlocked on White Theme.
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => setActiveMainView('HOME')}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  border: '1px solid rgba(255,255,255,0.4)',
                  color: '#ffffff',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '3px',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Govt Portal View
              </button>
              <button
                onClick={() => setActiveMainView('SPECIALIZED AI FORECAST')}
                style={{
                  background: '#ff9933',
                  border: 'none',
                  color: '#002b5c',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '3px',
                  fontSize: '0.68rem',
                  fontWeight: 800,
                  cursor: 'pointer',
                }}
              >
                AI Cockpit View
              </button>
            </div>
          </div>
        )}

        {/* System banner if backend not reachable */}
        {!isLoading && !today && (
          <div
            role="alert"
            style={{
              padding: '0.4rem 1.25rem',
              background: '#fff1f2',
              borderBottom: '1px solid #fda4af',
              fontSize: '0.75rem',
              color: '#be123c',
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'center',
            }}
          >
            <span aria-hidden="true">⚠</span>
            Backend API not reachable at{' '}
            <code style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.72rem' }}>
              http://127.0.0.1:8000
            </code>
            . Run <code style={{ fontFamily: 'var(--font-family-mono)', fontSize: '0.72rem' }}>python launch.py</code> in backend.
          </div>
        )}

        {/* VIEW 1: PUBLIC IMD HOME PORTAL */}
        {activeMainView === 'HOME' && (
          <IMDHomePortal
            onOpenAICockpit={() => setActiveMainView('SPECIALIZED AI FORECAST')}
            onOpenLogin={() => setLoginModalOpen(true)}
          />
        )}

        {/* VIEW 2: FULL AI FORECAST BUST DETECTION SYSTEM COCKPIT (WHITE THEME) */}
        {activeMainView === 'SPECIALIZED AI FORECAST' && (
          <AICockpit />
        )}
      </div>
    </AppContext.Provider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  )
}
