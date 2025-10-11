from fastapi import FastAPI, Request
from fastapi import responses
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from core.logging import setup_logging, REQUEST_ID
from contextlib import asynccontextmanager

from api.routers.auth import router as auth_router
from api.routers.backtest import router as backtest_router
from infrastructure.db import init_db, engine

# log
setup_logging()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logging.getLogger("app").info("Startup")
    await init_db()
    yield
    logging.getLogger("app").info("Shutdown")


app = FastAPI(title="Trading Backtest API", version="0.1.0", lifespan=app_lifespan)

allowed_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logging.getLogger("http").warning(
        "Service error",
        extra={
            "error": str(exc),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query": dict(request.query_params),
        },
    )
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    logger = logging.getLogger("http")
    req_id = request.headers.get("x-request-id") or request.headers.get(
        "x-correlation-id"
    )
    if not req_id:
        import uuid

        req_id = uuid.uuid4().hex
    token = REQUEST_ID.set(req_id)
    start = time.monotonic()
    logger.info(
        "Request start",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
            "client": request.client.host if request.client else None,
            "request_id": req_id,
        },
    )
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    logger.info(
        "Request end",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "request_id": req_id,
        },
    )
    # Expose request id to clients
    try:
        response.headers["x-request-id"] = req_id
    except Exception:
        pass
    # Reset contextvar
    REQUEST_ID.reset(token)
    return response


@app.get("/")
async def root():
    return {"message": "OK", "service": "Trading Backtest API"}


@app.get("/api/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/health")
async def health_alias():
    return {"status": "ok"}


@app.get("/api/readyz")
async def readyz():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return responses.JSONResponse(status_code=503, content={"ready": False})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.getLogger("http").exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


app.include_router(auth_router, prefix="/api/v1")
app.include_router(backtest_router, prefix="/api/v1")
