variable "function_name" {
  type = string
}

variable "description" {
  type    = string
  default = null
}

variable "source_dir" {
  type        = string
  description = "Directory containing Lambda source code to be zipped"
}

variable "handler" {
  type    = string
  default = "lambda_handler.handler"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "architecture" {
  type    = string
  default = "x86_64"
}

variable "timeout" {
  type    = number
  default = 30
}

variable "memory_size" {
  type    = number
  default = 512
}

variable "role_arn" {
  type = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "subnet_ids" {
  type    = list(string)
  default = null
}

variable "security_group_ids" {
  type    = list(string)
  default = null
}

variable "tracing_mode" {
  type    = string
  default = "Active"
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "api_gateway_execution_arn" {
  type    = string
  default = null
}

variable "create_api_gateway_permission" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
