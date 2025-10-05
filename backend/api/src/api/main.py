from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.auth import router as auth_router
from api.routers.backtest import router as backtest_router
from infrastructure.db import init_db


app = FastAPI(title="Trading Backtest API", version="0.1.0")

# CORS for local frontend development (Vite/Next/Vue CLI, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend origin in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
async def root():
    return {"message": "OK", "service": "Trading Backtest API"}


app.include_router(auth_router)
app.include_router(backtest_router)
