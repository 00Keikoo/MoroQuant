"""
Tests for MarketEventIterator

Validates:
1. Dataset snapshot validation
2. Market event ordering (deterministic timestamp sort)
3. Iterator determinism (same dataset = same sequence)
4. Runtime immutability (no dataset mutation)
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ml_service.research.models import DatasetSnapshot
from ml_service.research.dataset_manager.market_event_iterator import MarketEventIterator
from ml_service.simulation.models import MarketSnapshot


class TestMarketEventIterator:
    """Test suite for MarketEventIterator."""

    def test_dataset_snapshot_validation_requires_frozen(self):
        """Verify that non-frozen datasets are rejected."""
        snapshot = DatasetSnapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/tmp/test.csv",
            is_frozen=False,  # NOT frozen
            created_at="2024-01-01T00:00:00Z",
        )

        with pytest.raises(ValueError, match="must be frozen"):
            MarketEventIterator(snapshot)

    def test_market_event_iterator_ordering(self):
        """Verify events are sorted by timestamp regardless of input order."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()

            # Write events in REVERSE chronological order
            writer.writerow({
                'timestamp': '2024-01-01T04:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40400.0',
                'high': '40500.0',
                'low': '40300.0',
                'close': '40400.0',
                'volume': '1000.0',
            })
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
                'timestamp': '2024-01-01T03:00:00Z',
                'symbol': 'BTCUSDT',
                'open': '40300.0',
                'high': '40400.0',
                'low': '40200.0',
                'close': '40300.0',
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

            # Verify events are sorted by timestamp
            assert len(events) == 5

            expected_hours = [0, 1, 2, 3, 4]
            for i, event in enumerate(events):
                assert event.timestamp.hour == expected_hours[i]
                assert event.symbol == "BTCUSDT"

            # Verify ordering is strictly ascending
            for i in range(len(events) - 1):
                assert events[i].timestamp < events[i + 1].timestamp

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_market_event_iterator_determinism(self):
        """Same dataset produces identical sequence on multiple iterations."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()

            for i in range(3):
                writer.writerow({
                    'timestamp': f'2024-01-01T{i:02d}:00:00Z',
                    'symbol': 'BTCUSDT',
                    'open': f'{40000 + i * 100}',
                    'high': f'{40000 + i * 100 + 50}',
                    'low': f'{40000 + i * 100 - 50}',
                    'close': f'{40000 + i * 100}',
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

            # Create two separate iterators
            iterator1 = MarketEventIterator(snapshot)
            iterator2 = MarketEventIterator(snapshot)

            events1 = list(iterator1)
            events2 = list(iterator2)

            # Verify identical sequences
            assert len(events1) == len(events2)

            for e1, e2 in zip(events1, events2):
                assert e1.timestamp == e2.timestamp
                assert e1.symbol == e2.symbol
                assert e1.mid_price == e2.mid_price
                assert e1.volume == e2.volume

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_runtime_no_dataset_mutation(self):
        """Dataset file remains unchanged after iteration."""
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
            # Record original file content
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
            events = list(iterator)

            # Verify file unchanged
            with open(file_path, 'r') as f:
                final_content = f.read()

            assert original_content == final_content

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_market_snapshot_immutability(self):
        """Verify MarketSnapshot objects are frozen (immutable)."""
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

            iterator = MarketEventIterator(snapshot)
            events = list(iterator)

            # Attempt to mutate MarketSnapshot should raise
            with pytest.raises(Exception):  # FrozenInstanceError or similar
                events[0].mid_price = 99999.0

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_file_not_found_error(self):
        """Verify FileNotFoundError when dataset file missing."""
        snapshot = DatasetSnapshot(
            dataset_version_id="DS_1.0.0",
            fingerprint="a" * 64,
            file_path="/nonexistent/path/dataset.csv",
            is_frozen=True,
            created_at="2024-01-01T00:00:00Z",
        )

        iterator = MarketEventIterator(snapshot)

        with pytest.raises(FileNotFoundError):
            list(iterator)

    def test_iterator_length(self):
        """Verify __len__ returns correct event count."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            )
            writer.writeheader()

            for i in range(7):
                writer.writerow({
                    'timestamp': f'2024-01-01T{i:02d}:00:00Z',
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

            iterator = MarketEventIterator(snapshot)

            assert len(iterator) == 7

        finally:
            Path(file_path).unlink(missing_ok=True)
