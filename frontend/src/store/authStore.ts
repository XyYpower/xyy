import { create } from 'zustand'
import { authApi, type User } from '../api/auth'
import { ACCESS_KEY, REFRESH_KEY } from './authTokens'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string) => Promise<void>
  loadMe: () => Promise<void>
  refreshAccessToken: () => Promise<string | null>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem(ACCESS_KEY),
  refreshToken: localStorage.getItem(REFRESH_KEY),
  isAuthenticated: Boolean(localStorage.getItem(ACCESS_KEY)),

  login: async (username, password) => {
    const res = await authApi.login({ username, password })
    localStorage.setItem(ACCESS_KEY, res.data.access_token)
    localStorage.setItem(REFRESH_KEY, res.data.refresh_token)
    set({
      user: res.data.user,
      accessToken: res.data.access_token,
      refreshToken: res.data.refresh_token,
      isAuthenticated: true,
    })
  },

  register: async (username, password) => {
    const res = await authApi.register({ username, password })
    localStorage.setItem(ACCESS_KEY, res.data.access_token)
    localStorage.setItem(REFRESH_KEY, res.data.refresh_token)
    set({
      user: res.data.user,
      accessToken: res.data.access_token,
      refreshToken: res.data.refresh_token,
      isAuthenticated: true,
    })
  },

  loadMe: async () => {
    if (!get().accessToken) return
    const res = await authApi.me()
    set({ user: res.data, isAuthenticated: true })
  },

  refreshAccessToken: async () => {
    const refreshToken = get().refreshToken || localStorage.getItem(REFRESH_KEY)
    if (!refreshToken) return null
    try {
      const res = await authApi.refresh(refreshToken)
      localStorage.setItem(ACCESS_KEY, res.data.access_token)
      localStorage.setItem(REFRESH_KEY, res.data.refresh_token)
      set({
        user: res.data.user,
        accessToken: res.data.access_token,
        refreshToken: res.data.refresh_token,
        isAuthenticated: true,
      })
      return res.data.access_token
    } catch {
      get().logout()
      return null
    }
  },

  logout: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
  },
}))
