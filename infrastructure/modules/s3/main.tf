resource "aws_s3_bucket" "documents" {
  bucket = "${var.name}-medical-documents-${var.stage}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "corpus" {
  bucket = "${var.name}-knowledge-corpus-${var.stage}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "corpus" {
  bucket = aws_s3_bucket.corpus.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "bucket_names" {
  value = {
    documents = aws_s3_bucket.documents.id
    corpus   = aws_s3_bucket.corpus.id
  }
}
