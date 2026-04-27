import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      login: async (username: string, password: string) => {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password }),
        })

        const data = await response.json()

        if (data.success && data.data?.access_token) {
          set({
            user: { username, token: data.data.access_token },
            isAuthenticated: true,
          })
          localStorage.setItem('token', data.data.access_token)
        } else {
          throw new Error(data.message || '登录失败')
        }
      },
      logout: () => {
        set({
          user: null,
          isAuthenticated: false,
        })
        localStorage.removeItem('token')
      },
    }),
    {
      name: 'auth-storage',
    }
  )
)