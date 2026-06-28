output "security_group_ids" {
  value = { for k, sg in aws_security_group.this : k => sg.id }
}
