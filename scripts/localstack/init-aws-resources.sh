#!/bin/bash

# Script d'initialisation des ressources AWS dans LocalStack
# Ce script est exécuté automatiquement au démarrage de LocalStack

set -e

echo "🚀 Initialisation des ressources AWS dans LocalStack..."

# Configuration AWS CLI pour LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=eu-west-3
export AWS_ENDPOINT_URL=http://localhost:4566

# Attendre que LocalStack soit prêt
echo "⏳ Attente de LocalStack..."
timeout=30
counter=0
until curl -s http://localhost:4566/_localstack/health | grep -q '"sqs": "running"' || [ $counter -eq $timeout ]; do
  echo "Attente de SQS... ($counter/$timeout)"
  sleep 2
  ((counter++))
done

if [ $counter -eq $timeout ]; then
    echo "❌ Timeout: SQS n'est pas disponible dans LocalStack"
    echo "🔍 Status LocalStack:"
    curl -s http://localhost:4566/_localstack/health | jq .services.sqs || echo "jq non disponible"
    exit 1
fi

echo "✅ LocalStack est prêt !"

# Créer les queues SQS
echo "📨 Création des queues SQS..."

# Dead Letter Queue
aws --endpoint-url=http://localhost:4566 sqs create-queue \
    --queue-name trading-platform-monte-carlo-jobs-dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600"
    }' || echo "DLQ existe déjà"

# Queue principale avec DLQ
aws --endpoint-url=http://localhost:4566 sqs create-queue \
    --queue-name trading-platform-monte-carlo-jobs \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeout": "300"
    }' || echo "Queue principale existe déjà"

# Créer le bucket S3 pour les artefacts
echo "🪣 Création du bucket S3..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://trading-platform-monte-carlo-artifacts-local || echo "Bucket existe déjà"

# Créer les log groups CloudWatch
echo "📊 Création des log groups CloudWatch..."
aws --endpoint-url=http://localhost:4566 logs create-log-group \
    --log-group-name /aws/application/trading-platform || echo "Log group application existe déjà"

aws --endpoint-url=http://localhost:4566 logs create-log-group \
    --log-group-name /aws/worker/trading-platform-monte-carlo || echo "Log group worker existe déjà"

# Afficher les URLs des queues
echo "📋 Ressources créées :"
echo "  SQS Queue URL: http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs"
echo "  SQS DLQ URL: http://localhost:4566/000000000000/trading-platform-monte-carlo-jobs-dlq"
echo "  S3 Bucket: s3://trading-platform-monte-carlo-artifacts-local"
echo "  Redis: redis://localhost:4510 (via LocalStack) ou redis://localhost:6379 (standalone)"

echo "✅ Initialisation terminée !"