import { useAuthStore } from "@/stores/authStore";
export type AuthResponse = {
	access_token: string;
	token_type: string;
	sub?: string;
	email_verified?: boolean;
};
export type BacktestResponse = {
	timestamps: string[];
	equity_curve: number[];
	pnl: number;
	drawdown: number;
	sharpe: number;
};
export const BASE_URL = "/api/v1";
export function buildWsUrl(path: string): string {
	const base = BASE_URL.replace(/^http/, "ws");
	return `${base}${path}`;
}

function authHeader(): HeadersInit {
	const store = useAuthStore();
	if (store.token) return { Authorization: `Bearer ${store.token}` };
	return {};
}

async function buildHttpError(res: Response): Promise<Error> {
	let message = `HTTP ${res.status}`;
	try {
		const data = await res.json();
		if (data && typeof data === "object") {
			if ("detail" in data) {
				const detail = (data as { detail?: unknown }).detail;
				if (typeof detail === "string") message = detail;
				else if (detail && typeof detail === "object")
					message = JSON.stringify(detail);
			}
		}
	} catch {
		const text = await res.text().catch(() => "");
		if (text) message = text;
	}
	return new Error(message);
}

export async function fetchJson<T>(
	path: string,
	init: RequestInit = {},
): Promise<T> {
	const url = `${BASE_URL}${path}`;
	const hasBody = init.body !== undefined && init.body !== null;
	const headers: HeadersInit = {
		...(hasBody ? { "Content-Type": "application/json" } : {}),
		...(init.headers || {}),
		...authHeader(),
	};
	const res = await fetch(url, { ...init, headers });
	if (!res.ok) throw await buildHttpError(res);
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
	const headers: HeadersInit = { ...authHeader() };
	const res = await fetch(url, { method: "POST", headers, body: formData });
	if (!res.ok) {
		throw await buildHttpError(res);
	}
	return res.json() as Promise<T>;
}
