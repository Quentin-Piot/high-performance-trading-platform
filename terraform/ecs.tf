# -------------------
# ECS Cluster, Task Definition, and Service
# -------------------

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# ECS Task Definition (backend + postgres in same task)
resource "aws_ecs_task_definition" "backend_task" {
  family                   = "${var.project_name}-backend-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "postgres"
      image     = "postgres:16"
      essential = true
      environment = [
        { name = "POSTGRES_DB", value = "trading_db" },
        { name = "POSTGRES_USER", value = "postgres" },
        { name = "POSTGRES_PASSWORD", value = "postgres" }
      ]
      mountPoints = [
        {
          sourceVolume  = "postgres-data"
          containerPath = "/var/lib/postgresql/data"
          readOnly      = false
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "postgres"
        }
      }
    },
    {
      name      = "redis"
      image     = "redis:7-alpine"
      essential = true
      portMappings = [
        { containerPort = 6379, protocol = "tcp" }
      ]
      command = [
        "redis-server",
        "--appendonly", "no",
        "--save", "",
        "--maxmemory", "256mb",
        "--maxmemory-policy", "allkeys-lru",
        "--protected-mode", "yes"
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "redis"
        }
      }
    },
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true
      portMappings = [
        { containerPort = 8000, protocol = "tcp" }
      ]
      environment = [
        # Database configuration
        { name = "DATABASE_HOST", value = "localhost" }, # postgres in same task
        { name = "DATABASE_PORT", value = "5432" },
        { name = "DATABASE_NAME", value = "trading_db" },
        { name = "DATABASE_USER", value = "postgres" },
        { name = "DATABASE_PASSWORD", value = "postgres" },

        # Redis cache
        { name = "REDIS_URL", value = "redis://localhost:6379/0" },
        { name = "CACHE_ENABLED", value = "true" },

        # AWS configuration
        { name = "AWS_REGION", value = var.aws_region },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },

        # SQS configuration
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.monte_carlo_jobs.url },
        { name = "SQS_DLQ_URL", value = aws_sqs_queue.monte_carlo_dlq.url },
        { name = "SQS_VISIBILITY_TIMEOUT", value = "300" },
        { name = "SQS_MESSAGE_RETENTION", value = "1209600" },

        # CloudWatch Logs configuration
        { name = "ENABLE_CLOUDWATCH_LOGGING", value = "true" },
        { name = "AWS_LOG_GROUP", value = aws_cloudwatch_log_group.application.name },
        { name = "AWS_LOG_STREAM", value = "api-logs" },

        # S3 configuration
        { name = "S3_ARTIFACTS_BUCKET", value = aws_s3_bucket.monte_carlo_artifacts.bucket },

        # Application configuration
        { name = "ENVIRONMENT", value = var.env },
        { name = "FRONTEND_URL", value = var.frontend_url },

        # Google OAuth configuration
        { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
        { name = "GOOGLE_CLIENT_SECRET", value = var.google_client_secret },
        { name = "GOOGLE_REDIRECT_URI", value = var.google_redirect_uri },

        # Worker configuration
        { name = "RUN_WORKER", value = "true" }
      ]
      dependsOn = [
        { containerName = "postgres", condition = "START" },
        { containerName = "redis", condition = "START" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])

  volume {
    name = "postgres-data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.postgres.id
      root_directory     = "/"
      transit_encryption = "ENABLED"
    }
  }

  tags = {
    Name = "${var.project_name}-backend-task"
  }
}

# ECS Service
resource "aws_ecs_service" "backend_service" {
  name            = "${var.project_name}-backend-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [for s in aws_subnet.public : s.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.tg.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.listener]

  tags = {
    Name = "${var.project_name}-backend-svc"
  }
}