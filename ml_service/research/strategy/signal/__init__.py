"""Signal Generation Layer - Sprint 3.9C-1

Defines contracts for mapping ML predictions to trading signals.
"""

from ml_service.research.strategy.signal.interfaces import SignalGenerator
from ml_service.research.strategy.signal.generator import DefaultSignalGenerator

__all__ = [
    "SignalGenerator",
    "DefaultSignalGenerator",
]
