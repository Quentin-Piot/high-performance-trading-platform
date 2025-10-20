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
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.env
      ManagedBy   = "terraform"
      CreatedAt   = timestamp()
    }
  }
}

# -------------------
# Variables (defaults)
# -------------------

variable "aws_region" {
  type        = string
  default     = "eu-west-3"
  description = "AWS region for deployment"
}

variable "project_name" {
  type        = string
  default     = "trading-platform"
  description = "Project name used for resource naming"
  
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "env" {
  type        = string
  default     = "staging"
  description = "Environment name (staging, production, etc.)"
  
  validation {
    condition     = contains(["staging", "production", "development"], var.env)
    error_message = "Environment must be one of: staging, production, development."
  }
}

variable "vpc_cidr" {
  type        = string
  default     = "10.100.0.0/16"
  description = "CIDR block for VPC"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

# CloudFront custom domain settings
variable "frontend_alias_domain" {
  description = "Alias domain for CloudFront (e.g., hptp.quentinpiot.com)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (must be in us-east-1 for CloudFront)"
  type        = string
  default     = ""
}

variable "enable_monitoring" {
  description = "Enable enhanced monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "worker_desired_count" {
  description = "Desired number of worker instances"
  type        = number
  default     = 1
  
  validation {
    condition     = var.worker_desired_count >= 0 && var.worker_desired_count <= 10
    error_message = "Worker desired count must be between 0 and 10."
  }
}

# -------------------
# Data Sources
# -------------------

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# -------------------
# Random Resources
# -------------------

resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# -------------------
# VPC and Networking
# -------------------

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Public subnets for ALB and NAT gateways
resource "aws_subnet" "public" {
  count = min(length(data.aws_availability_zones.available.names), 3)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
    Type = "public"
  }
}

# Private subnets for ECS tasks
resource "aws_subnet" "private" {
  count = min(length(data.aws_availability_zones.available.names), 3)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-${count.index + 1}"
    Type = "private"
  }
}

# NAT Gateways for private subnet internet access
resource "aws_eip" "nat" {
  count = length(aws_subnet.public)

  domain = "vpc"
  
  depends_on = [aws_internet_gateway.main]

  tags = {
    Name = "${var.project_name}-nat-eip-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "main" {
  count = length(aws_subnet.public)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.project_name}-nat-${count.index + 1}"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table" "private" {
  count = length(aws_subnet.private)

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
  }
}

# Route table associations
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# -------------------
# Security Groups
# -------------------

# ALB Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ECS Security Group
resource "aws_security_group" "ecs_sg" {
  name_prefix = "${var.project_name}-ecs-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "PostgreSQL internal"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  ingress {
    description     = "Redis internal"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# EFS Security Group
resource "aws_security_group" "efs" {
  name_prefix = "${var.project_name}-efs-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from ECS"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-efs-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# -------------------
# CloudWatch Log Groups
# -------------------

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/ecs/${var.project_name}-backend"
  retention_in_days = var.env == "production" ? 30 : 7

  tags = {
    Name = "${var.project_name}-backend-logs"
  }
}

resource "aws_cloudwatch_log_group" "monte_carlo_worker" {
  name              = "/aws/ecs/${var.project_name}-monte-carlo-worker"
  retention_in_days = var.env == "production" ? 30 : 7

  tags = {
    Name = "${var.project_name}-worker-logs"
  }
}

# -------------------
# Enhanced Monitoring
# -------------------

resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_monitoring ? 1 : 0
  
  dashboard_name = "${var.project_name}-${var.env}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.backend_service.name],
            [".", "MemoryUtilization", ".", "."],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS Service Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessages", "QueueName", aws_sqs_queue.monte_carlo_jobs.name],
            [".", "ApproximateNumberOfMessagesVisible", ".", "."],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "SQS Queue Metrics"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.env}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = var.enable_monitoring ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    ServiceName = aws_ecs_service.backend_service.name
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = {
    Name = "${var.project_name}-high-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.env}-queue-backlog"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "100"
  alarm_description   = "This metric monitors SQS queue backlog"
  alarm_actions       = var.enable_monitoring ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    QueueName = aws_sqs_queue.monte_carlo_jobs.name
  }

  tags = {
    Name = "${var.project_name}-queue-backlog-alarm"
  }
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  count = var.enable_monitoring ? 1 : 0
  
  name = "${var.project_name}-${var.env}-alerts"

  tags = {
    Name = "${var.project_name}-alerts"
  }
}

# -------------------
# Backup Configuration
# -------------------

resource "aws_backup_vault" "main" {
  count = var.enable_backup ? 1 : 0
  
  name        = "${var.project_name}-${var.env}-backup-vault"
  kms_key_arn = aws_kms_key.backup[0].arn

  tags = {
    Name = "${var.project_name}-backup-vault"
  }
}

resource "aws_kms_key" "backup" {
  count = var.enable_backup ? 1 : 0
  
  description             = "KMS key for ${var.project_name} backups"
  deletion_window_in_days = 7

  tags = {
    Name = "${var.project_name}-backup-key"
  }
}

resource "aws_kms_alias" "backup" {
  count = var.enable_backup ? 1 : 0
  
  name          = "alias/${var.project_name}-backup"
  target_key_id = aws_kms_key.backup[0].key_id
}

resource "aws_backup_plan" "main" {
  count = var.enable_backup ? 1 : 0
  
  name = "${var.project_name}-${var.env}-backup-plan"

  rule {
    rule_name         = "daily_backup"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = "cron(0 5 ? * * *)"  # Daily at 5 AM UTC

    lifecycle {
      cold_storage_after = 30
      delete_after       = 120
    }

    recovery_point_tags = {
      Environment = var.env
      Project     = var.project_name
    }
  }

  tags = {
    Name = "${var.project_name}-backup-plan"
  }
}

# -------------------
# Continue with existing resources...
# -------------------

// ... existing code ...
