resource "aws_cloudtrail" "this" {
  name                          = var.trail_name
  s3_bucket_name                = var.s3_bucket_name
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = var.kms_key_arn

  cloud_watch_logs_group_arn = var.cloudwatch_log_group_arn != null ? "${var.cloudwatch_log_group_arn}:*" : null
  cloud_watch_logs_role_arn  = var.cloudwatch_role_arn

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  tags = merge(var.tags, {
    Name = var.trail_name
  })
}
