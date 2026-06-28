output "key_ids" {
  value = { for k, v in aws_kms_key.this : k => v.key_id }
}

output "key_arns" {
  value = { for k, v in aws_kms_key.this : k => v.arn }
}

output "alias_names" {
  value = { for k, v in aws_kms_alias.this : k => v.name }
}
