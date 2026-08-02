"""
Latency Models

Abstract interface and concrete implementations for simulating execution latency.
All models are pure functions with no side effects.
"""

from abc import ABC, abstractmethod


class ILatencyModel(ABC):
    """Interface for latency calculation"""

    @abstractmethod
    def get_latency_ms(self) -> int:
        """Get execution latency in milliseconds"""
        pass


class ZeroLatencyModel(ILatencyModel):
    """Zero latency model for instant execution"""

    def get_latency_ms(self) -> int:
        """Return zero latency for instant execution"""
        return 0
