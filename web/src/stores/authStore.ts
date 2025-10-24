import { defineStore } from 'pinia'
import { login as loginSvc, register as registerSvc } from '@/services/authService'
import { useErrorStore } from '@/stores/errorStore'
type Credentials = { email: string; password: string }
interface User {
  sub?: string
  email: string
  name?: string
  email_verified?: boolean
  provider: 'cognito' | 'google'
}
interface AuthState {
  token: string | null
  userEmail: string | undefined
  user: User | null
  isLoading: boolean
  googleAuthUrl: string | null
}
const STORAGE_KEYS = {
  TOKEN: 'hptp_auth_token',
  USER: 'hptp_user_data',
  USER_EMAIL: 'hptp_user_email'
} as const
const secureStorage = {
  setItem: (key: string, value: string) => {
    try {
      localStorage.setItem(key, value)
    } catch (error) {
      console.warn('Failed to save to localStorage:', error)
    }
  },
  getItem: (key: string): string | null => {
    try {
      return localStorage.getItem(key)
    } catch (error) {
      console.warn('Failed to read from localStorage:', error)
      return null
    }
  },
  removeItem: (key: string) => {
    try {
      localStorage.removeItem(key)
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error)
    }
  },
  clear: () => {
    try {
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key)
      })
    } catch (error) {
      console.warn('Failed to clear localStorage:', error)
    }
  }
}
export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: null,
    userEmail: undefined,
    user: null,
    isLoading: false,
    googleAuthUrl: null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.token && !!s.user,
    isGoogleUser: (s) => s.user?.provider === 'google',
    isCognitoUser: (s) => s.user?.provider === 'cognito',
    userName: (s) => s.user?.name || s.user?.email?.split('@')[0] || 'User',
  },
  actions: {
    persistUserData() {
      if (this.token) {
        secureStorage.setItem(STORAGE_KEYS.TOKEN, this.token)
      }
      if (this.user) {
        secureStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(this.user))
      }
      if (this.userEmail) {
        secureStorage.setItem(STORAGE_KEYS.USER_EMAIL, this.userEmail)
      }
    },
    loadPersistedData() {
      const token = secureStorage.getItem(STORAGE_KEYS.TOKEN)
      const userData = secureStorage.getItem(STORAGE_KEYS.USER)
      const userEmail = secureStorage.getItem(STORAGE_KEYS.USER_EMAIL)
      if (token) {
        this.token = token
      }
      if (userData) {
        try {
          this.user = JSON.parse(userData)
        } catch (error) {
          console.warn('Failed to parse user data from localStorage:', error)
          secureStorage.removeItem(STORAGE_KEYS.USER)
        }
      }
      if (userEmail) {
        this.userEmail = userEmail
      }
    },
    async register({ email, password }: Credentials) {
      this.isLoading = true
      try {
        const resp = await registerSvc({ email, password })
        this.token = resp.access_token
        this.userEmail = email
        this.user = {
          sub: resp.sub || '',
          email,
          email_verified: resp.email_verified || false,
          provider: 'cognito'
        }
        this.persistUserData()
      } catch (e: unknown) {
        useErrorStore().log('error.auth_register_failed', e instanceof Error ? e.message : String(e), { email })
        throw e
      } finally {
        this.isLoading = false
      }
    },
    async login({ email, password }: Credentials) {
      this.isLoading = true
      try {
        const resp = await loginSvc({ email, password })
        this.token = resp.access_token
        this.userEmail = email
        this.user = {
          sub: resp.sub || '',
          email,
          email_verified: resp.email_verified || false,
          provider: 'cognito'
        }
        this.persistUserData()
      } catch (e: unknown) {
        useErrorStore().log('error.auth_login_failed', e instanceof Error ? e.message : String(e), { email })
        throw e
      } finally {
        this.isLoading = false
      }
    },
    async loginWithGoogle(redirectUrl: string = '/simulate') {
      this.isLoading = true
      try {
        const baseUrl = '/api/v1'
        const googleAuthUrl = `${baseUrl}/auth/google/login?redirect_url=${encodeURIComponent(window.location.origin + redirectUrl)}`
        secureStorage.setItem('google_redirect_url', redirectUrl)
        window.location.href = googleAuthUrl
      } catch (e: unknown) {
        useErrorStore().log('error.google_auth_failed', e instanceof Error ? e.message : String(e))
        this.isLoading = false
        throw e
      }
    },
    async handleGoogleCallback() {
      const urlParams = new URLSearchParams(window.location.search)
      const authStatus = urlParams.get('auth')
      const provider = urlParams.get('provider')
      const email = urlParams.get('email')
      const userId = urlParams.get('user_id')
      const token = urlParams.get('token')
      const identityId = urlParams.get('identity_id')
      const error = urlParams.get('error')
      const message = urlParams.get('message')
      if (error) {
        useErrorStore().log('error.google_callback_failed', message || error)
        return false
      }
      if (authStatus === 'success' && provider === 'google' && email && token) {
        this.user = {
          sub: identityId || `google_${userId}`,
          email,
          email_verified: true,
          provider: 'google'
        }
        this.userEmail = email
        this.token = token 
        this.persistUserData()
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
        return true
      }
      return false
    },
    async fetchUserInfo() {
      if (!this.token) return null
      try {
        return this.user
      } catch (e: unknown) {
        useErrorStore().log('error.fetch_user_failed', e instanceof Error ? e.message : String(e))
        return null
      }
    },
    logout() {
      this.token = null
      this.userEmail = undefined
      this.user = null
      this.googleAuthUrl = null
      secureStorage.clear()
    },
    rehydrate() {
      this.loadPersistedData()
      if (this.token && !this.user) {
        this.logout()
      }
    },
  },
})