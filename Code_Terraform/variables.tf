variable "project_name" {
  type        = string
  description = "Project name used as prefix for resources"
}

variable "environment" {
  type        = string
  description = "Environment (e.g. prod, dev)"
}

variable "region" {
  type        = string
  description = "Primary AWS region"
  default     = "ap-southeast-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "private_subnets" {
  type = list(object({
    name              = string
    cidr_block        = string
    availability_zone = string
  }))
}

variable "frontend_bucket_name" {
  type        = string
  description = "S3 bucket hosting the Vue.js static site"
}

variable "logs_bucket_name" {
  type        = string
  description = "S3 bucket for CloudTrail and access logs"
}

variable "domain_name" {
  type        = string
  description = "Apex domain (oanhlab.com)"
}

variable "frontend_subdomain" {
  type        = string
  description = "Subdomain serving the SPA (e.g. app.oanhlab.com)"
}

variable "create_route53_zone" {
  type        = bool
  default     = true
  description = "Set false if the hosted zone already exists; provide existing_zone_id instead"
}

variable "existing_zone_id" {
  type    = string
  default = null
}

variable "dynamodb_table_name" {
  type    = string
  default = "conduit"
}

variable "lambda_source_dir" {
  type        = string
  default     = "./backend/dist"
  description = "Directory holding packaged Lambda code (with dependencies)"
}

variable "lambda_memory_size" {
  type    = number
  default = 1024
}

variable "lambda_timeout" {
  type    = number
  default = 30
}

variable "jwt_secret" {
  type        = string
  sensitive   = true
  description = "Secret for signing JWTs"
}

variable "alert_email" {
  type        = string
  description = "Email address subscribed to alarm SNS topic"
}

variable "enable_waf" {
  type        = bool
  description = "Attach the WAF Web ACL to the CloudFront distribution. Set false only for temporary controlled testing."
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
