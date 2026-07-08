"""Trade Explorer API response schemas.

Pydantic models for OpenAPI documentation and runtime validation.
"""

from typing import List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field


class TradeResponse(BaseModel):
    """Single trade position response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Trade position ID")
    symbol: str = Field(..., description="Trading pair symbol")
    direction: str = Field(..., description="Trade direction (LONG or SHORT)")
    entry_price: float = Field(..., description="Entry price")
    current_price: Optional[float] = Field(None, description="Current market price")
    size_usdt: float = Field(..., description="Position size in USDT")
    qty: float = Field(..., description="Position quantity in base asset")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    signal_id: Optional[int] = Field(None, description="Linked signal ID")
    status: str = Field(..., description="Trade status (OPEN or CLOSED)")
    realized_pnl: float = Field(..., description="Realized profit/loss")
    opened_at: str = Field(..., description="Trade open timestamp")
    closed_at: Optional[str] = Field(None, description="Trade close timestamp")
    confidence: Optional[int] = Field(None, description="Signal confidence (0-100)")
    regime: Optional[str] = Field(None, description="Market regime")
    timeframe: Optional[str] = Field(None, description="Signal timeframe")


class SignalResponse(BaseModel):
    """Signal linked to a trade."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Signal ID")
    symbol: str = Field(..., description="Trading pair symbol")
    timeframe: str = Field(..., description="Signal timeframe")
    timestamp: int = Field(..., description="Signal generation timestamp")
    direction: str = Field(..., description="Signal direction (LONG or SHORT)")
    confidence: int = Field(..., ge=0, le=100, description="Signal confidence (0-100)")


class TradeDetailResponse(BaseModel):
    """Trade detail with optional linked signal."""

    trade: TradeResponse = Field(..., description="Trade position")
    signal: Optional[SignalResponse] = Field(None, description="Linked signal if available")


class TradeListResponse(BaseModel):
    """Paginated list of trades."""

    trades: List[TradeResponse] = Field(..., description="List of trade positions")
    total: int = Field(..., ge=0, description="Total matching trades")
    limit: int = Field(..., ge=1, description="Results per page")
    offset: int = Field(..., ge=0, description="Results skipped")


class SummaryResponse(BaseModel):
    """Trade analytics summary."""

    total_trades: int = Field(..., ge=0, description="Total number of trades")
    winning_trades: int = Field(..., ge=0, description="Number of profitable trades")
    losing_trades: int = Field(..., ge=0, description="Number of losing trades")
    win_rate: float = Field(..., ge=0, le=1, description="Win rate (0-1)")
    gross_profit: float = Field(..., description="Total profit from winning trades")
    gross_loss: float = Field(..., description="Total loss from losing trades")
    net_profit: float = Field(..., description="Net profit/loss")
    average_profit: float = Field(..., description="Average profit per winning trade")
    average_loss: float = Field(..., description="Average loss per losing trade")
    average_hold_duration_seconds: float = Field(..., ge=0, description="Average hold time in seconds")
    average_trade_duration_seconds: float = Field(..., ge=0, description="Average trade duration in seconds")
    largest_win: float = Field(..., description="Largest single win")
    largest_loss: float = Field(..., description="Largest single loss")
    long_count: int = Field(..., ge=0, description="Number of long trades")
    short_count: int = Field(..., ge=0, description="Number of short trades")
    open_count: int = Field(..., ge=0, description="Number of open trades")
    closed_count: int = Field(..., ge=0, description="Number of closed trades")


class MetadataResponse(BaseModel):
    """Available filter values."""

    symbols: Set[str] = Field(..., description="Available trading symbols")
    directions: Set[str] = Field(..., description="Available trade directions")
    statuses: Set[str] = Field(..., description="Available trade statuses")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., ge=400, lt=600, description="HTTP status code")
