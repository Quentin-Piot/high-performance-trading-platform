export async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 15000)
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } finally {
    clearTimeout(timer)
  }
}
export async function postJson<T>(url: string, body: unknown, init?: RequestInit): Promise<T> {
  return getJson<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    body: JSON.stringify(body),
    ...init,
  })
}
export async function postForm<T>(url: string, form: FormData, init?: RequestInit): Promise<T> {
  return getJson<T>(url, {
    method: 'POST',
    body: form,
    ...init,
  })
}