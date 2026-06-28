locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Environment = var.environment
    Project     = var.project_name
  })
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

############################################
# KMS — keys for S3, DynamoDB, CloudWatch
############################################
module "kms" {
  source = "./modules/kms"

  kms_keys = {
    s3       = { description = "KMS key for S3 buckets" }
    dynamodb = { description = "KMS key for DynamoDB tables" }
    logs     = { description = "KMS key for CloudWatch Logs & CloudTrail" }
    sns      = { description = "KMS key for SNS topics" }
  }
  tags = local.common_tags
}

# Allow CloudWatch Logs service to use the logs KMS key (needed when encrypting log groups)
resource "aws_kms_key_policy" "logs" {
  key_id = module.kms.key_ids["logs"]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnableRootPermissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowCloudWatchLogs"
        Effect    = "Allow"
        Principal = { Service = "logs.${var.region}.amazonaws.com" }
        Action = [
          "kms:Encrypt*",
          "kms:Decrypt*",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*",
        ]
        Resource = "*"
        Condition = {
          ArnEquals = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:*"
          }
        }
      },
      {
        Sid       = "AllowCloudTrail"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action = [
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
        ]
        Resource = "*"
      },
    ]
  })
}

# Allow CloudFront (OAC) to decrypt frontend S3 objects encrypted with the s3 KMS key.
# Without this, S3 returns 403 AccessDenied to CloudFront when serving the SPA.
resource "aws_kms_key_policy" "s3" {
  key_id = module.kms.key_ids["s3"]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnableRootPermissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowCloudFrontDecrypt"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = ["kms:Decrypt"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = module.cloudfront.distribution_arn
          }
        }
      },
    ]
  })
}

# Allow CloudWatch Alarms to publish to the encrypted SNS alarm topic.
resource "aws_kms_key_policy" "sns" {
  key_id = module.kms.key_ids["sns"]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnableRootPermissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowCloudWatchAlarms"
        Effect    = "Allow"
        Principal = { Service = "cloudwatch.amazonaws.com" }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:cloudwatch:${var.region}:${data.aws_caller_identity.current.account_id}:alarm:${local.name_prefix}-*"
          }
        }
      },
      {
        Sid       = "AllowEventBridgeSecurityRules"
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:events:${var.region}:${data.aws_caller_identity.current.account_id}:rule/${local.name_prefix}-*"
          }
        }
      },
    ]
  })
}

############################################
# VPC + Endpoints (private subnets only)
############################################
module "vpc" {
  source = "./modules/vpc"

  vpc_name        = "${local.name_prefix}-vpc"
  cidr_block      = var.vpc_cidr
  private_subnets = var.private_subnets
  tags            = local.common_tags
}

module "security_group" {
  source = "./modules/security_group"

  vpc_id = module.vpc.vpc_id
  tags   = local.common_tags

  security_groups = {
    lambda = {
      name        = "${local.name_prefix}-lambda-sg"
      description = "SG for Lambda ENIs in private subnets"
      egress = [
        {
          # 0.0.0.0/0 needed for the DynamoDB & S3 *gateway* endpoints, whose traffic
          # targets the service's public IP ranges (not the VPC CIDR). With no NAT/IGW
          # route in the private subnets, only the VPC endpoints are actually reachable.
          description = "Allow HTTPS to VPC endpoints (gateway + interface)"
          from_port   = 443
          to_port     = 443
          ip_protocol = "tcp"
          cidr_ipv4   = "0.0.0.0/0"
        },
      ]
    }
    vpce = {
      name        = "${local.name_prefix}-vpce-sg"
      description = "SG for interface VPC endpoints"
      ingress = [
        {
          description = "Allow HTTPS from Lambda SG (via CIDR)"
          from_port   = 443
          to_port     = 443
          ip_protocol = "tcp"
          cidr_ipv4   = var.vpc_cidr
        },
      ]
    }
  }
}

