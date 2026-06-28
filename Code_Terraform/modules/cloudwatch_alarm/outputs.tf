output "alarm_arns" {
  value = { for k, v in aws_cloudwatch_metric_alarm.this : k => v.arn }
}
