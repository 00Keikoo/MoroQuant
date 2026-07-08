"""Core registry operations for experiment persistence and comparison."""

from datetime import datetime
from typing import List, Optional

from ml_service.research.experiment_engine.types import ExperimentResult, StrategyConfig, StrategyResult
from ml_service.research.experiment_registry.types import StoredExperiment, ComparisonResult
from ml_service.research.experiment_registry import storage


def save_experiment(experiment_result: ExperimentResult):
    """Save experiment to persistent storage.

    Args:
        experiment_result: Experiment result from experiment engine
    """
    storage.init_schema()

    created_at = datetime.utcnow().isoformat()

    storage.insert_experiment(
        experiment_id=experiment_result.experiment_id,
        snapshot_id=experiment_result.snapshot_id,
        created_at=created_at
    )

    for result in experiment_result.results:
        storage.insert_result(
            experiment_id=experiment_result.experiment_id,
            config_id=result.config_id,
            pnl=result.pnl,
            winrate=result.winrate,
            sharpe=result.sharpe,
            max_drawdown=result.max_drawdown,
            consistency_score=result.consistency_score,
            trade_count=result.trade_count
        )


def save_experiment_with_configs(
    experiment_result: ExperimentResult,
    configs: List[StrategyConfig]
):
    """Save experiment with strategy configs.

    Args:
        experiment_result: Experiment result from experiment engine
        configs: List of strategy configs used in experiment
    """
    storage.init_schema()

    created_at = datetime.utcnow().isoformat()

    storage.insert_experiment(
        experiment_id=experiment_result.experiment_id,
        snapshot_id=experiment_result.snapshot_id,
        created_at=created_at
    )

    for config in configs:
        storage.insert_config(
            experiment_id=experiment_result.experiment_id,
            config_id=config.config_id,
            threshold_long=config.threshold_long,
            threshold_short=config.threshold_short,
            regime_filter=config.regime_filter
        )

    for result in experiment_result.results:
        storage.insert_result(
            experiment_id=experiment_result.experiment_id,
            config_id=result.config_id,
            pnl=result.pnl,
            winrate=result.winrate,
            sharpe=result.sharpe,
            max_drawdown=result.max_drawdown,
            consistency_score=result.consistency_score,
            trade_count=result.trade_count
        )


def load_experiment(experiment_id: str) -> Optional[StoredExperiment]:
    """Load experiment from storage.

    Args:
        experiment_id: Experiment ID to load

    Returns:
        StoredExperiment if found, None otherwise
    """
    storage.init_schema()

    exp_data = storage.select_experiment(experiment_id)
    if not exp_data:
        return None

    config_rows = storage.select_configs(experiment_id)
    result_rows = storage.select_results(experiment_id)

    configs = [
        StrategyConfig(
            config_id=row['config_id'],
            threshold_long=row['threshold_long'],
            threshold_short=row['threshold_short'],
            enable_filter=False,
            regime_filter=row['regime_filter']
        )
        for row in config_rows
    ]

    results = [
        StrategyResult(
            config_id=row['config_id'],
            pnl=row['pnl'],
            winrate=row['winrate'],
            sharpe=row['sharpe'],
            max_drawdown=row['max_drawdown'],
            consistency_score=row['consistency_score'],
            trade_count=row['trade_count']
        )
        for row in result_rows
    ]

    return StoredExperiment(
        experiment_id=exp_data['experiment_id'],
        snapshot_id=exp_data['snapshot_id'],
        created_at=exp_data['created_at'],
        configs=configs,
        results=results
    )


def list_experiments() -> List[StoredExperiment]:
    """List all experiments.

    Returns:
        List of stored experiments with metadata only
    """
    storage.init_schema()

    exp_rows = storage.select_all_experiments()

    experiments = []
    for row in exp_rows:
        exp = StoredExperiment(
            experiment_id=row['experiment_id'],
            snapshot_id=row['snapshot_id'],
            created_at=row['created_at'],
            configs=[],
            results=[]
        )
        experiments.append(exp)

    return experiments


def compare_experiments(
    base_experiment_id: str,
    compare_experiment_id: str
) -> Optional[ComparisonResult]:
    """Compare two experiments.

    Args:
        base_experiment_id: Base experiment ID
        compare_experiment_id: Experiment to compare against base

    Returns:
        ComparisonResult if both experiments exist, None otherwise
    """
    storage.init_schema()

    base_exp = load_experiment(base_experiment_id)
    compare_exp = load_experiment(compare_experiment_id)

    if not base_exp or not compare_exp:
        return None

    base_pnl = sum(r.pnl for r in base_exp.results)
    compare_pnl = sum(r.pnl for r in compare_exp.results)

    base_winrate = sum(r.winrate for r in base_exp.results) / len(base_exp.results) if base_exp.results else 0.0
    compare_winrate = sum(r.winrate for r in compare_exp.results) / len(compare_exp.results) if compare_exp.results else 0.0

    base_sharpe = sum(r.sharpe for r in base_exp.results) / len(base_exp.results) if base_exp.results else 0.0
    compare_sharpe = sum(r.sharpe for r in compare_exp.results) / len(compare_exp.results) if compare_exp.results else 0.0

    base_consistency = sum(r.consistency_score for r in base_exp.results) / len(base_exp.results) if base_exp.results else 0.0
    compare_consistency = sum(r.consistency_score for r in compare_exp.results) / len(compare_exp.results) if compare_exp.results else 0.0

    base_drawdown = max((r.max_drawdown for r in base_exp.results), default=0.0)
    compare_drawdown = max((r.max_drawdown for r in compare_exp.results), default=0.0)

    return ComparisonResult(
        base_experiment_id=base_experiment_id,
        compare_experiment_id=compare_experiment_id,
        pnl_diff=compare_pnl - base_pnl,
        sharpe_diff=compare_sharpe - base_sharpe,
        winrate_diff=compare_winrate - base_winrate,
        consistency_diff=compare_consistency - base_consistency,
        drawdown_diff=compare_drawdown - base_drawdown
    )
