"""Research integrity validation layer.

Pure validation layer that ensures research results are scientifically trustworthy.
No database writes, no modifications to existing engines.
"""

from .types import IntegrityReport, BiasFlag, RiskLevel
from .service import IntegrityService
from .validators import (
    SnapshotIntegrityValidator,
    ReplayIntegrityValidator,
    ResearchBiasDetector
)

__all__ = [
    'IntegrityReport',
    'BiasFlag',
    'RiskLevel',
    'IntegrityService',
    'SnapshotIntegrityValidator',
    'ReplayIntegrityValidator',
    'ResearchBiasDetector',
]
