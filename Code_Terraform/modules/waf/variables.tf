variable "web_acl_name" {
  type = string
}

variable "description" {
  type    = string
  default = "Web ACL for CloudFront"
}

variable "managed_rule_groups" {
  type = list(object({
    name     = string
    priority = number
  }))
  default = [
    { name = "AWSManagedRulesCommonRuleSet", priority = 10 },
    { name = "AWSManagedRulesKnownBadInputsRuleSet", priority = 20 },
    { name = "AWSManagedRulesSQLiRuleSet", priority = 30 },
    { name = "AWSManagedRulesAmazonIpReputationList", priority = 40 },
  ]
}

variable "common_rule_set_count_rules" {
  type        = list(string)
  description = "AWSManagedRulesCommonRuleSet sub-rules to override to Count, typically for controlled testing."
  default     = []
}

variable "rate_limit" {
  type    = number
  default = 2000
}

variable "login_rate_limit" {
  type        = number
  description = "Max requests per 5-min window per IP to /api/users/login before blocking (WAF minimum is 100)"
  default     = 100
}

variable "rate_limit_count_only" {
  type        = bool
  description = "Set true to keep rate-limit rules in count mode so they do not block requests."
  default     = false
}

variable "sqli_hardening_count_only" {
  type        = bool
  description = "Set true to keep the custom SQLi hardening rule (sqli-json-body-strict) in count mode for before/after measurement instead of blocking."
  default     = false
}

variable "log_retention_days" {
  type        = number
  description = "Retention for the WAF CloudWatch log group"
  default     = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
