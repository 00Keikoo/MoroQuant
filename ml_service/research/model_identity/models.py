"""

Model Identity Models
Sprint 3.9D-4

Immutable representation of discovered model artifacts.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class ModelIdentity:
	artifact_path: str

	symbol: str
	timeframe: str
	model_type: str
	asset_class: str

	feature_count: int
	feature_fingerprint: str

	trained_at: str

	validation_available: bool
	calibration_available: bool

	sample_count: int
	lifecycle_status: str
