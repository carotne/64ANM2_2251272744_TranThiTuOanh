variable "distribution_name" {
  type = string
}

variable "comment" {
  type    = string
  default = null
}

variable "price_class" {
  type    = string
  default = "PriceClass_100"
}

variable "aliases" {
  type    = list(string)
  default = []
}

variable "s3_bucket_regional_domain_name" {
  type = string
}

variable "api_gateway_domain" {
  type        = string
  description = "API Gateway HTTP API endpoint without https://"
}

variable "api_gateway_origin_path" {
  type    = string
  default = ""
}

variable "web_acl_arn" {
  type    = string
  default = null
}

variable "acm_certificate_arn" {
  type    = string
  default = null
}

variable "origin_verify_secret" {
  type        = string
  description = "Secret sent to the API origin as X-Origin-Verify so the backend can reject non-CloudFront traffic"
  default     = null
  sensitive   = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
