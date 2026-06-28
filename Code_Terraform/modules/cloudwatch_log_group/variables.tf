variable "log_group_name" {
  type = string
}

variable "retention_in_days" {
  type    = number
  default = 90
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
