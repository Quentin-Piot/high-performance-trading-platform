from pydantic import BaseModel
from typing import List

class BacktestResponse(BaseModel):
    timestamps: List[str]
    equity_curve: List[float]
    pnl: float
    drawdown: float
    sharpe: float
