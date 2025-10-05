import { useAuthStore } from '@/stores/authStore'

export type AuthResponse = { access_token: string; token_type: string }
export type BacktestResponse = { timestamps: string[]; equity_curve: number[]; pnl: number; drawdown: number; sharpe: number }

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string

function authHeader(): HeadersInit {
  const store = useAuthStore()
  if (store.token) return { Authorization: `Bearer ${store.token}` }
  return {}
}

export async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`
  const headers: HeadersInit = { 'Content-Type': 'application/json', ...(init.headers || {}), ...authHeader() }
  const res = await fetch(url, { ...init, headers })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export async function postJson<T>(path: string, body: unknown, init: RequestInit = {}): Promise<T> {
  return fetchJson<T>(path, { ...init, method: 'POST', body: JSON.stringify(body) })
}

export async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = `${BASE_URL}${path}`
  const headers: HeadersInit = { ...authHeader() } // do NOT set Content-Type; browser sets boundary
  const res = await fetch(url, { method: 'POST', headers, body: formData })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}