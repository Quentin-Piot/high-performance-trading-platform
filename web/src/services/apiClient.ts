import { useAuthStore } from "@/stores/authStore";

export type AuthResponse = { access_token: string; token_type: string };
export type BacktestResponse = {
  timestamps: string[];
  equity_curve: number[];
  pnl: number;
  drawdown: number;
  sharpe: number;
};

// API base URL configuration using environment variable
// Local: http://localhost:8000/api/v1 (via VITE_API_BASE_URL)
// Production: /api/v1 (default fallback)
const BASE_URL = "/api/v1";

function authHeader(): HeadersInit {
  const store = useAuthStore();
  if (store.token) return { Authorization: `Bearer ${store.token}` };
  return {};
}

export async function fetchJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init.headers || {}),
    ...authHeader(),
  };
  const res = await fetch(url, { ...init, headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function postJson<T>(
  path: string,
  body: unknown,
  init: RequestInit = {},
): Promise<T> {
  return fetchJson<T>(path, {
    ...init,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function postFormData<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: HeadersInit = { ...authHeader() }; // do NOT set Content-Type; browser sets boundary
  const res = await fetch(url, { method: "POST", headers, body: formData });
  if (!res.ok) {
    // Try to surface backend JSON error detail when available
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && typeof data === "object") {
        // FastAPI-style error: { detail: string | object }
        if (typeof data.detail === "string") message = data.detail;
        else if (data.detail && typeof data.detail === "object")
          message = JSON.stringify(data.detail);
      }
    } catch {
      const text = await res.text().catch(() => "");
      if (text) message = text;
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}
