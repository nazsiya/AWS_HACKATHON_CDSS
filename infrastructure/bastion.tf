# Bastion Host for tunnel to private RDS Aurora.
# SSM-only by default; set bastion_ssh_public_key + bastion_allowed_cidr to use SSH tunnel (reference/docs/infrastructure/bastion-setup.md).
# Using Amazon Linux 2 for reliable SSM agent registration.
data "aws_ami" "bastion_ami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_key_pair" "bastion" {
  count = var.bastion_ssh_public_key != "" ? 1 : 0

  key_name   = "${local.name_prefix}-bastion-key"
  public_key = var.bastion_ssh_public_key
}

resource "aws_iam_role" "bastion" {
  name = "${local.name_prefix}-bastion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "bastion_ssm" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "bastion" {
  name = "${local.name_prefix}-bastion-profile"
  role = aws_iam_role.bastion.name
}

resource "aws_security_group" "bastion" {
  name        = "${local.name_prefix}-bastion-sg"
  description = "Security group for SSM bastion"
  vpc_id      = aws_vpc.main.id

  # SSH from your IP when bastion_allowed_cidr is set (for SSH tunnel per reference)
  dynamic "ingress" {
    for_each = var.bastion_allowed_cidr != "" ? [1] : []
    content {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.bastion_allowed_cidr]
      description = "SSH for port-forward to Aurora"
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-bastion-sg"
  }
}

resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.bastion_ami.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public_a.id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  iam_instance_profile        = aws_iam_instance_profile.bastion.name
  associate_public_ip_address = true
  key_name                    = var.bastion_ssh_public_key != "" ? aws_key_pair.bastion[0].key_name : null

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2
  }

  tags = {
    Name = "${local.name_prefix}-bastion"
  }
}

output "bastion_instance_id" {
  value = aws_instance.bastion.id
}

output "bastion_public_ip" {
  value       = aws_instance.bastion.public_ip
  description = "Bastion public IP (for SSH tunnel: ssh -L 5433:aurora:5432 ec2-user@this-ip)"
}
