variable "trail_name" {
  type = string
}

variable "s3_bucket_name" {
  type = string
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "cloudwatch_log_group_arn" {
  type    = string
  default = null
}

variable "cloudwatch_role_arn" {
  type    = string
  default = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
