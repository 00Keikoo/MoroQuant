"""
Market Event Iterator

Converts DatasetSnapshot into ordered MarketSnapshot sequence.
Provides deterministic, immutable market event replay for backtesting.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterator, List

from ml_service.research.models import DatasetSnapshot
from ml_service.simulation.models import MarketSnapshot


class MarketEventIterator:
    """
    Iterates over market events from a dataset snapshot.

    Responsibilities:
    - Load dataset from snapshot file_path
    - Convert raw data to MarketSnapshot objects
    - Ensure deterministic timestamp ordering
    - Maintain immutability

    Does NOT:
    - Execute strategy logic
    - Calculate portfolio state
    - Create orders
    - Mutate dataset
    """

    def __init__(self, dataset_snapshot: DatasetSnapshot):
        if not dataset_snapshot.is_frozen:
            raise ValueError(
                f"Dataset snapshot '{dataset_snapshot.dataset_version_id}' "
                "must be frozen for backtesting"
            )

        self.snapshot = dataset_snapshot
        self._events: List[MarketSnapshot] = []
        self._loaded = False

    def _load_events(self) -> None:
        """Load and sort market events from dataset file."""
        if self._loaded:
            return

        file_path = Path(self.snapshot.file_path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {self.snapshot.file_path}"
            )

        events = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                event = self._parse_row(row)
                events.append(event)

        # Deterministic sort by timestamp
        events.sort(key=lambda e: e.timestamp)

        self._events = events
        self._loaded = True

    def _parse_row(self, row: dict) -> MarketSnapshot:
        """
        Parse CSV row into immutable MarketSnapshot.

        Expected columns:
        - timestamp: ISO format datetime string
        - symbol: ticker symbol
        - open: open price
        - high: high price
        - low: low price
        - close: close price
        - volume: trading volume
        """
        timestamp_str = row['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Calculate mid_price, bid, ask from OHLC
        close_price = float(row['close'])
        open_price = float(row.get('open', close_price))
        high_price = float(row.get('high', close_price))
        low_price = float(row.get('low', close_price))

        # Use close as mid_price for simplicity
        mid_price = close_price

        # Estimate bid/ask spread (0.1% default)
        spread = mid_price * 0.001
        bid = mid_price - (spread / 2)
        ask = mid_price + (spread / 2)

        return MarketSnapshot(
            timestamp=timestamp,
            symbol=row['symbol'],
            mid_price=mid_price,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=float(row.get('volume', 0.0)),
            open_interest=float(row.get('open_interest', 0.0)) if 'open_interest' in row else None,
            funding_rate=float(row.get('funding_rate', 0.0)) if 'funding_rate' in row else None,
        )

    def __iter__(self) -> Iterator[MarketSnapshot]:
        """Iterate over market events in timestamp order."""
        self._load_events()
        return iter(self._events)

    def __len__(self) -> int:
        """Return number of market events."""
        self._load_events()
        return len(self._events)
