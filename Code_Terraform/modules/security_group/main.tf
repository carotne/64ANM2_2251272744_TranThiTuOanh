resource "aws_security_group" "this" {
  for_each = var.security_groups

  name        = each.value.name
  description = each.value.description
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = each.value.name
  })
}

resource "aws_vpc_security_group_ingress_rule" "this" {
  for_each = {
    for r in flatten([
      for sg_key, sg in var.security_groups : [
        for idx, rule in coalesce(sg.ingress, []) : {
          key         = "${sg_key}-in-${idx}"
          sg_key      = sg_key
          cidr_ipv4   = rule.cidr_ipv4
          from_port   = rule.from_port
          to_port     = rule.to_port
          ip_protocol = rule.ip_protocol
          description = rule.description
        }
      ]
    ]) : r.key => r
  }

  security_group_id = aws_security_group.this[each.value.sg_key].id
  cidr_ipv4         = each.value.cidr_ipv4
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  ip_protocol       = each.value.ip_protocol
  description       = each.value.description
}

resource "aws_vpc_security_group_egress_rule" "this" {
  for_each = {
    for r in flatten([
      for sg_key, sg in var.security_groups : [
        for idx, rule in coalesce(sg.egress, []) : {
          key         = "${sg_key}-out-${idx}"
          sg_key      = sg_key
          cidr_ipv4   = rule.cidr_ipv4
          from_port   = rule.from_port
          to_port     = rule.to_port
          ip_protocol = rule.ip_protocol
          description = rule.description
        }
      ]
    ]) : r.key => r
  }

  security_group_id = aws_security_group.this[each.value.sg_key].id
  cidr_ipv4         = each.value.cidr_ipv4
  from_port         = each.value.from_port
  to_port           = each.value.to_port
  ip_protocol       = each.value.ip_protocol
  description       = each.value.description
}
