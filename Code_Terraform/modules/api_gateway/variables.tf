variable "api_name" {
  type = string
}

variable "description" {
  type    = string
  default = null
}

variable "stage_name" {
  type    = string
  default = "$default"
}

variable "lambda_invoke_arn" {
  type = string
}

variable "cors_allow_origins" {
  type    = list(string)
  default = ["*"]
}

variable "access_log_group_arn" {
  type = string
}

variable "route_keys" {
  type        = list(string)
  description = "HTTP API route keys that are allowed to invoke Lambda, for example GET /api/health-check."
  default     = ["ANY /{proxy+}", "ANY /"]
}

variable "throttling_burst_limit" {
  type    = number
  default = 50
}

variable "throttling_rate_limit" {
  type    = number
  default = 20
}

variable "tags" {
  type    = map(string)
  default = {}
}
