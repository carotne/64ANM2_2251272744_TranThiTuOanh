import hmac

from app.routes import articles, comments, health, profiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import users
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Conduit on Lambda", version="1.0.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Reject any request that did not come through CloudFront. CloudFront injects the
    # X-Origin-Verify header with the shared secret on every API-origin request; a
    # client hitting the public API Gateway URL directly cannot supply it -> 403.
    @application.middleware("http")
    async def verify_origin(request: Request, call_next):
        secret = settings.origin_verify_secret
        if secret:
            provided = request.headers.get("x-origin-verify", "")
            if not hmac.compare_digest(provided, secret):
                return JSONResponse(status_code=403, content={"message": "Forbidden"})
        return await call_next(request)

    api_prefix = "/api"
    application.include_router(health.router, prefix=api_prefix)
    application.include_router(users.router, prefix=api_prefix)
    application.include_router(profiles.router, prefix=api_prefix)
    application.include_router(articles.router, prefix=api_prefix)
    application.include_router(articles.tags_router, prefix=api_prefix)
    application.include_router(comments.router, prefix=api_prefix)

    return application


app = create_app()
