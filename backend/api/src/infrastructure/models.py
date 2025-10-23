import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db import Base


# -----------------------------------------
# User
# -----------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=True
    )  # Made nullable for Cognito users
    cognito_sub: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )  # Cognito user ID
    name: Mapped[str] = mapped_column(String(255), nullable=True)  # User's display name
    auth_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="email"
    )  # "email", "google", "mixed"
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    strategies: Mapped[list["Strategy"]] = relationship(back_populates="owner")
    backtest_histories: Mapped[list["BacktestHistory"]] = relationship(
        back_populates="user"
    )


# -----------------------------------------
# Strategy
# -----------------------------------------
class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    params: Mapped[str] = mapped_column(String(1000), nullable=True)

    owner: Mapped[User] = relationship(back_populates="strategies")
    backtests: Mapped[list["Backtest"]] = relationship(back_populates="strategy")


# -----------------------------------------
# Backtest
# -----------------------------------------
class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id"), nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    strategy: Mapped[Strategy] = relationship(back_populates="backtests")


# -----------------------------------------
# Job (Monte Carlo Queue System)
# -----------------------------------------
class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("dedup_key", name="uq_job_dedup_key"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    worker_id: Mapped[str] = mapped_column(String(100), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    artifact_url: Mapped[str] = mapped_column(String(500), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)

    # Job timing fields for duration tracking
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# -----------------------------------------
# BacktestHistory (for user backtest tracking)
# -----------------------------------------
class BacktestHistory(Base):
    __tablename__ = "backtest_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # Backtest parameters
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    start_date: Mapped[str] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str] = mapped_column(String(50), nullable=True)
    initial_capital: Mapped[float] = mapped_column(
        Float, nullable=False, default=10000.0
    )

    # Monte Carlo parameters
    monte_carlo_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    monte_carlo_method: Mapped[str] = mapped_column(String(50), nullable=True)
    sample_fraction: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_scale: Mapped[float] = mapped_column(Float, nullable=True)

    # Data source information
    datasets_used: Mapped[dict] = mapped_column(JSON, nullable=True)
    price_type: Mapped[str] = mapped_column(String(20), nullable=False, default="close")

    # Results summary
    total_return: Mapped[float] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=True)
    win_rate: Mapped[float] = mapped_column(Float, nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=True)

    # Execution metadata
    execution_time_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="backtest_histories")
