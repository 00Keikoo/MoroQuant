"""Research Benchmark Module - Sprint 3.9D-1

Provides interfaces, models, and scoring logic for comparing ResearchReports.
"""

from ml_service.research.benchmark.models import BenchmarkResult
from ml_service.research.benchmark.interfaces import ResearchBenchmark
from ml_service.research.benchmark.benchmark import DefaultResearchBenchmark
from ml_service.research.benchmark.scoring import calculate_absolute_score

__all__ = [
    "BenchmarkResult",
    "ResearchBenchmark",
    "DefaultResearchBenchmark",
    "calculate_absolute_score",
]
