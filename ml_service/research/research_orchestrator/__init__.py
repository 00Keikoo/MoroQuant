"""Research Orchestrator module."""

from ml_service.research.research_orchestrator.service import ResearchOrchestratorService
from ml_service.research.research_orchestrator.analytics import ResearchOrchestratorAnalytics
from ml_service.research.research_orchestrator.types import (
    JobConfig,
    JobState,
    StageType,
    ResearchJob,
    JobStep,
    JobLog,
    PipelineMetrics
)

# Dynamically load the research_orchestrator.py file located in parent directory to resolve package vs file name conflict.
import importlib.util
from pathlib import Path

file_path = Path(__file__).parent.parent / "research_orchestrator.py"
spec = importlib.util.spec_from_file_location("research_orchestrator_file", file_path)
if spec and spec.loader:
    research_orchestrator_file = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(research_orchestrator_file)
    ResearchOrchestrator = research_orchestrator_file.ResearchOrchestrator
else:
    raise ImportError("Could not load ResearchOrchestrator from parent module file.")

__all__ = [
    'ResearchOrchestratorService',
    'ResearchOrchestratorAnalytics',
    'JobConfig',
    'JobState',
    'StageType',
    'ResearchJob',
    'JobStep',
    'JobLog',
    'PipelineMetrics',
    'ResearchOrchestrator'
]

