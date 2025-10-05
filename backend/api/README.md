# Trading Simulation & Backtesting API (MVP)

Backend FastAPI modulaire pour une plateforme de backtest de stratégies (SMA crossover) avec Docker + PostgreSQL, JWT auth et tests.

## Structure du projet

```
backend/api/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── src/
│   ├── api/
│   │   ├── main.py
│   │   └── routers/
│   │       ├── auth.py
│   │       └── backtest.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── domain/
│   │   └── schemas/
│   │       ├── auth.py
│   │       └── backtest.py
│   ├── infrastructure/
│   │   ├── db.py
│   │   ├── models.py
│   │   └── repositories/
│   │       └── users.py
│   └── services/
│       └── backtest_service.py
└── tests/
    └── test_backtest_service.py
```

## Prérequis

- Python 3.13 (Poetry si vous voulez installer localement)
- Docker + Docker Compose

## Variables d’environnement

Copiez `.env.example` en `.env` et ajustez si nécessaire:

```
ENV=development
DATABASE_URL=postgresql+psycopg://postgres:postgres@pg:5432/trading_db
JWT_SECRET=changeme-dev-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=trading_db
```

## Lancer en Docker (API + PostgreSQL)

```
docker compose up --build
```

API disponible sur `http://localhost:8000`.

## Lancer localement (Poetry)

```
poetry install
poetry run uvicorn api.main:app --reload --app-dir src
```

## Endpoints principaux

- `POST /auth/register` — Body JSON `{ "email": "...", "password": "..." }` → retourne un token JWT.
- `POST /auth/login` — Body JSON `{ "email": "...", "password": "..." }` → retourne un token JWT.
- `POST /backtest` — multipart form:
  - `csv`: fichier CSV (colonnes: `date`, `close`)
  - `sma_short`: int, `sma_long`: int

Exemple de requête curl:

```
curl -X POST "http://localhost:8000/backtest?sma_short=10&sma_long=20" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "csv=@./sample.csv"
```

Réponse JSON (extrait):

```
{
  "equity_curve": [1.0, 1.003, ...],
  "pnl": 0.045,
  "drawdown": 0.12
}
```

## Tests

```
poetry run pytest -q
```

## Notes d’architecture

- Clean Architecture modulaire (domain, services, infrastructure, api).
- Service de backtest vectorisé (Pandas/NumPy) pour facilité d’extension.
- Prêt pour async/queues à venir (workers, BackgroundTasks). 
- Base prête pour RDS (PostgreSQL) via `DATABASE_URL`.