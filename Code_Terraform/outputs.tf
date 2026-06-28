output "cloudfront_domain_name" {
  description = "CloudFront distribution domain (alias target)"
  value       = module.cloudfront.distribution_domain_name
}

output "frontend_url" {
  description = "Public URL of the SPA"
  value       = "https://${var.frontend_subdomain}"
}

output "api_gateway_endpoint" {
  description = "Internal API Gateway endpoint (CloudFront /api/* origin)"
  value       = module.api_gateway.api_endpoint
}

output "frontend_bucket" {
  value = module.frontend_bucket.bucket_id
}

output "logs_bucket" {
  value = module.logs_bucket.bucket_id
}

output "dynamodb_table" {
  value = module.dynamodb.table_name
}

output "lambda_function_name" {
  value = module.conduit_lambda.function_name
}

output "route53_name_servers" {
  description = "Set these NS records at the domain registrar (only if create_route53_zone = true)"
  value       = module.route53.name_servers
}
