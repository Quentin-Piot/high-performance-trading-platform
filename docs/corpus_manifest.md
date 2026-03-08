# RAG Corpus Manifest

## Purpose

This file describes the documentation corpus available in `docs/` and how it should be used by a retriever.

It helps with:
- retrieval prioritization
- query routing (which document to search first)
- avoiding noisy answers from the wrong source

## Recommended Indexing Scope

Index by default:
- `docs/context.md`
- `docs/architecture.md`
- `docs/workers.md`
- `docs/routes.md`
- `docs/decisions.md`
- `docs/metrics.md`
- `docs/testing.md`
- `docs/infrastructure.md`
- `docs/glossary.md`

Optional (non-text / lower priority):
- `docs/speed_insights.jpg` (image asset; exclude from text-only RAG unless using multimodal retrieval)

## Document Catalog

## `docs/context.md`

### Covers
- project motivation and learning goals
- why FastAPI / CPU-bound workloads / finance / AWS / IaC
- scope and non-goals
- defensible interview positioning

### Use when
- the question is “Why was this project built?”
- the user asks about intent, learning goals, or positioning
- you need a non-technical or semi-technical overview

### Avoid using as primary source for
- exact endpoint behavior
- precise runtime implementation details

## `docs/architecture.md`

### Covers
- end-to-end system architecture
- component responsibilities (frontend, API, services, workers, DB)
- data flow (local CSV/upload -> backtest/Monte Carlo -> results)
- async job flow and concurrency layers
- ASCII architecture diagram

### Use when
- the question is about system design
- the user asks “how does the whole thing work?”
- you need to explain data flow or component interactions

### Related code anchors
- `backend/api/src/api/main.py`
- `backend/api/src/api/routes/monte_carlo.py`
- `backend/api/src/workers/simple_worker.py`
- `backend/api/src/services/mc_backtest_service.py`

## `docs/workers.md`

### Covers
- thread-based async job worker (`SimpleMonteCarloWorker`)
- process-pool parallelism in Monte Carlo service
- progress tracking semantics
- cancellation behavior
- in-memory state vs DB mirror/fallback

### Use when
- the question is about async jobs, progress, cancellation, concurrency
- the user asks “thread worker vs process pool?”
- the question concerns restart behavior or durability limits

### Avoid ambiguity
- Use this doc to distinguish job orchestration from CPU parallelism

## `docs/routes.md`

### Covers
- HTTP and WebSocket routes
- route purpose, auth expectations, and caveats
- endpoint groups (auth, backtest, Monte Carlo, history, performance)
- backend vs frontend status vocabulary mapping

### Use when
- the question is about API surface area
- the user asks “which endpoint does X?”
- building demos, clients, or route-level debugging

### Retrieval tip
- Prefer this doc before raw route files for quick endpoint lookup

## `docs/decisions.md`

### Covers
- major technical decisions in the format:
  - problem -> options -> chosen -> why -> trade-offs
- stack choices
- worker strategy
- Monte Carlo parallelism design
- persistence approach
- AWS/IaC and CI/CD choices

### Use when
- the question is “Why this design?”
- the user asks for trade-offs or alternatives
- interview prep / architecture review discussions

### Avoid using as primary source for
- exact current route payloads (use `docs/routes.md`)

## `docs/metrics.md`

### Covers
- implemented financial metrics (PnL/total return, drawdown, Sharpe)
- Monte Carlo distributions and equity envelope
- formulas and code locations
- executed validation on real CSV data
- performance benchmark (`parallel_workers=1` vs `14`)
- benchmark CLI tool usage

### Use when
- the question is about metric definitions or interpretation
- the user asks how metrics are computed
- the user asks whether process-pool parallelism improves speed

### Important constraint
- explicitly states missing predictive-market metrics (Brier/calibration)

## `docs/testing.md`

### Covers
- backend test inventory by file and area
- what each test file validates
- how to run lint/typecheck/tests
- current frontend testing status and gaps

### Use when
- the question is “Is this tested?”
- the user asks how to run validation
- the user asks specifically about WebSocket / async tests

## `docs/infrastructure.md`

### Covers
- Terraform/AWS resources and deployment topology
- CloudFront/S3/ALB/ECS/EFS/Cognito/IAM/CloudWatch/Route53
- env vars injected by ECS
- Terraform and CI/CD deployment flows
- current infra trade-offs

### Use when
- the question is about deployment architecture
- AWS resource ownership and purpose
- Terraform variables and rollout process

## Retrieval Priority (Practical)

Use this order for most user questions:

1. `docs/routes.md` for endpoint/API questions
2. `docs/workers.md` for async/progress/concurrency questions
3. `docs/architecture.md` for end-to-end design questions
4. `docs/decisions.md` for trade-offs and rationale
5. `docs/metrics.md` for finance/math/performance questions
6. `docs/infrastructure.md` for AWS/Terraform/CI-CD questions
7. `docs/testing.md` for quality/testing questions
8. `docs/context.md` for motivation/positioning questions

## Chunking Recommendations (for a simple RAG pipeline)

- Chunk by `##` section (not by fixed token size only)
- Keep headings in the chunk text
- Preserve code/file paths in the same chunk as the explanation
- Do not merge unrelated sections across documents
- Store metadata:
  - `path`
  - `section_title`
  - `topic` (architecture/routes/workers/metrics/etc.)
  - `doc_priority`

## Known Corpus Boundaries

This docs corpus is intentionally scoped to the current repository implementation.

If documentation and code disagree:
- treat the codebase as the source of truth
- use docs to accelerate retrieval/navigation, not to override runtime behavior

It should not be used to answer:
- live market data questions
- predictive market scoring questions (Brier/calibration)
- claims about external queue infrastructure not implemented in the active code path
