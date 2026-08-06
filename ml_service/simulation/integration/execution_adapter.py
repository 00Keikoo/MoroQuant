"""
Execution Adapter

Converts simulation orders to execution requests and calls the execution simulator.
Returns fills for portfolio processing.
"""

from typing import Optional

from ml_service.simulation.execution.execution_models import ExecutionFill, ExecutionReport
from ml_service.simulation.execution.simulator import ExecutionSimulator
from ml_service.simulation.interfaces import IExecutionContext
from ml_service.simulation.models import Order, MarketSnapshot


class ExecutionAdapter:
    """
    Adapter connecting simulation orders to execution simulator.

    Responsibilities:
    - Convert simulation Order to execution format
    - Call ExecutionSimulator with market context
    - Return ExecutionFill events
    - Handle execution failures gracefully
    """

    def __init__(self, execution_simulator: ExecutionSimulator):
        self.execution_simulator = execution_simulator

    def execute_order(
        self,
        order: Order,
        market_snapshot: MarketSnapshot,
        context: IExecutionContext,
    ) -> Optional[ExecutionFill]:
        """
        Execute an order using the execution simulator.

        Args:
            order: Simulation order to execute
            market_snapshot: Current market state
            context: Execution context with market data

        Returns:
            ExecutionFill if successful, None if execution failed
        """
        result = self.execution_simulator.simulate_execution(order, context)

        if result.is_fully_filled():
            report = result._report
            if report.emitted_fills:
                return report.emitted_fills[0]

        return None
