import datetime
import json
import re
import hashlib
from typing import Dict, Optional, Any
from dataclasses import replace

from ml_service.research.models import DatasetSnapshot
from ml_service.research.research_session import make_immutable

class DatasetSnapshotManager:
    """
    Manages the lifecycle, metadata validation, and hash verification of Dataset Snapshots.
    Enforces immutability and determinism without database persistence or file writes.
    """
    def __init__(self) -> None:
        self._snapshots: Dict[str, DatasetSnapshot] = {}

    def get_snapshot(self, dataset_version_id: str) -> DatasetSnapshot:
        """Retrieves a snapshot by its version ID. Raises KeyError if not found."""
        if dataset_version_id not in self._snapshots:
            raise KeyError(f"Snapshot with version ID '{dataset_version_id}' not found.")
        return self._snapshots[dataset_version_id]

    def create_snapshot(
        self,
        dataset_version_id: str,
        fingerprint: str,
        file_path: str,
        is_frozen: bool = True,
        created_at: Optional[str] = None
    ) -> DatasetSnapshot:
        """
        Creates, validates, and registers a new DatasetSnapshot.
        Raises ValueError if validation fails.
        """
        if created_at is None:
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        snapshot = DatasetSnapshot(
            dataset_version_id=dataset_version_id,
            fingerprint=fingerprint,
            file_path=file_path,
            is_frozen=is_frozen,
            created_at=created_at
        )

        self.validate_snapshot(snapshot)
        self._snapshots[dataset_version_id] = snapshot
        return snapshot

    def validate_snapshot(self, snapshot: DatasetSnapshot) -> None:
        """
        Validates the metadata of a DatasetSnapshot.
        Raises ValueError if validation fails.
        """
        # Validate version format (DS_[Major].[Minor].[Patch])
        if not re.match(r"^DS_\d+\.\d+\.\d+$", snapshot.dataset_version_id):
            raise ValueError(
                f"Invalid dataset_version_id '{snapshot.dataset_version_id}'. "
                "Must match semantic versioning format 'DS_[Major].[Minor].[Patch]' (e.g. DS_1.0.0)."
            )

        # Validate fingerprint format (SHA-256 hash: 64 hex characters)
        if not re.match(r"^[a-f0-9]{64}$", snapshot.fingerprint):
            raise ValueError(
                f"Invalid fingerprint '{snapshot.fingerprint}'. "
                "Must be a valid 64-character hexadecimal SHA-256 hash."
            )

        # Validate file path
        if not snapshot.file_path or not isinstance(snapshot.file_path, str):
            raise ValueError("File path must be a non-empty string.")

        # Validate created_at format
        try:
            # Check ISO format compatibility
            datetime.datetime.fromisoformat(snapshot.created_at.replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(f"Invalid created_at timestamp '{snapshot.created_at}': {e}")

        # Validate is_frozen
        if not isinstance(snapshot.is_frozen, bool):
            raise ValueError("is_frozen must be a boolean.")

    def verify_hash(self, snapshot: DatasetSnapshot, data: Any) -> bool:
        """
        Verifies that the snapshot's fingerprint matches the hash of the provided data.
        If data is a 64-character hex string, directly compares with fingerprint.
        Otherwise, serializes data deterministically with standard float precision (%.8f)
        and compares with the SHA-256 signature.
        """
        if isinstance(data, str) and re.match(r"^[a-f0-9]{64}$", data):
            return snapshot.fingerprint == data

        # Deterministic serialization for hashing
        calculated_hash = self.calculate_canonical_hash(data)
        return snapshot.fingerprint == calculated_hash

    def calculate_canonical_hash(self, data: Any) -> str:
        """
        Computes a deterministic SHA-256 hash of the input data structure.
        Numeric fields are formatted to %.8f to eliminate float precision variations.
        Dictionaries are sorted alphabetically.
        """
        def serialize_canonical(val: Any) -> Any:
            if isinstance(val, float):
                return f"{val:.8f}"
            elif isinstance(val, dict):
                return {k: serialize_canonical(v) for k, v in sorted(val.items())}
            elif isinstance(val, (list, tuple)):
                return [serialize_canonical(x) for x in val]
            return val

        serialized = serialize_canonical(data)
        json_str = json.dumps(serialized, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def serialize(self, snapshot: DatasetSnapshot) -> str:
        """Exposes deterministic JSON string serialization for a DatasetSnapshot."""
        return json.dumps(snapshot.to_dict(), sort_keys=True)
