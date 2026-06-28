output "api_id" {
  value = aws_apigatewayv2_api.this.id
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.this.api_endpoint
}

output "execution_arn" {
  value = aws_apigatewayv2_api.this.execution_arn
}

output "stage_invoke_url" {
  value = aws_apigatewayv2_stage.this.invoke_url
}

output "api_domain" {
  value = replace(aws_apigatewayv2_api.this.api_endpoint, "https://", "")
}
