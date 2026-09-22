import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

export type UserRole = 'user' | 'admin'

export interface UserProfile {
  username: string
  name: string
  role: UserRole
  department?: string
  avatar?: string
}

interface AuthContextType {
  user: UserProfile | null
  isLoggedIn: boolean
  isAdmin: boolean
  loginModalOpen: boolean
  setLoginModalOpen: (open: boolean) => void
  login: (username: string, role: UserRole, name?: string, department?: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const STORAGE_KEY = 'ncmrwf_auth_user'

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [loginModalOpen, setLoginModalOpen] = useState(false)

  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [user])

  const login = (username: string, role: UserRole, name?: string, department?: string) => {
    const profile: UserProfile = {
      username,
      role,
      name: name || (role === 'admin' ? 'Dr. V. Sharma (Duty Forecaster)' : username.split('@')[0] || 'Meteorology Researcher'),
      department: department || (role === 'admin' ? 'NCMRWF / MoES Operational Division' : 'IMD Regional Meteorological Centre'),
    }
    setUser(profile)
    setLoginModalOpen(false)
  }

  const logout = () => {
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn: !!user,
        isAdmin: user?.role === 'admin',
        loginModalOpen,
        setLoginModalOpen,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
