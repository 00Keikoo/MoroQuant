"""
Registry Snapshot Builder
Sprint 3.9D-5

Creates deterministic snapshots of model registry state.
"""

import hashlib
import json
from datetime import datetime, timezone
from ml_service.research.model_identity import ModelIdentity
from .models import RegistrySnapshot
from .interfaces import IRegistrySnapshotBuilder


class RegistrySnapshotBuilder(IRegistrySnapshotBuilder):
    """
    Creates immutable snapshots of model registry state.

    Snapshot identity is deterministic based on model content,
    not timestamp. Identical registry state produces identical snapshot_id.
    """

    def build(self, models: tuple[ModelIdentity, ...]) -> RegistrySnapshot:
        sorted_models = tuple(sorted(models, key=self._model_sort_key))

        snapshot_id = self._compute_snapshot_id(sorted_models)
        created_at = datetime.now(timezone.utc).isoformat()
        total_models = len(sorted_models)
        summary = self._build_summary(sorted_models)

        return RegistrySnapshot(
            snapshot_id=snapshot_id,
            created_at=created_at,
            total_models=total_models,
            models=sorted_models,
            summary=summary,
        )

    def _model_sort_key(self, model: ModelIdentity) -> tuple:
        return (
            model.symbol,
            model.timeframe,
            model.model_type,
            model.asset_class,
            model.artifact_path,
        )

    def _compute_snapshot_id(self, models: tuple[ModelIdentity, ...]) -> str:
        fingerprints = []

        for model in models:
            model_data = {
                "artifact_path": model.artifact_path,
                "symbol": model.symbol,
                "timeframe": model.timeframe,
                "model_type": model.model_type,
                "asset_class": model.asset_class,
                "feature_fingerprint": model.feature_fingerprint,
                "lifecycle_status": model.lifecycle_status,
                "validation_available": model.validation_available,
            }

            model_json = json.dumps(model_data, sort_keys=True)
            fingerprints.append(model_json)

        combined = "\n".join(fingerprints)
        hash_digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        return f"snapshot_{hash_digest[:16]}"

    def _build_summary(self, models: tuple[ModelIdentity, ...]) -> dict:
        by_lifecycle = {}
        by_model_type = {}
        by_symbol = {}

        for model in models:
            by_lifecycle[model.lifecycle_status] = by_lifecycle.get(model.lifecycle_status, 0) + 1
            by_model_type[model.model_type] = by_model_type.get(model.model_type, 0) + 1
            by_symbol[model.symbol] = by_symbol.get(model.symbol, 0) + 1

        return {
            "by_lifecycle": by_lifecycle,
            "by_model_type": by_model_type,
            "by_symbol": by_symbol,
            "total_with_validation": sum(1 for m in models if m.validation_available),
            "total_with_calibration": sum(1 for m in models if m.calibration_available),
        }
