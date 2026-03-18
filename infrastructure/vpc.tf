# VPC and networking for RDS Aurora
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${local.name_prefix}-vpc"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "${local.name_prefix}-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "${local.name_prefix}-private-b"
  }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.10.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-a"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.name_prefix}-public-rt"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

#
# Private routing for Lambdas in VPC
#
# When Lambdas are attached to the private subnets to reach Aurora, they also need
# egress to AWS APIs (Secrets Manager, SSM, Bedrock, SNS, etc.). We provide:
# - NAT Gateway for general outbound internet egress
# - VPC endpoints for S3 (gateway) and core AWS APIs (interface) to reduce NAT reliance
#

resource "aws_eip" "nat" {
  count = var.enable_lambda_vpc ? 1 : 0

  domain = "vpc"
  tags = {
    Name = "${local.name_prefix}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  count = var.enable_lambda_vpc ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public_a.id

  depends_on = [aws_internet_gateway.main]

  tags = {
    Name = "${local.name_prefix}-nat"
  }
}

resource "aws_route_table" "private" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = {
    Name = "${local.name_prefix}-private-rt"
  }
}

resource "aws_route_table_association" "private_a" {
  count = var.enable_lambda_vpc ? 1 : 0

  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_route_table_association" "private_b" {
  count = var.enable_lambda_vpc ? 1 : 0

  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_security_group" "vpc_endpoints" {
  count = var.enable_lambda_vpc ? 1 : 0

  name        = "${local.name_prefix}-vpce-sg"
  description = "Security group for Interface VPC Endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-vpce-sg"
  }
}

# Gateway endpoint for S3 (no NAT needed for S3 access)
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private[0].id]

  tags = {
    Name = "${local.name_prefix}-vpce-s3"
  }
}

# Interface endpoints for core AWS APIs used by Lambdas
resource "aws_vpc_endpoint" "secretsmanager" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]

  tags = {
    Name = "${local.name_prefix}-vpce-secretsmanager"
  }
}

resource "aws_vpc_endpoint" "ssm" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ssm"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]

  tags = {
    Name = "${local.name_prefix}-vpce-ssm"
  }
}

resource "aws_vpc_endpoint" "ssmmessages" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]

  tags = {
    Name = "${local.name_prefix}-vpce-ssmmessages"
  }
}

resource "aws_vpc_endpoint" "ec2messages" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ec2messages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]

  tags = {
    Name = "${local.name_prefix}-vpce-ec2messages"
  }
}

resource "aws_vpc_endpoint" "logs" {
  count = var.enable_lambda_vpc ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]

  tags = {
    Name = "${local.name_prefix}-vpce-logs"
  }
}

resource "aws_db_subnet_group" "aurora" {
  name       = "${local.name_prefix}-aurora-subnets-v2"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "${local.name_prefix}-aurora-subnets"
  }
}

resource "aws_security_group" "aurora" {
  name        = "${local.name_prefix}-aurora-sg"
  description = "Security group for Aurora cluster"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    cidr_blocks     = [aws_vpc.main.cidr_block]
    security_groups = [
      aws_security_group.lambda.id,
      aws_security_group.bastion.id
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-aurora-sg"
  }
}

# Security group for CDSS Lambdas (when running in VPC to reach RDS)
resource "aws_security_group" "lambda" {
  name        = "${local.name_prefix}-lambda-sg"
  description = "Security group for CDSS Lambda functions in VPC"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-lambda-sg"
  }
}
