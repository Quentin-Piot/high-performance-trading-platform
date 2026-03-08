# API and WebSocket Routes (RAG-Friendly Reference)

## Purpose

This file provides a retrieval-friendly map of the backend surface area:
- HTTP endpoints
- WebSocket endpoints
- route purpose
- auth expectations
- notable implementation caveats

Main API prefix:
- `/api/v1`

Platform endpoints (outside `/api/v1`):
- `/api/healthz`
- `/api/health`
- `/api/readyz`
- `/api/metrics`
- `/routes`

## Platform Endpoints (`backend/api/src/api/main.py`)

### `GET /`
- Purpose: root liveness/info response

### `GET /api/healthz`
- Purpose: basic health check

### `GET /api/health`
- Purpose: comprehensive health check (includes registered checks such as DB)

### `GET /api/readyz`
- Purpose: readiness check (DB connectivity)

### `GET /api/metrics`
- Purpose: application/runtime metrics summary (JSON)

### `GET /routes`
- Purpose: route introspection/debugging helper

## Auth (Local JWT) - `backend/api/src/api/routes/auth.py`

Router prefix:
- `/auth`

Full paths:

### `POST /api/v1/auth/register`
- Purpose: create local user and return token
- Response model: `Token`

### `POST /api/v1/auth/login`
- Purpose: local login and return token
- Response model: `Token`

## Google OAuth / Cognito Integration - `backend/api/src/api/routes/google_auth.py`

Router prefix:
- `/auth/google`

Full paths:

### `GET /api/v1/auth/google/login`
- Purpose: start Google OAuth login flow

### `GET /api/v1/auth/google/callback`
- Purpose: OAuth callback handler

### `GET /api/v1/auth/google/user-info`
- Purpose: fetch linked Google user info

### `POST /api/v1/auth/google/link-account`
- Purpose: link Google account to existing user

### `DELETE /api/v1/auth/google/unlink-account`
- Purpose: unlink Google account

## Backtest Routes - `backend/api/src/api/routes/backtest.py`

Router has no explicit prefix; routes are mounted directly under `/api/v1`.

### `GET /api/v1/backtest`
- Purpose: run synchronous backtest using a **local dataset** (`symbol + date range`)
- Inputs:
  - `symbol`, `start_date`, `end_date`
  - strategy params (`sma_short`, `sma_long`, `period`, `overbought`, `oversold`)
  - `strategy`, `price_type`, `include_aggregated`, `normalize`
- Output:
  - `BacktestResponse` (single or multi-shape depending on options)

### `POST /api/v1/backtest`
- Purpose: run synchronous backtest using **CSV uploads** or local dataset params
- Inputs:
  - multipart `csv[]` (up to 10 files) OR local dataset params
  - same strategy and formatting params as `GET`
- Notes:
  - performs best-effort history persistence if user is authenticated

## Monte Carlo Routes - `backend/api/src/api/routes/monte_carlo.py`

Router prefix:
- `/monte-carlo`

Full base prefix after mount:
- `/api/v1/monte-carlo`

### `POST /api/v1/monte-carlo/run`
- Purpose: synchronous Monte Carlo simulation
- Inputs:
  - local dataset or uploaded CSV
  - `num_runs`, `initial_capital`
  - `method` (`bootstrap`, `gaussian`)
  - `sample_fraction`, `gaussian_scale`
  - strategy params (SMA/RSI)
  - `price_type`, `normalize`
- Output:
  - Monte Carlo summary (metrics distributions + optional equity envelope)
- Implementation note:
  - calls `run_monte_carlo_on_df(..., parallel_workers=DEFAULT_PARALLEL_WORKERS)`

### `POST /api/v1/monte-carlo/async`
- Purpose: submit async Monte Carlo job and receive `job_id`
- Implementation notes:
  - submits to `SimpleMonteCarloWorker` (thread worker)
  - creates DB job record best-effort for mirror/fallback

### `GET /api/v1/monte-carlo/async/{job_id}`
- Purpose: retrieve async job status/progress/result
- Lookup order:
  1. in-memory worker state
  2. DB fallback (`JobRepository`) if not found in memory

### `DELETE /api/v1/monte-carlo/async/{job_id}`
- Purpose: logical cancel of async job
- Caveat:
  - marks job `cancelled` but does not guarantee immediate CPU interruption

### `GET /api/v1/monte-carlo/async`
- Purpose: list async Monte Carlo jobs (runtime worker view)

### `GET /api/v1/monte-carlo/symbols/date-ranges`
- Purpose: return min/max available dates for each local symbol dataset

### `WS /api/v1/monte-carlo/ws/{job_id}`
- Purpose: real-time progress/status updates for async Monte Carlo jobs
- Used by frontend for progress bar updates

## History Routes - `backend/api/src/api/routes/history.py`

Router prefix:
- `/history`

Full base prefix:
- `/api/v1/history`

### `GET /api/v1/history/`
- Purpose: paginated history list for current user
- Auth: required
- Query params:
  - `page`, `per_page`
  - optional `strategy` filter

### `GET /api/v1/history/stats`
- Purpose: aggregate user history stats
- Auth: required

### `GET /api/v1/history/{history_id}`
- Purpose: history entry detail
- Auth: required

### `PUT /api/v1/history/{history_id}/results`
- Purpose: update stored history results (system-style update endpoint)
- Auth: required

### `DELETE /api/v1/history/{history_id}`
- Purpose: delete a history entry
- Auth: required

### `POST /api/v1/history/rerun`
- Purpose: create a new history entry from an existing one with optional overrides
- Current behavior:
  - returns `status: "queued"` but does not trigger a distributed queue worker

## Performance / Monitoring Routes - `backend/api/src/api/routes/performance.py`

Router prefix:
- `/performance`

Full base prefix:
- `/api/v1/performance`

### `GET /api/v1/performance/database`
- Purpose: DB pool/table/index/slow-query stats

### `GET /api/v1/performance/cache`
- Purpose: cache stats endpoint
- Current state:
  - returns disabled placeholder values (cache is not wired)

### `GET /api/v1/performance/metrics`
- Purpose: combined DB + cache performance summary

### `POST /api/v1/performance/database/optimize/{table_name}`
- Purpose: optimize a table (allowlist)
- Allowed tables:
  - `jobs`
  - `users`

### `POST /api/v1/performance/database/create-indexes`
- Purpose: create performance indexes

### `DELETE /api/v1/performance/cache/clear`
- Purpose: clear cache (disabled implementation)

### `DELETE /api/v1/performance/cache/pattern/{pattern}`
- Purpose: clear cache by pattern (disabled implementation)

## Status Vocabulary (Backend vs Frontend)

Backend async job statuses (worker/runtime):
- `pending`
- `running`
- `completed`
- `failed`
- `cancelled`

Frontend-normalized UI statuses:
- `pending` -> `submitted`
- `running` -> `processing`

## RAG Chunking Tips

For best retrieval quality:
- keep one chunk per router section
- include method + path + purpose in the same chunk
- keep caveats near the endpoint they apply to
