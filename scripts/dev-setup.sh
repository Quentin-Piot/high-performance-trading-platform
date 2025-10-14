#!/bin/bash

# Script de configuration pour l'environnement de développement
# Usage: ./scripts/dev-setup.sh

set -e

echo "🚀 Configuration de l'environnement de développement..."

# Vérifier si LocalStack est installé
if ! command -v localstack &> /dev/null; then
    echo "❌ LocalStack n'est pas installé. Installez-le avec:"
    echo "   brew install localstack/tap/localstack-cli"
    exit 1
fi

# Vérifier si Redis est installé (optionnel, LocalStack peut fournir Redis)
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis n'est pas installé. Vous pouvez l'installer avec:"
    echo "   brew install redis"
    echo "   (LocalStack peut aussi fournir Redis)"
fi

echo "✅ Prérequis vérifiés"

# Créer le fichier .env s'il n'existe pas
if [ ! -f "backend/api/.env" ]; then
    echo "📝 Création du fichier .env..."
    cp backend/api/.env.example backend/api/.env
    echo "✅ Fichier .env créé depuis .env.example"
else
    echo "✅ Fichier .env existe déjà"
fi

# Démarrer Redis en arrière-plan si installé
if command -v redis-server &> /dev/null; then
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "🔴 Démarrage de Redis..."
        redis-server --daemonize yes --port 6379
        echo "✅ Redis démarré sur le port 6379"
    else
        echo "✅ Redis est déjà en cours d'exécution"
    fi
fi

# Démarrer LocalStack en arrière-plan
echo "🐳 Démarrage de LocalStack..."
if pgrep -f "localstack" > /dev/null; then
    echo "⚠️  LocalStack semble déjà en cours d'exécution. Arrêt..."
    pkill -f localstack || true
    sleep 2
fi

# Configurer les variables d'environnement pour LocalStack
export SERVICES=sqs,s3,logs,iam,elasticache
export DEBUG=1
export PERSISTENCE=0

# Démarrer LocalStack
localstack start --detached

# Attendre que LocalStack soit prêt
echo "⏳ Attente de LocalStack..."
timeout=60
counter=0
until curl -s http://localhost:4566/_localstack/health | grep -q '"sqs": "available"' || [ $counter -eq $timeout ]; do
    echo "Attente de LocalStack... ($counter/$timeout)"
    sleep 2
    ((counter++))
done

if [ $counter -eq $timeout ]; then
    echo "❌ Timeout: LocalStack n'a pas démarré dans les temps"
    exit 1
fi

echo "✅ LocalStack est prêt !"

# Exécuter le script d'initialisation
echo "🔧 Initialisation des ressources AWS..."
./scripts/localstack/init-aws-resources.sh

echo ""
echo "🎉 Environnement de développement prêt !"
echo ""
echo "📋 Services disponibles :"
echo "  • LocalStack: http://localhost:4566"
if command -v redis-server &> /dev/null; then
    echo "  • Redis: redis://localhost:6379"
else
    echo "  • Redis (via LocalStack): redis://localhost:4510"
fi
echo "  • SQS Queue: http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs"
echo "  • S3 Bucket: s3://trading-platform-monte-carlo-artifacts-local"
echo ""
echo "🚀 Pour démarrer votre backend :"
echo "  cd backend/api"
echo "  poetry install"
echo "  poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "🛑 Pour arrêter l'environnement :"
echo "  localstack stop"
if command -v redis-server &> /dev/null; then
    echo "  redis-cli shutdown"
fi