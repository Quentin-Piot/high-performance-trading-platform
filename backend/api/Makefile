.PHONY: install lint format typecheck test run

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
