# Technical Decisions (Problem -> Options -> Chosen -> Why)

## Document Scope

This file captures major technical choices in the current codebase and their trade-offs.

It is intentionally written in a retrieval-friendly format:
- one decision per section
- explicit problem statement
- current state vs future direction clearly separated

## 1) API Framework: FastAPI + Pydantic

### Problem
Build a typed API quickly for backtesting, async Monte Carlo jobs, auth, history, and monitoring.

### Options considered
- Flask + extensions
- Django / DRF
- FastAPI

### Chosen
FastAPI + Pydantic schemas (`backend/api/src/api`, `backend/api/src/domain/schemas`)

### Why
- fast iteration for JSON APIs
- strong validation and typed request/response models
- async-friendly (WebSocket + async DB)

### Trade-offs
- route modules can become large if business logic leaks into them
- requires discipline around service/repository boundaries

## 2) Frontend Stack: Vue 3 + TypeScript + Pinia

### Problem
Deliver a responsive UI for simulation workflows and async job tracking.

### Options considered
- React + state library
- Vue 3 + Pinia
- server-rendered UI only

### Chosen
Vue 3 + Pinia + service modules (`web/src/services/*`, `web/src/stores/*`)

### Why
- good readability and fast delivery for a portfolio/product demo
- clean separation between UI, stores, and API clients
- async orchestration is easy to follow in store code

### Trade-offs
- custom router (`web/src/router.ts`) is simpler but less standard than `vue-router`

## 3) Async Monte Carlo UX: Application-Level Thread Worker (MVP)

### Problem
Run long Monte Carlo jobs without blocking HTTP requests and while preserving a good UX (progress/status/result by `job_id`).

### Options considered
- synchronous only
- distributed queue + worker service (SQS/Redis/Celery)
- in-process worker with thread pool

### Chosen
`SimpleMonteCarloWorker` in-process (`backend/api/src/workers/simple_worker.py`)

### Why
- low operational complexity
- easy local development
- fast path to a real async UI with progress and WebSocket support

### Trade-offs
- runtime jobs stored in memory
- limited horizontal scalability
- running jobs are lost on backend restart
- cancellation is logical, not hard preemption

## 4) Monte Carlo CPU Parallelism: Process Pool in Service Layer

### Problem
Monte Carlo runs are CPU-heavy and can be slow when executed sequentially.

### Options considered
- always sequential
- process pool inside service
- fully external distributed compute workers

### Chosen
`ProcessPoolExecutor` inside `run_monte_carlo_on_df(...)` (`backend/api/src/services/mc_backtest_service.py`)

### Why
- reuses existing service logic
- improves performance for larger run counts
- no extra infrastructure required

### Current behavior (important)
API paths now pass `DEFAULT_PARALLEL_WORKERS` explicitly (CPU-aware default from the Monte Carlo service, based on `os.cpu_count() or 1`).

This means process pool usage is **possible by default**, but real behavior depends on runtime constraints.

### Trade-offs
- multiprocessing startup overhead hurts small run counts
- environment-dependent reliability (permissions/sandbox/process limits)
- more CPU/RAM pressure than sequential execution
- harder performance predictability across machines

## 5) Job Persistence Strategy: Incremental Adoption of `jobs` Table

### Problem
Improve observability/retrievability of async jobs without rewriting the async execution model all at once.

### Options considered
- no DB persistence for async jobs
- immediate DB source-of-truth migration
- incremental DB mirror + fallback

### Chosen
Use `JobRepository` + `jobs` table as best-effort mirror/fallback for async Monte Carlo status

### Why
- incremental, low-risk improvement
- better diagnostics and recovery of terminal state data
- prepares future evolution toward durable queue-backed jobs

### Trade-offs
- temporary dual state model (in-memory runtime + DB mirror)
- not a full durability/retry solution yet

## 6) Domain Modeling: Backtesting on Price Series (Not Prediction)

### Problem
Demonstrate robust long-running compute pipelines without over-claiming predictive trading capability.

### Options considered
- predictive ML/forecasting pipeline
- strategy backtesting + Monte Carlo robustness analysis

### Chosen
Vectorized backtesting + Monte Carlo perturbation (`bootstrap`, `gaussian`) on price data

### Why
- easier to validate and explain
- strong fit for async compute, progress tracking, and reliability demos
- produces meaningful outputs (PnL/drawdown/Sharpe distributions)

### Trade-offs
- not a forecasting engine
- no predictive market metrics (Brier/calibration) in current repo

