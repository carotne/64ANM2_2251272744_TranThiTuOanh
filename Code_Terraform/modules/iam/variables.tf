variable "roles" {
  type = map(object({
    name                  = string
    description           = optional(string)
    path                  = optional(string, "/")
    max_session_duration  = optional(number, 3600)
    force_detach_policies = optional(bool, false)
    assume_role_policy    = string
    custom_policy_refs    = optional(list(string), [])
    managed_policy_arns   = optional(list(string), [])
    tags                  = optional(map(string), {})
  }))
  default = {}
}

variable "custom_policies" {
  type = map(object({
    name        = string
    description = optional(string)
    policy      = string
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
