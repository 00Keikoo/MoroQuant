"""
Registry Diff Engine
Sprint 3.9D-5

Compares registry snapshots and identifies changes.
"""

from ml_service.research.model_identity import ModelIdentity
from .models import RegistrySnapshot, RegistryDiff
from .interfaces import IRegistryDiffEngine


class RegistryDiffEngine(IRegistryDiffEngine):
    """
    Compares two registry snapshots and produces an immutable diff.

    Comparison based on:
    - artifact fingerprint
    - feature fingerprint
    - validation status
    - lifecycle status
    """

    def diff(
        self,
        previous: RegistrySnapshot,
        current: RegistrySnapshot
    ) -> RegistryDiff:
        prev_by_path = {m.artifact_path: m for m in previous.models}
        curr_by_path = {m.artifact_path: m for m in current.models}

        prev_paths = set(prev_by_path.keys())
        curr_paths = set(curr_by_path.keys())

        added_paths = curr_paths - prev_paths
        removed_paths = prev_paths - curr_paths
        common_paths = prev_paths & curr_paths

        added_models = tuple(
            curr_by_path[path]
            for path in sorted(added_paths)
        )

        removed_models = tuple(
            prev_by_path[path]
            for path in sorted(removed_paths)
        )

        modified_models = []
        for path in sorted(common_paths):
            prev_model = prev_by_path[path]
            curr_model = curr_by_path[path]

            if self._is_modified(prev_model, curr_model):
                modified_models.append((prev_model, curr_model))

        return RegistryDiff(
            added_models=added_models,
            removed_models=removed_models,
            modified_models=tuple(modified_models),
        )

    def _is_modified(
        self,
        previous: ModelIdentity,
        current: ModelIdentity
    ) -> bool:
        return (
            previous.feature_fingerprint != current.feature_fingerprint
            or previous.validation_available != current.validation_available
            or previous.lifecycle_status != current.lifecycle_status
        )
