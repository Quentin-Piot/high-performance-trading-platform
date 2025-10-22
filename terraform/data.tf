# -------------------
# Data Sources
# -------------------

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_availability_zones" "azs" {
  state = "available"
}

# Use the pre-existing hosted zone delegated for hptp.quentinpiot.com
data "aws_route53_zone" "hptp" {
  name         = "hptp.quentinpiot.com."
  private_zone = false
}

# Random suffix for unique resource names
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}