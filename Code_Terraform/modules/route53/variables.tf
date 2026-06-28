variable "create_zone" {
  type    = bool
  default = true
}

variable "zone_name" {
  type = string
}

variable "existing_zone_id" {
  type    = string
  default = null
}

variable "records" {
  type = map(object({
    name    = string
    type    = string
    ttl     = optional(number)
    records = optional(list(string))
    alias = optional(object({
      name                   = string
      zone_id                = string
      evaluate_target_health = bool
    }))
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