module "vpc_endpoint" {
  source = "./modules/vpc_endpoint"

  vpc_id = module.vpc.vpc_id
  region = var.region
  tags   = local.common_tags

  gateway_endpoints = {
    dynamodb = {
      service         = "dynamodb"
      route_table_ids = [module.vpc.private_route_table_id]
    }
    s3 = {
      service         = "s3"
      route_table_ids = [module.vpc.private_route_table_id]
    }
  }

  interface_endpoints = {
    logs = {
      service            = "logs"
      subnet_ids         = module.vpc.private_subnet_ids
      security_group_ids = [module.security_group.security_group_ids["vpce"]]
    }
    kms = {
      service            = "kms"
      subnet_ids         = module.vpc.private_subnet_ids
      security_group_ids = [module.security_group.security_group_ids["vpce"]]
    }
  }
}

############################################
# S3 buckets — frontend + logs
############################################
module "frontend_bucket" {
  source = "./modules/s3_bucket"

  bucket_name       = var.frontend_bucket_name
  enable_versioning = true
  enable_encryption = true
  kms_key_arn       = module.kms.key_arns["s3"]
  force_destroy     = true
  tags              = local.common_tags
}

module "logs_bucket" {
  source = "./modules/s3_bucket"

  bucket_name       = var.logs_bucket_name
  enable_versioning = true
  enable_encryption = true
  kms_key_arn       = module.kms.key_arns["logs"]
  force_destroy     = true
  tags              = local.common_tags

  lifecycle_rules = [
    {
      id              = "expire-old-logs"
      status          = "Enabled"
      expiration_days = 365
      transitions = [
        { days = 30, storage_class = "STANDARD_IA" },
        { days = 90, storage_class = "GLACIER" },
      ]
    },
  ]

  bucket_policy = data.aws_iam_policy_document.logs_bucket_policy.json
}

data "aws_iam_policy_document" "logs_bucket_policy" {
  statement {
    sid = "AWSCloudTrailAclCheck"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl"]
    resources = ["arn:aws:s3:::${var.logs_bucket_name}"]
  }

  statement {
    sid = "AWSCloudTrailWrite"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["arn:aws:s3:::${var.logs_bucket_name}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

############################################
# DynamoDB — single-table design for conduit
############################################
module "dynamodb" {
  source = "./modules/dynamodb"

  table_name  = "${local.name_prefix}-${var.dynamodb_table_name}"
  hash_key    = "PK"
  range_key   = "SK"
  kms_key_arn = module.kms.key_arns["dynamodb"]
  tags        = local.common_tags

  attributes = [
    { name = "PK", type = "S" },
    { name = "SK", type = "S" },
    { name = "GSI1PK", type = "S" },
    { name = "GSI1SK", type = "S" },
    { name = "GSI2PK", type = "S" },
    { name = "GSI2SK", type = "S" },
    { name = "GSI3PK", type = "S" },
    { name = "GSI3SK", type = "S" },
  ]

  global_secondary_indexes = [
    {
      name            = "GSI1"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
    },
    {
      name            = "GSI2"
      hash_key        = "GSI2PK"
      range_key       = "GSI2SK"
      projection_type = "ALL"
    },
    {
      name            = "GSI3"
      hash_key        = "GSI3PK"
      range_key       = "GSI3SK"
      projection_type = "ALL"
    },
  ]
}

############################################
# IAM — Lambda execution role
############################################
module "iam" {
  source = "./modules/iam"

  tags = local.common_tags

  custom_policies = {
    lambda_dynamodb = {
      name = "${local.name_prefix}-lambda-dynamodb"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "dynamodb:GetItem",
              "dynamodb:PutItem",
              "dynamodb:UpdateItem",
              "dynamodb:DeleteItem",
              "dynamodb:Query",
              "dynamodb:BatchGetItem",
              "dynamodb:BatchWriteItem",
              "dynamodb:ConditionCheckItem",
            ]
            Resource = [
              module.dynamodb.table_arn,
              "${module.dynamodb.table_arn}/index/*",
            ]
          },
        ]
      })
    }

    lambda_kms = {
      name = "${local.name_prefix}-lambda-kms"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
            Resource = [
              module.kms.key_arns["dynamodb"],
              module.kms.key_arns["logs"],
            ]
          },
        ]
      })
    }
  }

  roles = {
    lambda = {
      name = "${local.name_prefix}-lambda-exec"
      assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [{
          Effect    = "Allow"
          Principal = { Service = "lambda.amazonaws.com" }
          Action    = "sts:AssumeRole"
        }]
      })
      managed_policy_arns = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
      ]
      custom_policy_refs = ["lambda_dynamodb", "lambda_kms"]
    }
  }
}

