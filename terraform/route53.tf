# -------------------
# Route 53 DNS Records
# -------------------

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