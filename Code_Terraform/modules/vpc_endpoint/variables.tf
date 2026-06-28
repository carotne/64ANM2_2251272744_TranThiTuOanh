variable "vpc_id" {
  type = string
}

variable "region" {
  type = string
}

variable "gateway_endpoints" {
  type = map(object({
    service         = string
    route_table_ids = list(string)
  }))
  default = {}
}

variable "interface_endpoints" {
  type = map(object({
    service            = string
    subnet_ids         = list(string)
    security_group_ids = list(string)
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