############################################
# CloudWatch Log Groups
############################################
module "lambda_log_group" {
  source = "./modules/cloudwatch_log_group"

  log_group_name    = "/aws/lambda/${local.name_prefix}-conduit-api"
  retention_in_days = 90
  kms_key_arn       = module.kms.key_arns["logs"]
  tags              = local.common_tags

  depends_on = [aws_kms_key_policy.logs]
}

module "apigw_log_group" {
  source = "./modules/cloudwatch_log_group"

  log_group_name    = "/aws/apigateway/${local.name_prefix}-conduit"
  retention_in_days = 90
  kms_key_arn       = module.kms.key_arns["logs"]
  tags              = local.common_tags

  depends_on = [aws_kms_key_policy.logs]
}

############################################
# Lambda — Conduit API
############################################
# Shared secret injected by CloudFront into every API-origin request as the
# X-Origin-Verify header; the FastAPI app rejects requests without it, so the
# public API Gateway endpoint cannot be reached directly (bypassing CloudFront/WAF).
resource "random_password" "origin_verify" {
  length  = 48
  special = false
}

module "conduit_lambda" {
  source = "./modules/lambda"

  function_name = "${local.name_prefix}-conduit-api"
  description   = "Conduit RealWorld API (FastAPI on Lambda + DynamoDB)"
  source_dir    = var.lambda_source_dir
  handler       = "lambda_handler.handler"
  runtime       = "python3.12"
  memory_size   = var.lambda_memory_size
  timeout       = var.lambda_timeout
  role_arn      = module.iam.role_arns["lambda"]
  tags          = local.common_tags

  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_group.security_group_ids["lambda"]]

  environment_variables = {
    DYNAMODB_TABLE       = module.dynamodb.table_name
    JWT_SECRET           = var.jwt_secret
    AWS_REGION_APP       = var.region
    LOG_LEVEL            = "INFO"
    ORIGIN_VERIFY_SECRET = random_password.origin_verify.result
  }

  api_gateway_execution_arn     = module.api_gateway.execution_arn
  create_api_gateway_permission = true

  depends_on = [module.lambda_log_group]
}

############################################
# API Gateway — HTTP API in front of Lambda
############################################
module "api_gateway" {
  source = "./modules/api_gateway"

  api_name             = "${local.name_prefix}-conduit-api"
  description          = "Public HTTP API for Conduit (proxied via CloudFront)"
  stage_name           = "$default"
  lambda_invoke_arn    = module.conduit_lambda.invoke_arn
  access_log_group_arn = module.apigw_log_group.arn
  cors_allow_origins   = ["https://${var.frontend_subdomain}"]
  route_keys = [
    "GET /api/health-check",
    "POST /api/users",
    "POST /api/users/login",
    "GET /api/user",
    "PUT /api/user",
    "GET /api/profiles/{username}",
    "POST /api/profiles/{username}/follow",
    "DELETE /api/profiles/{username}/follow",
    "GET /api/articles",
    "POST /api/articles",
    "GET /api/articles/feed",
    "GET /api/articles/{slug}",
    "PUT /api/articles/{slug}",
    "DELETE /api/articles/{slug}",
    "POST /api/articles/{slug}/favorite",
    "DELETE /api/articles/{slug}/favorite",
    "GET /api/articles/{slug}/comments",
    "POST /api/articles/{slug}/comments",
    "DELETE /api/articles/{slug}/comments/{comment_id}",
    "GET /api/tags",
  ]
  tags = local.common_tags
}

