variable "topic_name" {
  type = string
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "email_subscribers" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
