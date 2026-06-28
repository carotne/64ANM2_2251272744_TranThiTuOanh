project_name = "oanhlab"
environment  = "prod"
region       = "ap-southeast-1"

vpc_cidr = "10.0.0.0/16"
private_subnets = [
  {
    name              = "lambda-a"
    cidr_block        = "10.0.1.0/24"
    availability_zone = "ap-southeast-1a"
  },
  {
    name              = "lambda-b"
    cidr_block        = "10.0.2.0/24"
    availability_zone = "ap-southeast-1b"
  },
]

frontend_bucket_name = "oanhlab-conduit-frontend-prod"
logs_bucket_name     = "oanhlab-conduit-logs"

domain_name        = "oanhlab.com"
frontend_subdomain = "www.oanhlab.com"

create_route53_zone = false
existing_zone_id    = "Z03104772JFTM2RTU9JFI"

dynamodb_table_name = "conduit"

lambda_source_dir  = "./backend/dist"
lambda_memory_size = 1024
lambda_timeout     = 30

jwt_secret  = "uIws2yA8AZ9GvvEL_5zTxs9W2EQcDDBR_ByY2vBX12W0tIr1QT_lgmvvNRT1gJWQ"
alert_email = "tranthituoanh1107@gmail.com"

enable_waf = true

tags = {
  Project   = "oanhlab-conduit"
  ManagedBy = "Terraform"
  Owner     = "OanhTTT"
}
