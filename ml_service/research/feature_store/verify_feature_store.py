"""Verification tests for Feature Store."""

import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

from ml_service.research.feature_store.service import FeatureService
from ml_service.research.feature_store.feature_types import FeatureLifecycleState
from ml_service.research.dataset_manager.service import DatasetService
from ml_service.research.dataset_manager.types import LifecycleState
from ml_service.research.snapshot_engine.types import Snapshot


def create_test_snapshot() -> Snapshot:
    """Create test snapshot with sample data."""
    signals = []
    timestamps = [1609459200 + i * 3600 for i in range(30)]

    for ts in timestamps:
        for symbol in ['BTCUSDT', 'ETHUSDT']:
            signals.append({
                'timestamp': ts,
                'symbol': symbol,
                'direction': 'long',
                'confidence': 0.7,
                'features_json': {
                    'close': 40000.0 + np.random.randn() * 100,
                    'volume': 1000.0 + np.random.randn() * 50
                }
            })

    return Snapshot(
        snapshot_id='snap_test_001',
        timestamp=datetime.utcnow().isoformat(),
        trades=[],
        signals=signals
    )


def compute_rsi_feature(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Compute RSI feature (simplified for testing)."""
    period = params['period']

    result = df[['timestamp', 'symbol']].copy()

    def calc_rsi(group):
        close = group['close'].reset_index(drop=True)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    rsi_values = []
    for symbol in df['symbol'].unique():
        symbol_data = df[df['symbol'] == symbol].copy()
        symbol_rsi = calc_rsi(symbol_data)
        rsi_values.extend(symbol_rsi.values)

    result['rsi'] = rsi_values

    return result


def test_feature_definition_registration():
    """Test 1: Feature definition creation."""
    print("\n=== Test 1: Feature Definition Registration ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        service = FeatureService(db_path=str(db_path), storage_dir=tmpdir)

        definition = service.register_definition(
            feature_name='rsi_14',
            description='Relative Strength Index with period 14',
            formula_ref='technical_indicators.compute_rsi'
        )

        assert definition.feature_name == 'rsi_14'
        assert 'Relative Strength Index' in definition.description

        retrieved = service.repository.find_definition('rsi_14')
        assert retrieved is not None
        assert retrieved.feature_name == 'rsi_14'

        print("✓ Feature definition registered successfully")


def test_feature_version_registration():
    """Test 2: Feature version creation."""
    print("\n=== Test 2: Feature Version Registration ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        service = FeatureService(db_path=str(db_path), storage_dir=tmpdir)

        service.register_definition(
            feature_name='rsi_14',
            description='RSI indicator',
            formula_ref='rsi'
        )

        version = service.register_version(
            feature_name='rsi_14',
            version='1.0.0',
            parameters={'period': 14, 'col': 'close'}
        )

        assert version.feature_version_id == 'rsi_14_v1.0.0'
        assert version.parameters['period'] == 14

        retrieved = service.repository.find_version('rsi_14_v1.0.0')
        assert retrieved is not None
        assert retrieved.parameters['period'] == 14

        print("✓ Feature version registered successfully")


def test_feature_dataset_computation():
    """Test 3: Feature dataset creation from source dataset."""
    print("\n=== Test 3: Feature Dataset Computation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage_dir = Path(tmpdir) / "storage"

        dataset_service = DatasetService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "datasets")
        )
        feature_service = FeatureService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "features")
        )

        snapshot = create_test_snapshot()
        dataset_meta, dataset_df = dataset_service.create_dataset(snapshot, version='1.0.0')
        dataset_service.freeze_dataset(dataset_meta.dataset_id)
        dataset_meta, dataset_df = dataset_service.get_dataset(dataset_meta.dataset_id)

        feature_service.register_definition(
            feature_name='rsi_14',
            description='RSI indicator',
            formula_ref='rsi'
        )

        feature_service.register_version(
            feature_name='rsi_14',
            version='1.0.0',
            parameters={'period': 14}
        )

        feature_meta, feature_df = feature_service.compute_feature_dataset(
            source_dataset_metadata=dataset_meta,
            source_df=dataset_df,
            feature_version_id='rsi_14_v1.0.0',
            compute_fn=compute_rsi_feature
        )

        assert feature_meta.lifecycle_state == FeatureLifecycleState.VALIDATED
        assert 'rsi' in feature_df.columns
        assert len(feature_df) == len(dataset_df)
        assert feature_meta.source_dataset_id == dataset_meta.dataset_id

        print(f"✓ Feature dataset computed: {feature_meta.feature_dataset_id}")
        print(f"  Source: {feature_meta.source_dataset_id}")
        print(f"  Version: {feature_meta.feature_version_id}")
        print(f"  Fingerprint: {feature_meta.fingerprint[:16]}...")


def test_lineage_tracking():
    """Test 4: Lineage verification."""
    print("\n=== Test 4: Lineage Tracking ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage_dir = Path(tmpdir) / "storage"

        dataset_service = DatasetService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "datasets")
        )
        feature_service = FeatureService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "features")
        )

        snapshot = create_test_snapshot()
        dataset_meta, dataset_df = dataset_service.create_dataset(snapshot)
        dataset_service.freeze_dataset(dataset_meta.dataset_id)
        dataset_meta, _ = dataset_service.get_dataset(dataset_meta.dataset_id)

        feature_service.register_definition('rsi_14', 'RSI', 'rsi')
        feature_service.register_version('rsi_14', '1.0.0', {'period': 14})

        feature_meta, _ = feature_service.compute_feature_dataset(
            source_dataset_metadata=dataset_meta,
            source_df=dataset_df,
            feature_version_id='rsi_14_v1.0.0',
            compute_fn=compute_rsi_feature
        )

        datasets = feature_service.repository.find_datasets_by_source(dataset_meta.dataset_id)
        assert len(datasets) == 1
        assert datasets[0].feature_dataset_id == feature_meta.feature_dataset_id

        print("✓ Lineage tracked correctly")
        print(f"  Dataset: {dataset_meta.dataset_id}")
        print(f"  → Feature Dataset: {feature_meta.feature_dataset_id}")


def test_fingerprint_consistency():
    """Test 5: Fingerprint determinism."""
    print("\n=== Test 5: Fingerprint Consistency ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage_dir = Path(tmpdir) / "storage"

        dataset_service = DatasetService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "datasets")
        )
        feature_service = FeatureService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "features")
        )

        snapshot = create_test_snapshot()
        dataset_meta, dataset_df = dataset_service.create_dataset(snapshot)
        dataset_service.freeze_dataset(dataset_meta.dataset_id)
        dataset_meta, dataset_df = dataset_service.get_dataset(dataset_meta.dataset_id)

        feature_service.register_definition('rsi_14', 'RSI', 'rsi')
        feature_service.register_version('rsi_14', '1.0.0', {'period': 14})

        feature_meta, feature_df = feature_service.compute_feature_dataset(
            dataset_meta, dataset_df, 'rsi_14_v1.0.0', compute_rsi_feature
        )

        fingerprint1 = feature_meta.fingerprint

        fingerprint2 = feature_service._compute_fingerprint(feature_df)

        assert fingerprint1 == fingerprint2

        print("✓ Fingerprint is deterministic")
        print(f"  Fingerprint: {fingerprint1[:16]}...")


def test_leakage_rejection():
    """Test 6: Leakage protection."""
    print("\n=== Test 6: Leakage Rejection ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        feature_service = FeatureService(db_path=str(db_path), storage_dir=tmpdir)

        source_df = pd.DataFrame({
            'timestamp': [1, 2, 3, 4, 5],
            'symbol': ['BTC'] * 5,
            'close': [100, 110, 105, 115, 120]
        })

        feature_df_invalid = pd.DataFrame({
            'timestamp': [1, 2, 3, 4, 6],
            'symbol': ['BTC'] * 5,
            'rsi': [50, 55, 52, 58, 60]
        })

        result = feature_service.validator.validate_feature_dataset(
            source_df, feature_df_invalid, 'rsi_14'
        )

        assert not result.is_valid
        assert any('leakage' in err.lower() for err in result.errors)

        print("✓ Future data leakage detected and rejected")


def test_frozen_immutability():
    """Test 7: Frozen artifact protection."""
    print("\n=== Test 7: Frozen Artifact Protection ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage_dir = Path(tmpdir) / "storage"

        dataset_service = DatasetService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "datasets")
        )
        feature_service = FeatureService(
            db_path=str(db_path),
            storage_dir=str(storage_dir / "features")
        )

        snapshot = create_test_snapshot()
        dataset_meta, dataset_df = dataset_service.create_dataset(snapshot)
        dataset_service.freeze_dataset(dataset_meta.dataset_id)
        dataset_meta, dataset_df = dataset_service.get_dataset(dataset_meta.dataset_id)

        feature_service.register_definition('rsi_14', 'RSI', 'rsi')
        feature_service.register_version('rsi_14', '1.0.0', {'period': 14})

        feature_meta, _ = feature_service.compute_feature_dataset(
            dataset_meta, dataset_df, 'rsi_14_v1.0.0', compute_rsi_feature
        )

        feature_service.freeze_feature_dataset(feature_meta.feature_dataset_id)

        feature_meta_frozen, _ = feature_service.get_feature_dataset(feature_meta.feature_dataset_id)
        assert feature_meta_frozen.is_frozen
        assert feature_meta_frozen.lifecycle_state == FeatureLifecycleState.FROZEN

        import os
        stat_result = os.stat(feature_meta_frozen.storage_path)
        is_read_only = not (stat_result.st_mode & 0o200)
        assert is_read_only

        print("✓ Feature dataset frozen successfully")
        print(f"  State: {feature_meta_frozen.lifecycle_state.value}")
        print(f"  File permissions: read-only")


def test_index_integrity():
    """Test 8: Timestamp and symbol alignment validation."""
    print("\n=== Test 8: Index Integrity Validation ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        feature_service = FeatureService(db_path=str(db_path), storage_dir=tmpdir)

        source_df = pd.DataFrame({
            'timestamp': [1, 2, 3, 4, 5],
            'symbol': ['BTC', 'BTC', 'ETH', 'ETH', 'BTC'],
            'close': [100, 110, 105, 115, 120]
        })

        feature_df_misaligned = pd.DataFrame({
            'timestamp': [1, 2, 3, 4, 5],
            'symbol': ['BTC', 'ETH', 'BTC', 'ETH', 'BTC'],
            'rsi': [50, 55, 52, 58, 60]
        })

        result = feature_service.validator.validate_feature_dataset(
            source_df, feature_df_misaligned, 'rsi_14'
        )

        assert not result.is_valid
        assert any('symbol' in err.lower() and 'alignment' in err.lower() for err in result.errors)

        print("✓ Index misalignment detected and rejected")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Feature Store Verification Tests")
    print("=" * 60)

    tests = [
        test_feature_definition_registration,
        test_feature_version_registration,
        test_feature_dataset_computation,
        test_lineage_tracking,
        test_fingerprint_consistency,
        test_leakage_rejection,
        test_frozen_immutability,
        test_index_integrity
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    import sys
    sys.exit(0 if main() else 1)
