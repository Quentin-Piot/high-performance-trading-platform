# -------------------
# Variables (defaults)
# -------------------

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

# Frontend URL for OAuth redirects
variable "frontend_url" {
  description = "Frontend URL for OAuth redirects (e.g., https://hptp.quentinpiot.com)"
  type        = string
}