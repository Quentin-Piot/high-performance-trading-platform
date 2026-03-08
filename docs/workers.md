# Async Workers and Parallel Execution (Current Implementation)

## Why This Document Exists

This repository has **two different concurrency layers** for Monte Carlo execution. They are often confused.

This document separates them clearly:
- application-level async job worker (thread-based)
- compute-level parallel Monte Carlo execution (process-based)

## 1) Application-Level Async Worker: `SimpleMonteCarloWorker`

Primary file:
- `backend/api/src/workers/simple_worker.py`

## Role

`SimpleMonteCarloWorker` makes long Monte Carlo computations non-blocking for the HTTP API.

It is responsible for:
- creating and tracking job state (`job_id`, status, progress)
- running jobs in background threads
- storing runtime results/errors
- exposing progress/results through API routes and WebSocket

## Concurrency Model

- `ThreadPoolExecutor(max_workers=max_concurrent_jobs)`
- default global worker instance uses `max_concurrent_jobs=2`
- jobs stored in-memory in `self.jobs: dict[str, SimpleMonteCarloJob]`

This layer is about **job orchestration**, not CPU-optimized simulation throughput.

## Job Input (What It Consumes)

A submitted async Monte Carlo job includes:
- `csv_data` (bytes)
- `filename`
- `strategy_name`
- `strategy_params`
- `runs`
- `method` (`bootstrap` or `gaussian`)
- `method_params`
- `price_type`
- `normalize`
- optional callback

## Job Output (What It Produces)

Runtime job snapshot shape includes:
- `job_id`
- `status` (`pending`, `running`, `completed`, `failed`, `cancelled`)
- `progress` (`0.0` to `1.0`)
- timestamps (`created_at`, `started_at`, `completed_at`)
- `result` (Monte Carlo summary)
- `error` (failure message)
- `runs`, `filename`

## Lifecycle and State Transitions

Typical state flow:
- `pending` -> `running` -> `completed`

Failure/cancel paths:
- `pending`/`running` -> `failed`
- `pending`/`running` -> `cancelled` (logical cancel)

## Progress Tracking (Thread Worker View)

Inside `_execute_job(...)`, the worker passes a `progress_callback(processed, total)` to the Monte Carlo service.

Worker-side behavior:
- converts processed/total to ratio `progress`
- updates job state under lock
- emits debug logs

This means the UI progress bar is based on **real compute progress**, not a frontend timer.

## Error Handling (Thread Worker View)

The worker wraps execution in `try/except` and on error:
- sets `status = "failed"`
- stores `error`
- sets `completed_at`
- logs stack trace (`exc_info=True`)
- calls callback with error payload (best effort)

## Cancellation Semantics (Important Limitation)

`cancel_job(job_id)` performs a **logical cancellation**:
- it marks the job as `cancelled`
- it does not guarantee immediate interruption of an in-flight CPU computation

This is acceptable for MVP UX, but not a hard cancellation mechanism.

## Cleanup Behavior

`start_cleanup_task()` starts a background daemon thread that periodically:
- removes old terminal-state jobs (`completed`, `failed`, `cancelled`)
- default retention window: 24h

This prevents unbounded growth of in-memory job metadata.

## 2) Compute-Level Parallelism: `ProcessPoolExecutor` in Monte Carlo Service

Primary file:
- `backend/api/src/services/mc_backtest_service.py`

## Role

This is not a job worker service. It is a **CPU parallelization mechanism** used inside a single Monte Carlo request/job.

It parallelizes individual Monte Carlo simulation runs using:
- `ProcessPoolExecutor`

## When It Is Used

`run_monte_carlo_on_df(...)` chooses between sequential and process-pool execution based on:
- `runs > 1`
- `parallel_workers > 1`

Current API behavior:
- API paths pass `DEFAULT_PARALLEL_WORKERS` explicitly (CPU-aware default from the Monte Carlo service)
- this may enable the process pool automatically depending on the machine/runtime

## What It Consumes

Each process-pool task receives serialized worker args including:
- CSV bytes
- strategy name + params
- method + method params
- seed
- price type

Each process reconstructs a synthetic series and runs the backtest independently.

## What It Produces

Each task returns a `MonteCarloResult` (or `None` on failure) containing:
- `pnl`
- `sharpe`
- `drawdown`
- optional `equity_curve`

The parent process aggregates all successful runs into:
- metrics distributions (`pnl`, `sharpe`, `drawdown`)
- optional `equity_envelope`

## Progress Tracking (Process Pool View)

Progress is tracked in the **parent process**, not in child processes.

Implementation detail:
- parent iterates `as_completed(futures)`
- increments `completed_runs`
- throttles updates (time/progress thresholds)
- invokes the shared `progress_callback`

Impact on UI:
- progress bar still works with process pools
- updates may become more bursty (multiple runs finishing close together)

## Error Handling (Process Pool View)

At per-run level:
- child task exceptions are caught inside `monte_carlo_worker(...)`
- worker logs and returns `None`

At aggregate level:
- parent counts only successful runs
- if all runs fail -> `RuntimeError("All Monte Carlo runs failed")`

## Environment Caveats

Process pools are environment-sensitive. They may fail or behave differently due to:
- multiprocessing permissions (sandboxed/dev environments)
- CPU limits
- memory pressure
- process startup overhead

This is why benchmarking on the target runtime matters.

## 3) Async Job Persistence: In-Memory + DB Fallback

The async Monte Carlo API currently uses a hybrid model:
- in-memory thread worker = runtime source of truth
- `jobs` table (`JobRepository`) = best-effort mirror + fallback retrieval

Implemented behaviors in `api/routes/monte_carlo.py`:
- best-effort job row creation on async submit
- best-effort status mirroring from runtime state to DB
- DB fallback when job is not found in worker memory

Not implemented yet:
- distributed queue (SQS/Redis)
- external worker process/service
- restart-safe recovery of running jobs
- durable retry/idempotency on exposed async path

## 4) Practical Mental Model (For Interviews and RAG)

Use these terms precisely:

- **Thread worker** (`SimpleMonteCarloWorker`): async job orchestration and UX lifecycle
- **Process pool** (`mc_backtest_service.py`): CPU parallel execution of simulation runs

This distinction avoids architecture confusion and improves retrieval quality in RAG answers.

## RAG Question Prompts That Map Well to This Doc

- “How does async Monte Carlo progress work?”
- “What is the difference between the worker and the process pool?”
- “Is cancellation hard or soft?”
- “Can jobs survive backend restart?”
