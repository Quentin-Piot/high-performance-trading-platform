# -------------------
# Outputs
# -------------------

output "ecr_repo_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "s3_bucket" {
  description = "Name of the frontend S3 bucket"
  value       = aws_s3_bucket.frontend_bucket.bucket
}

output "cloudfront_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "alb_dns" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.alb.dns_name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.backend_service.name
}

# New outputs for queue and logging infrastructure
output "sqs_queue_url" {
  description = "URL of the main SQS queue for Monte Carlo jobs"
  value       = aws_sqs_queue.monte_carlo_jobs.url
}

output "sqs_dlq_url" {
  description = "URL of the Dead Letter Queue for failed Monte Carlo jobs"
  value       = aws_sqs_queue.monte_carlo_dlq.url
}

output "cloudwatch_log_group" {
  description = "Name of the CloudWatch log group for application logs"
  value       = aws_cloudwatch_log_group.application.name
}

output "cloudwatch_worker_log_group" {
  description = "Name of the CloudWatch log group for Monte Carlo worker logs"
  value       = aws_cloudwatch_log_group.monte_carlo_worker.name
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for Monte Carlo artifacts"
  value       = aws_s3_bucket.monte_carlo_artifacts.arn
}

output "s3_artifacts_bucket" {
  description = "Name of the S3 bucket for Monte Carlo artifacts"
  value       = aws_s3_bucket.monte_carlo_artifacts.bucket
}

output "iam_task_role_arn" {
  description = "ARN of the ECS task role with application permissions"
  value       = aws_iam_role.ecs_task_role.arn
}