"""
Tests for Latency Models
"""

import pytest

from ml_service.simulation.execution.latency import (
    ILatencyModel,
    ZeroLatencyModel,
)


def test_zero_latency_model_creation():
    """Test ZeroLatencyModel creation"""
    model = ZeroLatencyModel()
    assert model is not None


def test_zero_latency_returns_zero():
    """Test ZeroLatencyModel returns zero latency"""
    model = ZeroLatencyModel()
    latency = model.get_latency_ms()
    assert latency == 0


def test_ilatency_model_is_abstract():
    """Test ILatencyModel cannot be instantiated"""
    with pytest.raises(TypeError):
        ILatencyModel()
