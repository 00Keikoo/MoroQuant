"""JSON Event Ledger Storage - Sprint 3.9D-10

JSON-based append-only storage for registry events.
ADR-024 compliant: research layer only, no database, corruption-tolerant.
"""

import json
from pathlib import Path
from typing import Optional

from ml_service.research.registry_event_ledger.models import RegistryEventRecord


class JsonEventStorage:
    """JSON-based append-only event storage.

    Features:
    - Append-only writes
    - Corruption-tolerant reads
    - Deterministic ordering by timestamp
    - No SQLite or database dependencies
    """

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: RegistryEventRecord, payload: dict) -> None:
        """Append event record and payload to JSON file.

        Args:
            record: Event record metadata
            payload: Full event payload
        """
        entry = {
            "record": record.to_dict(),
            "payload": payload,
        }

        mode = "a" if self.storage_path.exists() else "w"
        with open(self.storage_path, mode) as f:
            json.dump(entry, f, sort_keys=True)
            f.write("\n")

    def read_all(self) -> list[tuple[RegistryEventRecord, dict]]:
        """Read all events with corruption tolerance.

        Returns:
            List of (record, payload) tuples in chronological order
        """
        if not self.storage_path.exists():
            return []

        events = []
        with open(self.storage_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    record = RegistryEventRecord.from_dict(entry["record"])
                    payload = entry["payload"]
                    events.append((record, payload))
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    continue

        events.sort(key=lambda x: x[0].created_at)
        return events
