import { postJson, type AuthResponse } from '@/services/apiClient'
import { retry } from '@/lib/retry'

export type Credentials = { email: string; password: string }

export async function register(credentials: Credentials): Promise<AuthResponse> {
  return retry(() => postJson<AuthResponse>('/api/v1/auth/register', credentials))
}

export async function login(credentials: Credentials): Promise<AuthResponse> {
  return retry(() => postJson<AuthResponse>('/api/v1/auth/login', credentials))
}