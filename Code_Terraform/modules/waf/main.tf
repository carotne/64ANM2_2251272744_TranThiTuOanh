resource "aws_wafv2_web_acl" "this" {
  provider = aws.us_east_1

  name        = var.web_acl_name
  description = var.description
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = var.managed_rule_groups
    content {
      name     = rule.value.name
      priority = rule.value.priority

      override_action {
        none {}
      }

      statement {
        managed_rule_group_statement {
          name        = rule.value.name
          vendor_name = "AWS"

          dynamic "rule_action_override" {
            for_each = rule.value.name == "AWSManagedRulesCommonRuleSet" ? toset(var.common_rule_set_count_rules) : []
            content {
              name = rule_action_override.value

              action_to_use {
                count {}
              }
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = rule.value.name
        sampled_requests_enabled   = true
      }
    }
  }

  # Stricter, login-specific rate limit to slow credential brute-force /
  # stuffing. Evaluated before the general limit (lower priority number).
  rule {
    name     = "rate-limit-login"
    priority = 5

    action {
      dynamic "block" {
        for_each = var.rate_limit_count_only ? [] : [1]
        content {}
      }

      dynamic "count" {
        for_each = var.rate_limit_count_only ? [1] : []
        content {}
      }
    }

    statement {
      rate_based_statement {
        limit              = var.login_rate_limit
        aggregate_key_type = "IP"

        scope_down_statement {
          byte_match_statement {
            search_string         = "/api/users/login"
            positional_constraint = "STARTS_WITH"

            field_to_match {
              uri_path {}
            }

            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit-login"
      sampled_requests_enabled   = true
    }
  }

  # --- Custom SQLi hardening (defense-in-depth, edge layer) -----------------
  # The AWS managed SQLi rule set inspects the body at LOW sensitivity and does
  # not normalise comment-based obfuscation, so it lets most encoded/commented
  # payloads through.
  #
  # This is a GENERIC detector, not a signature list: it runs AWS WAF's SQLi
  # engine (libinjection — the same technology the managed rule set uses) over
  # JSON body VALUES at HIGH sensitivity. It flags strings whose *SQL grammar*
  # is suspicious, so it generalises to payloads it has never seen, rather than
  # matching a fixed wordlist. The text transformations strip evasion tricks
  # BEFORE the engine scores the input:
  #   URL_DECODE         %23 -> #, %2f -> / ...
  #   REPLACE_COMMENTS   '/**/OR/**/1=1' -> ' OR 1=1'
  #   COMPRESS_WHITE_SPACE + LOWERCASE   normalise spacing/case
  # Applies to every JSON endpoint, not just login.
  rule {
    name     = "sqli-json-body-strict"
    priority = 6

    action {
      dynamic "block" {
        for_each = var.sqli_hardening_count_only ? [] : [1]
        content {}
      }
      dynamic "count" {
        for_each = var.sqli_hardening_count_only ? [1] : []
        content {}
      }
    }

    statement {
      sqli_match_statement {
        sensitivity_level = "HIGH"

        field_to_match {
          json_body {
            match_scope = "VALUE"
            match_pattern {
              all {}
            }
            invalid_fallback_behavior = "MATCH"
            oversize_handling         = "CONTINUE"
          }
        }

        text_transformation {
          priority = 0
          type     = "URL_DECODE"
        }
        text_transformation {
          priority = 1
          type     = "REPLACE_COMMENTS"
        }
        text_transformation {
          priority = 2
          type     = "COMPRESS_WHITE_SPACE"
        }
        text_transformation {
          priority = 3
          type     = "LOWERCASE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "sqli-json-body-strict"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "rate-limit-ip"
    priority = 100

    action {
      dynamic "block" {
        for_each = var.rate_limit_count_only ? [] : [1]
        content {}
      }

      dynamic "count" {
        for_each = var.rate_limit_count_only ? [1] : []
        content {}
      }
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit-ip"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = var.web_acl_name
    sampled_requests_enabled   = true
  }

  tags = merge(var.tags, {
    Name = var.web_acl_name
  })
}

# WAF logging -> CloudWatch Logs. The log group name MUST start with
# "aws-waf-logs-" and live in us-east-1 (same as the CloudFront-scoped Web ACL).
resource "aws_cloudwatch_log_group" "waf" {
  provider = aws.us_east_1

  name              = "aws-waf-logs-${var.web_acl_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_wafv2_web_acl_logging_configuration" "this" {
  provider = aws.us_east_1

  resource_arn            = aws_wafv2_web_acl.this.arn
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
}
