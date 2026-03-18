variable "name" {
  type = string
}

variable "stage" {
  type = string
}

variable "agent_lambdas" {
  description = "Map of agent identifiers to their Lambda function names and ARNs"
  type = map(object({
    function_name = string
    arn           = string
  }))
}
