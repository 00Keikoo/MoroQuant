"""Trade Explorer REST API routes.

Read-only endpoints for trade list, detail, summary, and metadata.
All business logic delegated to ExplorerQueryService.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ml_service.api.schemas import (
    TradeResponse,
    SignalResponse,
    TradeDetailResponse,
    TradeListResponse,
    MetadataResponse,
    SummaryResponse
)
from ml_service.services.explorer_query_service import (
    ExplorerQueryService,
    TradeListResult,
    TradeWithSignal,
    MetadataResult
)
from ml_service.repositories.trade_repository import TradeRepository, TradePosition
from ml_service.repositories.signal_repository import SignalRepository, Signal
from ml_service.repositories.equity_repository import EquityRepository
from ml_service.analytics import TradeAnalyticsResult

router = APIRouter(prefix="/api/v1/explorer", tags=["Trade Explorer"])


def get_explorer_service() -> ExplorerQueryService:
    """Dependency injection for ExplorerQueryService."""
    trade_repo = TradeRepository()
    signal_repo = SignalRepository()
    equity_repo = EquityRepository()
    return ExplorerQueryService(trade_repo, signal_repo, equity_repo)


@router.get("/trades", response_model=TradeListResponse)
async def get_trades(
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    direction: Optional[str] = Query(None, description="Filter by direction"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    sort_by: str = Query("opened_at", description="Column to sort by"),
    sort_order: str = Query("DESC", description="Sort order (ASC or DESC)"),
    service: ExplorerQueryService = Depends(get_explorer_service)
) -> TradeListResponse:
    """Query trades with filtering, pagination, and sorting."""
    result = service.get_trade_list(
        status=status,
        symbol=symbol,
        direction=direction,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return TradeListResponse(
        trades=[TradeResponse.model_validate(t) for t in result.trades],
        total=result.total,
        limit=result.limit,
        offset=result.offset
    )


@router.get("/trades/{trade_id}", response_model=TradeDetailResponse)
async def get_trade_detail(
    trade_id: int,
    service: ExplorerQueryService = Depends(get_explorer_service)
) -> TradeDetailResponse:
    """Get trade detail with linked signal."""
    result = service.get_trade_detail(trade_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    signal_response = None
    if result.signal:
        signal_response = SignalResponse(
            id=result.signal.id,
            symbol=result.signal.symbol,
            timeframe=result.signal.timeframe,
            timestamp=result.signal.timestamp,
            direction=result.signal.direction,
            confidence=result.signal.confidence
        )

    return TradeDetailResponse(
        trade=TradeResponse.model_validate(result.trade),
        signal=signal_response
    )


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    service: ExplorerQueryService = Depends(get_explorer_service)
) -> SummaryResponse:
    """Get trade analytics summary."""
    analytics = service.get_summary()

    return SummaryResponse(
        total_trades=analytics.total_trades,
        winning_trades=analytics.winning_trades,
        losing_trades=analytics.losing_trades,
        win_rate=analytics.win_rate,
        gross_profit=analytics.gross_profit,
        gross_loss=analytics.gross_loss,
        net_profit=analytics.net_profit,
        average_profit=analytics.average_profit,
        average_loss=analytics.average_loss,
        average_hold_duration_seconds=analytics.average_hold_duration_seconds,
        average_trade_duration_seconds=analytics.average_trade_duration_seconds,
        largest_win=analytics.largest_win,
        largest_loss=analytics.largest_loss,
        long_count=analytics.long_count,
        short_count=analytics.short_count,
        open_count=analytics.open_count,
        closed_count=analytics.closed_count
    )


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata(
    service: ExplorerQueryService = Depends(get_explorer_service)
) -> MetadataResponse:
    """Get available filter values."""
    metadata = service.get_metadata()

    return MetadataResponse(
        symbols=metadata.symbols,
        directions=metadata.directions,
        statuses=metadata.statuses
    )
