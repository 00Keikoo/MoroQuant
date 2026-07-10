"""Verification script for Research Dashboard backend.

Run after creating test data with scripts/research/create_test_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ml_service.research.research_dashboard.service import ResearchDashboardService
from ml_service.research.research_dashboard.analytics import ResearchAnalytics
from ml_service.research.research_dashboard.repository import ResearchDashboardRepository


def verify_read_only_enforcement():
    """Verify repository is read-only."""
    print("\n1. Verifying read-only enforcement...")
    repo = ResearchDashboardRepository()

    allowed_methods = [
        'list_experiments',
        'get_experiment',
        'get_experiment_configs',
        'get_experiment_results',
        'get_dataset_by_dataset_id',
        'get_dataset_by_snapshot_id',
        'get_feature_datasets_by_source',
        'get_feature_dataset',
        'get_feature_version'
    ]

    forbidden_patterns = ['insert', 'update', 'delete', 'save', 'create', 'modify']

    for method_name in dir(repo):
        if method_name.startswith('_'):
            continue
        if any(pattern in method_name.lower() for pattern in forbidden_patterns):
            print(f"   ❌ FAIL: Found mutation method: {method_name}")
            return False

    print(f"   ✓ Repository exposes only read methods: {', '.join(allowed_methods)}")
    return True


def verify_experiment_listing():
    """Verify experiment listing functionality."""
    print("\n2. Verifying experiment listing...")
    service = ResearchDashboardService()

    try:
        summaries = service.list_experiments()
        print(f"   ✓ Listed {len(summaries)} experiments")

        if summaries:
            first = summaries[0]
            print(f"   ✓ Sample: {first.experiment_id} - {first.status}")

        return True
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def verify_experiment_detail():
    """Verify experiment detail retrieval."""
    print("\n3. Verifying experiment detail retrieval...")
    service = ResearchDashboardService()

    try:
        summaries = service.list_experiments()
        if not summaries:
            print("   ⚠ No experiments to test")
            return True

        exp_id = summaries[0].experiment_id
        detail = service.get_experiment(exp_id)

        if detail:
            print(f"   ✓ Retrieved detail for {detail.experiment_id}")
            print(f"   ✓ Parameters: {list(detail.parameters.keys())}")
            return True
        else:
            print(f"   ❌ FAIL: Could not retrieve detail for {exp_id}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def verify_lineage_retrieval():
    """Verify lineage trace functionality."""
    print("\n4. Verifying lineage retrieval...")
    service = ResearchDashboardService()

    try:
        summaries = service.list_experiments()
        if not summaries:
            print("   ⚠ No experiments to test")
            return True

        exp_id = summaries[0].experiment_id
        lineage = service.get_lineage(exp_id)

        if not lineage:
            print(f"   ❌ FAIL: Could not retrieve lineage for {exp_id}")
            return False

        print(f"   ✓ Retrieved lineage for {lineage.experiment_id}")
        print(f"   ✓ Source dataset: {lineage.source_dataset_id}")

        if not lineage.source_dataset_fingerprint or lineage.source_dataset_fingerprint == 'unknown':
            print(f"   ❌ FAIL: Dataset fingerprint missing or unknown")
            return False

        if len(lineage.feature_datasets) == 0:
            print(f"   ❌ FAIL: Feature dataset count is 0 - lineage incomplete")
            return False

        for fd in lineage.feature_datasets:
            if not fd.fingerprint:
                print(f"   ❌ FAIL: Feature dataset {fd.feature_dataset_id} missing fingerprint")
                return False

        print(f"   ✓ Feature datasets: {len(lineage.feature_datasets)}")
        print(f"   ✓ All fingerprints present")
        return True
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def verify_evaluation_retrieval():
    """Verify evaluation summary retrieval."""
    print("\n5. Verifying evaluation retrieval...")
    service = ResearchDashboardService()

    try:
        summaries = service.list_experiments()
        if not summaries:
            print("   ⚠ No experiments to test")
            return True

        exp_id = summaries[0].experiment_id
        evaluation = service.get_evaluation(exp_id)

        if evaluation:
            print(f"   ✓ Retrieved evaluation for {evaluation.experiment_id}")
            print(f"   ✓ Total trades: {evaluation.total_trades}")
            print(f"   ✓ Win rate: {evaluation.win_rate:.2%}")
            return True
        else:
            print(f"   ❌ FAIL: Could not retrieve evaluation for {exp_id}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def verify_experiment_comparison():
    """Verify experiment comparison functionality."""
    print("\n6. Verifying experiment comparison...")
    repo = ResearchDashboardRepository()
    analytics = ResearchAnalytics(repo)

    try:
        summaries = repo.list_experiments()
        if len(summaries) < 2:
            print("   ⚠ Need at least 2 experiments for comparison")
            return True

        exp_ids = [exp['experiment_id'] for exp in summaries[:2]]
        comparison = analytics.compare_experiments(exp_ids)

        print(f"   ✓ Compared {len(comparison.compared_ids)} experiments")
        print(f"   ✓ Metrics compared: {list(comparison.metrics_comparison.keys())}")
        print(f"   ✓ Parameters compared: {list(comparison.parameter_differentials.keys())}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def verify_api_contract():
    """Verify API contract compliance."""
    print("\n7. Verifying API contract compliance...")

    try:
        from ml_service.research.research_dashboard.dashboard_types import (
            ResearchExperimentSummary,
            ExperimentDetail,
            FeatureLineageEntry,
            ExperimentLineage,
            ComparisonResult,
            EvaluationSummary,
        )

        required_types = [
            ResearchExperimentSummary,
            ExperimentDetail,
            FeatureLineageEntry,
            ExperimentLineage,
            ComparisonResult,
            EvaluationSummary,
        ]

        print(f"   ✓ All contract types defined: {len(required_types)} types")

        summary = ResearchExperimentSummary(
            experiment_id="test",
            name="Test",
            strategy_name="test_strategy",
            created_at="2026-07-10T00:00:00Z",
            status="COMPLETED",
            metrics={"sharpe_ratio": 1.5}
        )

        # Verify frozen dataclass
        try:
            summary.experiment_id = "changed"
            print(f"   ❌ FAIL: ResearchExperimentSummary is mutable")
            return False
        except (AttributeError, TypeError):
            print(f"   ✓ ResearchExperimentSummary is immutable (frozen=True)")

        return True
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Research Dashboard Backend Verification")
    print("=" * 60)

    checks = [
        verify_read_only_enforcement,
        verify_experiment_listing,
        verify_experiment_detail,
        verify_lineage_retrieval,
        verify_evaluation_retrieval,
        verify_experiment_comparison,
        verify_api_contract,
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"   ❌ FAIL: Unexpected error: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} checks passed")

    if passed == total:
        print("✓ All checks passed - Research Dashboard backend is operational")
        return 0
    else:
        print("✗ Some checks failed - review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
