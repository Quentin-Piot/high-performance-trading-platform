# -------------------
# CloudWatch Log Groups
# -------------------

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7  # Réduit de 14 à 7 jours pour économiser

  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/application/${var.project_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-app-logs"
  }
}