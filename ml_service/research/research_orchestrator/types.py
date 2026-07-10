"""Type definitions for research orchestrator."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List


class JobState(Enum):
    """Research job lifecycle states per ADR-014."""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StageType(Enum):
    """Pipeline stage types."""
    SNAPSHOT = "SNAPSHOT"
    DATASET = "DATASET"
    FEATURE = "FEATURE"
    EXPERIMENT = "EXPERIMENT"
    EVALUATION = "EVALUATION"
    REGISTRY = "REGISTRY"
    DASHBOARD = "DASHBOARD"


@dataclass
class JobConfig:
    """Configuration for a research job."""
    symbol: str
    timeframe: str
    algorithm: str
    start_date: str
    end_date: str
    parameters: Dict[str, Any]


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    stage_type: StageType
    status: str
    started_at: str
    completed_at: Optional[str] = None
    output_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_trace: Optional[str] = None


@dataclass
class ResearchJob:
    """Research job metadata."""
    job_id: str
    state: JobState
    config: JobConfig
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_by: str = "system"
    error_message: Optional[str] = None
    error_stage: Optional[StageType] = None


@dataclass
class JobStep:
    """Individual step in a research job."""
    step_id: str
    job_id: str
    stage_type: StageType
    status: str
    started_at: str
    completed_at: Optional[str] = None
    output_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class JobLog:
    """Execution log entry."""
    log_id: str
    job_id: str
    timestamp: str
    level: str
    message: str
    stage_type: Optional[StageType] = None


@dataclass
class PipelineMetrics:
    """Pipeline execution metrics."""
    job_id: str
    total_duration_seconds: float
    stage_durations: Dict[str, float]
    success: bool
    failed_stage: Optional[str] = None
