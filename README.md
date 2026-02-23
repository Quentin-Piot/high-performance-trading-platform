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
- Runs Monte Carlo simulations (sync + async job flow)
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
- `workers/`: in-process async Monte Carlo worker with job tracking
- `infrastructure/`: DB, repositories, auth integrations, storage

### Frontend

- `pages/`: `Simulate`, `History`, `Login`, `Register`
- `stores/`: auth + backtest state
- `services/`: API calls, response normalization, WebSocket progress
- `components/backtest/`: forms, charts, Monte Carlo visualization

## Local Development

### Backend

```bash
cd backend/api
uv sync --dev
cp .env.example .env
uv run python scripts/bootstrap.py
```

API runs on `http://localhost:8000`.

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

## AWS / Terraform

Infrastructure is defined in `terraform/` and targets an AWS deployment with ECS + CloudFront + Cognito.

This setup is optimized for demo/portfolio usage and can be evolved toward a more production-grade architecture (managed DB/cache, horizontal workers, etc.).

## Contributions

### Quentin Piot

- Full-stack architecture and implementation (Vue / FastAPI)
- Monte Carlo engine and async worker flow
- Real-time progress tracking (WebSocket)
- AWS infrastructure and CI/CD (Terraform, ECS, CloudFront, Cognito)

### Mayeul Saint Georges Chaumet

- Trading research and strategy design
- Backtesting logic specifications
- Financial modeling and Monte Carlo methodology

## Notes

- This is a demonstration project, not a trading system for live execution.
- It is intended to showcase engineering approach, architecture choices, and product implementation quality.
