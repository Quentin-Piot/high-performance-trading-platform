import { defineStore } from 'pinia'
import { postJson, type AuthResponse } from '@/services/apiClient'

type Credentials = { email: string; password: string }

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null as string | null,
    userEmail: undefined as string | undefined,
  }),
  getters: {
    isAuthenticated: (s) => !!s.token,
  },
  actions: {
    async register({ email, password }: Credentials) {
      const resp = await postJson<AuthResponse>('/api/v1/auth/register', { email, password })
      this.token = resp.access_token
      this.userEmail = email
      try { localStorage.setItem('token', this.token) } catch { void 0 }
    },
    async login({ email, password }: Credentials) {
      const resp = await postJson<AuthResponse>('/api/v1/auth/login', { email, password })
      this.token = resp.access_token
      this.userEmail = email
      try { localStorage.setItem('token', this.token) } catch { void 0 }
    },
    logout() {
      this.token = null
      this.userEmail = undefined
      try { localStorage.removeItem('token') } catch { void 0 }
    },
    rehydrate() {
      try {
        const t = localStorage.getItem('token')
        if (t) this.token = t
      } catch { void 0 }
    },
  },
})