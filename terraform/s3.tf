# -------------------
# S3 Buckets
# -------------------

# S3 bucket for frontend (private) + CloudFront OAI
resource "aws_s3_bucket" "frontend_bucket" {
  bucket        = "${var.project_name}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # convenient for dev; remove for strict prod

  tags = {
    Name = "${var.project_name}-frontend-bucket"
  }
}

# Enable ACLs for the bucket (required for aws_s3_bucket_acl)
resource "aws_s3_bucket_ownership_controls" "frontend_bucket" {
  bucket = aws_s3_bucket.frontend_bucket.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Disable public access block to allow ACL configuration
resource "aws_s3_bucket_public_access_block" "frontend_bucket" {
  bucket = aws_s3_bucket.frontend_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_acl" "frontend_bucket" {
  depends_on = [
    aws_s3_bucket_ownership_controls.frontend_bucket,
    aws_s3_bucket_public_access_block.frontend_bucket,
  ]

  bucket = aws_s3_bucket.frontend_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "frontend_bucket" {
  bucket = aws_s3_bucket.frontend_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend_bucket" {
  bucket = aws_s3_bucket.frontend_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CloudFront Origin Access Identity
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
        Sid    = "AllowCloudFrontServicePrincipalReadOnly",
        Effect = "Allow",
        Principal = {
          CanonicalUser = aws_cloudfront_origin_access_identity.oai.s3_canonical_user_id
        },
        Action   = "s3:GetObject",
        Resource = "${aws_s3_bucket.frontend_bucket.arn}/*"
      }
    ]
  })
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