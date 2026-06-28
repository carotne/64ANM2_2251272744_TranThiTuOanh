variable "kms_keys" {
  type = map(object({
    description             = string
    deletion_window_in_days = optional(number, 30)
    enable_key_rotation     = optional(bool, true)
    policy                  = optional(string)
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
