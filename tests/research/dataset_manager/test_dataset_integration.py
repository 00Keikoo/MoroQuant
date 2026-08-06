"""
Simplified tests for MarketEventIterator and Dataset Integration

Validates core dataset integration functionality without requiring full orchestrator.
"""

import csv
import tempfile
from pathlib import Path
import pytest

from ml_service.research.models import DatasetSnapshot
from ml_service.research.dataset_manager.market_event_iterator import MarketEventIterator
from ml_service.research.dataset_service import DatasetService
from ml_service.research.dataset_snapshot import DatasetSnapshotManager
from ml_service.research.dataset_repository import DatasetRepository


class TestMarketEventIteratorCore:
    """Core tests for MarketEventIterator without orchestrator dependencies."""

    def test_frozen_dataset_required(self):
        """Verify non-frozen datasets are rejected."""
        snapshot = DatasetSnapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/tmp/test.csv",
            is_frozen=False,
            created_at="2024-01-01T00:00:00Z",
        )

        with pytest.raises(ValueError, match="must be frozen"):
            MarketEventIterator(snapshot)

    def test_event_ordering_deterministic(self):
        """Events are sorted by timestamp."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()
            # Write in reverse order
            writer.writerow({
                'timestamp': '2024-01-01T02:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40200.0',
                'high': '40300.0',
                'low': '40100.0',
                'close': '40200.0',
                'volume': '1000.0',
            })
            writer.writerow({
                'timestamp': '2024-01-01T00:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40000.0',
                'high': '40100.0',
                'low': '39900.0',
                'close': '40000.0',
                'volume': '1000.0',
            })
            writer.writerow({
                'timestamp': '2024-01-01T01:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40100.0',
                'high': '40200.0',
                'low': '40000.0',
                'close': '40100.0',
                'volume': '1000.0',
            })
            file_path = f.name

        try:
            snapshot = DatasetSnapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=True,
                created_at="2024-01-01T00:00:00Z",
            )

            iterator = MarketEventIterator(snapshot)
            events = list(iterator)

            assert len(events) == 3
            assert events[0].timestamp.hour == 0
            assert events[1].timestamp.hour == 1
            assert events[2].timestamp.hour == 2

            for i in range(len(events) - 1):
                assert events[i].timestamp < events[i + 1].timestamp

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_iterator_determinism(self):
        """Same dataset yields identical sequences."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()
            writer.writerow({
                'timestamp': '2024-01-01T00:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40000.0',
                'high': '40100.0',
                'low': '39900.0',
                'close': '40000.0',
                'volume': '1000.0',
            })
            file_path = f.name

        try:
            snapshot = DatasetSnapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=True,
                created_at="2024-01-01T00:00:00Z",
            )

            iterator1 = MarketEventIterator(snapshot)
            iterator2 = MarketEventIterator(snapshot)

            events1 = list(iterator1)
            events2 = list(iterator2)

            assert len(events1) == len(events2)
            for e1, e2 in zip(events1, events2):
                assert e1.timestamp == e2.timestamp
                assert e1.mid_price == e2.mid_price

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_dataset_file_immutability(self):
        """Dataset file unchanged after iteration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()
            writer.writerow({
                'timestamp': '2024-01-01T00:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40000.0',
                'high': '40100.0',
                'low': '39900.0',
                'close': '40000.0',
                'volume': '1000.0',
            })
            file_path = f.name

        try:
            with open(file_path, 'r') as f:
                original_content = f.read()

            snapshot = DatasetSnapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=True,
                created_at="2024-01-01T00:00:00Z",
            )

            iterator = MarketEventIterator(snapshot)
            list(iterator)

            with open(file_path, 'r') as f:
                final_content = f.read()

            assert original_content == final_content

        finally:
            Path(file_path).unlink(missing_ok=True)


class TestDatasetServiceIntegration:
    """Test DatasetService integration with MarketEventIterator."""

    def test_dataset_service_loads_frozen_snapshot(self):
        """DatasetService can create and retrieve frozen snapshots."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()
            writer.writerow({
                'timestamp': '2024-01-01T00:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40000.0',
                'high': '40100.0',
                'low': '39900.0',
                'close': '40000.0',
                'volume': '1000.0',
            })
            file_path = f.name

        try:
            repository = DatasetRepository()
            snapshot_manager = DatasetSnapshotManager()
            dataset_service = DatasetService(
                repository=repository,
                snapshot_manager=snapshot_manager,
            )

            snapshot = dataset_service.create_snapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=True,
                created_at="2024-01-01T00:00:00Z",
            )

            assert snapshot.is_frozen
            assert snapshot.dataset_version_id == "DS_1.0.0"

            retrieved = dataset_service.get_snapshot("DS_1.0.0")
            assert retrieved.fingerprint == snapshot.fingerprint

            iterator = MarketEventIterator(retrieved)
            events = list(iterator)
            assert len(events) == 1

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_dataset_service_rejects_unfrozen_for_iteration(self):
        """MarketEventIterator rejects unfrozen datasets."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()
            writer.writerow({
                'timestamp': '2024-01-01T00:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40000.0',
                'high': '40100.0',
                'low': '39900.0',
                'close': '40000.0',
                'volume': '1000.0',
            })
            file_path = f.name

        try:
            repository = DatasetRepository()
            snapshot_manager = DatasetSnapshotManager()
            dataset_service = DatasetService(
                repository=repository,
                snapshot_manager=snapshot_manager,
            )

            snapshot = dataset_service.create_snapshot(
                dataset_version_id="DS_1.0.0",
                fingerprint="a" * 64,
                file_path=file_path,
                is_frozen=False,  # Not frozen
                created_at="2024-01-01T00:00:00Z",
            )

            with pytest.raises(ValueError, match="must be frozen"):
                MarketEventIterator(snapshot)

        finally:
            Path(file_path).unlink(missing_ok=True)
