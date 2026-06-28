# Conduit Frontend (Vue 3) — S3 + CloudFront deployment

Adapted from `vue3-realworld-example-app`. The SPA is built locally with `pnpm`
and uploaded to the S3 bucket created by Terraform. CloudFront serves
`/api/*` from API Gateway and everything else from the bucket.

## Prerequisites

- Node.js 20+ and pnpm 10+
- `aws` CLI configured with credentials that can write to the bucket
- Terraform already applied (gives you the bucket name + distribution id)

## Build

```bash
pnpm install
pnpm build
```

`VITE_API_HOST` is left empty so the SPA calls the same host it was served
from. CloudFront routes `/api/*` to API Gateway.

## Deploy

```bash
BUCKET=$(cd .. && terraform output -raw frontend_bucket)
CF_ID=$(cd .. && terraform output -raw cloudfront_domain_name)

aws s3 sync dist/ "s3://${BUCKET}/" --delete

# Invalidate CloudFront after each deploy
aws cloudfront create-invalidation \
    --distribution-id "${CF_ID}" \
    --paths "/*"
```
