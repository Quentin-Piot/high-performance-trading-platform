# -------------------
# EFS File System
# -------------------

resource "aws_efs_file_system" "postgres" {
  encrypted = true

  tags = {
    Name = "${var.project_name}-efs"
  }
}

# Mount targets across the public subnets
resource "aws_efs_mount_target" "mt" {
  for_each = { for idx, s in aws_subnet.public : idx => s.id }

  file_system_id  = aws_efs_file_system.postgres.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs_sg.id]
}