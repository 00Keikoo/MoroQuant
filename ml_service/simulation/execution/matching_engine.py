"""
Matching Engine

Pure functional matching engine for order execution simulation.
Supports MARKET orders with validation and lifecycle transitions.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional

from ml_service.simulation.execution.execution_models import (
    ExecutionOrder,
    ExecutionFill,
    ExecutionReport,
    ExecutionLifecycle,
    OrderType,
    FillPolicy,
)
from ml_service.simulation.execution.slippage import ISlippageModel
from ml_service.simulation.execution.commission import ICommissionModel
from ml_service.simulation.execution.latency import ILatencyModel
from ml_service.simulation.execution.liquidity import ILiquidityModel
from ml_service.simulation.models import MarketSnapshot
from ml_service.simulation.interfaces import IExecutionContext


class IMatchingEngine(ABC):
    """Interface for matching engine implementations"""

    @abstractmethod
    def validate_order(self, order: ExecutionOrder) -> Optional[str]:
        """Validate order parameters. Returns rejection reason if invalid, None if valid."""
        pass

    @abstractmethod
    def execute_order(
        self,
        order: ExecutionOrder,
        snapshot: MarketSnapshot,
        context: IExecutionContext,
    ) -> ExecutionReport:
        """Execute order against market snapshot. Returns ExecutionReport with fills and updated status."""
        pass


class MatchingEngine(IMatchingEngine):
    """
    Pure functional matching engine for order execution.

    Supports BUY/SELL MARKET orders with configurable friction models.
    """

    def __init__(
        self,
        slippage_model: ISlippageModel,
        commission_model: ICommissionModel,
        latency_model: ILatencyModel,
        liquidity_model: ILiquidityModel,
    ):
        self.slippage_model = slippage_model
        self.commission_model = commission_model
        self.latency_model = latency_model
        self.liquidity_model = liquidity_model

    def validate_order(self, order: ExecutionOrder) -> Optional[str]:
        """
        Validate order parameters.

        Returns rejection reason if invalid, None if valid.
        """
        if order.request.quantity <= 0:
            return "Quantity must be positive"

        if not order.request.symbol:
            return "Symbol is required"

        if order.request.side not in ["BUY", "SELL"]:
            return "Side must be BUY or SELL"

        if order.request.order_type not in [OrderType.MARKET]:
            return f"Order type {order.request.order_type} not supported (only MARKET)"

        return None

    def execute_order(
        self,
        order: ExecutionOrder,
        snapshot: MarketSnapshot,
        context: IExecutionContext,
    ) -> ExecutionReport:
        """
        Execute order against market snapshot.

        Returns ExecutionReport with fills and updated status.
        """
        rejection_reason = self.validate_order(order)
        if rejection_reason:
            return ExecutionReport(
                order_id=order.order_id,
                status=ExecutionLifecycle.REJECTED,
                emitted_fills=[],
                remaining_quantity=order.request.quantity,
                rejection_reason=rejection_reason,
                timestamp=context.get_current_time(),
            )

        if order.request.order_type == OrderType.MARKET:
            return self._execute_market_order(order, snapshot, context)

        return ExecutionReport(
            order_id=order.order_id,
            status=ExecutionLifecycle.REJECTED,
            emitted_fills=[],
            remaining_quantity=order.request.quantity,
            rejection_reason=f"Order type {order.request.order_type} not implemented",
            timestamp=context.get_current_time(),
        )

    def _execute_market_order(
        self,
        order: ExecutionOrder,
        snapshot: MarketSnapshot,
        context: IExecutionContext,
    ) -> ExecutionReport:
        """Execute MARKET order immediately at current price plus slippage"""

        base_price = self._get_execution_price(order, snapshot)
        slippage = self.slippage_model.calculate_slippage(order, snapshot)

        if order.request.side == "BUY":
            execution_price = base_price + slippage
        else:
            execution_price = base_price - slippage

        available_volume = self.liquidity_model.get_available_volume(
            execution_price, snapshot
        )

        if available_volume < order.request.quantity:
            if order.request.fill_policy == FillPolicy.REJECT:
                return ExecutionReport(
                    order_id=order.order_id,
                    status=ExecutionLifecycle.REJECTED,
                    emitted_fills=[],
                    remaining_quantity=order.request.quantity,
                    rejection_reason="Insufficient liquidity",
                    timestamp=context.get_current_time(),
                )
            filled_quantity = available_volume
        else:
            filled_quantity = order.request.quantity

        is_maker = False
        commission = self.commission_model.calculate_commission(
            filled_quantity, execution_price, is_maker
        )

        latency_ms = self.latency_model.get_latency_ms()
        executed_at = snapshot.timestamp + timedelta(milliseconds=latency_ms)

        fill = ExecutionFill(
            fill_id=self._generate_fill_id(order.order_id, executed_at),
            order_id=order.order_id,
            symbol=order.request.symbol,
            side=order.request.side,
            quantity=filled_quantity,
            price=execution_price,
            commission=commission,
            slippage=slippage,
            executed_at=executed_at,
        )

        remaining_quantity = order.request.quantity - filled_quantity

        if remaining_quantity > 0:
            status = ExecutionLifecycle.PARTIALLY_FILLED
        else:
            status = ExecutionLifecycle.FILLED

        return ExecutionReport(
            order_id=order.order_id,
            status=status,
            emitted_fills=[fill],
            remaining_quantity=remaining_quantity,
            rejection_reason=None,
            timestamp=context.get_current_time(),
        )

    def _get_execution_price(
        self, order: ExecutionOrder, snapshot: MarketSnapshot
    ) -> float:
        """Get base execution price before slippage"""
        if order.request.side == "BUY":
            return snapshot.ask if snapshot.ask else snapshot.mid_price
        else:
            return snapshot.bid if snapshot.bid else snapshot.mid_price

    def _generate_fill_id(self, order_id: str, executed_at: datetime) -> str:
        """Generate deterministic fill ID from order_id and timestamp"""
        import hashlib
        data = f"{order_id}:{executed_at.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
