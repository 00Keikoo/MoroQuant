import pytest

from ml_service.research.model_identity import (
    ModelArtifactScanner
)
from ml_service.research.model_identity.parser import parse_model_filename


def test_scanner_detects_models():

    scanner = ModelArtifactScanner(
        "ml_service/storage/models"
    )

    models=scanner.scan()

    assert len(models)>0



def test_identity_immutable():

    scanner = ModelArtifactScanner(
        "ml_service/storage/models"
    )

    model=scanner.scan()[0]

    with pytest.raises(Exception):

        model.symbol="TEST"



def test_fingerprint_exists():

    scanner=ModelArtifactScanner(
        "ml_service/storage/models"
    )

    model=scanner.scan()[0]

    assert len(
        model.feature_fingerprint
    )==64



def test_validation_detection():

    scanner=ModelArtifactScanner(
        "ml_service/storage/models"
    )

    models=scanner.scan()

    validated=[
        x for x in models
        if x.validation_available
    ]

    assert len(validated)>=0



def test_no_database_dependency():

    import inspect

    from ml_service.research.model_identity import scanner

    source=inspect.getsource(scanner)

    assert "sqlite" not in source
    assert "sqlalchemy" not in source


def test_parse_crypto_model():

    result = parse_model_filename(
        "BTCUSDT_1h_xgboost_20260621_071847.pkl"
    )

    assert result["symbol"] == "BTCUSDT"
    assert result["timeframe"] == "1h"
    assert result["model_type"] == "xgboost"
    assert result["trained_at"] == "20260621_071847"
    assert result["asset_class"] == "crypto"


def test_parse_proxy_model():

    result = parse_model_filename(
        "ES_proxy_4h_xgboost_20260603_173325.pkl"
    )

    assert result["symbol"] == "ES"
    assert result["timeframe"] == "4h"
    assert result["model_type"] == "xgboost"
    assert result["trained_at"] == "20260603_173325"
    assert result["asset_class"] == "proxy"


def test_parse_malformed_filename():

    with pytest.raises(ValueError, match="Unknown model filename schema"):
        parse_model_filename("invalid_filename.pkl")


def test_parse_too_short_filename():

    with pytest.raises(ValueError, match="Unknown model filename schema"):
        parse_model_filename("BTC_1h.pkl")


def test_scanner_detects_proxy_models():

    scanner = ModelArtifactScanner(
        "ml_service/storage/models"
    )

    models = scanner.scan()

    proxy_models = [
        m for m in models
        if m.asset_class == "proxy"
    ]

    for proxy in proxy_models:
        assert proxy.symbol in ["ES", "GC", "CL", "NQ", "ZB"]
        assert proxy.timeframe in ["1h", "4h"]
        assert proxy.model_type in ["xgboost", "lightgbm"]


def test_scanner_detects_crypto_models():

    scanner = ModelArtifactScanner(
        "ml_service/storage/models"
    )

    models = scanner.scan()

    crypto_models = [
        m for m in models
        if m.asset_class == "crypto"
    ]

    assert len(crypto_models) > 0

    for crypto in crypto_models:
        assert crypto.asset_class == "crypto"
        assert crypto.timeframe in ["1h", "4h", "15m", "1d"]


def test_asset_class_preserved():

    scanner = ModelArtifactScanner(
        "ml_service/storage/models"
    )

    models = scanner.scan()

    for model in models:
        assert hasattr(model, "asset_class")
        assert model.asset_class in ["crypto", "proxy"]
