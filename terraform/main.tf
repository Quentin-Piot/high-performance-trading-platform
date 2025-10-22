###############################################################################
# High Performance Trading Platform - Terraform Infrastructure
#
# This infrastructure is now modularized across multiple files:
# - versions.tf: Terraform and provider version constraints
# - providers.tf: Provider configurations
# - variables.tf: Input variables
# - data.tf: Data sources and random resources
# - vpc.tf: VPC, subnets, IGW, route tables
# - security_groups.tf: Security groups for ALB, ECS, and EFS
# - s3.tf: S3 buckets for frontend and Monte Carlo artifacts
# - cloudfront.tf: CloudFront distribution
# - route53.tf: DNS records
# - ecr.tf: ECR repository
# - efs.tf: EFS file system for Postgres data
# - iam.tf: IAM roles and policies
# - cloudwatch.tf: CloudWatch log groups
# - sqs.tf: SQS queues for Monte Carlo jobs
# - alb.tf: Application Load Balancer
# - ecs.tf: ECS cluster, task definition, and service
# - outputs.tf: Output values
# - cognito.tf: Cognito user pool and identity provider (existing)
#
# USAGE:
#   terraform init
#   terraform plan -var-file="terraform.tfvars"
#   terraform apply -var-file="terraform.tfvars"
#
# NOTES:
# - Database runs inside same Fargate task as backend and uses EFS for persistence
#   (simple and cost-effective for demo/low-traffic projects)
# - For production-grade setup, consider moving to RDS
# - All resources are properly tagged and follow AWS best practices
###############################################################################

# This file is intentionally kept minimal after refactoring.
# All resources have been moved to their respective specialized files.
