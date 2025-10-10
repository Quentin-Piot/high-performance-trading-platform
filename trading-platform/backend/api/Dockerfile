FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir "poetry>=1.7,<2.0"

ENV POETRY_VIRTUALENVS_CREATE=false
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/src:${PYTHONPATH}

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY src ./src
COPY alembic.ini ./
COPY scripts ./scripts

EXPOSE 8000

CMD ["python", "scripts/bootstrap.py"]
