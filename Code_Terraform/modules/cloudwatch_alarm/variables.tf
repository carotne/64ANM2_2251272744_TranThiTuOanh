variable "alarms" {
  type = map(object({
    name                = string
    description         = optional(string)
    comparison_operator = string
    evaluation_periods  = number
    metric_name         = string
    namespace           = string
    period              = number
    statistic           = string
    threshold           = number
    treat_missing_data  = optional(string, "notBreaching")
    dimensions          = optional(map(string), {})
    alarm_actions       = optional(list(string), [])
    ok_actions          = optional(list(string), [])
  }))
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
