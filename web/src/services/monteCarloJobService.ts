import { postJson, fetchJson, postFormData } from "./apiClient";

export type JobStatus =
  | "PENDING"
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface MonteCarloJobRequest {
  symbol: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  initial_capital: number;
  num_runs: number;
  strategy_params?: Record<string, any>;
  method?: string; // optional, e.g., "bootstrap"
  sample_fraction?: number; // optional
  gaussian_scale?: number; // optional
  // Backend expects numeric JobPriority: 1(low),2(normal),3(high),4(critical)
  priority?: 1 | 2 | 3 | 4;
}

export interface JobSubmitResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobProgressResponse {
  job_id: string;
  status: JobStatus;
  progress?: number; // 0..1
  current_run?: number;
  total_runs?: number;
  eta_seconds?: number | null;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  result?: any;
  error_message?: string | null;
}

export async function submitMonteCarloJob(
  payload: MonteCarloJobRequest
): Promise<JobSubmitResponse> {
  // Ensure a unique identifier per job without overriding existing one
  const uid = (globalThis.crypto?.randomUUID?.() ?? `uid_${Date.now()}_${Math.random().toString(36).slice(2,10)}`);
  const strategyParams = {
    ...(payload.strategy_params || {}),
    unique_id: payload.strategy_params?.unique_id ?? uid,
  };
  const payloadWithId: MonteCarloJobRequest = { ...payload, strategy_params: strategyParams };
  return postJson<JobSubmitResponse>("/monte-carlo/jobs", payloadWithId);
}

export async function submitMonteCarloJobUpload(
  file: File,
  fields: {
    start_date: string;
    end_date: string;
    num_runs: number;
    initial_capital: number;
    strategy_params?: Record<string, any>;
    method?: string;
    priority?: 1 | 2 | 3 | 4;
    timeout_seconds?: number;
  }
): Promise<JobSubmitResponse> {
  const form = new FormData();
  form.append("csv", file);
  form.append("start_date", fields.start_date);
  form.append("end_date", fields.end_date);
  form.append("num_runs", String(fields.num_runs));
  form.append("initial_capital", String(fields.initial_capital));

  // Ensure unique_id in strategy_params_json without overriding existing one
  const uid = (globalThis.crypto?.randomUUID?.() ?? `uid_${Date.now()}_${Math.random().toString(36).slice(2,10)}`);
  const paramsWithId = {
    ...(fields.strategy_params || {}),
    unique_id: fields.strategy_params?.unique_id ?? uid,
  };
  form.append("strategy_params_json", JSON.stringify(paramsWithId));

  if (fields.method) form.append("method", fields.method);
  if (fields.priority) form.append("priority", String(fields.priority));
  if (fields.timeout_seconds) form.append("timeout_seconds", String(fields.timeout_seconds));

  return postFormData<JobSubmitResponse>("/monte-carlo/jobs/upload", form);
}

export async function getMonteCarloJobStatus(
  jobId: string
): Promise<JobProgressResponse> {
  return fetchJson<JobProgressResponse>(`/monte-carlo/jobs/${jobId}/progress`);
}

export async function getMonteCarloJobResult(
  jobId: string
): Promise<JobResponse> {
  return fetchJson<JobResponse>(`/monte-carlo/jobs/${jobId}`);
}