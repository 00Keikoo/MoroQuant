"""
Execution Simulator

Pure functional execution simulator that orchestrates order matching and fill generation.
Implements IExecutionSimulator interface for use by the Simulation Orchestrator.
"""

from datetime import datetime
from typing import Optional

from ml_service.simulation.execution.execution_models import (
    ExecutionRequest,
    ExecutionOrder,
    ExecutionFill,
    ExecutionReport,
    ExecutionLifecycle,
)
from ml_service.simulation.execution.matching_engine import IMatchingEngine
from ml_service.simulation.interfaces import (
    IExecutionSimulator,
    IExecutionContext,
    IExecutionResult,
)
from ml_service.simulation.models import Order


class ExecutionResult(IExecutionResult):
    """Execution result implementation"""

    def __init__(self, report: ExecutionReport, fills: list[ExecutionFill]):
        self._report = report
        self._fills = fills

    def get_filled_quantity(self) -> float:
        return sum(fill.quantity for fill in self._fills)

    def get_average_price(self) -> float:
        if not self._fills:
            return 0.0
        total_value = sum(fill.quantity * fill.price for fill in self._fills)
        total_quantity = sum(fill.quantity for fill in self._fills)
        return total_value / total_quantity if total_quantity > 0 else 0.0

    def get_total_fees(self) -> float:
        return sum(fill.commission for fill in self._fills)

    def get_slippage(self) -> float:
        return sum(fill.slippage * fill.quantity for fill in self._fills)

    def is_fully_filled(self) -> bool:
        return self._report.status == ExecutionLifecycle.FILLED


class ExecutionSimulator(IExecutionSimulator):
    """
    Pure functional execution simulator.

    Orchestrates matching engine and friction models for deterministic order execution.
    """

    def __init__(
        self,
        matching_engine: IMatchingEngine,
    ):
        self.matching_engine = matching_engine

    def simulate_execution(
        self,
        order: Order,
        context: IExecutionContext,
    ) -> IExecutionResult:
        """
        Simulate order execution in given market context.

        Returns IExecutionResult with fills and execution metrics.
        """
        snapshot = context.get_market_snapshot(order.symbol)
        if not snapshot:
            return ExecutionResult(
                ExecutionReport(
                    order_id=order.order_id,
                    status=ExecutionLifecycle.REJECTED,
                    emitted_fills=[],
                    remaining_quantity=order.quantity,
                    rejection_reason=f"No market data for {order.symbol}",
                    timestamp=context.get_current_time(),
                ),
                [],
            )

        execution_request = self._order_to_execution_request(order)
        execution_order = self._create_execution_order(order, execution_request, context)

        report = self.matching_engine.execute_order(execution_order, snapshot, context)

        return ExecutionResult(report, report.emitted_fills)

    def estimate_fill_price(
        self,
        order: Order,
        context: IExecutionContext,
    ) -> float:
        """Estimate likely fill price for order"""
        snapshot = context.get_market_snapshot(order.symbol)
        if not snapshot:
            return 0.0

        execution_request = self._order_to_execution_request(order)
        execution_order = self._create_execution_order(order, execution_request, context)

        slippage = self.matching_engine.slippage_model.calculate_slippage(
            execution_order, snapshot
        )

        if order.side.value == "BUY":
            base_price = snapshot.ask if snapshot.ask else snapshot.mid_price
            return base_price + slippage
        else:
            base_price = snapshot.bid if snapshot.bid else snapshot.mid_price
            return base_price - slippage

    def estimate_slippage(
        self,
        order: Order,
        context: IExecutionContext,
    ) -> float:
        """Estimate slippage for order"""
        snapshot = context.get_market_snapshot(order.symbol)
        if not snapshot:
            return 0.0

        execution_request = self._order_to_execution_request(order)
        execution_order = self._create_execution_order(order, execution_request, context)

        return self.matching_engine.slippage_model.calculate_slippage(
            execution_order, snapshot
        )

    def _order_to_execution_request(self, order: Order) -> ExecutionRequest:
        """Convert Order to ExecutionRequest"""
        from ml_service.simulation.execution.execution_models import (
            OrderType,
            ExecutionPolicy,
            FillPolicy,
        )

        order_type_map = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP": OrderType.STOP,
        }

        return ExecutionRequest(
            symbol=order.symbol,
            side=order.side.value,
            order_type=order_type_map.get(order.order_type.value, OrderType.MARKET),
            quantity=order.quantity,
            price=order.price,
            execution_policy=ExecutionPolicy.GTC,
            fill_policy=FillPolicy.FULL_FILL,
            requested_at=order.created_at,
        )

    def _create_execution_order(
        self, order: Order, request: ExecutionRequest, context: IExecutionContext
    ) -> ExecutionOrder:
        """Create ExecutionOrder from Order and ExecutionRequest"""
        return ExecutionOrder(
            order_id=order.order_id,
            request=request,
            status=ExecutionLifecycle.VALIDATED,
            cumulative_filled_qty=0.0,
            average_filled_price=0.0,
            active_price=None,
            created_at=order.created_at,
            updated_at=context.get_current_time(),
        )
