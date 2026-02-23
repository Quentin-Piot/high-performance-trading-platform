resource "aws_db_subnet_group" "postgres" {
  name       = "${var.project_name}-${var.env}-db-subnets"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]

  tags = {
    Name = "${var.project_name}-db-subnets"
  }
}

resource "aws_db_instance" "postgres" {
  identifier                     = "${var.project_name}-${var.env}-postgres"
  engine                         = "postgres"
  engine_version                 = "16.3"
  instance_class                 = var.db_instance_class
  allocated_storage              = var.db_allocated_storage
  max_allocated_storage          = var.db_allocated_storage * 5
  db_name                        = var.db_name
  username                       = var.db_username
  manage_master_user_password    = true
  storage_encrypted              = true
  db_subnet_group_name           = aws_db_subnet_group.postgres.name
  vpc_security_group_ids         = [aws_security_group.db_sg.id]
  publicly_accessible            = false
  skip_final_snapshot            = lower(var.env) != "production"
  deletion_protection            = lower(var.env) == "production"
  backup_retention_period        = lower(var.env) == "production" ? 7 : 1
  copy_tags_to_snapshot          = true
  apply_immediately              = true
  performance_insights_enabled   = false
  auto_minor_version_upgrade     = true

  tags = {
    Name        = "${var.project_name}-postgres"
    Environment = var.env
  }
}
