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
      const resp = await postJson<AuthResponse>('/auth/register', { email, password })
      this.token = resp.access_token
      this.userEmail = email
      try { localStorage.setItem('token', this.token) } catch {}
    },
    async login({ email, password }: Credentials) {
      const resp = await postJson<AuthResponse>('/auth/login', { email, password })
      this.token = resp.access_token
      this.userEmail = email
      try { localStorage.setItem('token', this.token) } catch {}
    },
    logout() {
      this.token = null
      this.userEmail = undefined
      try { localStorage.removeItem('token') } catch {}
    },
    rehydrate() {
      try {
        const t = localStorage.getItem('token')
        if (t) this.token = t
      } catch {}
    },
  },
})