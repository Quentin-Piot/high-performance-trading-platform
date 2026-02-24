# HPTP - High Performance Trading Platform (Demo Project)

Backtesting and Monte Carlo simulation platform built with a Vue frontend, a FastAPI backend, and AWS/Terraform infrastructure.

This repository is a portfolio/demo project designed to showcase full-stack engineering, data processing, async workflows, and production-oriented infrastructure decisions.

## Why this project is relevant (interview/demo)

- End-to-end product: frontend, backend, data processing, auth, persistence, infra
- Quant-oriented logic: strategy backtests, metrics, Monte Carlo simulation
- Real-time UX: WebSocket progress updates for async Monte Carlo jobs
- Cloud/IaC: Terraform deployment on AWS (ECS, CloudFront, Cognito, S3)
- Clean engineering stack: `uv`/`ruff`/`basedpyright` on backend, `pnpm`/Biome on frontend

## What it does

- Runs backtests on uploaded CSVs or local datasets
- Supports SMA crossover and RSI reversion strategies
- Computes key metrics (PnL, drawdown, Sharpe)
- Runs Monte Carlo simulations (sync + async job flow with real progress updates)
- Streams progress updates to the frontend
- Stores authenticated users' run history

## Tech Stack

### Frontend (`web/`)

- Vue 3 + TypeScript
- Pinia
- Tailwind CSS + shadcn-vue
- Vite
- lightweight-charts + ECharts
- Biome (lint/format)

### Backend (`backend/api/`)

- FastAPI
- Pandas / NumPy
- SQLAlchemy (async)
- PostgreSQL
- `uv`, `ruff`, `basedpyright`, `pytest`

### Infra (`terraform/`)

- AWS ECS (Fargate)
- CloudFront + S3
- Cognito
- ALB
- ECR
- CloudWatch

## Architecture (high level)

### Backend

- `domain/`: core models and schemas
- `strategies/`: SMA / RSI logic + metrics
- `services/`: backtest orchestration + Monte Carlo engine
- `api/routes/`: FastAPI endpoints (`/api/v1`)
- `workers/`: in-process async Monte Carlo worker (thread pool) with job tracking
- `infrastructure/`: DB, repositories, auth integrations, storage

Notes:
- Async Monte Carlo jobs are currently executed by an in-process worker (no external queue yet).
- Job status is tracked in-memory during execution, with best-effort DB persistence/fallback for retrieval.

### Frontend

- `pages/`: `Landing`, `Simulate`, `History`, `Login`, `Register`
- `stores/`: auth + backtest state
- `services/`: API calls, response normalization, WebSocket progress
- `components/backtest/`: forms, charts, Monte Carlo visualization

## Local Development

### Backend

```bash
docker compose -f docker-compose.db.yml up -d
cd backend/api
uv sync --dev
cp .env.example .env
uv run python scripts/bootstrap.py
```

API runs on `http://localhost:8000`.
Local PostgreSQL is required for backend startup and authenticated history features.

### Frontend

```bash
cd web
pnpm install
pnpm dev
```

Frontend runs on `http://localhost:5173`.

## Quality / Verification

### Backend

```bash
cd backend/api
make lint
make typecheck
make test
```

### Frontend

```bash
cd web
pnpm lint
pnpm build
```

## RAG (Mistral SDK, CLI MVP)

The repository includes a local CLI RAG tool for querying project docs with citations.

Current RAG scope:
- local corpus (`docs/*.md`, `README.md`)
- fixed-size character chunking
- Mistral embeddings (`mistral-embed`) for retrieval
- Mistral generation (`mistral-small-latest` by default)
- no frontend UI and no API route (CLI only)

### 1) Configure backend env (`backend/api/.env`)

Set at least:

```env
MISTRAL_API_KEY=your_mistral_api_key
```

Notes:
- This MVP is intentionally local/CLI-first for demo usage.

Optional overrides:

```env
RAG_INDEX_PATH=/absolute/or/project/path/to/.rag/index.json
RAG_EMBEDDING_MODEL=mistral-embed
RAG_MODEL=mistral-small-latest
RAG_TOP_K_DEFAULT=5
RAG_TOP_K_MAX=10
```

### 2) Build the local RAG index (embeddings)

```bash
cd backend/api
uv run python scripts/rag_cli.py build
```

### 3) Query the local RAG tool (Mistral SDK generation + citations)

Answer text only (default):

```bash
cd backend/api
uv run python scripts/rag_cli.py query \
  "Explain the difference between the thread worker and the process pool." \
  --top-k 3 \
  --topic workers
```

Full JSON response (including sources and timings):

```bash
cd backend/api
uv run python scripts/rag_cli.py query \
  "Explain the difference between the thread worker and the process pool." \
  --top-k 3 \
  --topic workers \
  --json
```

Notes:
- unchanged chunks reuse their existing embeddings via `chunk_id + content_sha256` matching
- global overrides like `--output` and `--chunk-target-chars` must be passed before `build`/`query`
- if docs and code disagree, code is the source of truth

## AWS / Terraform

Infrastructure is defined in `terraform/` and targets an AWS deployment with ECS + CloudFront + Cognito.

Current Terraform intentionally favors cost/simplicity for demo usage: the backend API and PostgreSQL run in the same ECS task (with EFS for Postgres data). This can be evolved toward a more production-grade architecture (managed DB/cache, separate worker service, horizontal workers, etc.).

## Contributions

### Quentin Piot

- Full-stack architecture and implementation (Vue / FastAPI)
- Monte Carlo engine and async worker flow
- Real-time progress tracking (WebSocket)
- AWS infrastructure and CI/CD (Terraform, ECS, CloudFront, Cognito)

### Mayeul Saint Georges Chaumet

- Product feedback on finance-facing UX and framing
- Domain-level feedback on financial concepts and terminology
- Sanity-check feedback on standard financial metrics/calculations and their interpretation

## Notes

- This is a demonstration project, not a trading system for live execution.
- It is intended to showcase engineering approach, architecture choices, and product implementation quality.
