import { createContext, useContext } from 'react'
import type { SystemToday } from '../lib/api'

export interface AppContextValue {
  today: SystemToday | null
  isLoading: boolean
}

export const AppContext = createContext<AppContextValue>({
  today: null,
  isLoading: true,
})

export const useAppContext = () => useContext(AppContext)
