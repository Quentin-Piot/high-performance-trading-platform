import { buildWsUrl } from "@/services/apiClient";

export type MonteCarloJobStatus =
	| "submitted"
	| "processing"
	| "completed"
	| "failed"
	| "cancelled"
	| "not_found";

type RawMonteCarloJobStatus = MonteCarloJobStatus | "pending" | "running";

type RawMonteCarloWsMessage = {
	job_id: string;
	status: RawMonteCarloJobStatus;
	progress: number | null;
	runs?: number;
	started_at?: string | null;
	completed_at?: string | null;
	error?: string | null;
};

export type MonteCarloWsMessage = {
	job_id: string;
	status: MonteCarloJobStatus;
	progress: number | null;
	runs?: number;
	started_at?: string | null;
	completed_at?: string | null;
	error?: string | null;
};

function normalizeJobStatus(
	status: RawMonteCarloJobStatus,
): MonteCarloJobStatus {
	if (status === "pending") return "submitted";
	if (status === "running") return "processing";
	return status;
}

export type MonteCarloProgressHandler = (msg: MonteCarloWsMessage) => void;

export type ConnectOptions = {
	onOpen?: () => void;
	onUpdate?: MonteCarloProgressHandler;
	onError?: (err: Event | Error) => void;
	onClose?: (ev: CloseEvent) => void;
};

export type Connection = {
	socket: WebSocket;
	disconnect: () => void;
};

export function connectMonteCarloProgress(
	jobId: string,
	opts: ConnectOptions = {},
): Connection {
	const url = buildWsUrl(`/monte-carlo/ws/${encodeURIComponent(jobId)}`);
	const socket = new WebSocket(url);

	socket.addEventListener("open", () => {
		opts.onOpen?.();
	});

	socket.addEventListener("message", (event) => {
		try {
			const data = JSON.parse(event.data) as RawMonteCarloWsMessage;
			let progress = data.progress;
			if (typeof progress === "number") {
				if (progress < 0) progress = 0;
				if (progress > 1) progress = 1;
			}
			const normalized: MonteCarloWsMessage = {
				...data,
				status: normalizeJobStatus(data.status),
				progress,
			};
			opts.onUpdate?.(normalized);
			if (
				["completed", "failed", "cancelled", "not_found"].includes(
					normalized.status,
				)
			) {
				try {
					socket.close();
				} catch {}
			}
		} catch (e) {
			opts.onError?.(e as Error);
		}
	});

	socket.addEventListener("error", (e) => {
		opts.onError?.(e);
	});

	socket.addEventListener("close", (ev) => {
		opts.onClose?.(ev);
	});

	return {
		socket,
		disconnect: () => {
			try {
				socket.close();
			} catch {}
		},
	};
}
export async function waitForMonteCarloCompletion(
	jobId: string,
	opts: Omit<ConnectOptions, "onUpdate"> = {},
): Promise<MonteCarloWsMessage> {
	return new Promise((resolve, reject) => {
		const { disconnect } = connectMonteCarloProgress(jobId, {
			...opts,
			onUpdate: (msg) => {
				if (
					["completed", "failed", "cancelled", "not_found"].includes(msg.status)
				) {
					disconnect();
					resolve(msg);
				}
			},
			onError: (e) => {
				opts.onError?.(e);
				disconnect();
				reject(e);
			},
		});
	});
}
