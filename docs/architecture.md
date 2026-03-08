# System Architecture (Code-Accurate)

## Scope and Non-Scope

This repository currently implements a **stock backtesting and Monte Carlo simulation platform**.

It does **not** currently implement:
- Polymarket ingestion
- Kalshi ingestion
- prediction-market evaluation metrics (Brier score, calibration curves)

Current supported data inputs are:
- local CSV datasets in `backend/api/src/datasets/*.csv`
- CSV uploads through the API

## Architectural Overview

The system has four main layers:
- frontend application (`web/`)
- backend API (`backend/api/src/api/`)
- compute and strategy layer (`services/`, `strategies/`, `workers/`)
- persistence and infrastructure (`infrastructure/`, `terraform/`)

A key design detail is that Monte Carlo execution uses **two concurrency layers**:
- a thread-based async job worker for API UX (job orchestration)
- an optional process pool for CPU parallelism inside Monte Carlo execution

## Frontend (`web/`)

Technology:
- Vue 3 + TypeScript
- Pinia state management
- custom lightweight router (`web/src/router.ts`)

Main views (`web/src/App.vue`):
- `LandingView`
- `SimulateView`
- `HistoryView`
- `LoginView`
- `RegisterView`

Key frontend integration modules:
- `web/src/services/backtestService.ts`
- `web/src/services/monteCarloWsService.ts`
- `web/src/services/apiClient.ts`
- `web/src/stores/backtestStore.ts`

Responsibilities:
- collect backtest and Monte Carlo parameters
- submit sync/async requests
- subscribe to WebSocket progress updates
- poll async job status as fallback
- render charts, metrics, and history

## Backend API (`backend/api/src/api/`)

Technology:
- FastAPI
- Pydantic schemas
- async SQLAlchemy integration

Entrypoint:
- `backend/api/src/api/main.py`

Routers mounted under `/api/v1`:
- auth (`auth.py`, `google_auth.py`)
- backtest (`backtest.py`)
- Monte Carlo (`monte_carlo.py`)
- history (`history.py`)
- performance (`performance.py`)

Platform endpoints outside `/api/v1`:
- `/api/healthz`
- `/api/health`
- `/api/readyz`
- `/api/metrics`
- `/routes`

Responsibilities:
- request validation and parameter normalization
- auth / user identity handling
- sync and async compute orchestration
- history persistence (best effort when applicable)
- health and observability endpoints

## Compute and Strategy Layer

## Backtest services and strategies

Primary files:
- `backend/api/src/services/backtest_service.py`
- `backend/api/src/strategies/moving_average.py`
- `backend/api/src/strategies/rsi_reversion.py`
- `backend/api/src/strategies/metrics.py`

Responsibilities:
- parse CSV price series
- run strategies (`sma_crossover`, `rsi`/`rsi_reversion`)
- compute equity curve and financial metrics (`pnl`, `drawdown`, `sharpe`)

## Monte Carlo service (CPU work)

Primary file:
- `backend/api/src/services/mc_backtest_service.py`

Responsibilities:
- generate synthetic price series (`bootstrap`, `gaussian`)
- rerun strategy over many simulations
- aggregate metric distributions (`mean`, `std`, percentiles)
- compute `equity_envelope` percentiles over time
- publish progress updates via callback

Concurrency behavior:
- sequential execution when `parallel_workers <= 1`
- `ProcessPoolExecutor` execution when `parallel_workers > 1`

Current API behavior:
- API paths pass `DEFAULT_PARALLEL_WORKERS` explicitly
- `DEFAULT_PARALLEL_WORKERS` is CPU-aware (`os.cpu_count() or 1`)
- actual process-pool usage depends on machine/runtime constraints

## Async job worker (API UX / orchestration)

Primary file:
- `backend/api/src/workers/simple_worker.py`

Responsibilities:
- create `job_id`
- store runtime job state in memory
- run Monte Carlo execution in background thread(s)
- update progress/status/result/error
- support WebSocket progress UX and status polling

Concurrency mechanism:
- `ThreadPoolExecutor(max_workers=2)` for async job orchestration

This worker is **not** a distributed queue worker.

## Persistence Layer (`backend/api/src/infrastructure/`)

Database:
- PostgreSQL via SQLAlchemy async (`infrastructure/db.py`)

Core models (`infrastructure/models.py`):
- `User`
- `BacktestHistory`
- `Job`

Repositories:
- `UserRepository`
- `BacktestHistoryRepository`
- `JobRepository`

