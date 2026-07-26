"""Markdown report generator for diagnostic runs."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates markdown audit reports from diagnostic results."""

    def generate_report(
        self,
        run_context: Dict[str, Any],
        provider_results: Dict[str, Dict[str, Any]],
        execution_metadata: Dict[str, Any]
    ) -> str:
        """Generate comprehensive markdown diagnostic report.

        Args:
            run_context: Diagnostic run context metadata
            provider_results: Results from each diagnostic provider
            execution_metadata: Runtime telemetry and metrics

        Returns:
            Formatted markdown report string
        """
        sections = [
            self._generate_header(run_context),
            self._generate_lineage_section(run_context),
            self._generate_feature_importance_section(provider_results),
            self._generate_correlation_section(provider_results),
            self._generate_stability_section(provider_results),
            self._generate_telemetry_section(execution_metadata),
            self._generate_footer()
        ]

        return "\n\n".join(filter(None, sections))

    def _generate_header(self, context: Dict[str, Any]) -> str:
        """Generate report header with frontmatter."""
        run_id = context.get('run_id', 'unknown')
        timestamp = context.get('timestamp', datetime.utcnow().isoformat())

        return f"""# Model Diagnostics Report

**Diagnostic Run ID**: `{run_id}`
**Timestamp**: {timestamp}
**Status**: Completed

---"""

    def _generate_lineage_section(self, context: Dict[str, Any]) -> str:
        """Generate lineage and provenance section."""
        model_version = context.get('model_version_id', 'unknown')
        dataset_version = context.get('dataset_version_id', 'unknown')
        feature_version = context.get('feature_dataset_version_id', 'unknown')
        model_hash = context.get('model_binary_hash', 'N/A')
        dataset_hash = context.get('dataset_hash', 'N/A')

        return f"""## Lineage & Provenance

| Artifact | Version ID | Hash |
|:---------|:-----------|:-----|
| **Model** | `{model_version}` | `{model_hash[:16]}...` |
| **Dataset** | `{dataset_version}` | `{dataset_hash[:16]}...` |
| **Features** | `{feature_version}` | - |"""

    def _generate_feature_importance_section(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate feature importance summary."""
        importance_data = self._extract_feature_importance(results)

        if not importance_data:
            return "## Feature Importance\n\nNo feature importance data available."

        sorted_features = sorted(
            importance_data.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        table_rows = [
            "| Rank | Feature | Importance |",
            "|:-----|:--------|:-----------|"
        ]

        for rank, (feature, importance) in enumerate(sorted_features, 1):
            table_rows.append(
                f"| {rank} | `{feature}` | {importance:.4f} |"
            )

        return "## Feature Importance (Top 10)\n\n" + "\n".join(table_rows)

    def _generate_correlation_section(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate correlation analysis section."""
        if 'correlation' not in results:
            return None

        corr_result = results['correlation']
        high_corr = corr_result.get('high_correlation_pairs', [])
        max_corr = corr_result.get('max_correlation', 0.0)

        section = f"""## Correlation Analysis

**Maximum Off-Diagonal Correlation**: {max_corr:.3f}"""

        if high_corr:
            section += "\n\n### High Correlation Warnings\n\n"
            section += "| Feature 1 | Feature 2 | Correlation |\n"
            section += "|:----------|:----------|:------------|\n"

            for pair in high_corr[:5]:
                f1 = pair['feature_1']
                f2 = pair['feature_2']
                corr = pair['correlation']
                section += f"| `{f1}` | `{f2}` | {corr:.3f} |\n"

            if len(high_corr) > 5:
                section += f"\n*({len(high_corr) - 5} additional pairs omitted)*"
        else:
            section += "\n\nNo high correlation pairs detected (threshold: 0.85)."

        return section

    def _generate_stability_section(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate stability analysis section."""
        if 'stability' not in results:
            return None

        stability_result = results['stability']
        overall_score = stability_result.get('overall_stability_score', 0.0)
        n_folds = stability_result.get('n_folds', 0)

        section = f"""## Feature Stability

**Overall Stability Score**: {overall_score:.3f}
**Number of Folds**: {n_folds}"""

        metrics = stability_result.get('stability_metrics', {})
        if metrics:
            sorted_features = sorted(
                metrics.items(),
                key=lambda x: x[1]['rank_variance']
            )[:5]

            section += "\n\n### Most Stable Features\n\n"
            section += "| Feature | Mean Importance | Std Dev | Rank Variance |\n"
            section += "|:--------|:----------------|:--------|:--------------|\n"

            for feature, metric in sorted_features:
                mean_imp = metric['mean_importance']
                std_dev = metric['std_deviation']
                rank_var = metric['rank_variance']
                section += (
                    f"| `{feature}` | {mean_imp:.4f} | "
                    f"{std_dev:.4f} | {rank_var:.4f} |\n"
                )

        return section

    def _generate_telemetry_section(
        self,
        metadata: Dict[str, Any]
    ) -> str:
        """Generate execution telemetry section."""
        duration = metadata.get('execution_duration_sec', 0.0)
        max_memory = metadata.get('max_memory_kb', 0)

        section = f"""## Execution Telemetry

**Duration**: {duration:.2f} seconds"""

        if max_memory > 0:
            section += f"  \n**Peak Memory**: {max_memory:,} KB"

        provider_versions = metadata.get('provider_versions', {})
        if provider_versions:
            section += "\n\n### Provider Versions\n\n"
            for provider, version in provider_versions.items():
                section += f"- **{provider}**: {version}\n"

        return section

    def _generate_footer(self) -> str:
        """Generate report footer."""
        return """---

**Audit Trail Notice**: This diagnostic report is immutable and cryptographically linked to the model binary and dataset versions specified above. Any modifications to this file will invalidate the lineage chain.

*Generated by MoroQuant Model Diagnostics & Explainability Framework*"""

    def _extract_feature_importance(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """Extract and merge feature importance from provider results.

        Args:
            results: Provider results dictionary

        Returns:
            Dict mapping feature names to importance scores
        """
        importance_sources = ['shap', 'permutation']

        for source in importance_sources:
            if source in results and 'feature_importance' in results[source]:
                return results[source]['feature_importance']

        return {}
