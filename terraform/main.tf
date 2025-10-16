###############################################################################

# trading-platform - Terraform (all-in-one)

# - Region: eu-west-3 (override with -var aws_region if needed)

# - Creates: VPC, Subnets, IGW, ALB, ECS Cluster, ECR, S3+CloudFront (OAI),

#   EFS, ECS Fargate Task (backend + postgres), Service, security groups.

#

# USAGE:

#   terraform init

#   terraform apply -var="aws_region=eu-west-3"

#

# NOTES / TRADEOFFS:

# - DB runs inside same Fargate task as backend and uses EFS for persistence

#   (simple and cheap for a demo / low-traffic project).

# - If you want production-grade DB: move to RDS (I'll provide later).

###############################################################################


terraform {
  required_version = ">= 1.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
  }
}


provider "aws" {

  region = var.aws_region

}


# -------------------

# Variables (defaults)

# -------------------

variable "aws_region" {

  type = string

  default = "eu-west-3"

}


variable "project_name" {

  type = string

  default = "trading-platform"

}


variable "env" {

  type = string

  default = "staging"

}


variable "vpc_cidr" {

  type = string

  default = "10.100.0.0/16"

}


# -------------------

# Data

# -------------------
 
# CloudFront custom domain settings
variable "frontend_alias_domain" {
  description = "Alias domain for CloudFront (e.g., hptp.quentinpiot.com)"
  type        = string
}

# ACM certificate ARN in us-east-1 (preexisting)
variable "acm_certificate_arn" {
  description = "ARN of the existing ACM certificate in us-east-1"
  type        = string
}

data "aws_caller_identity" "current" {}


data "aws_availability_zones" "azs" {

  state = "available"

}


# -------------------

# Basic infra: VPC, Subnets, IGW, RouteTable

# -------------------

resource "aws_vpc" "main" {

  cidr_block = var.vpc_cidr

  enable_dns_hostnames = true

  enable_dns_support = true

  tags = { Name = "${var.project_name}-vpc-${var.env}" }

}


# two public subnets (spread across AZs)

resource "aws_subnet" "public" {

  count = 2

  vpc_id = aws_vpc.main.id

  cidr_block = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)

  availability_zone = data.aws_availability_zones.azs.names[count.index]

  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-public-${count.index}" }

}


resource "aws_internet_gateway" "igw" {

  vpc_id = aws_vpc.main.id

  tags = { Name = "${var.project_name}-igw" }

}


resource "aws_route_table" "public_rt" {

  vpc_id = aws_vpc.main.id

  route {

    cidr_block = "0.0.0.0/0"

    gateway_id = aws_internet_gateway.igw.id

  }

  tags = { Name = "${var.project_name}-public-rt" }

}


resource "aws_route_table_association" "public_assoc" {

  count = length(aws_subnet.public)

  subnet_id = aws_subnet.public[count.index].id

  route_table_id = aws_route_table.public_rt.id

}


# -------------------

# Security Groups

# -------------------

# ALB SG: allow 80 from internet

resource "aws_security_group" "alb_sg" {

  name = "alb-sg"

  description = "Security group for Application Load Balancer"

  vpc_id = aws_vpc.main.id


  ingress {

    from_port = 80

    to_port = 80

    protocol = "tcp"

    cidr_blocks = ["0.0.0.0/0"]

  }


  egress {

    from_port = 0

    to_port = 0

    protocol = "-1"

    cidr_blocks = ["0.0.0.0/0"]

  }

}



# ECS tasks SG: allow 8000 from ALB only; allow outbound to anywhere

resource "aws_security_group" "ecs_sg" {

  name = "${var.project_name}-ecs-sg"

  vpc_id = aws_vpc.main.id

  description = "ECS tasks SG - allow traffic from ALB on app port"


  ingress {

    from_port = 8000

    to_port = 8000

    protocol = "tcp"

    security_groups = [aws_security_group.alb_sg.id]

    description = "Allow ALB to ECS"

  }


  egress {

    from_port = 0

    to_port = 0

    protocol = "-1"

    cidr_blocks = ["0.0.0.0/0"]

  }


  tags = {

    Name = "${var.project_name}-ecs-sg"

  }

}



# EFS SG: allow NFS from ECS tasks SG

resource "aws_security_group" "efs_sg" {

  name = "${var.project_name}-efs-sg"

  vpc_id = aws_vpc.main.id

  description = "EFS SG - allow NFS from ECS tasks"


  ingress {

    from_port = 2049

    to_port = 2049

    protocol = "tcp"

    security_groups = [aws_security_group.ecs_sg.id]

    description = "Allow ECS to EFS"

  }


  egress {

    from_port = 0

    to_port = 0

    protocol = "-1"

    cidr_blocks = ["0.0.0.0/0"]

  }


  tags = {

    Name = "${var.project_name}-efs-sg"

  }

}



# -------------------

# S3 bucket for frontend (private) + CloudFront OAI

# -------------------