############################################
# Route53 + ACM (cert in us-east-1 for CloudFront)
############################################
module "route53" {
  source = "./modules/route53"

  create_zone      = var.create_route53_zone
  zone_name        = var.domain_name
  existing_zone_id = var.existing_zone_id
  tags             = local.common_tags

  records = {
    cloudfront = {
      name = var.frontend_subdomain
      type = "A"
      alias = {
        name                   = module.cloudfront.distribution_domain_name
        zone_id                = module.cloudfront.distribution_hosted_zone_id
        evaluate_target_health = false
      }
    }
  }
}

module "acm_cloudfront" {
  source = "./modules/acm"

  providers = {
    aws = aws.us_east_1
  }

  domain_name = var.frontend_subdomain
  zone_id     = module.route53.zone_id
  tags        = local.common_tags
}

############################################
# WAF (CloudFront scope, us-east-1)
############################################
module "waf" {
  source = "./modules/waf"

  providers = {
    aws.us_east_1 = aws.us_east_1
  }

  web_acl_name          = "${local.name_prefix}-cf-waf"
  rate_limit            = 2000
  rate_limit_count_only = false
  tags                  = local.common_tags

}

############################################
# CloudFront — entry point for FE + /api/*
############################################
module "cloudfront" {
  source = "./modules/cloudfront"

  distribution_name              = "${local.name_prefix}-cf"
  comment                        = "Conduit CDN"
  aliases                        = [var.frontend_subdomain]
  s3_bucket_regional_domain_name = module.frontend_bucket.bucket_regional_domain_name
  api_gateway_domain             = module.api_gateway.api_domain
  web_acl_arn                    = var.enable_waf ? module.waf.web_acl_arn : null
  acm_certificate_arn            = module.acm_cloudfront.certificate_arn
  origin_verify_secret           = random_password.origin_verify.result
  tags                           = local.common_tags
}

# Bucket policy granting CloudFront OAC access to the frontend bucket
resource "aws_s3_bucket_policy" "frontend_oac" {
  bucket = module.frontend_bucket.bucket_id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontServicePrincipalReadOnly"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${module.frontend_bucket.bucket_arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = module.cloudfront.distribution_arn
        }
      }
    }]
  })
}

############################################
# CloudTrail — multi-region trail to S3
############################################
module "cloudtrail" {
  source = "./modules/cloudtrail"

  trail_name     = "${local.name_prefix}-trail"
  s3_bucket_name = module.logs_bucket.bucket_id
  kms_key_arn    = module.kms.key_arns["logs"]
  tags           = local.common_tags

  depends_on = [aws_kms_key_policy.logs, module.logs_bucket]
}

############################################
# GuardDuty
############################################
module "guardduty" {
  source = "./modules/guardduty"
  tags   = local.common_tags
}

############################################
# SNS + CloudWatch alarms
############################################
module "alarm_topic" {
  source = "./modules/sns_topic"

  topic_name        = "${local.name_prefix}-alarms"
  kms_key_arn       = module.kms.key_arns["sns"]
  email_subscribers = [var.alert_email]
  tags              = local.common_tags

  depends_on = [aws_kms_key_policy.sns]
}

