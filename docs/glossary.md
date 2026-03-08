# Glossary (Stable Terms for RAG and Explanations)

## Purpose

This glossary defines the preferred vocabulary for this repository.

Use it to:
- keep answers consistent
- avoid vague explanations
- disambiguate similar concepts (especially concurrency terms)

## A

## API Route

An HTTP or WebSocket endpoint exposed by the FastAPI backend.

Examples:
- `GET /api/v1/backtest`
- `POST /api/v1/monte-carlo/async`
- `WS /api/v1/monte-carlo/ws/{job_id}`

## Async Job (Monte Carlo)

A long-running Monte Carlo task submitted through the async API (`/api/v1/monte-carlo/async`) and tracked by `job_id`.

It includes:
- status
- progress
- timestamps
- result or error

## B

## Backtest

Replaying a strategy on historical price data to measure behavior and compute metrics.

In this repo, backtests are run on:
- local CSV datasets
- uploaded CSV files

Implemented strategies:
- SMA crossover
- RSI reversion

## Bootstrap (Monte Carlo Method)

A Monte Carlo method that resamples historical returns with replacement and reconstructs a synthetic price path.

Purpose:
- stress test strategy robustness under resampled return sequences

## C

## CSV Bytes Path

A shared internal representation used by services (`csv_data: bytes`) so local datasets and uploaded files can use the same compute pipeline.

Why it matters:
- reduces duplicated compute logic

## D

## Drawdown

The decline of the equity curve from a previous peak.

## Max Drawdown

The worst peak-to-trough decline over the full equity curve.

In this codebase, it is computed from the equity curve as:
- `equity / cummax(equity) - 1`
- then taking the minimum value

## E

## Equity Curve

The cumulative portfolio value over time during a backtest or simulation.

In this repo:
- derived from cumulative strategy returns
- used to compute total return and drawdown
- used in Monte Carlo to build the `equity_envelope`

## Equity Envelope (Monte Carlo)

A time-aligned percentile summary across many Monte Carlo equity curves.

Percentiles included:
- `p5`, `p25`, `median`, `p75`, `p95`

Purpose:
- visualize the spread of simulated outcomes over time

## F

## Fallback (DB Fallback for Async Jobs)

When the async status endpoint cannot find a job in the in-memory worker, it attempts to read job state from the database (`jobs` table) using `JobRepository`.

This improves resilience for status lookup, but does not provide full restart recovery of running jobs.

## G

## Gaussian (Monte Carlo Method)

A Monte Carlo method that adds Gaussian noise to historical returns before reconstructing synthetic prices.

Purpose:
- test sensitivity to perturbations in return dynamics

## H

## Health Check (`/api/health`, `/api/healthz`)

Endpoints used to verify application runtime status.

- `/api/healthz`: basic liveness-style check
- `/api/health`: more detailed status including registered checks (e.g., database)

## I

## In-Memory Job State

Async Monte Carlo job state stored in the `SimpleMonteCarloWorker.jobs` dictionary at runtime.

Characteristics:
- fast access
- lost on backend restart
- current runtime source of truth for active jobs

## J

## Job Mirror (Best-Effort DB Mirror)

The async Monte Carlo routes persist a best-effort copy of runtime job status/progress/result into the `jobs` table.

Important:
- this is a mirror/fallback mechanism
- not yet a fully durable queue-backed job system

## Job ID

A unique identifier for an async Monte Carlo job.

Used for:
- status polling
- WebSocket subscription
- result retrieval
- log correlation (`job_id`)

## M

## Monte Carlo (in this project)

Repeated backtest execution on synthetic price series generated from historical data.

Goal in this repo:
- robustness analysis of strategy outcomes
- distribution of metrics (PnL, Sharpe, drawdown)

Non-goal:
- direct market prediction

## Metrics Distribution

A statistical summary of Monte Carlo outcomes for one metric (e.g., `pnl`).

Fields in this repo:
- `mean`
- `std`
- `p5`
- `p25`
- `median`
- `p75`
- `p95`

## P

## PnL (`pnl` in responses)

In this repository's backtest responses, `pnl` corresponds to **total return as a fraction**, not absolute currency profit.

Example:
- `0.20` means `+20%`, not `$0.20`

## Process Pool

The `ProcessPoolExecutor` used inside `mc_backtest_service.py` to parallelize Monte Carlo simulation runs across processes.

Role:
- CPU parallelism for simulation runs

Not the same thing as:
- the async job worker (`SimpleMonteCarloWorker`)

## Progress Callback

A callback function used by `run_monte_carlo_on_df(...)` to report progress as `(processed_runs, total_runs)`.

This is the source of truth for the async progress bar.

## R

## RAG (Retrieval-Augmented Generation)

A system that retrieves relevant documents/chunks before generating an answer.

In this repo context:
- the `docs/*.md` files are intended to serve as a high-quality RAG corpus

## Ready Check (`/api/readyz`)

Endpoint that checks whether the application is ready to serve traffic, including database connectivity.

## S

## Sharpe Ratio

A risk-adjusted performance metric defined (in this repo) as:
- mean(strategy returns) / std(strategy returns)
- annualized by `sqrt(annualization)` (default `252`)

Important caveat:
- local datasets may not be daily frequency, so the default annualization may not match the dataset cadence

## SimpleMonteCarloWorker

The in-process thread-based async worker that manages Monte Carlo job lifecycle for the API.

Responsibilities:
- submit jobs
- track status/progress/result
- expose in-memory state to API routes

## T

## Thread Worker (Application Worker)

The `ThreadPoolExecutor`-based worker used for async job orchestration (`SimpleMonteCarloWorker`).

Role:
- job lifecycle and UX responsiveness

Not the same thing as:
- process pool CPU parallelism

## Total Return

The return of the equity curve from start to end of the backtest:
- `equity[-1] / equity[0] - 1`

This is what the API often exposes as `pnl` for backtests.

## W

## WebSocket Progress Stream

The WebSocket endpoint `WS /api/v1/monte-carlo/ws/{job_id}` used by the frontend to receive async job progress updates in real time.

## Preferred Phrasing (For Clear Answers)

Use these distinctions consistently:

- “thread worker” = async job orchestration (`SimpleMonteCarloWorker`)
- “process pool” = CPU parallelism inside Monte Carlo service
- “job mirror/fallback” = best-effort DB persistence for async job status
- “current implementation” = what is in the repo now
- “future architecture” = queue-backed/distributed worker roadmap

## Terms to Avoid (or qualify)

- “queue” (unless explicitly stating it is not in the active Monte Carlo async path)
- “durable async jobs” (not true yet)
- “profitability” (not the project goal)
- “prediction” (Monte Carlo here is robustness simulation, not forecasting)
