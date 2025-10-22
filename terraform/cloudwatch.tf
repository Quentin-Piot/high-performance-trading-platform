# -------------------
# CloudWatch Log Groups
# -------------------

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/application/${var.project_name}"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-app-logs"
  }
}

resource "aws_cloudwatch_log_group" "monte_carlo_worker" {
  name              = "/aws/worker/${var.project_name}-monte-carlo"
  retention_in_days = 30

  tags = {
    Name = "${var.project_name}-worker-logs"
  }
}