resource "aws_dynamodb_table" "sessions" {
  name         = "${var.name}-sessions-${var.stage}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sessionId"
  range_key    = "sk"

  attribute {
    name = "sessionId"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
}

resource "aws_dynamodb_table" "medication_schedules" {
  name         = "${var.name}-medication-schedules-${var.stage}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "patientId"
  range_key    = "scheduleId"

  attribute {
    name = "patientId"
    type = "S"
  }
  attribute {
    name = "scheduleId"
    type = "S"
  }
}

output "table_names" {
  value = {
    sessions             = aws_dynamodb_table.sessions.name
    medication_schedules = aws_dynamodb_table.medication_schedules.name
  }
}
