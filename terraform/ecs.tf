locals {
  backend_environment = [
    { name = "DATABASE_HOST", value = aws_db_instance.postgres.address },
    { name = "DATABASE_PORT", value = tostring(aws_db_instance.postgres.port) },
    { name = "DATABASE_NAME", value = var.db_name },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "AWS_DEFAULT_REGION", value = var.aws_region },
    { name = "ENABLE_CLOUDWATCH_LOGGING", value = "true" },
    { name = "AWS_LOG_GROUP", value = aws_cloudwatch_log_group.application.name },
    { name = "AWS_LOG_STREAM", value = "api-logs" },
    { name = "S3_ARTIFACTS_BUCKET", value = aws_s3_bucket.monte_carlo_artifacts.bucket },
    { name = "ENVIRONMENT", value = var.env },
    { name = "FRONTEND_URL", value = var.frontend_url },
    { name = "JWT_ALGORITHM", value = "HS256" },
    { name = "ACCESS_TOKEN_EXPIRE_MINUTES", value = "43200" },
    { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
    { name = "GOOGLE_REDIRECT_URI", value = var.google_redirect_uri },
    { name = "COGNITO_REGION", value = var.aws_region },
    { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.main.id },
    { name = "COGNITO_CLIENT_ID", value = aws_cognito_user_pool_client.web_client.id },
    { name = "COGNITO_IDENTITY_POOL_ID", value = aws_cognito_identity_pool.main.id }
  ]

  backend_secrets = concat(
    [
      { name = "DATABASE_USER", valueFrom = "${aws_db_instance.postgres.master_user_secret[0].secret_arn}:username::" },
      { name = "DATABASE_PASSWORD", valueFrom = "${aws_db_instance.postgres.master_user_secret[0].secret_arn}:password::" },
      { name = "JWT_SECRET", valueFrom = var.jwt_secret_arn }
    ],
    var.app_google_client_secret_arn != "" ? [
      { name = "GOOGLE_CLIENT_SECRET", valueFrom = var.app_google_client_secret_arn }
    ] : []
  )
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

resource "aws_ecs_task_definition" "backend_task" {
  family                   = "${var.project_name}-backend-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true
      cpu       = 512
      memory    = 1024
      portMappings = [
        { containerPort = 8000, protocol = "tcp" }
      ]
      environment = local.backend_environment
      secrets     = local.backend_secrets
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

  tags = {
    Name = "${var.project_name}-backend-task"
  }
}

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

  depends_on = [aws_lb_listener.https]

  tags = {
    Name = "${var.project_name}-backend-svc"
  }
}
