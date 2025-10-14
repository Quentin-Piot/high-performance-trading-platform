# High-Performance Trading Simulation & Backtesting API

Backend FastAPI modulaire pour une plateforme de backtest de stratégies (SMA crossover) avec Docker + PostgreSQL, JWT auth, tests et optimisations de performance avancées.

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

## Variables d'environnement

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
LOG_LEVEL=INFO
LOG_FORMAT=console

# Redis Configuration (pour le cache)
REDIS_URL=redis://localhost:6379/0
REDIS_TTL=3600

# Performance Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# Queue Configuration (SQS)
AWS_REGION=us-east-1
SQS_QUEUE_URL=your-sqs-queue-url
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

### Format des logs

- Dev (humain): définir `LOG_FORMAT=console` pour une sortie lisible en console.
- Prod (classique JSON): définir `LOG_FORMAT=json` pour des logs structurés.

## Endpoints principaux

### Authentification
- `POST /auth/register` — Body JSON `{ "email": "...", "password": "..." }` → retourne un token JWT.
- `POST /auth/login` — Body JSON `{ "email": "...", "password": "..." }` → retourne un token JWT.

### Backtesting
- `POST /backtest` — multipart form:
  - `csv`: fichier CSV (colonnes: `date`, `close`)
  - `sma_short`: int, `sma_long`: int

### Monte Carlo Simulations
- `POST /api/v1/monte-carlo/jobs` — Créer une nouvelle simulation Monte Carlo
- `GET /api/v1/monte-carlo/jobs/{job_id}` — Obtenir le statut d'un job
- `GET /api/v1/monte-carlo/jobs/{job_id}/progress` — Obtenir le progrès détaillé d'un job
- `GET /api/v1/monte-carlo/jobs` — Lister tous les jobs avec filtres

### Performance Monitoring
- `GET /api/v1/performance/database` — Statistiques de performance de la base de données
- `GET /api/v1/performance/cache` — Statistiques du cache Redis
- `GET /api/v1/performance/system` — Métriques système (CPU, mémoire)
- `GET /api/v1/performance/indexes` — Analyse des index de base de données
- `POST /api/v1/performance/indexes/optimize` — Optimiser les index automatiquement

### Health Checks
- `GET /api/healthz` — Health check général
- `GET /api/readyz` — Readiness check pour la base de données

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

## Notes d'architecture

- Clean Architecture modulaire (domain, services, infrastructure, api).
- Service de backtest vectorisé (Pandas/NumPy) pour facilité d'extension.
- Prêt pour async/queues à venir (workers, BackgroundTasks). 
- Base prête pour RDS (PostgreSQL) via `DATABASE_URL`.

## Optimisations de Performance

### Cache Redis
- Cache distribué pour les résultats de calculs coûteux
- TTL configurable par type de données
- Invalidation automatique lors des mises à jour
- Métriques de performance du cache disponibles via API

### Optimisations Base de Données
- Pool de connexions asynchrones avec `AsyncAdaptedQueuePool`
- Index automatiques sur les colonnes fréquemment utilisées
- Analyse de performance des requêtes
- Optimisation automatique des index via API

### Monitoring et Métriques
- Collecte de métriques système (CPU, mémoire, disque)
- Monitoring des performances de base de données
- Statistiques de cache en temps réel
- Health checks complets pour tous les services

### Architecture Asynchrone
- FastAPI avec support async/await complet
- Gestionnaire de jobs Monte Carlo asynchrone
- Workers distribués pour les calculs intensifs
- Queue SQS pour la distribution des tâches

### Tests de Performance
- Tests d'intégration pour les optimisations
- Tests de charge pour valider les performances
- Benchmarks automatisés
- Monitoring de la mémoire et des connexions