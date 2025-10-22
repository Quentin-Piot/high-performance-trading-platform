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
until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"' || [ $counter -eq $timeout ]; do
  echo "Attente de LocalStack... ($counter/$timeout)"
  sleep 2
  ((counter++))
done

if [ $counter -eq $timeout ]; then
    echo "❌ Timeout: LocalStack n'est pas disponible"
    echo "🔍 Status LocalStack:"
    curl -s http://localhost:4566/_localstack/health | jq .services || echo "jq non disponible"
    exit 1
fi

echo "✅ LocalStack est prêt !"

# Créer le User Pool Cognito (simulé avec S3 pour LocalStack Community)
echo "👤 Simulation du User Pool Cognito avec S3..."
# Note: Cognito n'est pas disponible dans LocalStack Community
# On utilise des valeurs par défaut configurées dans .env

USER_POOL_ID="eu-west-3_test123"
CLIENT_ID="test_client_id"
IDENTITY_POOL_ID="eu-west-3:test-identity-pool-id"

echo "User Pool ID: $USER_POOL_ID (simulé)"
echo "Client ID: $CLIENT_ID (simulé)"
echo "Identity Pool ID: $IDENTITY_POOL_ID (simulé)"

# Créer le bucket S3 pour les artefacts
echo "🪣 Création du bucket S3..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://trading-platform-bucket || echo "Bucket existe déjà"

echo "📋 Ressources créées :"
echo "  User Pool ID: $USER_POOL_ID"
echo "  Client ID: $CLIENT_ID"
echo "  Identity Pool ID: $IDENTITY_POOL_ID"
echo "  S3 Bucket: s3://trading-platform-bucket"
echo "  Cognito Endpoint: http://localhost:4566"

echo "✅ Initialisation terminée !"