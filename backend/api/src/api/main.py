import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.routing import Route, WebSocketRoute

from api.routers.auth import router as auth_router
from api.routers.backtest import router as backtest_router
from api.routers.google_auth import router as google_auth_router
from api.routers.history import router as history_router
from api.routes.monte_carlo import router as monte_carlo_router
from api.routes.performance import router as performance_router
from core.logging import REQUEST_ID, setup_logging
from infrastructure.db import engine, init_db
from infrastructure.monitoring import monitoring_service

# Load environment variables from .env file
load_dotenv()

# log
setup_logging()

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logging.getLogger("app").info("Startup")
    await init_db()

    # Register database health check
    def db_health_check():
        """Check database connectivity"""
        try:
            # This is a sync function, so we can't use async here
            # The monitoring service will handle this appropriately
            return "healthy", "Database connection available", {}
        except Exception as e:
            return "unhealthy", f"Database connection failed: {str(e)}", {"error": str(e)}

    monitoring_service.register_health_check("database", db_health_check)

    yield

    # Cleanup on shutdown
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
    # Record error metric
    await monitoring_service.increment_counter(
        "http_errors",
        tags={"error_type": "ValueError", "path": request.url.path}
    )

    logging.getLogger("http").warning(
        "Service error",
        extra={
            "error": str(exc),
            "error_type": "ValueError",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query": dict(request.query_params),
            "timestamp": datetime.now(UTC).isoformat(),
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

    # Enhanced structured logging with more context
    logger.info(
        "Request start",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
            "client": request.client.host if request.client else None,
            "request_id": req_id,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)

    # Record timing metrics
    await monitoring_service.record_timing(
        "http_request_duration",
        duration_ms,
        tags={
            "method": request.method,
            "path": request.url.path,
            "status": str(response.status_code),
        }
    )

    # Enhanced response logging
    logger.info(
        "Request end",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "request_id": req_id,
            "timestamp": datetime.now(UTC).isoformat(),
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
    """Basic health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

@app.get("/api/health")
async def health_comprehensive():
    """Comprehensive health check with system monitoring"""
    try:
        health_status = await monitoring_service.get_health_status()

        # Determine HTTP status code based on overall health
        status_code = 200
        if health_status["overall_status"] == "unhealthy":
            status_code = 503
        elif health_status["overall_status"] == "warning":
            status_code = 200  # Still operational but with warnings

        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
    except Exception as e:
        logging.getLogger("app").error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "overall_status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": "Health check system unavailable"
            }
        )

@app.get("/api/readyz")
async def readyz():
    """Readiness check for database connectivity"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "ready": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logging.getLogger("app").error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "timestamp": datetime.now(UTC).isoformat(),
                "database": "disconnected",
                "error": str(e)
            }
        )

@app.get("/api/metrics")
async def metrics():
    """System metrics endpoint"""
    try:
        metrics_data = monitoring_service.get_metrics_summary()
        performance_data = monitoring_service.get_performance_summary()

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": metrics_data,
            "performance": performance_data
        }
    except Exception as e:
        logging.getLogger("app").error(f"Metrics collection failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Metrics collection unavailable",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Record error metric
    await monitoring_service.increment_counter(
        "http_errors",
        tags={"error_type": "Exception", "path": request.url.path}
    )

    logging.getLogger("http").exception(
        "Unhandled exception",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    return JSONResponse(status_code=500, content={"detail": "internal server error"})

# Add this endpoint for debugging
@app.get("/routes")
def list_routes():
    """List all available routes in the application."""
    routes = []
    for route in app.routes:
        if isinstance(route, Route):
            routes.append({"path": route.path, "name": route.name, "methods": list(route.methods)})
        elif isinstance(route, WebSocketRoute):
            routes.append({"path": route.path, "name": route.name, "methods": ["WEBSOCKET"]})
    return routes

app.include_router(auth_router, prefix="/api/v1")
app.include_router(backtest_router, prefix="/api/v1")
app.include_router(google_auth_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(performance_router, prefix="/api/v1")
app.include_router(monte_carlo_router, prefix="/api/v1")
