resource "aws_cloudwatch_event_bus" "cdss" {
  name = "${var.name}-events-${var.stage}"
}

# Rule for Supervisor routing requests
resource "aws_cloudwatch_event_rule" "agent_routing" {
  for_each = var.agent_lambdas

  name           = "${var.name}-route-to-${each.key}-${var.stage}"
  description    = "Route Supervisor actions to the ${each.key} agent"
  event_bus_name = aws_cloudwatch_event_bus.cdss.name

  event_pattern = jsonencode({
    source      = ["cdss.agent.supervisor"]
    detail-type = ["AgentActionRequested"]
    detail = {
      target_agent = [each.key]
    }
  })
}

resource "aws_cloudwatch_event_target" "agent_routing" {
  for_each = var.agent_lambdas

  rule           = aws_cloudwatch_event_rule.agent_routing[each.key].name
  event_bus_name = aws_cloudwatch_event_bus.cdss.name
  target_id      = "Target${each.key}Agent"
  arn            = each.value.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  for_each = var.agent_lambdas

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.agent_routing[each.key].arn
}

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.cdss.name
}

output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.cdss.arn
}
