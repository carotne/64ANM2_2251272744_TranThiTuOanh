variable "vpc_id" {
  type = string
}

variable "security_groups" {
  type = map(object({
    name        = string
    description = string
    ingress = optional(list(object({
      description = string
      from_port   = number
      to_port     = number
      ip_protocol = string
      cidr_ipv4   = string
    })))
    egress = optional(list(object({
      description = string
      from_port   = number
      to_port     = number
      ip_protocol = string
      cidr_ipv4   = string
    })))
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
