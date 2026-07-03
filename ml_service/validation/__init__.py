"""Execution Validation Suite.

Internal validation framework ensuring every execution metric
recorded by MoroQuant is mathematically correct and internally consistent.
"""

from .execution_validator import validate_all_positions, validate_position
from .execution_report import ValidationReport

__all__ = ["validate_all_positions", "validate_position", "ValidationReport"]
