variable "vpc_name" {
  type        = string
  description = "Name of the VPC"
}

variable "cidr_block" {
  type        = string
  description = "CIDR block for the VPC"
}

variable "private_subnets" {
  type = list(object({
    name              = string
    cidr_block        = string
    availability_zone = string
  }))
  description = "Private subnets to host Lambda ENIs and VPC endpoints"
}

variable "tags" {
  type    = map(string)
  default = {}
}
