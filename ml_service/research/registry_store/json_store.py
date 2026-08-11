"""
JSON Registry Snapshot Store
Sprint 3.9D-6

Filesystem-based persistence with deterministic JSON serialization.
No database, no pickle - pure JSON.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from ml_service.research.registry_snapshot import RegistrySnapshot
from ml_service.research.model_identity import ModelIdentity
from .interfaces import RegistrySnapshotStore
from .models import RegistrySnapshotRecord


class JsonRegistrySnapshotStore(RegistrySnapshotStore):
    def __init__(self, storage_path: str = "storage/research_registry_snapshots"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: RegistrySnapshot) -> str:
        snapshot_data = self._serialize_snapshot(snapshot)

        file_path = self.storage_path / f"snapshot_{snapshot.snapshot_id}.json"
        temp_path = file_path.with_suffix('.json.tmp')

        with open(temp_path, 'w') as f:
            json.dump(snapshot_data, f, indent=2, sort_keys=True)

        os.rename(temp_path, file_path)

        return snapshot.snapshot_id

    def load(self, snapshot_id: str) -> RegistrySnapshot:
        file_path = self.storage_path / f"snapshot_{snapshot_id}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found")

        with open(file_path, 'r') as f:
            snapshot_data = json.load(f)

        return self._deserialize_snapshot(snapshot_data)

    def list_snapshots(self) -> tuple[RegistrySnapshotRecord, ...]:
        records = []

        for file_path in self.storage_path.glob("snapshot_*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                record = RegistrySnapshotRecord(
                    snapshot_id=data['snapshot_id'],
                    file_path=str(file_path),
                    created_at=data['created_at'],
                    model_count=data['total_models']
                )
                records.append(record)
            except (json.JSONDecodeError, KeyError):
                continue

        return tuple(sorted(records, key=lambda r: r.created_at))

    def get_latest(self) -> RegistrySnapshot | None:
        records = self.list_snapshots()

        if not records:
            return None

        latest_record = records[-1]
        return self.load(latest_record.snapshot_id)

    def _serialize_snapshot(self, snapshot: RegistrySnapshot) -> dict:
        return {
            'snapshot_id': snapshot.snapshot_id,
            'created_at': snapshot.created_at,
            'total_models': snapshot.total_models,
            'summary': snapshot.summary,
            'models': [self._serialize_model(m) for m in snapshot.models]
        }

    def _deserialize_snapshot(self, data: dict) -> RegistrySnapshot:
        models = tuple(self._deserialize_model(m) for m in data['models'])

        return RegistrySnapshot(
            snapshot_id=data['snapshot_id'],
            created_at=data['created_at'],
            total_models=data['total_models'],
            models=models,
            summary=data['summary']
        )

    def _serialize_model(self, model: ModelIdentity) -> dict:
        return {
            'artifact_path': model.artifact_path,
            'symbol': model.symbol,
            'timeframe': model.timeframe,
            'model_type': model.model_type,
            'asset_class': model.asset_class,
            'feature_count': model.feature_count,
            'feature_fingerprint': model.feature_fingerprint,
            'trained_at': model.trained_at,
            'validation_available': model.validation_available,
            'calibration_available': model.calibration_available,
            'sample_count': model.sample_count,
            'lifecycle_status': model.lifecycle_status
        }

    def _deserialize_model(self, data: dict) -> ModelIdentity:
        return ModelIdentity(
            artifact_path=data['artifact_path'],
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            model_type=data['model_type'],
            asset_class=data['asset_class'],
            feature_count=data['feature_count'],
            feature_fingerprint=data['feature_fingerprint'],
            trained_at=data['trained_at'],
            validation_available=data['validation_available'],
            calibration_available=data['calibration_available'],
            sample_count=data['sample_count'],
            lifecycle_status=data['lifecycle_status']
        )
