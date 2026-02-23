variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Name of the project, used as a prefix for resources"
  type        = string
  default     = "trading-platform"
}

variable "env" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.100.0.0/16"
}

variable "frontend_alias_domain" {
  description = "Alias domain for CloudFront (e.g., hptp.quentinpiot.com)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ARN of the existing ACM certificate in us-east-1 for CloudFront"
  type        = string
}

variable "alb_certificate_arn" {
  description = "ARN of the ACM certificate in the workload region for the ALB HTTPS listener"
  type        = string
}

variable "frontend_url" {
  description = "Frontend URL for OAuth redirects (e.g., https://hptp.quentinpiot.com)"
  type        = string
}

variable "google_redirect_uri" {
  description = "Google OAuth redirect URI for backend authentication"
  type        = string
}

variable "jwt_secret_arn" {
  description = "Secrets Manager or SSM ARN exposed to ECS as JWT_SECRET"
  type        = string
}

variable "app_google_client_secret_arn" {
  description = "Secrets Manager or SSM ARN exposed to ECS as GOOGLE_CLIENT_SECRET"
  type        = string
  default     = ""
}

variable "google_client_id" {
  description = "Google OAuth Client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret used by Cognito identity provider"
  type        = string
  default     = ""
  sensitive   = true
}

variable "db_name" {
  description = "Application database name"
  type        = string
  default     = "trading_db"
}

variable "db_username" {
  description = "Application database master username"
  type        = string
  default     = "postgres"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Initial RDS allocated storage in GiB"
  type        = number
  default     = 20
}
