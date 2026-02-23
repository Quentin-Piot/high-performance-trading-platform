
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_availability_zones" "azs" {
  state = "available"
}
data "aws_route53_zone" "hptp" {
  name         = "hptp.quentinpiot.com."
  private_zone = false
}
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}