###############################################
# Worker ECS and S3 hardening (Terraform split)
###############################################

# ECS Task Definition (worker Monte Carlo)
resource "aws_ecs_task_definition" "worker_task" {
  family                   = "${var.project_name}-monte-carlo-worker-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true
      command   = ["python", "-m", "workers.monte_carlo_worker"]
      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
        { name = "ENVIRONMENT", value = var.env },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.monte_carlo_jobs.url },
        { name = "SQS_DLQ_URL", value = aws_sqs_queue.monte_carlo_dlq.url },
        { name = "SQS_VISIBILITY_TIMEOUT", value = "300" },
        { name = "SQS_MESSAGE_RETENTION", value = "1209600" },
        { name = "MAX_CONCURRENT_JOBS", value = "1" },
        { name = "POLL_INTERVAL", value = "1.0" },
        { name = "HEALTH_CHECK_INTERVAL", value = "30.0" },
        { name = "WORKER_ID", value = "ecs-mc-worker" },
        { name = "ENABLE_CLOUDWATCH_LOGGING", value = "true" },
        { name = "AWS_LOG_GROUP", value = aws_cloudwatch_log_group.monte_carlo_worker.name },
        { name = "AWS_LOG_STREAM", value = "worker-logs" },
        { name = "S3_ARTIFACTS_BUCKET", value = aws_s3_bucket.monte_carlo_artifacts.bucket }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.monte_carlo_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])
}

# ECS Service (worker Monte Carlo)
resource "aws_ecs_service" "worker_service" {
  name            = "${var.project_name}-monte-carlo-worker-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker_task.arn
  desired_count   = 0

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = [for s in aws_subnet.public : s.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  depends_on = [
    aws_sqs_queue.monte_carlo_jobs,
    aws_cloudwatch_log_group.monte_carlo_worker,
    aws_iam_role.ecs_task_role,
    aws_iam_role.ecs_task_execution_role
  ]

  tags = { Name = "${var.project_name}-monte-carlo-worker-svc" }
}

# Harden S3 artifacts bucket: block all public access
resource "aws_s3_bucket_public_access_block" "monte_carlo_artifacts_block" {
  bucket                  = aws_s3_bucket.monte_carlo_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Worker-specific outputs
output "worker_service_name" {
  description = "Name of the ECS worker service"
  value       = aws_ecs_service.worker_service.name
}

output "worker_task_family" {
  description = "Family name of the ECS worker task"
  value       = aws_ecs_task_definition.worker_task.family
}

# Autoscaling: scale to 0 when queue is empty, scale out on backlog
resource "aws_appautoscaling_target" "worker_desired" {
  max_capacity       = 2
  min_capacity       = 0
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "worker_target_tracking" {
  name               = "${var.project_name}-mc-worker-tt-sqs"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_desired.resource_id
  scalable_dimension = aws_appautoscaling_target.worker_desired.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_desired.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 1
    scale_in_cooldown  = 60
    scale_out_cooldown = 30

    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"

      dimensions {
        name  = "QueueName"
        value = aws_sqs_queue.monte_carlo_jobs.name
      }
    }
  }
}

# ECR: cleanup old images to reduce storage costs
resource "aws_ecr_lifecycle_policy" "backend_cleanup" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire images beyond last 5"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}