"""
Registry Store Models
Sprint 3.9D-6

Immutable records for persisted registry snapshots.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistrySnapshotRecord:
    snapshot_id: str
    file_path: str
    created_at: str
    model_count: int
