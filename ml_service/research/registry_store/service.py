"""
Registry Store Service
Sprint 3.9D-6

High-level service coordinating:
ModelArtifactScanner -> RegistrySnapshotBuilder -> JsonRegistrySnapshotStore
"""

from ml_service.research.model_identity import ModelIdentity
from ml_service.research.registry_snapshot import (
    RegistrySnapshot,
    RegistrySnapshotBuilder,
    RegistryDiff,
    RegistryDiffEngine
)
from .interfaces import RegistrySnapshotStore
from .json_store import JsonRegistrySnapshotStore


class RegistryStoreService:
    def __init__(self, store: RegistrySnapshotStore | None = None):
        self.store = store or JsonRegistrySnapshotStore()
        self.snapshot_builder = RegistrySnapshotBuilder()
        self.diff_engine = RegistryDiffEngine()

    def create_snapshot(self, models: tuple[ModelIdentity, ...]) -> RegistrySnapshot:
        snapshot = self.snapshot_builder.build(models)
        self.store.save(snapshot)
        return snapshot

    def get_latest_snapshot(self) -> RegistrySnapshot | None:
        return self.store.get_latest()

    def compare_with_latest(self, models: tuple[ModelIdentity, ...]) -> RegistryDiff | None:
        latest = self.get_latest_snapshot()

        if latest is None:
            return None

        current = self.snapshot_builder.build(models)
        return self.diff_engine.diff(latest, current)
