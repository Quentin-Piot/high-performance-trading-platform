FROM python:3.13-slim AS builder

WORKDIR /app

# Installer Poetry uniquement pour la phase de build
RUN pip install --no-cache-dir "poetry>=1.7,<2.0"

# Installer les dépendances (groupe principal) dans le site-packages global
ENV POETRY_VIRTUALENVS_CREATE=false
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

FROM python:3.13-slim

WORKDIR /app

# Copier les dépendances installées depuis le builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copier le code de l'application
COPY src ./src
COPY alembic.ini ./
COPY scripts ./scripts

EXPOSE 8000

CMD ["python", "scripts/bootstrap.py"]