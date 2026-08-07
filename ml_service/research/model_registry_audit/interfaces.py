"""Model Registry Audit Interfaces - Sprint 3.9D-4

Defines the abstract interface for classification and audit of model registries.
"""

from abc import ABC, abstractmethod
from typing import Tuple
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_registry_audit.models import AuditReport


class RegistryClassificationAuditor(ABC):
    """Abstract interface for classification and governance audit of discovered models.

    Adheres to ADR-024 compliance. Implementation must be stateless, deterministic,
    and free of database/execution system dependencies.
    """

    @abstractmethod
    def audit(self, models: Tuple[ModelIdentity, ...]) -> AuditReport:
        """Analyze discovered model identities and generate an immutable audit report.

        Args:
            models: Tuple of ModelIdentity instances.

        Returns:
            AuditReport: Immutable report detailing classification counts.
        """
        pass
