# Project Context (Why This Project Exists)

## Purpose of the Project

This project was built to go beyond a typical web fullstack application and explore a more compute-oriented backend workload.

It is a practical engineering project, not a research paper and not a claim of trading profitability.

## Main Motivations

## 1) Go deeper with FastAPI

A primary goal was to use FastAPI in a more advanced way than a standard CRUD API:
- request validation
- async endpoints
- WebSocket progress updates
- background job orchestration

This project provided a good environment to work on API design under realistic constraints (long-running tasks, progress tracking, error handling).

## 2) Work on CPU-bound workloads (not only IO-bound web flows)

Most of my previous fullstack web experience was centered around IO-bound constraints:
- HTTP requests
- databases
- frontend/backend integration
- API orchestration

This project was intentionally chosen to work on **CPU-bound** behavior:
- Monte Carlo simulations
- repeated backtest runs
- concurrency trade-offs (thread worker vs process pool)
- performance measurement and tuning

That shift is one of the core reasons this project exists.

## 3) Rebuild hands-on fluency with NumPy/Pandas

Another goal was to get back into numerical/data-oriented Python tooling:
- `pandas` for data loading, cleaning, and time series handling
- `numpy` for statistics and percentile calculations

Backtesting and Monte Carlo simulation were a practical way to do this with a concrete output (equity curves, distributions, risk metrics).

## 4) Use finance as a technically useful domain (not as a business claim)

Finance/backtesting was chosen because it creates a useful engineering playground for:
- time series data processing
- reproducible calculations
- metrics and validation
- simulation workloads
- result interpretation and visualization

The goal is not to present a profitable strategy.

The goal is to demonstrate:
- correctness of the computation pipeline
- engineering design for long-running jobs
- operational thinking around performance and observability

## 5) Build a complete AWS architecture (end-to-end)

A major objective was to deploy a full application stack on AWS using multiple services in a coherent way.

This includes, in the current repo:
- CloudFront
- S3
- ALB
- ECS Fargate
- EFS
- Cognito
- IAM
- CloudWatch
- Route53

This was intentionally part of the project scope to practice shipping a full system, not only local application code.

## 6) Improve Infrastructure as Code (IaC) skills

The Terraform setup is also a learning and improvement target.

Goals included:
- structuring a real deployment with Terraform
- understanding resource dependencies
- managing configuration via variables
- making the environment reproducible
- documenting trade-offs clearly

This project is not presented as a perfect production architecture. It is presented as a **practical, working IaC-backed deployment** with explicit trade-offs.

## RAG Retrieval Notes

This file is useful for answering questions such as:
- “Why was this project built?”
- “What skills was it meant to strengthen?”
- “Why finance?”
- “How should this project be positioned in an interview?”
