"""Service layer for Research Dashboard orchestration."""

import json
from typing import Optional, List

from ml_service.research.research_dashboard.repository import ResearchDashboardRepository
from ml_service.research.research_dashboard.dashboard_types import (
    ResearchExperimentSummary,
    ExperimentDetail,
    ExperimentLineage,
    FeatureLineageEntry,
    EvaluationSummary,
)


class ResearchDashboardService:
    """Orchestrates research dashboard queries across modules."""

    def __init__(self, repository: Optional[ResearchDashboardRepository] = None):
        self.repository = repository or ResearchDashboardRepository()

    def list_experiments(
        self,
        strategy_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[ResearchExperimentSummary]:
        """List all experiments with summary metrics."""
        experiments = self.repository.list_experiments(strategy_filter, status_filter)

        summaries = []
        for exp in experiments:
            results = self.repository.get_experiment_results(exp['experiment_id'])

            if results:
                best_result = max(results, key=lambda r: r['sharpe'])
                metrics = {
                    'sharpe_ratio': best_result['sharpe'],
                    'max_drawdown': best_result['max_drawdown'],
                    'total_return': best_result['pnl']
                }
            else:
                metrics = {}

            summaries.append(ResearchExperimentSummary(
                experiment_id=exp['experiment_id'],
                name=exp['experiment_id'],
                strategy_name='unknown',
                created_at=exp['created_at'],
                status='COMPLETED',
                metrics=metrics
            ))

        return summaries

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentDetail]:
        """Get detailed experiment configuration and results."""
        exp = self.repository.get_experiment(experiment_id)
        if not exp:
            return None

        configs = self.repository.get_experiment_configs(experiment_id)

        if configs:
            first_config = configs[0]
            parameters = {
                'threshold_long': first_config['threshold_long'],
                'threshold_short': first_config['threshold_short'],
                'regime_filter': first_config.get('regime_filter')
            }
        else:
            parameters = {}

        return ExperimentDetail(
            experiment_id=exp['experiment_id'],
            name=exp['experiment_id'],
            description=f"Experiment using snapshot {exp['snapshot_id']}",
            strategy_name='unknown',
            parameters=parameters,
            created_at=exp['created_at'],
            status='COMPLETED',
            duration_seconds=0.0,
            git_commit='unknown'
        )

    def get_lineage(self, experiment_id: str) -> Optional[ExperimentLineage]:
        """Trace lineage from experiment back to source dataset and features."""
        exp = self.repository.get_experiment(experiment_id)
        if not exp:
            return None

        snapshot_id = exp['snapshot_id']

        dataset = self.repository.get_dataset_by_snapshot_id(snapshot_id)
        if not dataset:
            return ExperimentLineage(
                experiment_id=experiment_id,
                source_dataset_id=snapshot_id,
                source_dataset_fingerprint='unknown',
                feature_datasets=[]
            )

        feature_datasets = self.repository.get_feature_datasets_by_source(dataset['dataset_id'])

        lineage_entries = []
        for fd in feature_datasets:
            lineage_entries.append(FeatureLineageEntry(
                feature_dataset_id=fd['feature_dataset_id'],
                feature_version_id=fd['feature_version_id'],
                fingerprint=fd['fingerprint']
            ))

        return ExperimentLineage(
            experiment_id=experiment_id,
            source_dataset_id=dataset['dataset_id'],
            source_dataset_fingerprint=dataset['fingerprint'],
            feature_datasets=lineage_entries
        )

    def get_evaluation(self, experiment_id: str) -> Optional[EvaluationSummary]:
        """Get evaluation summary for an experiment."""
        results = self.repository.get_experiment_results(experiment_id)
        if not results:
            return None

        total_trades = sum(r['trade_count'] for r in results)
        win_rate = sum(r['winrate'] * r['trade_count'] for r in results) / total_trades if total_trades > 0 else 0.0

        avg_return = sum(r['pnl'] for r in results) / len(results) if results else 0.0
        avg_trades = total_trades / len(results) if results else 0.0
        average_trade_return = avg_return / avg_trades if avg_trades > 0 else 0.0

        best_result = max(results, key=lambda r: r['sharpe'])
        profit_factor = 1.0 + best_result['pnl']

        return EvaluationSummary(
            experiment_id=experiment_id,
            total_trades=total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_trade_return=average_trade_return,
            daily_return_volatility=None,
            information_coefficient=None
        )