resource "aws_s3_bucket" "frontend_bucket" {

  bucket = "${var.project_name}-frontend-${data.aws_caller_identity.current.account_id}"

  acl = "private"

  force_destroy = true # convenient for dev; remove for strict prod

  versioning { enabled = true }

  server_side_encryption_configuration {

    rule {

      apply_server_side_encryption_by_default {

        sse_algorithm = "AES256"

      }

    }

  }

  tags = { Name = "${var.project_name}-frontend-bucket" }

}


resource "aws_cloudfront_origin_access_identity" "oai" {

  comment = "OAI for ${aws_s3_bucket.frontend_bucket.id}"

}


# S3 bucket policy to allow CloudFront OAI to GetObject

resource "aws_s3_bucket_policy" "frontend_policy" {

  bucket = aws_s3_bucket.frontend_bucket.id

  policy = jsonencode({

    Version = "2012-10-17",

    Statement = [

      {

        Sid = "AllowCloudFrontServicePrincipalReadOnly",

        Effect = "Allow",

        Principal = {

          CanonicalUser = aws_cloudfront_origin_access_identity.oai.s3_canonical_user_id

        },

        Action = "s3:GetObject",

        Resource = "${aws_s3_bucket.frontend_bucket.arn}/*"

      }

    ]

  })

}


# CloudFront distribution for frontend

resource "aws_cloudfront_distribution" "frontend" {

  enabled = true


  # 🔹 Frontend (S3)

  origin {

    domain_name = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name

    origin_id = "S3-${aws_s3_bucket.frontend_bucket.id}"


    s3_origin_config {

      origin_access_identity = aws_cloudfront_origin_access_identity.oai.cloudfront_access_identity_path

    }

  }


  # 🔹 Backend (ALB)

  origin {

    domain_name = aws_lb.alb.dns_name

    origin_id = "API-Backend"

    custom_origin_config {

      http_port = 80

      https_port = 443

      origin_protocol_policy = "http-only"

      origin_ssl_protocols = ["TLSv1.2"]

    }

  }


  default_root_object = "index.html"

  # SPA routing fallback: serve index.html for 403/404 from S3
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }


  default_cache_behavior {

    allowed_methods = ["GET", "HEAD", "OPTIONS"]

    cached_methods = ["GET", "HEAD"]

    target_origin_id = "S3-${aws_s3_bucket.frontend_bucket.id}"

    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {

      query_string = true

      cookies { forward = "none" }

    }

    min_ttl = 0

    default_ttl = 3600

    max_ttl = 86400

  }


  ordered_cache_behavior {

    path_pattern = "/api/*"

    target_origin_id = "API-Backend"

    viewer_protocol_policy = "redirect-to-https"


    allowed_methods = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]

    cached_methods = ["GET", "HEAD"]


    forwarded_values {

      query_string = true

      headers = ["Authorization", "Content-Type", "Origin"]

      cookies { forward = "all" }

    }


    compress = true

  }


  price_class = "PriceClass_100"


  restrictions {

    geo_restriction {

      restriction_type = "none"

    }

  }


  viewer_certificate {

    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"

  }

  aliases = [var.frontend_alias_domain]

  tags = {

    Name = "${var.project_name}-cf"

  }

}

# -------------------
# Route 53 alias for CloudFront
# -------------------

# Use the pre-existing hosted zone delegated for hptp.quentinpiot.com
data "aws_route53_zone" "hptp" {
  name         = "hptp.quentinpiot.com."
  private_zone = false
}

# Create A record alias pointing the subdomain to CloudFront
resource "aws_route53_record" "alias_frontend" {
  zone_id = data.aws_route53_zone.hptp.zone_id
  name    = var.frontend_alias_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}



# -------------------

# ECR repo for backend

# -------------------

resource "aws_ecr_repository" "backend" {

  name = "${var.project_name}_backend"

  image_tag_mutability = "MUTABLE"

  tags = { Name = "${var.project_name}-backend-ecr" }

}


# -------------------

# EFS for Postgres data

# -------------------

resource "aws_efs_file_system" "postgres" {

  encrypted = true

  tags = { Name = "${var.project_name}-efs" }

}


# mount targets across the public subnets

resource "aws_efs_mount_target" "mt" {

  for_each = { for idx, s in aws_subnet.public : idx => s.id }

  file_system_id = aws_efs_file_system.postgres.id

  subnet_id = each.value

  security_groups = [aws_security_group.efs_sg.id]

}


# -------------------

# IAM Roles for ECS tasks

# -------------------

data "aws_iam_policy_document" "ecs_task_assume_role" {

  statement {

    actions = ["sts:AssumeRole"]

    principals {

      type = "Service"

      identifiers = ["ecs-tasks.amazonaws.com"]

    }

  }

}


resource "aws_iam_role" "ecs_task_execution_role" {

  name = "${var.project_name}-ecs-task-exec-role"

  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

}


# Attach managed policies for task execution (ECR pull, logs)
resource "aws_iam_role_policy_attachment" "exec_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Add ECR read (included above but safe) and EFS client
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "efs_client" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientFullAccess"
}

