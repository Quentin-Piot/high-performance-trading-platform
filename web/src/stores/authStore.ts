import { defineStore } from 'pinia'
import { login as loginSvc, register as registerSvc } from '@/services/authService'
import { useErrorStore } from '@/stores/errorStore'

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
      try {
        const resp = await registerSvc({ email, password })
        this.token = resp.access_token
        this.userEmail = email
        try { localStorage.setItem('token', this.token) } catch { void 0 }
      } catch (e: unknown) {
        useErrorStore().log('error.auth_register_failed', e instanceof Error ? e.message : String(e), { email })
        throw e
      }
    },
    async login({ email, password }: Credentials) {
      try {
        const resp = await loginSvc({ email, password })
        this.token = resp.access_token
        this.userEmail = email
        try { localStorage.setItem('token', this.token) } catch { void 0 }
      } catch (e: unknown) {
        useErrorStore().log('error.auth_login_failed', e instanceof Error ? e.message : String(e), { email })
        throw e
      }
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