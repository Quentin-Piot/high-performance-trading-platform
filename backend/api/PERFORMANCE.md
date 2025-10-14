# Performance Optimization Guide

Ce document détaille les optimisations de performance implémentées dans l'API de trading et comment les utiliser efficacement.

## Vue d'ensemble des optimisations

### 1. Cache Redis Distribué

Le système utilise Redis pour mettre en cache les résultats de calculs coûteux et améliorer les temps de réponse.

#### Configuration
```python
# Configuration dans .env
REDIS_URL=redis://localhost:6379/0
REDIS_TTL=3600  # TTL par défaut en secondes
```

#### Utilisation du décorateur de cache
```python
from infrastructure.cache import cached_result

@cached_result(prefix="backtest", ttl=1800)
async def expensive_calculation(param1: str, param2: int):
    # Calcul coûteux ici
    return result
```

#### Métriques de cache disponibles
- Hit rate (taux de succès)
- Miss rate (taux d'échec)
- Nombre total de clés
- Utilisation mémoire
- Latence moyenne

### 2. Optimisations Base de Données

#### Pool de connexions asynchrones
```python
# Configuration automatique dans db.py
engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

#### Index automatiques
Le système crée automatiquement des index sur les colonnes fréquemment utilisées :
- `jobs.status` - pour les requêtes de filtrage par statut
- `jobs.created_at` - pour les requêtes temporelles
- `jobs.user_id` - pour les requêtes par utilisateur
- `users.email` - pour l'authentification

#### Analyse de performance
```bash
# Via API
GET /api/v1/performance/indexes
POST /api/v1/performance/indexes/optimize
```

### 3. Monitoring et Métriques

#### Endpoints de monitoring
```bash
# Statistiques de base de données
GET /api/v1/performance/database

# Statistiques de cache
GET /api/v1/performance/cache

# Métriques système
GET /api/v1/performance/system
```

#### Métriques collectées
- **Base de données** : Connexions actives, requêtes lentes, taille des tables
- **Cache** : Hit/miss ratio, latence, utilisation mémoire
- **Système** : CPU, mémoire, disque, réseau
- **Application** : Temps de réponse, erreurs, throughput

### 4. Architecture Asynchrone

#### Gestionnaire de jobs Monte Carlo
```python
# Soumission asynchrone de jobs
job_id = await job_manager.submit_job(payload, priority=JobPriority.HIGH)

# Suivi du progrès
progress = await job_manager.get_job_progress(job_id)
```

#### Workers distribués
Les workers Monte Carlo s'exécutent de manière asynchrone et peuvent être distribués sur plusieurs machines.

## Tests de Performance

### Tests d'intégration
```bash
# Tests des optimisations de performance
pytest tests/test_performance_simple.py -v

# Tests de charge
pytest tests/test_load_performance.py -v
```

### Benchmarks
Les tests incluent :
- Tests de concurrence API (100 requêtes simultanées)
- Tests d'efficacité mémoire du cache
- Tests de performance de base de données
- Tests de connexions multiples

## Bonnes Pratiques

### 1. Utilisation du Cache
- Utilisez le cache pour les calculs coûteux (> 100ms)
- Définissez des TTL appropriés selon la fréquence de mise à jour
- Invalidez le cache lors des modifications de données

### 2. Optimisation des Requêtes
- Utilisez les index existants dans vos requêtes
- Évitez les requêtes N+1
- Utilisez la pagination pour les grandes listes

### 3. Monitoring
- Surveillez régulièrement les métriques de performance
- Configurez des alertes sur les seuils critiques
- Analysez les requêtes lentes périodiquement

### 4. Scaling
- Le cache Redis peut être clusterisé pour la haute disponibilité
- Les workers peuvent être distribués sur plusieurs instances
- La base de données supporte le read scaling avec des réplicas

## Dépannage

### Cache Redis
```bash
# Vérifier la connectivité Redis
redis-cli ping

# Statistiques Redis
redis-cli info memory
redis-cli info stats
```

### Base de données
```bash
# Requêtes lentes PostgreSQL
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

# Index inutilisés
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_tup_read = 0;
```

### Monitoring
```bash
# Health checks
curl http://localhost:8000/api/healthz
curl http://localhost:8000/api/readyz

# Métriques de performance
curl http://localhost:8000/api/v1/performance/system
```

## Configuration Avancée

### Variables d'environnement de performance
```bash
# Pool de connexions DB
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_RECYCLE=3600

# Cache Redis
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_KEEPALIVE=True
REDIS_SOCKET_KEEPALIVE_OPTIONS={}

# Workers
MAX_CONCURRENT_JOBS=10
JOB_TIMEOUT=3600
WORKER_HEARTBEAT_INTERVAL=30
```

### Scaling Horizontal
Pour scaler horizontalement :
1. Déployez plusieurs instances de l'API
2. Utilisez un load balancer (nginx, ALB)
3. Configurez Redis en mode cluster
4. Utilisez des réplicas PostgreSQL pour les lectures
5. Distribuez les workers sur plusieurs machines