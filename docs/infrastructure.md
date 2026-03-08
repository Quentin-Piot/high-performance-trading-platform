# Infrastructure (Terraform + AWS)

## Scope

This document describes the infrastructure currently defined in `terraform/` and the deployment model used by the repository.

It focuses on:
- what is created
- why it is configured that way
- how deployment works
- practical limitations and trade-offs

## High-Level Deployment Topology

Current cloud architecture (Terraform-managed AWS):
- frontend static assets on **S3**
- **CloudFront** distribution in front of frontend and API
- backend API on **ECS Fargate**
- PostgreSQL running in the **same ECS task** as backend (MVP / cost optimization)
- **EFS** for PostgreSQL persistence
- **ALB** in front of backend
- **Cognito** (+ Google IdP) for authentication federation
- **CloudWatch Logs** for runtime logs
- **Route53** for custom domain routing

## Terraform Files and Resources

## `terraform/vpc.tf`
Creates networking foundations:
- `aws_vpc.main`
- public subnets
- internet gateway
- public route table + associations

## `terraform/security_groups.tf`
Creates security groups for:
- ALB
- ECS service/task
- EFS

Purpose:
- restrict traffic paths (ALB -> ECS, ECS -> EFS)

## `terraform/alb.tf`
Creates:
- `aws_lb.alb`
- `aws_lb_target_group.tg`
- `aws_lb_listener.listener`

Purpose:
- route HTTP traffic to backend container port `8000`

## `terraform/ecs.tf`
Creates:
- `aws_ecs_cluster.main`
- `aws_ecs_task_definition.backend_task`
- `aws_ecs_service.backend_service`

Important current design choice:
- ECS task definition includes **two containers**:
  - `backend`
  - `postgres`

This is a deliberate cost/simplicity trade-off, not a final enterprise setup.

## `terraform/efs.tf`
Creates:
- `aws_efs_file_system.postgres`
- EFS mount targets

Purpose:
- persist PostgreSQL data used by the ECS task

## `terraform/ecr.tf`
Creates:
- backend Docker image repository (ECR)

## `terraform/s3.tf`
Creates:
- frontend bucket (static hosting origin for CloudFront)
- Monte Carlo artifacts bucket
- bucket policies / OAI integration
- versioning + server-side encryption
- lifecycle for artifacts bucket

## `terraform/cloudfront.tf`
Creates CloudFront distribution with two origins:
- frontend S3 bucket
- backend ALB

Key behaviors:
- default behavior serves frontend (SPA-friendly)
- `/api/*` routes to backend (no caching)
- `assets/*` uses long cache TTLs
- 403/404 fallback to `/index.html` for SPA routing

## `terraform/cognito.tf`
Creates authentication resources:
- Cognito user pool
- user pool domain
- app client
- Google identity provider
- identity pool
- IAM roles/policies for identity pool attachment

## `terraform/iam.tf`
Creates IAM roles/policies for:
- ECS task execution
- ECS task runtime permissions
- app-specific AWS access (logs/S3/etc.)

## `terraform/cloudwatch.tf`
Creates log groups for:
- ECS containers
- application logs

## `terraform/route53.tf`
Creates Route53 alias record(s) pointing custom domain traffic to CloudFront.

## `terraform/data.tf`
Includes supporting resources/data helpers (e.g., random suffixes / lookups used by other modules).

## Key Terraform Variables

Defined in `terraform/variables.tf`.

Commonly required variables:
- `aws_region`
- `project_name`
- `env`
- `jwt`
- `vpc_cidr`
- `frontend_alias_domain`
- `acm_certificate_arn` (must be in `us-east-1` for CloudFront)
- `frontend_url`
- `google_redirect_uri`

Example values:
- `terraform/terraform.tfvars.example`

## Backend Runtime Environment Variables (Injected by ECS)

`terraform/ecs.tf` injects environment variables for the backend container, including:

Database:
- `DATABASE_URL`
- `DATABASE_HOST`
- `DATABASE_PORT`
- `DATABASE_NAME`
- `DATABASE_USER`
- `DATABASE_PASSWORD`

Application:
- `ENVIRONMENT`
- `FRONTEND_URL`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

AWS / logging / storage:
- `AWS_REGION`
- `AWS_DEFAULT_REGION`
- `ENABLE_CLOUDWATCH_LOGGING`
- `AWS_LOG_GROUP`
- `AWS_LOG_STREAM`
- `S3_ARTIFACTS_BUCKET`

Auth federation:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `COGNITO_REGION`
- `COGNITO_USER_POOL_ID`
- `COGNITO_CLIENT_ID`
- `COGNITO_IDENTITY_POOL_ID`

## Deployment Workflows

## 1) Terraform infrastructure deployment

Typical flow:

```bash
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Good practices (important):
- do not commit `*.tfstate` or `tfplan*`
- prefer a remote Terraform backend for team usage
- rotate secrets if a state file was ever exposed

## 2) Application CI/CD (`.github/workflows/deploy.yml`)

Trigger:
- push to `master`

Pipeline structure:

### Detect changes
- path filtering for `backend/**`, `web/**`, workflow files

### Frontend pipeline
- install dependencies (`pnpm`)
- lint
- build
- upload build artifact
- deploy to S3
- invalidate CloudFront cache

### Backend pipeline
- install deps via `uv`
- run `make lint`, `make typecheck`, `make test`
- build Docker image
- push image to ECR
- force ECS service redeploy

## Local Development Infrastructure

Full stack:

```bash
docker compose up --build
```

Postgres only:

```bash
docker compose -f docker-compose.db.yml up -d
```

## Current Limitations and Trade-offs

- backend and PostgreSQL share one ECS task (cheap/simple, but less isolated)
- no external queue service for async Monte Carlo jobs
- DB HA is limited compared with managed RDS setups
- infrastructure is production-oriented but intentionally cost-constrained

## RAG Retrieval Tips

For infra questions, prioritize these files:
- `docs/infrastructure.md`
- `terraform/ecs.tf`
- `terraform/cloudfront.tf`
- `terraform/s3.tf`
- `terraform/cognito.tf`
- `.github/workflows/deploy.yml`
