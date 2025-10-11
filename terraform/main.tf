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

    aws = { source = "hashicorp/aws", version = "~> 5.0" }

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

    cloudfront_default_certificate = true

  }
  
#  aliases = ["hptp.quentinpiot.com"]

  tags = {

    Name = "${var.project_name}-cf"

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

  role = aws_iam_role.ecs_task_execution_role.name

  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

}


# Add ECR read (included above but safe) and EFS client

resource "aws_iam_role_policy_attachment" "ecr_read" {

  role = aws_iam_role.ecs_task_execution_role.name

  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"

}


resource "aws_iam_role_policy_attachment" "efs_client" {

  role = aws_iam_role.ecs_task_execution_role.name

  policy_arn = "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientFullAccess"

}


# CloudWatch Log Group

resource "aws_cloudwatch_log_group" "ecs" {

  name = "/ecs/${var.project_name}"

  retention_in_days = 14

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

  family = "${var.project_name}-backend-task"

  requires_compatibilities = ["FARGATE"]

  network_mode = "awsvpc"

  cpu = "512"

  memory = "1024"

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  task_role_arn = aws_iam_role.ecs_task_execution_role.arn


  container_definitions = jsonencode([

    {

      name = "postgres"

      image = "postgres:16"

      essential = true

      environment = [

        { name = "POSTGRES_DB", value = "trading_db" },

        { name = "POSTGRES_USER", value = "postgres" },

        { name = "POSTGRES_PASSWORD", value = "postgres" }

      ]

      mountPoints = [

        {

          sourceVolume = "postgres-data"

          containerPath = "/var/lib/postgresql/data"

          readOnly = false

        }

      ]

      logConfiguration = {

        logDriver = "awslogs"

        options = {

          "awslogs-group" = aws_cloudwatch_log_group.ecs.name

          "awslogs-region" = var.aws_region

          "awslogs-stream-prefix" = "postgres"

        }

      }

    },

    {

      name = "backend"

      image = "${aws_ecr_repository.backend.repository_url}:latest"

      essential = true

      portMappings = [

        { containerPort = 8000, protocol = "tcp" }

      ]

      environment = [

        { name = "DATABASE_HOST", value = "localhost" }, # postgres in same task

        { name = "DATABASE_PORT", value = "5432" },

        { name = "DATABASE_NAME", value = "trading_db" },

        { name = "DATABASE_USER", value = "postgres" },

        { name = "DATABASE_PASSWORD", value = "postgres" }

      ]

      dependsOn = [

        { containerName = "postgres", condition = "START" }

      ]

      logConfiguration = {

        logDriver = "awslogs"

        options = {

          "awslogs-group" = aws_cloudwatch_log_group.ecs.name

          "awslogs-region" = var.aws_region

          "awslogs-stream-prefix" = "backend"

        }

      }

    }

  ])


  volume {

    name = "postgres-data"

    efs_volume_configuration {

      file_system_id = aws_efs_file_system.postgres.id

      root_directory = "/"

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
