# Configuration de Production

## Variables d'environnement GitHub Secrets

Pour que le déploiement en production fonctionne, vous devez configurer les secrets suivants dans votre repository GitHub (Settings > Secrets and variables > Actions) :

### AWS Configuration
- `AWS_ACCESS_KEY_ID` : Clé d'accès AWS pour le déploiement
- `AWS_SECRET_ACCESS_KEY` : Clé secrète AWS pour le déploiement
- `AWS_ACCOUNT_ID` : ID de votre compte AWS (ex: 491085385866)

### Infrastructure
- `S3_BUCKET` : Nom du bucket S3 pour le frontend (ex: trading-platform-frontend-491085385866)
- `CLOUDFRONT_DIST_ID` : ID de la distribution CloudFront (optionnel)
- `ECS_CLUSTER_NAME` : Nom du cluster ECS (ex: trading-platform-cluster)
- `ECS_SERVICE_NAME` : Nom du service ECS (ex: trading-platform-backend-svc)

### Cognito Configuration
- `COGNITO_REGION` : Région AWS Cognito (ex: eu-west-3)
- `COGNITO_USER_POOL_ID` : ID du User Pool Cognito (ex: eu-west-3_pb05WIUdA)
- `COGNITO_CLIENT_ID` : ID du client Cognito (ex: hcl2tpol6rk94cu1u0cg9o4f4)
- `COGNITO_IDENTITY_POOL_ID` : ID de l'Identity Pool Cognito (ex: eu-west-3:cd70617e-bd7c-45ba-8196-e7818bda3b14)

### Google OAuth Configuration
- `GOOGLE_CLIENT_ID` : Client ID Google OAuth
- `GOOGLE_CLIENT_SECRET` : Client Secret Google OAuth

## Configuration Google OAuth

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer ou sélectionner un projet
3. Activer l'API Google Identity
4. Créer des identifiants OAuth 2.0
5. Ajouter les URLs de redirection autorisées :
   - `https://trading-platform-alb-1363873398.eu-west-3.elb.amazonaws.com/api/v1/auth/google/callback`
   - `https://votre-domaine-cloudfront.cloudfront.net/auth/callback` (si vous utilisez un domaine personnalisé)

## Variables d'environnement Backend (Production)

Le backend en production doit avoir ces variables d'environnement configurées dans ECS :

```bash
# Database
DATABASE_URL=postgresql+psycopg://username:password@rds-endpoint:5432/trading_db

# JWT
JWT_SECRET=your-production-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AWS Cognito
COGNITO_REGION=eu-west-3
COGNITO_USER_POOL_ID=eu-west-3_pb05WIUdA
COGNITO_CLIENT_ID=hcl2tpol6rk94cu1u0cg9o4f4
COGNITO_IDENTITY_POOL_ID=eu-west-3:cd70617e-bd7c-45ba-8196-e7818bda3b14

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://trading-platform-alb-1363873398.eu-west-3.elb.amazonaws.com/api/v1/auth/google/callback

# SQS
SQS_QUEUE_URL=https://sqs.eu-west-3.amazonaws.com/491085385866/trading-platform-monte-carlo-jobs
SQS_DLQ_URL=https://sqs.eu-west-3.amazonaws.com/491085385866/trading-platform-monte-carlo-jobs-dlq

# S3
S3_ARTIFACTS_BUCKET=trading-platform-monte-carlo-artifacts-mek4tzqx

# Redis (ElastiCache)
REDIS_URL=redis://your-elasticache-endpoint:6379

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## Déploiement

1. Configurer tous les secrets GitHub
2. Pousser sur la branche `master`
3. Le workflow GitHub Actions se déclenchera automatiquement et :
   - Construira et poussera l'image Docker du backend vers ECR
   - Construira le frontend avec les variables d'environnement de production
   - Déploiera le frontend sur S3
   - Invalidera le cache CloudFront
   - Forcera un nouveau déploiement ECS

## Vérifications post-déploiement

1. Vérifier que le service ECS est en cours d'exécution
2. Tester l'API via l'ALB : `https://trading-platform-alb-1363873398.eu-west-3.elb.amazonaws.com/api/v1/health`
3. Tester le frontend via CloudFront
4. Tester l'authentification Google