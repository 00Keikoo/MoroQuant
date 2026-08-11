"""
Registry Snapshot Interfaces
Sprint 3.9D-5
"""

from abc import ABC, abstractmethod
from ml_service.research.model_identity import ModelIdentity
from .models import RegistrySnapshot, RegistryDiff


class IRegistrySnapshotBuilder(ABC):
    @abstractmethod
    def build(self, models: tuple[ModelIdentity, ...]) -> RegistrySnapshot:
        pass


class IRegistryDiffEngine(ABC):
    @abstractmethod
    def diff(
        self,
        previous: RegistrySnapshot,
        current: RegistrySnapshot
    ) -> RegistryDiff:
        pass
