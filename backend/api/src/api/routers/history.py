"""
FastAPI router for backtest history management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.simple_auth import SimpleUser, get_current_user_simple
from domain.schemas.history import (
    BacktestHistoryList,
    BacktestHistoryResponse,
    BacktestHistoryUpdate,
    BacktestRerunRequest,
    UserStatsResponse,
)
from infrastructure.db import get_session
from infrastructure.repositories.backtest_history_repository import (
    BacktestHistoryRepository,
)
from infrastructure.repositories.user_repository import UserRepository

router = APIRouter(prefix="/history", tags=["backtest-history"])
async def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    """Dependency to get user repository."""
    return UserRepository(session)
async def get_history_repo(
    session: AsyncSession = Depends(get_session),
) -> BacktestHistoryRepository:
    """Dependency to get backtest history repository."""
    return BacktestHistoryRepository(session)
@router.get("/", response_model=BacktestHistoryList)
async def get_user_history(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    strategy: str | None = Query(None, description="Filter by strategy"),
    current_user: SimpleUser = Depends(get_current_user_simple),
    user_repo: UserRepository = Depends(get_user_repo),
    history_repo: BacktestHistoryRepository = Depends(get_history_repo),
):
    """Get user's backtest history with pagination."""
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    offset = (page - 1) * per_page
    items = await history_repo.get_user_history(
        user_id=user.id,
        limit=per_page + 1,
        offset=offset,
        strategy_filter=strategy,
    )
    has_next = len(items) > per_page
    if has_next:
        items = items[:-1]
    has_prev = page > 1
    response_items = [BacktestHistoryResponse.model_validate(item) for item in items]
    return BacktestHistoryList(
        items=response_items,
        total=len(
            response_items
        ),
        page=page,
        per_page=per_page,
        has_next=has_next,
        has_prev=has_prev,
    )
@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: SimpleUser = Depends(get_current_user_simple),
    user_repo: UserRepository = Depends(get_user_repo),
    history_repo: BacktestHistoryRepository = Depends(get_history_repo),
):
    """Get user's backtest statistics."""
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    stats = await history_repo.get_user_stats(user.id)
    return UserStatsResponse(**stats)
@router.get("/{history_id}", response_model=BacktestHistoryResponse)
async def get_history_detail(
    history_id: int,
    current_user: SimpleUser = Depends(get_current_user_simple),
    user_repo: UserRepository = Depends(get_user_repo),
    history_repo: BacktestHistoryRepository = Depends(get_history_repo),
):
    """Get detailed information about a specific backtest."""
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    history = await history_repo.get_by_id(history_id, user_id=user.id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backtest history not found"
        )
    return BacktestHistoryResponse.model_validate(history)
@router.put("/{history_id}/results", response_model=BacktestHistoryResponse)
async def update_backtest_results(
    history_id: int,
    results: BacktestHistoryUpdate,
    current_user: SimpleUser = Depends(get_current_user_simple),
    user_repo: UserRepository = Depends(get_user_repo),
    history_repo: BacktestHistoryRepository = Depends(get_history_repo),
):
    """Update backtest results (typically called by the system after completion)."""
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    updated_history = await history_repo.update_results(
        history_id=history_id, **results.model_dump(exclude_unset=True)
    )
    if not updated_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backtest history not found"
        )
    if updated_history.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this backtest",
        )
    return BacktestHistoryResponse.model_validate(updated_history)
@router.delete("/{history_id}")
async def delete_history(
    history_id: int,
    current_user: SimpleUser = Depends(get_current_user_simple),
    user_repo: UserRepository = Depends(get_user_repo),
    history_repo: BacktestHistoryRepository = Depends(get_history_repo),
):
    """Delete a backtest history entry."""
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    deleted = await history_repo.delete_history(history_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backtest history not found"
        )
    return {"message": "Backtest history deleted successfully"}
@router.post("/rerun")
async def rerun_backtest(
    rerun_request: BacktestRerunRequest,
    current_user: SimpleUser = Depends(get_current_user_simple),
    user_repo: UserRepository = Depends(get_user_repo),
    history_repo: BacktestHistoryRepository = Depends(get_history_repo),
):
    """Rerun a backtest from history with optional parameter overrides."""
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    original_history = await history_repo.get_by_id(
        rerun_request.history_id, user_id=user.id
    )
    if not original_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original backtest history not found",
        )
    new_params = original_history.strategy_params.copy()
    if rerun_request.override_params:
        new_params.update(rerun_request.override_params)
    datasets = rerun_request.new_datasets or original_history.datasets_used
    start_date = original_history.start_date
    end_date = original_history.end_date
    if rerun_request.new_date_range:
        start_date = rerun_request.new_date_range.get("start_date", start_date)
        end_date = rerun_request.new_date_range.get("end_date", end_date)
    new_history = await history_repo.create_history_entry(
        user_id=user.id,
        strategy=original_history.strategy,
        strategy_params=new_params,
        start_date=start_date,
        end_date=end_date,
        initial_capital=original_history.initial_capital,
        monte_carlo_runs=original_history.monte_carlo_runs,
        monte_carlo_method=original_history.monte_carlo_method,
        sample_fraction=original_history.sample_fraction,
        gaussian_scale=original_history.gaussian_scale,
        datasets_used=datasets,
        price_type=original_history.price_type,
    )
    return {
        "message": "Backtest rerun initiated",
        "new_history_id": new_history.id,
        "status": "queued",
    }
