resource "aws_cloudwatch_event_bus" "cdss" {
  name = "${var.name}-events-${var.stage}"
}

# Optional: rules for inter-agent events (e.g. reminder scheduled -> Engagement Agent)
# resource "aws_cloudwatch_event_rule" "reminder" { ... }
# resource "aws_cloudwatch_event_target" "reminder_lambda" { ... }

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.cdss.name
}
