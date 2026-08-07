"""Model Registry Auditor Implementation - Sprint 3.9D-4

Implements classification auditor and safety checks for discovered models.
"""

from typing import Tuple
from ml_service.research.model_identity.models import ModelIdentity
from ml_service.research.model_registry_audit.interfaces import RegistryClassificationAuditor
from ml_service.research.model_registry_audit.models import AuditReport


class DefaultRegistryClassificationAuditor(RegistryClassificationAuditor):
    """Default implementation of registry classification auditor.

    Adheres to ADR-024 compliance: stateless, pure-functional, and deterministic.
    """

    def audit(self, models: Tuple[ModelIdentity, ...]) -> AuditReport:
        """Audit a tuple of ModelIdentity objects.

        Args:
            models: Tuple of ModelIdentity instances.

        Returns:
            AuditReport detailing classification counts.
        """
        total_models = len(models)
        crypto_models = 0
        proxy_models = 0
        validated_models = 0
        calibrated_models = 0
        governance_ready_models = 0
        invalid_models = 0

        for model in models:
            # Asset class counting
            if model.asset_class == "crypto":
                crypto_models += 1
            elif model.asset_class == "proxy":
                proxy_models += 1
            else:
                invalid_models += 1

            # Validation availability
            if model.validation_available is True:
                validated_models += 1

            # Calibration availability
            if model.calibration_available is True:
                calibrated_models += 1

            # Lifecycle status GOVERNANCE_READY
            if model.lifecycle_status == "GOVERNANCE_READY":
                governance_ready_models += 1

        return AuditReport(
            total_models=total_models,
            crypto_models=crypto_models,
            proxy_models=proxy_models,
            validated_models=validated_models,
            calibrated_models=calibrated_models,
            governance_ready_models=governance_ready_models,
            invalid_models=invalid_models,
        )


def is_production_candidate(model_identity: ModelIdentity) -> bool:
    """Production safety guard.

    Proxy models are external context features and must NEVER become production candidates.
    Trading models (crypto) must pass validation to be candidates.

    Args:
        model_identity: ModelIdentity instance to evaluate.

    Returns:
        bool: True if model is eligible as a production candidate.
    """
    if model_identity.asset_class == "crypto" and model_identity.validation_available is True:
        return True
    return False
