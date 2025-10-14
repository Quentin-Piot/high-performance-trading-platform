#!/bin/bash

# Script pour arrêter l'environnement de développement
# Usage: ./scripts/stop-dev.sh

echo "🛑 Arrêt de l'environnement de développement..."

# Arrêter LocalStack
if pgrep -f "localstack" > /dev/null; then
    echo "🐳 Arrêt de LocalStack..."
    localstack stop
    echo "✅ LocalStack arrêté"
else
    echo "ℹ️  LocalStack n'est pas en cours d'exécution"
fi

# Arrêter Redis si installé et en cours d'exécution
if command -v redis-cli &> /dev/null && pgrep -x "redis-server" > /dev/null; then
    echo "🔴 Arrêt de Redis..."
    redis-cli shutdown
    echo "✅ Redis arrêté"
else
    echo "ℹ️  Redis n'est pas en cours d'exécution ou non installé"
fi

echo "✅ Environnement de développement arrêté"