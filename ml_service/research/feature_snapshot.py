import datetime
import json
import re
import hashlib
from typing import Dict, Optional, Any
from dataclasses import replace

from ml_service.research.models import FeatureSnapshot
from ml_service.research.research_session import make_immutable

class FeatureSnapshotManager:
    """
    Manages the lifecycle, metadata validation, and hash verification of Feature Snapshots.
    Enforces immutability and determinism without database persistence or file writes.
    """
    def __init__(self) -> None:
        self._snapshots: Dict[str, FeatureSnapshot] = {}

    def get_snapshot(self, feature_dataset_id: str) -> FeatureSnapshot:
        """Retrieves a snapshot by its feature dataset ID. Raises KeyError if not found."""
        if feature_dataset_id not in self._snapshots:
            raise KeyError(f"Feature snapshot with ID '{feature_dataset_id}' not found.")
        return self._snapshots[feature_dataset_id]

    def create_snapshot(
        self,
        feature_dataset_id: str,
        source_dataset_id: str,
        fingerprint: str,
        file_path: str,
        is_frozen: bool = True,
        created_at: Optional[str] = None
    ) -> FeatureSnapshot:
        """
        Creates, validates, and registers a new FeatureSnapshot.
        Raises ValueError if validation fails.
        """
        if created_at is None:
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        snapshot = FeatureSnapshot(
            feature_dataset_id=feature_dataset_id,
            source_dataset_id=source_dataset_id,
            fingerprint=fingerprint,
            file_path=file_path,
            is_frozen=is_frozen,
            created_at=created_at
        )

        self.validate_snapshot(snapshot)
        self._snapshots[feature_dataset_id] = snapshot
        return snapshot

    def validate_snapshot(self, snapshot: FeatureSnapshot) -> None:
        """
        Validates the metadata of a FeatureSnapshot.
        Raises ValueError if validation fails.
        """
        # Validate feature_dataset_id format (FDS_[Major].[Minor].[Patch])
        if not re.match(r"^FDS_\d+\.\d+\.\d+$", snapshot.feature_dataset_id):
            raise ValueError(
                f"Invalid feature_dataset_id '{snapshot.feature_dataset_id}'. "
                "Must match semantic versioning format 'FDS_[Major].[Minor].[Patch]' (e.g. FDS_1.0.0)."
            )

        # Validate source_dataset_id format (DS_[Major].[Minor].[Patch])
        if not re.match(r"^DS_\d+\.\d+\.\d+$", snapshot.source_dataset_id):
            raise ValueError(
                f"Invalid source_dataset_id '{snapshot.source_dataset_id}'. "
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

    def verify_hash(self, snapshot: FeatureSnapshot, data: Any) -> bool:
        """
        Verifies that the snapshot's fingerprint matches the hash of the provided data.
        If data is a 64-character hex string, directly compares with fingerprint.
        Otherwise, serializes data deterministically with standard float precision (%.8f)
        and compares with the SHA-256 signature.
        """
        if isinstance(data, str) and re.match(r"^[a-f0-9]{64}$", data):
            return snapshot.fingerprint == data

        # Deterministic serialization for hashing
        json_str = self.canonical_json(data)
        calculated_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        return snapshot.fingerprint == calculated_hash

    def canonical_json(self, data: Any) -> str:
        """
        Computes a deterministic canonical JSON string of the input data structure.
        Numeric float fields are formatted to %.8f to eliminate float precision variations.
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
        return json.dumps(serialized, sort_keys=True, separators=(',', ':'))

    def to_dict(self, snapshot: FeatureSnapshot) -> Dict[str, Any]:
        """Converts a FeatureSnapshot to a dictionary representation."""
        if not isinstance(snapshot, FeatureSnapshot):
            raise ValueError("Input must be a FeatureSnapshot instance.")
        return snapshot.to_dict()
