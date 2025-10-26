resource "aws_cloudfront_distribution" "frontend" {
  enabled = true
  comment = "HPTP Frontend Distribution (eu-west-3)"

  # === Origins ===
  origin {
    domain_name = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.frontend_bucket.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.oai.cloudfront_access_identity_path
    }
  }

  origin {
    domain_name = aws_lb.alb.dns_name
    origin_id   = "API-Backend"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # tu peux passer à "https-only" plus tard
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_root_object = "index.html"

  # === SPA Fallback ===
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

  # === Default Cache (HTML, light cache) ===
  default_cache_behavior {
    target_origin_id       = "S3-${aws_s3_bucket.frontend_bucket.id}"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      cookies {
        forward = "none"
      }
    }

    compress     = true
    min_ttl      = 0
    default_ttl  = 300      # 5 min cache HTML
    max_ttl      = 600      # 10 min max
  }

  # === Static Assets (long cache) ===
  ordered_cache_behavior {
    path_pattern           = "assets/*"
    target_origin_id       = "S3-${aws_s3_bucket.frontend_bucket.id}"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    compress     = true
    min_ttl      = 86400     # 1 day
    default_ttl  = 2592000   # 30 days
    max_ttl      = 31536000  # 1 year
  }

  # === Backend API (no cache) ===
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "API-Backend"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "Origin"]
      cookies {
        forward = "all"
      }
    }

    compress     = true
    min_ttl      = 0
    default_ttl  = 0
    max_ttl      = 0
  }

  # === Global Settings ===
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