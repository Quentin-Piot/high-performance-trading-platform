# Opérations Production – Commandes de Vérification et Maintenance

Ce guide rassemble les commandes pour vérifier et exploiter l’architecture en production sans divulguer de secrets. Remplacez les valeurs entre chevrons par vos propres identifiants lorsque nécessaire.

## Pré-requis
- `awscli` configuré (profil ou variables d’environnement)
- Accès aux ressources AWS dans la région `eu-west-3`
- `terraform` installé et initialisé dans le dossier `terraform/`

## Variables utiles (placeholders)
- `ECS_CLUSTER_NAME`: `trading-platform-cluster`
- `ECS_BACKEND_SERVICE`: `trading-platform-backend-svc`
- `ECS_WORKER_SERVICE`: `trading-platform-monte-carlo-worker-svc`
- `ECR_REPO_NAME`: `trading-platform_backend`
- `CF_DISTRIBUTION_ID`: `<votre_distribution_cloudfront_id>`

Vous pouvez obtenir certaines valeurs via Terraform:
```bash
cd terraform
terraform output -json | jq
```

## 1) Identité et région
```bash
aws sts get-caller-identity
aws configure list
```

## 2) Sorties clés Terraform
```bash
terraform output -raw alb_dns
terraform output -raw cloudfront_domain
terraform output -raw ecs_cluster_name
terraform output -raw ecs_service_name
terraform output -raw sqs_queue_url
terraform output -raw sqs_dlq_url
terraform output -raw ecr_repo_url
terraform output -raw s3_bucket
terraform output -raw s3_artifacts_bucket
```

## 3) ECS – Cluster, services, tâches
```bash
# Décrire le cluster
aws ecs describe-clusters --clusters "trading-platform-cluster"

# Décrire services backend et worker
aws ecs describe-services \
  --cluster "trading-platform-cluster" \
  --services "trading-platform-backend-svc" "trading-platform-monte-carlo-worker-svc"

# Lister les tâches en cours pour le backend
aws ecs list-tasks \
  --cluster "trading-platform-cluster" \
  --service-name "trading-platform-backend-svc" \
  --desired-status RUNNING

# Inspecter la task definition (présence du sidecar Redis)
aws ecs describe-task-definition --task-definition trading-platform-backend-task \
  --query 'taskDefinition.containerDefinitions[].name'

# Vérifier les variables du backend (REDIS_URL / CACHE_ENABLED)
aws ecs describe-task-definition --task-definition trading-platform-backend-task \
  --query 'taskDefinition.containerDefinitions[?name==`backend`].environment'
```

## 4) ALB – Santé des cibles et endpoint API
```bash
# Récupérer l’ARN du Target Group
aws elbv2 describe-target-groups --names trading-platform-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text

# Santé des cibles
aws elbv2 describe-target-health --target-group-arn <TG_ARN>

# Tester l’API via l’ALB
ALB_DNS=$(terraform output -raw alb_dns)
curl -sS "http://$ALB_DNS/api/health" -H "Accept: application/json"
```

## 5) CloudFront – Endpoint API
```bash
CF_DOMAIN=$(terraform output -raw cloudfront_domain)
curl -sS "https://$CF_DOMAIN/api/health" -H "Accept: application/json"
```

## 6) SQS – Attributs et autoscaling du worker
```bash
Q_URL=$(terraform output -raw sqs_queue_url)
aws sqs get-queue-attributes --queue-url "$Q_URL" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

# Scalable target et policy (DesiredCount du service worker)
aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids service/trading-platform-cluster/trading-platform-monte-carlo-worker-svc

aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/trading-platform-cluster/trading-platform-monte-carlo-worker-svc
```

## 7) Logs CloudWatch
```bash
# Logs ECS (containers backend/postgres/redis)
aws logs describe-log-streams --log-group-name /ecs/trading-platform \
  --order-by LastEventTime --descending --limit 5

# Logs worker
aws logs describe-log-streams --log-group-name /aws/worker/trading-platform-monte-carlo \
  --order-by LastEventTime --descending --limit 5

# Événements récents (exemple backend/postgres/redis)
aws logs filter-log-events --log-group-name /ecs/trading-platform --limit 50
```

## 8) ECR – Dépôt et lifecycle policy
```bash
aws ecr describe-repositories --repository-names trading-platform_backend
aws ecr get-lifecycle-policy --repository-name trading-platform_backend
```

## 9) S3 – Frontend (public access block) et artefacts
```bash
FRONTEND_BUCKET=$(terraform output -raw s3_bucket)
aws s3api get-public-access-block --bucket "$FRONTEND_BUCKET"

ARTIFACTS_BUCKET=$(terraform output -raw s3_artifacts_bucket)
aws s3 ls "s3://$ARTIFACTS_BUCKET" --human-readable --summarize
```

## 10) Redis – Exécution de commandes (inspection)
```bash
# Ouvrir une session sur le conteneur redis de la tâche backend (ECS Exec)
aws ecs execute-command \
  --cluster "trading-platform-cluster" \
  --task <TASK_ID> \
  --container redis \
  --command "redis-cli INFO" \
  --interactive
```

## 11) Maintenance courante
```bash
# Forcer un redeploy du service backend (redémarre le sidecar Redis)
aws ecs update-service \
  --cluster "trading-platform-cluster" \
  --service "trading-platform-backend-svc" \
  --force-new-deployment

# Invalider CloudFront après mise à jour du frontend
aws cloudfront create-invalidation \
  --distribution-id <CF_DISTRIBUTION_ID> \
  --paths "/*"

# Observer la file SQS
aws sqs get-queue-attributes --queue-url $(terraform output -raw sqs_queue_url) \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

## Notes
- Aucune donnée sensible n’est imprimée par ces commandes.
- Les noms de ressources (cluster, services, dépôts) ne sont pas des secrets.
- Adaptez la région si vous déployez en dehors de `eu-west-3`.