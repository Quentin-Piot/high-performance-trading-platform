import { postJson, fetchJson } from "./apiClient";

export type JobStatus =
  | "PENDING"
  | "QUEUED"
  | "RUNNING"
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
  return postJson<JobSubmitResponse>("/monte-carlo/jobs", payload);
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