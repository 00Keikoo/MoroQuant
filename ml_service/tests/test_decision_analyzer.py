"""Tests for DecisionAnalyzer skeleton.

Sprint 2.3B Commit 2: Tests analyzer structure and interface only.
No classification logic tested yet.
"""

import pytest

from ml_service.migrations.recovery.decision.analyzer import DecisionAnalyzer
from ml_service.migrations.recovery.models import (
    DecisionContext,
    DifferenceType,
    SchemaDifference,
)


class TestDecisionAnalyzerConstruction:
    """Test DecisionAnalyzer constructor."""

    def test_constructor(self):
        """DecisionAnalyzer can be constructed with DecisionContext."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)
        assert analyzer is not None
        assert analyzer.context == context


class TestDecisionAnalyzerInterface:
    """Test DecisionAnalyzer public interface."""

    def test_has_analyze_method(self):
        """DecisionAnalyzer has analyze method."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)
        assert hasattr(analyzer, 'analyze')
        assert callable(analyzer.analyze)


class TestDecisionAnalyzerAnalyze:
    """Test DecisionAnalyzer.analyze() behavior."""

    def test_analyze_empty_differences(self):
        """analyze() returns empty tuple when given empty tuple."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)
        result = analyzer.analyze(())
        assert result == ()

    def test_analyze_non_empty_raises_not_implemented(self):
        """analyze() raises NotImplementedError for non-empty differences."""
        context = DecisionContext(
            applied_migration_names=(),
            available_migration_files=(),
            migration_checksums={},
        )
        analyzer = DecisionAnalyzer(context)

        differences = (
            SchemaDifference(
                difference_type=DifferenceType.MISSING_TABLE,
                table_name="test_table",
            ),
        )

        with pytest.raises(NotImplementedError) as exc_info:
            analyzer.analyze(differences)

        assert "Decision classification is not implemented yet" in str(exc_info.value)
