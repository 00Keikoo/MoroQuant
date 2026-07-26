"""Type definitions and dataclasses for the Explainability Framework."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class DiagnosticRunContext:
    """Metadata context for a diagnostic run execution."""

    run_id: str
    model_version_id: str
    dataset_version_id: str
    feature_dataset_version_id: str
    model_binary_hash: str
    dataset_hash: str
    timestamp: str


@dataclass
class DiagnosticRunResult:
    """Result container for completed diagnostic run."""

    run_id: str
    status: str
    start_time: datetime
    end_time: datetime
    artifact_manifest: Dict[str, str]
    output_paths: Dict[str, str]
    execution_duration_sec: float
    max_memory_kb: Optional[int] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class ProviderConfig:
    """Configuration parameters for diagnostic providers."""

    enabled: bool = True
    max_shap_samples: int = 2500
    permutation_repetitions: int = 10
    random_seed: int = 42
    timeout_seconds: Optional[int] = None
    provider_specific: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagnosticConfig:
    """Global configuration for diagnostic execution."""

    active_providers: List[str] = field(default_factory=lambda: [
        'shap', 'correlation', 'permutation', 'stability'
    ])
    provider_configs: Dict[str, ProviderConfig] = field(default_factory=dict)
    enforce_immutability: bool = True
    compute_checksums: bool = True
    compression: str = 'snappy'
    feature_dataset_version_id: Optional[str] = None
