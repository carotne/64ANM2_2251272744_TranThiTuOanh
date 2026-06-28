resource "aws_iam_role" "this" {
  for_each = var.roles

  name                  = each.value.name
  description           = try(each.value.description, null)
  path                  = try(each.value.path, "/")
  max_session_duration  = try(each.value.max_session_duration, 3600)
  force_detach_policies = try(each.value.force_detach_policies, false)
  assume_role_policy    = each.value.assume_role_policy

  tags = merge(var.tags, each.value.tags)
}

resource "aws_iam_policy" "custom" {
  for_each = var.custom_policies

  name        = each.value.name
  description = try(each.value.description, null)
  policy      = each.value.policy
}

resource "aws_iam_role_policy_attachment" "custom" {
  for_each = {
    for p in flatten([
      for role_key, role in var.roles : [
        for policy_key in try(role.custom_policy_refs, []) : {
          role_key   = role_key
          policy_key = policy_key
        }
      ]
    ]) : "${p.role_key}-${p.policy_key}" => p
  }

  role       = aws_iam_role.this[each.value.role_key].name
  policy_arn = aws_iam_policy.custom[each.value.policy_key].arn
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each = {
    for p in flatten([
      for role_key, role in var.roles : [
        for policy_arn in try(role.managed_policy_arns, []) : {
          role_key   = role_key
          policy_arn = policy_arn
        }
      ]
    ]) : "${p.role_key}-${replace(p.policy_arn, "/[^a-zA-Z0-9]/", "-")}" => p
  }

  role       = aws_iam_role.this[each.value.role_key].name
  policy_arn = each.value.policy_arn
}
