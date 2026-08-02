"""
Tests for Commission Models
"""

import pytest

from ml_service.simulation.execution.commission import (
    ICommissionModel,
    BinanceSpotCommission,
    BinanceFuturesCommission,
)


def test_binance_spot_commission_creation():
    """Test BinanceSpotCommission creation"""
    model = BinanceSpotCommission(fee_pct=0.1)
    assert model.fee_pct == 0.1


def test_binance_spot_commission_default_fee():
    """Test BinanceSpotCommission default fee"""
    model = BinanceSpotCommission()
    assert model.fee_pct == 0.1


def test_binance_spot_commission_negative_fee():
    """Test BinanceSpotCommission rejects negative fee"""
    with pytest.raises(ValueError, match="fee_pct must be non-negative"):
        BinanceSpotCommission(fee_pct=-0.1)


def test_binance_spot_commission_calculation():
    """Test Binance Spot commission calculation"""
    model = BinanceSpotCommission(fee_pct=0.1)

    commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=True)

    expected = 1.0 * 50000.0 * (0.1 / 100.0)
    assert commission == expected
    assert commission == 50.0


def test_binance_spot_commission_maker_taker_same():
    """Test Binance Spot commission is same for maker and taker"""
    model = BinanceSpotCommission(fee_pct=0.1)

    maker_commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=True)
    taker_commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=False)

    assert maker_commission == taker_commission


def test_binance_futures_commission_creation():
    """Test BinanceFuturesCommission creation"""
    model = BinanceFuturesCommission(maker_fee_pct=0.02, taker_fee_pct=0.04)
    assert model.maker_fee_pct == 0.02
    assert model.taker_fee_pct == 0.04


def test_binance_futures_commission_default_fees():
    """Test BinanceFuturesCommission default fees"""
    model = BinanceFuturesCommission()
    assert model.maker_fee_pct == 0.02
    assert model.taker_fee_pct == 0.04


def test_binance_futures_commission_negative_fees():
    """Test BinanceFuturesCommission rejects negative fees"""
    with pytest.raises(ValueError, match="fee percentages must be non-negative"):
        BinanceFuturesCommission(maker_fee_pct=-0.02, taker_fee_pct=0.04)

    with pytest.raises(ValueError, match="fee percentages must be non-negative"):
        BinanceFuturesCommission(maker_fee_pct=0.02, taker_fee_pct=-0.04)


def test_binance_futures_commission_maker():
    """Test Binance Futures maker commission calculation"""
    model = BinanceFuturesCommission(maker_fee_pct=0.02, taker_fee_pct=0.04)

    commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=True)

    expected = 1.0 * 50000.0 * (0.02 / 100.0)
    assert commission == expected
    assert commission == 10.0


def test_binance_futures_commission_taker():
    """Test Binance Futures taker commission calculation"""
    model = BinanceFuturesCommission(maker_fee_pct=0.02, taker_fee_pct=0.04)

    commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=False)

    expected = 1.0 * 50000.0 * (0.04 / 100.0)
    assert commission == expected
    assert commission == 20.0


def test_binance_futures_maker_cheaper_than_taker():
    """Test maker fee is cheaper than taker fee"""
    model = BinanceFuturesCommission(maker_fee_pct=0.02, taker_fee_pct=0.04)

    maker_commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=True)
    taker_commission = model.calculate_commission(quantity=1.0, price=50000.0, is_maker=False)

    assert maker_commission < taker_commission


def test_icommission_model_is_abstract():
    """Test ICommissionModel cannot be instantiated"""
    with pytest.raises(TypeError):
        ICommissionModel()
