# Conduit Backend on AWS Lambda

Python FastAPI rewrite of the RealWorld "Conduit" API. Single-table DynamoDB
backend, JWT auth, packaged for AWS Lambda behind API Gateway HTTP API.

## Local development

```bash
python -m venv .venv && . .venv/Scripts/activate    # Windows
pip install -r requirements.txt
export DYNAMODB_TABLE=conduit
export JWT_SECRET=dev-secret
export AWS_REGION_APP=ap-southeast-1
uvicorn app.main:app --reload
```

## Build for Lambda

```bash
bash build.sh
```

Produces `backend/dist/` which the Terraform `lambda` module zips and uploads.

## Endpoints (RealWorld spec)

- `POST   /api/users` — register
- `POST   /api/users/login` — login
- `GET    /api/user` — current user
- `PUT    /api/user` — update current user
- `GET    /api/profiles/{username}`
- `POST   /api/profiles/{username}/follow`
- `DELETE /api/profiles/{username}/follow`
- `GET    /api/articles` (filter: tag, author, favorited, limit, offset)
- `GET    /api/articles/feed` (followed users)
- `POST   /api/articles`
- `GET    /api/articles/{slug}`
- `PUT    /api/articles/{slug}`
- `DELETE /api/articles/{slug}`
- `POST   /api/articles/{slug}/favorite`
- `DELETE /api/articles/{slug}/favorite`
- `GET    /api/articles/{slug}/comments`
- `POST   /api/articles/{slug}/comments`
- `DELETE /api/articles/{slug}/comments/{commentId}`
- `GET    /api/tags`
- `GET    /api/health-check`
