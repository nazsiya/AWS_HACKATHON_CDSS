variable "name" {
  type = string
}

variable "stage" {
  type = string
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "handlers" {
  type = map(string)
}

variable "env" {
  type    = map(string)
  default = {}
}
