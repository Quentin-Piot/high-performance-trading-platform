.PHONY: install lint format typecheck test run bench-mc-parallel

install:
	uv sync --dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run basedpyright

test:
	uv run pytest

run:
	uv run python scripts/bootstrap.py

bench-mc-parallel:
	uv run python scripts/benchmark_monte_carlo_parallelism.py