data "aws_iam_policy_document" "alarm_topic_policy" {
  statement {
    sid    = "DefaultOwnerPermissions"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = [
      "SNS:GetTopicAttributes",
      "SNS:SetTopicAttributes",
      "SNS:AddPermission",
      "SNS:RemovePermission",
      "SNS:DeleteTopic",
      "SNS:Subscribe",
      "SNS:ListSubscriptionsByTopic",
      "SNS:Publish",
    ]

    resources = [module.alarm_topic.arn]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid    = "AllowEventBridgePublish"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions   = ["SNS:Publish"]
    resources = [module.alarm_topic.arn]

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:events:${var.region}:${data.aws_caller_identity.current.account_id}:rule/${local.name_prefix}-*"]
    }
  }
}

resource "aws_sns_topic_policy" "alarm_topic" {
  arn    = module.alarm_topic.arn
  policy = data.aws_iam_policy_document.alarm_topic_policy.json
}

resource "aws_sns_topic" "waf_alarm_us_east_1" {
  provider = aws.us_east_1

  name = "${local.name_prefix}-waf-alarms"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-waf-alarms"
  })
}

resource "aws_sns_topic_subscription" "waf_alarm_email" {
  provider = aws.us_east_1

  topic_arn = aws_sns_topic.waf_alarm_us_east_1.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "waf_alarm_topic_policy" {
  statement {
    sid    = "DefaultOwnerPermissions"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = [
      "SNS:GetTopicAttributes",
      "SNS:SetTopicAttributes",
      "SNS:AddPermission",
      "SNS:RemovePermission",
      "SNS:DeleteTopic",
      "SNS:Subscribe",
      "SNS:ListSubscriptionsByTopic",
      "SNS:Publish",
    ]

    resources = [aws_sns_topic.waf_alarm_us_east_1.arn]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid    = "AllowCloudWatchWafAlarms"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    actions   = ["SNS:Publish"]
    resources = [aws_sns_topic.waf_alarm_us_east_1.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:cloudwatch:us-east-1:${data.aws_caller_identity.current.account_id}:alarm:${local.name_prefix}-waf-*"]
    }
  }
}

resource "aws_sns_topic_policy" "waf_alarm_us_east_1" {
  provider = aws.us_east_1

  arn    = aws_sns_topic.waf_alarm_us_east_1.arn
  policy = data.aws_iam_policy_document.waf_alarm_topic_policy.json
}

resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "${local.name_prefix}-guardduty-findings"
  description = "Send medium and high severity GuardDuty findings to SNS"

  event_pattern = jsonencode({
    source        = ["aws.guardduty"]
    "detail-type" = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 4] }]
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "guardduty_findings_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "sns"
  arn       = module.alarm_topic.arn
}

