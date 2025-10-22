import { defineStore } from 'pinia'
import { login as loginSvc, register as registerSvc } from '@/services/authService'
import { useErrorStore } from '@/stores/errorStore'

type Credentials = { email: string; password: string }

interface User {
  sub: string
  email: string
  name?: string
  email_verified: boolean
  provider: 'cognito' | 'google'
}

interface AuthState {
  token: string | null
  userEmail: string | undefined
  user: User | null
  isLoading: boolean
  googleAuthUrl: string | null
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
    async register({ email, password }: Credentials) {
      this.isLoading = true
      try {
        const resp = await registerSvc({ email, password })
        this.token = resp.access_token
        this.userEmail = email
        // Set basic user info for Cognito registration
        this.user = {
          sub: resp.sub || '',
          email,
          email_verified: false,
          provider: 'cognito'
        }
        try { localStorage.setItem('token', this.token) } catch { void 0 }
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
        // Set basic user info for Cognito login
        this.user = {
          sub: resp.sub || '',
          email,
          email_verified: resp.email_verified || false,
          provider: 'cognito'
        }
        try { localStorage.setItem('token', this.token) } catch { void 0 }
      } catch (e: unknown) {
        useErrorStore().log('error.auth_login_failed', e instanceof Error ? e.message : String(e), { email })
        throw e
      } finally {
        this.isLoading = false
      }
    },

    async loginWithGoogle(redirectUrl: string = '/dashboard') {
      this.isLoading = true
      try {
        // Redirect to backend Google OAuth endpoint
        const baseUrl = '/api/v1'
        const googleAuthUrl = `${baseUrl}/auth/google/login?redirect_url=${encodeURIComponent(window.location.origin + redirectUrl)}`
        
        // Store the intended redirect URL
        try { localStorage.setItem('google_redirect_url', redirectUrl) } catch { void 0 }
        
        // Redirect to Google OAuth
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
      const error = urlParams.get('error')
      const message = urlParams.get('message')

      if (error) {
        useErrorStore().log('error.google_callback_failed', message || error)
        return false
      }

      if (authStatus === 'success' && provider === 'google' && email) {
        // Set user as authenticated with Google
        this.user = {
          sub: `google_${email}`, // Temporary sub, should be updated with real data
          email,
          email_verified: true,
          provider: 'google'
        }
        this.userEmail = email
        this.token = 'google_authenticated' // Temporary token, should be replaced with real JWT
        
        try { localStorage.setItem('token', this.token) } catch { void 0 }
        
        // Clean up URL parameters
        const cleanUrl = window.location.pathname
        window.history.replaceState({}, document.title, cleanUrl)
        
        return true
      }

      return false
    },

    async fetchUserInfo() {
      if (!this.token) return null
      
      try {
        // This would call the backend to get current user info
        // For now, return the stored user
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
      try { 
        localStorage.removeItem('token')
        localStorage.removeItem('google_redirect_url')
      } catch { void 0 }
    },

    rehydrate() {
      try {
        const t = localStorage.getItem('token')
        if (t) {
          this.token = t
          // Try to restore user info from token or make API call
          // For now, just set token
        }
      } catch { void 0 }
    },
  },
})