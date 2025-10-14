# 🛠️ Environnement de Développement Local

Ce guide explique comment configurer et utiliser l'environnement de développement local avec LocalStack standalone (installé via Homebrew) pour simuler les services AWS.

## 🚀 Démarrage Rapide

### 1. Prérequis
- LocalStack installé via Homebrew (`brew install localstack/tap/localstack-cli`)
- Redis installé (optionnel) (`brew install redis`)
- Python 3.11+ avec Poetry

### 2. Configuration automatique
```bash
# Depuis la racine du projet
./scripts/dev-setup.sh
```

Ce script va :
- ✅ Vérifier les prérequis
- 📝 Créer le fichier `.env` depuis `.env.example`
- 🔴 Démarrer Redis (si installé)
- 🐳 Démarrer LocalStack en mode standalone
- 🔧 Initialiser les ressources AWS (SQS, S3, CloudWatch)

### 3. Démarrer le backend
```bash
cd backend/api
poetry install
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Services Disponibles

| Service | URL | Description |
|---------|-----|-------------|
| **LocalStack** | http://localhost:4566 | Gateway principal |
| **Redis** | redis://localhost:6379 | Cache et sessions (si installé) |
| **Redis (LocalStack)** | redis://localhost:4510 | Alternative via LocalStack |
| **SQS Queue** | http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs | Queue principale |
| **SQS DLQ** | http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs-dlq | Dead Letter Queue |
| **S3 Bucket** | s3://trading-platform-monte-carlo-artifacts-local | Stockage artefacts |

## 🔧 Configuration Manuelle (Alternative)

Si vous préférez configurer manuellement :

### 1. Démarrer Redis (optionnel)
```bash
redis-server --daemonize yes --port 6379
```

### 2. Démarrer LocalStack
```bash
localstack start --detached --config localstack-config.yml
```

### 3. Initialiser les ressources
```bash
./scripts/localstack/init-aws-resources.sh
```

### 4. Créer le fichier .env
```bash
cp backend/api/.env.example backend/api/.env
```

## 🧪 Tests et Vérification

### Tester SQS
```bash
# Envoyer un message
aws --endpoint-url=http://localhost:4566 sqs send-message \
    --queue-url http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs \
    --message-body '{"test": "message"}'

# Recevoir des messages
aws --endpoint-url=http://localhost:4566 sqs receive-message \
    --queue-url http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs
```

### Tester Redis
```bash
# Avec redis-cli
redis-cli -h localhost -p 6379 ping
# Doit retourner: PONG

# Ou avec Python
python -c "import redis; r=redis.Redis(host='localhost', port=6379); print('✅ Redis OK' if r.ping() else '❌ Redis KO')"
```

### Tester S3
```bash
# Lister les buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# Uploader un fichier test
echo "test content" > test.txt
aws --endpoint-url=http://localhost:4566 s3 cp test.txt s3://trading-platform-monte-carlo-artifacts-local/
rm test.txt
```

## 🔍 Debugging

### Logs LocalStack
```bash
localstack logs
# ou pour suivre en temps réel
localstack logs -f
```

### Status des services
```bash
curl http://localhost:4566/_localstack/health
```

### Interface Web LocalStack (optionnel)
Si vous avez LocalStack Pro, vous pouvez accéder à l'interface web sur http://localhost:4566

## 🛑 Arrêter l'environnement

```bash
# Script automatique
./scripts/stop-dev.sh

# Ou manuellement
localstack stop
redis-cli shutdown  # Si Redis installé
```

## 🔄 Variables d'Environnement

Le fichier `.env` contient toutes les configurations nécessaires :

```bash
# SQS (LocalStack)
SQS_QUEUE_URL=http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs
SQS_ENDPOINT_URL=http://localhost:4566

# Redis
REDIS_URL=redis://localhost:6379

# S3 (LocalStack)
S3_ARTIFACTS_BUCKET=trading-platform-monte-carlo-artifacts-local
S3_ENDPOINT_URL=http://localhost:4566

# AWS (LocalStack)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=eu-west-3
```

## 🚨 Problèmes Courants

### LocalStack ne démarre pas
- Vérifiez que le port 4566 n'est pas utilisé : `lsof -i :4566`
- Vérifiez les logs : `localstack logs`
- Redémarrez LocalStack : `localstack stop && localstack start --detached --config localstack-config.yml`

### Redis non accessible
- Si Redis standalone : vérifiez qu'il est démarré avec `pgrep redis-server`
- Alternative : utilisez Redis via LocalStack sur le port 4510
- Testez la connexion : `redis-cli -h localhost -p 6379 ping`

### Queues SQS non créées
- Relancez le script d'initialisation : `./scripts/localstack/init-aws-resources.sh`
- Vérifiez les logs : `localstack logs`

## 📚 Ressources

- [Documentation LocalStack](https://docs.localstack.cloud/)
- [AWS CLI avec LocalStack](https://docs.localstack.cloud/user-guide/integrations/aws-cli/)
- [Redis Documentation](https://redis.io/documentation)