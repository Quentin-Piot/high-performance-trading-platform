# -------------------
# SQS Queues for Monte Carlo Jobs
# -------------------

# Dead Letter Queue
resource "aws_sqs_queue" "monte_carlo_dlq" {
  name = "${var.project_name}-monte-carlo-jobs-dlq"

  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name        = "${var.project_name}-monte-carlo-dlq"
    Environment = var.env
  }
}

# Main Queue
resource "aws_sqs_queue" "monte_carlo_jobs" {
  name = "${var.project_name}-monte-carlo-jobs"

  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600 # 14 days
  max_message_size           = 262144  # 256 KB
  delay_seconds              = 0
  receive_wait_time_seconds  = 20 # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.monte_carlo_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-monte-carlo-queue"
    Environment = var.env
  }
}