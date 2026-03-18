# CloudFront OAC for S3-managed frontends
resource "aws_cloudfront_origin_access_control" "main" {
  name                              = "${local.name_prefix}-oac"
  description                       = "OAC for ${local.name_prefix} frontend buckets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Staff Web App CloudFront Distribution
resource "aws_cloudfront_distribution" "staff_app" {
  origin {
    domain_name              = aws_s3_bucket.main.bucket_regional_domain_name
    origin_id                = "StaffS3Origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.main.id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "StaffS3Origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  # SPA: serve index.html for 403/404 so client-side routes work
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name    = "${local.name_prefix}-staff-app-cf"
    Project = var.project_name
  }
}

# Patient Portal CloudFront Distribution
resource "aws_cloudfront_distribution" "patient_portal" {
  origin {
    domain_name              = aws_s3_bucket.corpus.bucket_regional_domain_name
    origin_id                = "PatientS3Origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.main.id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "PatientS3Origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name    = "${local.name_prefix}-patient-portal-cf"
    Project = var.project_name
  }
}

# Update S3 bucket policies for CloudFront OAC
resource "aws_s3_bucket_policy" "staff_bucket_access" {
  bucket = aws_s3_bucket.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowCloudFrontServicePrincipal"
      Effect = "Allow"
      Principal = {
        Service = "cloudfront.amazonaws.com"
      }
      Action   = "s3:GetObject"
      Resource = "${aws_s3_bucket.main.arn}/*"
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_cloudfront_distribution.staff_app.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_policy" "patient_bucket_access" {
  bucket = aws_s3_bucket.corpus.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowCloudFrontServicePrincipal"
      Effect = "Allow"
      Principal = {
        Service = "cloudfront.amazonaws.com"
      }
      Action   = "s3:GetObject"
      Resource = "${aws_s3_bucket.corpus.arn}/*"
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_cloudfront_distribution.patient_portal.arn
        }
      }
    }]
  })
}
