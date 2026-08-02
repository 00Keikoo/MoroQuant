"""
Tests for Liquidity Models
"""

import pytest
from datetime import datetime

from ml_service.simulation.execution.liquidity import (
    ILiquidityModel,
    InfiniteLiquidityModel,
)
from ml_service.simulation.models import MarketSnapshot


def create_test_snapshot():
    """Helper to create test snapshot"""
    return MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        symbol="BTCUSDT",
        mid_price=50000.0,
        bid=49995.0,
        ask=50005.0,
        spread=10.0,
        volume=1000.0,
    )


def test_infinite_liquidity_model_creation():
    """Test InfiniteLiquidityModel creation"""
    model = InfiniteLiquidityModel()
    assert model is not None


def test_infinite_liquidity_returns_infinite():
    """Test InfiniteLiquidityModel returns infinite volume"""
    model = InfiniteLiquidityModel()
    snapshot = create_test_snapshot()

    volume = model.get_available_volume(price=50000.0, snapshot=snapshot)

    assert volume == float('inf')


def test_infinite_liquidity_different_prices():
    """Test InfiniteLiquidityModel returns infinite for any price"""
    model = InfiniteLiquidityModel()
    snapshot = create_test_snapshot()

    volume_low = model.get_available_volume(price=10000.0, snapshot=snapshot)
    volume_high = model.get_available_volume(price=100000.0, snapshot=snapshot)

    assert volume_low == float('inf')
    assert volume_high == float('inf')


def test_iliquidity_model_is_abstract():
    """Test ILiquidityModel cannot be instantiated"""
    with pytest.raises(TypeError):
        ILiquidityModel()
