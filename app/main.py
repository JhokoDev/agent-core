import secrets
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import Settings
from app.database import Database
from app.logging import configure_logging
from app.models.base import ModelProvider
from app.models.registry import create_provider


def create_app(settings: Settings | None = None, provider: ModelProvider | None = None) -> FastAPI:
    config = settings or Settings()
    database = Database(config.database_path)
    model = provider if provider is not None else create_provider(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        app.state.audit = configure_logging(config.data_dir)
        try:
            yield
        finally:
            await model.aclose()
            for handler in app.state.audit.handlers[:]:
                handler.close()
                app.state.audit.removeHandler(handler)

    app = FastAPI(title="Personal Agent — Fase 0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    bearer = HTTPBearer(auto_error=False)

    async def authorize(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or not secrets.compare_digest(
                credentials.credentials.encode(), config.api_token.get_secret_value().encode()):
            raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})

    @app.middleware("http")
    async def audit(request, call_next):
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            app.state.audit.info("request", extra={"event": "http_request", "request_id": request_id,
                                                  "status": status,
                                                  "duration_ms": round((time.monotonic()-started)*1000, 2)})

    @app.get("/health")
    async def health():
        return {"status": "alive", "phase": 0}

    @app.get("/ready", dependencies=[Depends(authorize)])
    async def ready():
        db_ok = database.ready()
        model_health = await model.health()
        ok = db_ok and model_health.status == "ready"
        return JSONResponse(status_code=200 if ok else 503, content={
            "status": "ready" if ok else "degraded",
            "database": "ready" if db_ok else "unavailable",
            "llm": model_health.model_dump(),
            "bridge": "not_implemented", "tools": "disabled"})

    return app
