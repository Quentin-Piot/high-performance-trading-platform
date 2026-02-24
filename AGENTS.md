# Repository Guidelines

## Project Structure & Module Organization
`backend/api/` contains the FastAPI service. Core application code lives in `backend/api/src/` (API routes, services, strategies, domain schemas, infrastructure), and tests live in `backend/api/tests/`.

`web/` contains the Vue 3 + TypeScript frontend. App code is in `web/src/`, static assets in `web/public/`, and generated/shared UI primitives are under `web/src/components/ui/`.

`terraform/` holds AWS infrastructure (ECS, CloudFront, Cognito, S3, networking). Root-level `docker-compose.yml` runs the full stack; `docker-compose.db.yml` runs a local Postgres only.

## Build, Test, and Development Commands
- `cd backend/api && make install`: install backend dependencies with `uv`.
- `cd backend/api && make run`: start the API via `scripts/bootstrap.py` (FastAPI on `:8000`).
- `cd backend/api && make lint && make typecheck && make test`: Ruff, basedpyright, and pytest.
- `cd web && pnpm install && pnpm dev`: start Vite dev server (`:5173`).
- `cd web && pnpm lint && pnpm build`: Biome lint and production build.
- `docker compose up --build`: run frontend, backend, and Postgres together.
- `docker compose -f docker-compose.db.yml up -d`: local Postgres only.

## Coding Style & Naming Conventions
Backend Python uses Ruff formatting/linting (`line-length = 88`) and basedpyright. Use 4-space indentation, `snake_case` for modules/functions, `PascalCase` for classes, and `test_*.py` for tests.

Frontend uses Biome (`web/biome.json`) with tab indentation and double quotes. Prefer `PascalCase.vue` for components, `useX.ts` for composables, and descriptive service files like `backtestService.ts`.

## Testing Guidelines
Backend tests use `pytest` with `pytest-asyncio` (`asyncio_mode = strict`); property tests are present via Hypothesis. Run `cd backend/api && make test` before opening a PR. `pytest-cov` is available, but no minimum coverage threshold is enforced in-repo.

Frontend has no committed test runner yet; validate changes with `pnpm lint`, `pnpm build`, and manual checks for key flows (backtest, Monte Carlo, auth/history UI).

## Commit & Pull Request Guidelines
Follow Conventional Commits with a scope, as seen in history: `fix(api): ...`, `chore(front): ...`, `refactor(api): ...`.

PRs should include a short description, impacted areas (`web`, `backend/api`, `terraform`), validation commands run, screenshots for UI changes, and notes for migrations/env/Terraform impacts.
