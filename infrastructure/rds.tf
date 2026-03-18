resource "aws_rds_cluster" "aurora" {
  cluster_identifier                  = "${local.name_prefix}-aurora-cluster"
  engine                              = "aurora-postgresql"
  engine_mode                         = "provisioned"
  engine_version                      = "15.10"
  database_name                       = "cdssdb"
  master_username                     = var.db_username
  master_password                     = var.db_password
  db_subnet_group_name                = aws_db_subnet_group.aurora.name
  vpc_security_group_ids              = [aws_security_group.aurora.id]
  skip_final_snapshot                 = var.environment == "dev"
  storage_encrypted                   = true
  iam_database_authentication_enabled = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 1
  }

  tags = {
    Name        = "${local.name_prefix}-aurora"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_rds_cluster_instance" "aurora" {
  identifier         = "${local.name_prefix}-aurora-instance"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version

  tags = {
    Name = "${local.name_prefix}-aurora-instance"
  }
}
