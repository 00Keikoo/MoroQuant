"""Types for execution parity checking."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FilterCheckResult:
    """Result of a single execution filter check."""
    name: str
    passed: bool
    reason: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class ExecutionParityResult:
    """Result of execution parity check for a signal."""
    execution_allowed: bool
    block_reason: Optional[str]
    passed_filters: List[str]
    failed_filter: Optional[FilterCheckResult] = None
    position_size: Optional[float] = None
    sizing_multiplier: float = 1.0
    risk_check_result: Optional[dict] = None
    regime_check_result: Optional[dict] = None
