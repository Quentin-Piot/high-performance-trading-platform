provider "aws" {
  alias  = "global"
  region = "us-east-1"
}

resource "aws_cloudfront_function" "spa_fallback" {
  name    = "${var.project_name}-spa-fallback"
  runtime = "cloudfront-js-1.0"
  publish = true
  code = <<EOF
function handler(event) {
  var req = event.request;
  var uri = req.uri;
  if (uri.startsWith('/api/')) return req;
  if (uri.match(/\\.[a-zA-Z0-9]{2,5}(\\?.*)?$/)) return req;
  req.uri = '/index.html';
  return req;
}
EOF
}

resource "aws_cloudfront_cache_policy" "html_short" {
  provider = aws.global
  name     = "${var.project_name}-html-short"
  min_ttl  = 0
  default_ttl = 60
  max_ttl  = 600
  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
    cookies_config { cookie_behavior = "none" }
    headers_config { header_behavior = "none" }
    query_strings_config { query_string_behavior = "all" }
  }
}

resource "aws_cloudfront_cache_policy" "assets_long" {
  provider = aws.global
  name     = "${var.project_name}-assets-long"
  min_ttl  = 86400
  default_ttl = 31536000
  max_ttl  = 31536000
  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
    cookies_config { cookie_behavior = "none" }
    headers_config { header_behavior = "none" }
    query_strings_config { query_string_behavior = "none" }
  }
}

resource "aws_cloudfront_cache_policy" "api_disabled" {
  provider = aws.global
  name     = "${var.project_name}-api-disabled"
  min_ttl  = 0
  default_ttl = 0
  max_ttl  = 0
  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = false
    enable_accept_encoding_gzip   = false
    cookies_config { cookie_behavior = "all" }
    headers_config { header_behavior = "none" }
    query_strings_config { query_string_behavior = "all" }
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  provider    = aws.global
  depends_on  = [
    aws_cloudfront_cache_policy.html_short,
    aws_cloudfront_cache_policy.assets_long,
    aws_cloudfront_cache_policy.api_disabled
  ]

  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = [var.frontend_alias_domain]

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
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "S3-${aws_s3_bucket.frontend_bucket.id}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = aws_cloudfront_cache_policy.html_short.id
    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_fallback.arn
    }
  }

  ordered_cache_behavior {
    path_pattern           = "assets/*"
    target_origin_id       = "S3-${aws_s3_bucket.frontend_bucket.id}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = aws_cloudfront_cache_policy.assets_long.id
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "API-Backend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = aws_cloudfront_cache_policy.api_disabled.id
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = { Name = "${var.project_name}-cf" }
}
