from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Float
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
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    strategies: Mapped[list["Strategy"]] = relationship(back_populates="owner")


# -----------------------------------------
# Strategy
# -----------------------------------------
class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ex: "MovingAverage", "RSIReversion"
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Paramètres spécifiques à la stratégie (JSON pour flexibilité)
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
