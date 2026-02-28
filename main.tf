provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "cdss_test_bucket" {
  bucket = "cdss-infrastructure-test-bucket-${random_id.id.hex}"

  tags = {
    Name        = "CDSS Test Bucket"
    Environment = "Dev"
  }
}

resource "random_id" "id" {
  byte_length = 4
}

output "bucket_name" {
  value = aws_s3_bucket.cdss_test_bucket.id
}