## 7) Data Access Pattern: Shared CSV Bytes Path

### Problem
Support both local datasets and user uploads without duplicating the core compute pipeline.

### Options considered
- separate code paths for local and upload flows
- normalize both into a common representation

### Chosen
Convert both flows into `csv_data: bytes` and reuse the same services

### Why
- less duplication in compute layer
- simpler testing
- consistent behavior across local and uploaded data

### Trade-offs
- extra conversion step for local DataFrame -> CSV bytes
- route code still carries some orchestration complexity

## 8) Strategy Code Organization: Services + Strategy Modules

### Problem
Keep API routes focused on I/O while preserving testable, reusable business logic.

### Options considered
- put strategy logic inside routes
- single large service module
- route -> service -> strategy modules

### Chosen
Route orchestration in `api/routes/*`, strategy execution in `services/*` and `strategies/*`

### Why
- clearer boundaries
- easier unit testing of financial logic
- simpler future extension to more strategies

### Trade-offs
- some validation/orchestration duplication can still appear in routes
- requires ongoing refactoring discipline

## 9) Database and ORM: PostgreSQL + SQLAlchemy Async

### Problem
Persist users, history, and jobs with an async-capable backend stack.

### Options considered
- SQLite
- PostgreSQL + sync ORM
- PostgreSQL + SQLAlchemy async

### Chosen
PostgreSQL + SQLAlchemy async (`backend/api/src/infrastructure/db.py`)

### Why
- production-relevant persistence model
- compatible with FastAPI async endpoints
- supports history/jobs growth beyond demo-only persistence

### Trade-offs
- async DB handling adds complexity (sessions, tests, error handling)
- thread worker + async DB interactions require careful boundaries

## 10) Cache Strategy: API Surface Present, Cache Currently Disabled

### Problem
Prepare performance monitoring/cache endpoints without adding Redis complexity before the use case is proven.

### Options considered
- fully implement Redis cache now
- no cache features at all
- expose performance/cache API surface with disabled cache implementation

### Chosen
Performance endpoints include cache responses, but cache behavior is currently disabled

### Why
- keeps monitoring surface and future extension points visible
- lowers current operational complexity

### Trade-offs
- some endpoints return placeholders / disabled responses
- can create confusion if not documented clearly

## 11) AWS Infrastructure: Cost-Optimized Full Stack via Terraform

### Problem
Deploy a full-stack project to AWS with repeatable infrastructure and manageable cost.

### Options considered
- single VM deployment
- ECS + separate managed DB (RDS)
- ECS Fargate task containing backend + postgres (MVP)

### Chosen
Terraform-managed AWS stack with:
- S3 + CloudFront (frontend)
- ALB + ECS Fargate (backend)
- Postgres container in same ECS task + EFS persistence
- Cognito, IAM, Route53, CloudWatch

### Why
- low cost for a personal/portfolio production-like deployment
- reproducible infrastructure
- demonstrates real cloud/IaC deployment patterns

### Trade-offs
- backend and DB are not fully separated operationally
- weaker HA and isolation than ECS + RDS
- not the final architecture for high-criticality systems

## 12) CI/CD: Change-Aware Frontend/Backend Pipelines

### Problem
Avoid rebuilding/redeploying everything on every push.

### Options considered
- single monolithic pipeline
- separate pipelines without change detection
- path-based change detection with conditional jobs

### Chosen
GitHub Actions with `dorny/paths-filter` and separate frontend/backend stages

### Why
- faster CI feedback
- lower build/deploy cost
- clearer failure isolation by area (`web` vs `backend`)

### Trade-offs
- workflow YAML is longer and more complex
- path filters need maintenance as repo structure evolves

## 13) Observability: Structured Logs + Health/Readiness/Metrics

### Problem
Make the system debuggable and demo-ready in local and cloud environments.

### Options considered
- plain text logs only
- structured logs + request IDs + health endpoints

### Chosen
Structured logging (`core/logging.py`) with correlation IDs plus health/readiness/metrics endpoints

### Why
- easier debugging of async and multi-step flows
- better CloudWatch compatibility
- clearer operational story during interviews

### Trade-offs
- requires consistent `extra={...}` usage and context propagation
- logs need discipline to stay useful

## RAG Usage Tips

For “why was this chosen?” questions, prioritize retrieval from:
- `docs/decisions.md`
- `docs/architecture.md`
- `docs/workers.md`
- `docs/infrastructure.md`