Current async job persistence model:
- runtime source of truth = in-memory worker state
- DB `jobs` table = best-effort mirror and fallback lookup

## End-to-End Data Flow (Actual Current Flow)

## 1) Input data selection

Two supported input modes:

### A) Local dataset mode
- frontend sends `symbol`, `start_date`, `end_date`
- backend loads and filters `backend/api/src/datasets/{SYMBOL}.csv`
- backend converts filtered DataFrame to CSV bytes

### B) CSV upload mode
- frontend uploads CSV file(s)
- backend reads uploaded bytes directly

Both paths converge to the same compute representation:
- `csv_data: bytes`

## 2) CSV parsing and normalization

`CsvBytesPriceSeriesSource` handles:
- case/whitespace normalization of column names
- `close` vs `adj_close` resolution
- date parsing and sorting
- numeric conversion
- invalid row removal

## 3) Synchronous backtest flow (`/api/v1/backtest`)

1. Route validates strategy parameters
2. Route prepares local or uploaded CSV input
3. Service runs SMA or RSI strategy
4. Strategy pipeline computes:
- position series
- strategy returns
- equity curve
- metrics (`pnl`, `drawdown`, `sharpe`)
5. Response returns backtest result payload
6. If authenticated, a history row may be stored (best effort)

## 4) Synchronous Monte Carlo flow (`/api/v1/monte-carlo/run`)

1. Route validates params and filters data
2. Route calls `run_monte_carlo_on_df(...)`
3. Monte Carlo service creates synthetic price paths
4. Strategy is rerun on each synthetic path
5. Parent process aggregates metric distributions and envelope
6. Route returns Monte Carlo summary

## 5) Asynchronous Monte Carlo flow (`/api/v1/monte-carlo/async`)

1. Route validates params and prepares CSV bytes
2. Route submits job to `SimpleMonteCarloWorker`
3. Worker thread executes Monte Carlo service
4. Progress callback updates runtime `job.progress`
5. Frontend tracks progress via:
- WebSocket `/api/v1/monte-carlo/ws/{job_id}`
- HTTP polling `GET /api/v1/monte-carlo/async/{job_id}`
6. Status endpoint can fall back to DB if runtime job is missing
7. Final result is fetched by `job_id`

## ASCII Diagram (Simplified)

```text
[Browser / Vue UI]
   |-- HTTP (submit/status/results)
   |-- WebSocket (progress)
   v
[FastAPI API Routers]
   |-- /backtest -----------------> [Backtest Service] ---> [Strategies: SMA/RSI]
   |                                   |                        |
   |                                   v                        v
   |                              [CSV Parsing]          [Metrics: pnl/sharpe/dd]
   |
   |-- /monte-carlo/* -----------> [SimpleMonteCarloWorker]
   |                                   (ThreadPoolExecutor, job orchestration)
   |                                              |
   |                                              v
   |                                 [MC Service run_monte_carlo_on_df]
   |                                              |
   |                    +-------------------------+----------------------+
   |                    |                                                |
   |                    v                                                v
   |             [Sequential runs]                             [ProcessPool runs]
   |             (workers <= 1)                               (workers > 1)
   |                    \______________________________________________/
   |                                              |
   |                                              v
   |                        [Distributions + Equity Envelope + Progress]
   |
   |-- /history ------------------> [Repositories] -------------> [PostgreSQL]
   |-- /auth/* -------------------> [JWT / Cognito / Google OAuth]
   |
   +-- health/metrics/logs -------> [Monitoring + Structured Logs]

Cloud deployment:
Browser -> CloudFront -> S3 (frontend)
                  \-> /api/* -> ALB -> ECS task (backend + postgres) -> EFS
```

## Current Limitations (Important for Accurate Answers)

- No Polymarket/Kalshi ingestion in current codebase
- No predictive-market metrics (Brier/calibration) in current codebase
- Async jobs are not restart-safe (runtime state is in memory)
- No distributed queue yet (SQS/Redis not in active Monte Carlo path)
- Process pool behavior is environment-dependent (permissions/resources)

## RAG Retrieval Tips

For architecture/system-design questions, prioritize:
- `docs/architecture.md`
- `docs/workers.md`
- `docs/routes.md`
- `docs/decisions.md`
- `backend/api/src/api/routes/monte_carlo.py`
- `backend/api/src/workers/simple_worker.py`
- `backend/api/src/services/mc_backtest_service.py`
