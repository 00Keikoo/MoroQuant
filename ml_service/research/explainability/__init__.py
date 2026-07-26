"""Explainability Framework for Model Diagnostics."""

from .types import (
    DiagnosticRunContext,
    DiagnosticRunResult,
    ProviderConfig,
    DiagnosticConfig
)
from .providers.base import BaseDiagnosticProvider
from .providers import (
    ShapProvider,
    CorrelationProvider,
    PermutationProvider,
    StabilityProvider
)
from .writer import ArtifactWriter
from .service import ExplainabilityService
from .report import ReportGenerator

__all__ = [
    'DiagnosticRunContext',
    'DiagnosticRunResult',
    'ProviderConfig',
    'DiagnosticConfig',
    'BaseDiagnosticProvider',
    'ShapProvider',
    'CorrelationProvider',
    'PermutationProvider',
    'StabilityProvider',
    'ArtifactWriter',
    'ExplainabilityService',
    'ReportGenerator',
]
