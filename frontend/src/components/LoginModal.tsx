import React, { useState } from 'react'
import { useAuth, type UserRole } from '../context/AuthContext'

export function LoginModal() {
  const { loginModalOpen, setLoginModalOpen, login } = useAuth()
  const [activeTab, setActiveTab] = useState<UserRole>('user')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [department, setDepartment] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')

  if (!loginModalOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim()) {
      setError('Please enter your username or Govt email ID')
      return
    }
    if (!password.trim()) {
      setError('Please enter your password')
      return
    }

    if (activeTab === 'admin' && pin && pin !== '1234' && pin !== '0000') {
      // allow default demo pins
      setError('Invalid Duty Officer Security PIN. (Demo PIN: 1234)')
      return
    }

    setError('')
    login(
      username,
      activeTab,
      activeTab === 'admin' ? 'Dr. V. Sharma (Duty Officer)' : username,
      department || (activeTab === 'admin' ? 'NCMRWF Operational Forecasting Division' : 'IMD Regional Meteorological Centre')
    )
  }

  const handleQuickDemo = (role: UserRole) => {
    if (role === 'admin') {
      login('admin.ncmrwf@gov.in', 'admin', 'Dr. V. Sharma (Chief Forecaster)', 'NCMRWF / MoES Operational Division')
    } else {
      login('researcher.imd@gov.in', 'user', 'R. K. Patel (Senior Meteorologist)', 'IMD NWP Verification Wing')
    }
  }

  return (
    <div
      className="modal-overlay animate-fade-in"
      onClick={() => setLoginModalOpen(false)}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 13, 31, 0.75)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '460px',
          background: '#ffffff',
          borderRadius: '12px',
          boxShadow: '0 20px 50px rgba(0, 32, 96, 0.35)',
          border: '1px solid #003366',
          overflow: 'hidden',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            background: 'linear-gradient(135deg, #002b66 0%, #004080 100%)',
            color: '#ffffff',
            padding: '1.25rem 1.5rem',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          {/* Ashoka emblem icon */}
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
              flexShrink: 0,
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#003366" strokeWidth="1.75">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <circle cx="12" cy="11" r="3" />
            </svg>
          </div>

          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, letterSpacing: '0.01em', color: '#ffffff' }}>
              Ministry of Earth Sciences Portal
            </h3>
            <p style={{ fontSize: '0.75rem', color: '#b3d1ff', margin: '2px 0 0 0' }}>
              NCMRWF & IMD Forecast Bust Detection Access
            </p>
          </div>

          {/* Close button */}
          <button
            onClick={() => setLoginModalOpen(false)}
            aria-label="Close dialog"
            style={{
              position: 'absolute',
              top: '12px',
              right: '14px',
              background: 'rgba(255, 255, 255, 0.15)',
              border: 'none',
              color: '#ffffff',
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1rem',
            }}
          >
            ✕
          </button>
        </div>

        {/* Role Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '2px solid #e2e8f0',
            background: '#f8fafc',
          }}
        >
          <button
            type="button"
            onClick={() => {
              setActiveTab('user')
              setError('')
            }}
            style={{
              flex: 1,
              padding: '0.75rem 1rem',
              border: 'none',
              borderBottom: activeTab === 'user' ? '3px solid #004080' : '3px solid transparent',
              background: activeTab === 'user' ? '#ffffff' : 'transparent',
              color: activeTab === 'user' ? '#003366' : '#64748b',
              fontWeight: activeTab === 'user' ? 700 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            <span>👤</span> General User Login
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('admin')
              setError('')
            }}
            style={{
              flex: 1,
              padding: '0.75rem 1rem',
              border: 'none',
              borderBottom: activeTab === 'admin' ? '3px solid #b45309' : '3px solid transparent',
              background: activeTab === 'admin' ? '#ffffff' : 'transparent',
              color: activeTab === 'admin' ? '#b45309' : '#64748b',
              fontWeight: activeTab === 'admin' ? 700 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            <span>🛡️</span> Admin / Forecaster Login
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '1.25rem 1.5rem' }}>
          {error && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.625rem 0.875rem',
                background: '#fef2f2',
                border: '1px solid #fca5a5',
                borderRadius: '6px',
                color: '#b91c1c',
                fontSize: '0.78rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>⚠️</span> {error}
            </div>
          )}

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.35rem' }}>
              {activeTab === 'admin' ? 'Official MoES / NCMRWF Email or Employee ID' : 'Govt Email / Registered Username'}
            </label>
            <input
              type="text"
              placeholder={activeTab === 'admin' ? 'e.g. duty officer@ncmrwf.gov.in' : 'e.g. user@imd.gov.in'}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.85rem',
                color: '#0f172a',
                outline: 'none',
              }}
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.35rem' }}>
              Password
            </label>
            <input
              type="password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.85rem',
                color: '#0f172a',
                outline: 'none',
              }}
            />
          </div>

          {activeTab === 'admin' && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.35rem' }}>
                Duty Forecaster Security PIN (Demo: <code style={{ color: '#004080' }}>1234</code>)
              </label>
              <input
                type="password"
                placeholder="4-digit Security PIN"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                maxLength={4}
                style={{
                  width: '100%',
                  padding: '0.6rem 0.75rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  color: '#0f172a',
                  outline: 'none',
                  letterSpacing: '0.2em',
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.35rem' }}>
              Department / Meteorological Centre (Optional)
            </label>
            <input
              type="text"
              placeholder={activeTab === 'admin' ? 'NCMRWF Operational Forecasting Center' : 'IMD Regional Centre / University'}
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.75rem',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '0.85rem',
                color: '#0f172a',
                outline: 'none',
              }}
            />
          </div>

          {/* Action buttons */}
          <button
            type="submit"
            style={{
              width: '100%',
              padding: '0.75rem',
              background: activeTab === 'admin' ? 'linear-gradient(135deg, #b45309 0%, #d97706 100%)' : 'linear-gradient(135deg, #003366 0%, #004080 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              marginBottom: '1rem',
            }}
          >
            {activeTab === 'admin' ? 'Authenticate as Duty Forecaster' : 'Sign In as General User'}
          </button>

          {/* Quick Demo Login shortcuts */}
          <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '0.875rem', textAlign: 'center' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', display: 'block', marginBottom: '0.5rem' }}>
              ⚡ Quick Demo One-Click Sign In:
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => handleQuickDemo('user')}
                style={{
                  flex: 1,
                  padding: '0.4rem 0.5rem',
                  background: '#f1f5f9',
                  border: '1px solid #cbd5e1',
                  borderRadius: '4px',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  color: '#003366',
                  cursor: 'pointer',
                }}
              >
                👤 Quick User Login
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo('admin')}
                style={{
                  flex: 1,
                  padding: '0.4rem 0.5rem',
                  background: '#fef3c7',
                  border: '1px solid #f59e0b',
                  borderRadius: '4px',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: '#92400e',
                  cursor: 'pointer',
                }}
              >
                🛡️ Quick Admin Login
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