# IAM Task Role for application permissions
resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.project_name}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

# Custom policy for SQS, S3, and CloudWatch access
resource "aws_iam_policy" "app_permissions" {
  name        = "${var.project_name}-app-permissions"
  description = "Permissions for trading platform application"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = [
          aws_sqs_queue.monte_carlo_jobs.arn,
          aws_sqs_queue.monte_carlo_dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.monte_carlo_artifacts.arn,
          "${aws_s3_bucket.monte_carlo_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          aws_cloudwatch_log_group.application.arn,
          aws_cloudwatch_log_group.monte_carlo_worker.arn,
          "${aws_cloudwatch_log_group.application.arn}:*",
          "${aws_cloudwatch_log_group.monte_carlo_worker.arn}:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app_permissions" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.app_permissions.arn
}


# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/application/${var.project_name}"
  retention_in_days = 30
  tags              = { Name = "${var.project_name}-app-logs" }
}

resource "aws_cloudwatch_log_group" "monte_carlo_worker" {
  name              = "/aws/worker/${var.project_name}-monte-carlo"
  retention_in_days = 30
  tags              = { Name = "${var.project_name}-worker-logs" }
}

# -------------------
# SQS Queues for Monte Carlo Jobs
# -------------------

# Dead Letter Queue
resource "aws_sqs_queue" "monte_carlo_dlq" {
  name = "${var.project_name}-monte-carlo-jobs-dlq"

  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name        = "${var.project_name}-monte-carlo-dlq"
    Environment = var.env
  }
}

# Main Queue
resource "aws_sqs_queue" "monte_carlo_jobs" {
  name = "${var.project_name}-monte-carlo-jobs"

  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600 # 14 days
  max_message_size           = 262144  # 256 KB
  delay_seconds              = 0
  receive_wait_time_seconds  = 20 # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.monte_carlo_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-monte-carlo-queue"
    Environment = var.env
  }
}

# -------------------
# S3 Bucket for Monte Carlo Artifacts
# -------------------

resource "aws_s3_bucket" "monte_carlo_artifacts" {
  bucket = "${var.project_name}-monte-carlo-artifacts-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "${var.project_name}-monte-carlo-artifacts"
    Environment = var.env
  }
}

resource "aws_s3_bucket_versioning" "monte_carlo_artifacts" {
  bucket = aws_s3_bucket.monte_carlo_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "monte_carlo_artifacts" {
  bucket = aws_s3_bucket.monte_carlo_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "monte_carlo_artifacts" {
  bucket = aws_s3_bucket.monte_carlo_artifacts.id

  rule {
    id     = "cleanup_old_artifacts"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}


# -------------------

# ECS Cluster

# -------------------

resource "aws_ecs_cluster" "main" {

  name = "${var.project_name}-cluster"

}


# -------------------

# ALB + Target group + Listener

# -------------------

resource "aws_lb" "alb" {

  name = "${var.project_name}-alb"

  internal = false

  load_balancer_type = "application"

  security_groups = [aws_security_group.alb_sg.id]

  subnets = [for s in aws_subnet.public : s.id]

  tags = { Name = "${var.project_name}-alb" }

}


resource "aws_lb_target_group" "tg" {

  name = "${var.project_name}-tg"

  port = 8000

  protocol = "HTTP"

  vpc_id = aws_vpc.main.id

  target_type = "ip"

  health_check {

    path = "/api/health"

    matcher = "200-399"

    interval = 30

    timeout = 5

    healthy_threshold = 2

    unhealthy_threshold = 3

  }

  tags = { Name = "${var.project_name}-tg" }

}


resource "aws_lb_listener" "listener" {

  load_balancer_arn = aws_lb.alb.arn

  port = 80

  protocol = "HTTP"

  default_action {

    type = "forward"

    target_group_arn = aws_lb_target_group.tg.arn

  }

}


# -------------------

# ECS Task Definition (backend + postgres in same task)

# -------------------

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
}


# -------------------

# ECS Service

# -------------------

resource "aws_ecs_service" "backend_service" {

  name = "${var.project_name}-backend-svc"

  cluster = aws_ecs_cluster.main.id

  task_definition = aws_ecs_task_definition.backend_task.arn

  desired_count = 1

  launch_type = "FARGATE"


  network_configuration {

    subnets = [for s in aws_subnet.public : s.id]

    security_groups = [aws_security_group.ecs_sg.id]

    assign_public_ip = true

  }


  load_balancer {

    target_group_arn = aws_lb_target_group.tg.arn

    container_name = "backend"

    container_port = 8000

  }


  depends_on = [aws_lb_listener.listener]

  tags = { Name = "${var.project_name}-backend-svc" }

}


# -------------------
# Outputs
# -------------------

output "ecr_repo_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "s3_bucket" {
  value = aws_s3_bucket.frontend_bucket.bucket
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.frontend.domain_name
}

output "alb_dns" {
  value = aws_lb.alb.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.backend_service.name
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