resource "aws_cloudwatch_event_rule" "cloudtrail_sensitive_events" {
  name        = "${local.name_prefix}-cloudtrail-sensitive-events"
  description = "Send sensitive AWS API changes captured by CloudTrail to SNS"

  event_pattern = jsonencode({
    "detail-type" = ["AWS API Call via CloudTrail"]
    detail = {
      eventName = [
        "StopLogging",
        "DeleteTrail",
        "UpdateTrail",
        "PutEventSelectors",
        "CreateAccessKey",
        "CreateUser",
        "AttachUserPolicy",
        "AttachRolePolicy",
        "PutUserPolicy",
        "PutRolePolicy",
        "DeleteUserPolicy",
        "DeleteRolePolicy",
        "AuthorizeSecurityGroupIngress",
        "AuthorizeSecurityGroupEgress",
        "CreateRoute",
        "ReplaceRoute",
        "PutBucketPolicy",
        "DeleteBucketPolicy",
        "DeletePublicAccessBlock",
        "PutPublicAccessBlock",
        "DisableKey",
        "ScheduleKeyDeletion",
        "UpdateWebACL",
        "DeleteWebACL",
        "DeleteDetector",
        "UpdateDetector",
        "DeleteLogGroup",
        "DeleteMetricFilter",
      ]
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "cloudtrail_sensitive_events_sns" {
  rule      = aws_cloudwatch_event_rule.cloudtrail_sensitive_events.name
  target_id = "sns"
  arn       = module.alarm_topic.arn
}

module "cloudwatch_alarms" {
  source = "./modules/cloudwatch_alarm"

  tags = local.common_tags

  alarms = {
    lambda_errors = {
      name                = "${local.name_prefix}-lambda-errors"
      description         = "Lambda errors > 5 in 5 minutes"
      namespace           = "AWS/Lambda"
      metric_name         = "Errors"
      statistic           = "Sum"
      period              = 300
      evaluation_periods  = 1
      threshold           = 5
      comparison_operator = "GreaterThanThreshold"
      dimensions          = { FunctionName = module.conduit_lambda.function_name }
      alarm_actions       = [module.alarm_topic.arn]
      ok_actions          = [module.alarm_topic.arn]
    }
    lambda_throttles = {
      name                = "${local.name_prefix}-lambda-throttles"
      description         = "Lambda throttles > 0"
      namespace           = "AWS/Lambda"
      metric_name         = "Throttles"
      statistic           = "Sum"
      period              = 300
      evaluation_periods  = 1
      threshold           = 0
      comparison_operator = "GreaterThanThreshold"
      dimensions          = { FunctionName = module.conduit_lambda.function_name }
      alarm_actions       = [module.alarm_topic.arn]
    }
    apigw_5xx = {
      name                = "${local.name_prefix}-apigw-5xx"
      description         = "API Gateway 5xx > 5 in 5 minutes"
      namespace           = "AWS/ApiGateway"
      metric_name         = "5xx"
      statistic           = "Sum"
      period              = 300
      evaluation_periods  = 1
      threshold           = 5
      comparison_operator = "GreaterThanThreshold"
      dimensions          = { ApiId = module.api_gateway.api_id }
      alarm_actions       = [module.alarm_topic.arn]
    }
    apigw_4xx = {
      name                = "${local.name_prefix}-apigw-4xx"
      description         = "API Gateway 4xx > 20 in 5 minutes"
      namespace           = "AWS/ApiGateway"
      metric_name         = "4xx"
      statistic           = "Sum"
      period              = 300
      evaluation_periods  = 1
      threshold           = 20
      comparison_operator = "GreaterThanThreshold"
      dimensions          = { ApiId = module.api_gateway.api_id }
      alarm_actions       = [module.alarm_topic.arn]
      ok_actions          = [module.alarm_topic.arn]
    }
    dynamodb_throttles = {
      name                = "${local.name_prefix}-ddb-throttles"
      description         = "DynamoDB throttled requests"
      namespace           = "AWS/DynamoDB"
      metric_name         = "ThrottledRequests"
      statistic           = "Sum"
      period              = 300
      evaluation_periods  = 1
      threshold           = 0
      comparison_operator = "GreaterThanThreshold"
      dimensions          = { TableName = module.dynamodb.table_name }
      alarm_actions       = [module.alarm_topic.arn]
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  provider = aws.us_east_1

  alarm_name          = "${local.name_prefix}-waf-blocked-requests"
  alarm_description   = "WAF blocked requests > 0 in 5 minutes"
  namespace           = "AWS/WAFV2"
  metric_name         = "BlockedRequests"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    WebACL = "${local.name_prefix}-cf-waf"
    Rule   = "ALL"
  }

  actions_enabled = var.enable_waf
  alarm_actions   = [aws_sns_topic.waf_alarm_us_east_1.arn]
  tags            = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "waf_rate_limit_login" {
  provider = aws.us_east_1

  alarm_name          = "${local.name_prefix}-waf-rate-limit-login"
  alarm_description   = "WAF login rate-limit blocks > 0 in 5 minutes"
  namespace           = "AWS/WAFV2"
  metric_name         = "BlockedRequests"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    WebACL = "${local.name_prefix}-cf-waf"
    Rule   = "rate-limit-login"
  }

  actions_enabled = var.enable_waf
  alarm_actions   = [aws_sns_topic.waf_alarm_us_east_1.arn]
  tags            = local.common_tags
}
