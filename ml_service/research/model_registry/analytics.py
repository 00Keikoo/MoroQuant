"""Analytics layer for model registry - pure functions only."""

from typing import Dict, List, Any, Optional
from ml_service.research.model_registry.model_types import ModelVersionMetadata, ModelEvaluation


def compare_models(models: List[ModelVersionMetadata]) -> Dict[str, Any]:
    """Compare multiple models by evaluation metrics."""
    if not models:
        return {'error': 'No models provided'}

    comparisons = []
    for model in models:
        if not model.evaluation:
            continue

        comparisons.append({
            'model_version_id': model.model_version_id,
            'symbol': model.symbol,
            'timeframe': model.timeframe,
            'algorithm': model.algorithm,
            'sharpe_ratio': model.evaluation.sharpe_ratio,
            'max_drawdown': model.evaluation.max_drawdown,
            'ece': model.evaluation.ece,
            'brier_score': model.evaluation.brier_score,
            'win_rate': model.evaluation.win_rate,
            'profit_factor': model.evaluation.profit_factor,
            'sortino_ratio': model.evaluation.sortino_ratio,
            'trade_count': model.evaluation.trade_count,
            'lifecycle_state': model.lifecycle_state.value
        })

    if not comparisons:
        return {'error': 'No models with evaluations'}

    best_sharpe = max(comparisons, key=lambda x: x['sharpe_ratio'])
    best_sortino = max(comparisons, key=lambda x: x['sortino_ratio'])
    best_win_rate = max(comparisons, key=lambda x: x['win_rate'])
    lowest_drawdown = max(comparisons, key=lambda x: x['max_drawdown'])

    return {
        'comparison_table': comparisons,
        'best_sharpe': best_sharpe['model_version_id'],
        'best_sortino': best_sortino['model_version_id'],
        'best_win_rate': best_win_rate['model_version_id'],
        'lowest_drawdown': lowest_drawdown['model_version_id'],
        'count': len(comparisons)
    }


def production_readiness(model: ModelVersionMetadata) -> Dict[str, Any]:
    """Assess production readiness per ADR-013 quality gate."""
    if not model.evaluation:
        return {
            'ready': False,
            'reason': 'No evaluation metrics available',
            'checks': {}
        }

    checks = {
        'sharpe_ratio': {
            'value': model.evaluation.sharpe_ratio,
            'threshold': 1.5,
            'passed': model.evaluation.sharpe_ratio >= 1.5
        },
        'max_drawdown': {
            'value': model.evaluation.max_drawdown,
            'threshold': -0.15,
            'passed': model.evaluation.max_drawdown >= -0.15
        },
        'ece': {
            'value': model.evaluation.ece,
            'threshold': 0.05,
            'passed': model.evaluation.ece < 0.05
        },
        'brier_score': {
            'value': model.evaluation.brier_score,
            'threshold': 0.22,
            'passed': model.evaluation.brier_score < 0.22
        },
        'trade_count': {
            'value': model.evaluation.trade_count,
            'threshold': 100,
            'passed': model.evaluation.trade_count >= 100
        },
        'is_approved': {
            'value': model.evaluation.is_approved,
            'passed': model.evaluation.is_approved
        }
    }

    all_passed = all(check['passed'] for check in checks.values())

    return {
        'ready': all_passed,
        'model_version_id': model.model_version_id,
        'lifecycle_state': model.lifecycle_state.value,
        'checks': checks,
        'failing_checks': [k for k, v in checks.items() if not v['passed']]
    }


def ranking(models: List[ModelVersionMetadata], weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """Rank models by weighted composite score."""
    if not models:
        return []

    default_weights = {
        'sharpe_ratio': 0.30,
        'sortino_ratio': 0.20,
        'win_rate': 0.15,
        'profit_factor': 0.15,
        'max_drawdown': 0.10,
        'ece': 0.05,
        'brier_score': 0.05
    }

    weights = weights or default_weights

    ranked = []
    for model in models:
        if not model.evaluation:
            continue

        score = 0.0
        score += weights.get('sharpe_ratio', 0) * model.evaluation.sharpe_ratio
        score += weights.get('sortino_ratio', 0) * model.evaluation.sortino_ratio
        score += weights.get('win_rate', 0) * model.evaluation.win_rate
        score += weights.get('profit_factor', 0) * model.evaluation.profit_factor
        score += weights.get('max_drawdown', 0) * (1 + model.evaluation.max_drawdown)
        score += weights.get('ece', 0) * (1 - model.evaluation.ece)
        score += weights.get('brier_score', 0) * (1 - model.evaluation.brier_score)

        ranked.append({
            'model_version_id': model.model_version_id,
            'symbol': model.symbol,
            'timeframe': model.timeframe,
            'algorithm': model.algorithm,
            'composite_score': score,
            'sharpe_ratio': model.evaluation.sharpe_ratio,
            'sortino_ratio': model.evaluation.sortino_ratio,
            'win_rate': model.evaluation.win_rate,
            'lifecycle_state': model.lifecycle_state.value
        })

    ranked.sort(key=lambda x: x['composite_score'], reverse=True)

    return ranked


def lineage_summary(lineage_chain: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize lineage chain for quick review."""
    if not lineage_chain:
        return {'error': 'No lineage data provided'}

    return {
        'model': {
            'version_id': lineage_chain.get('model_version_id'),
            'model_id': lineage_chain.get('model_id'),
            'version': lineage_chain.get('version'),
            'symbol': lineage_chain.get('symbol'),
            'timeframe': lineage_chain.get('timeframe'),
            'algorithm': lineage_chain.get('algorithm')
        },
        'upstream': {
            'snapshot': lineage_chain.get('snapshot_id'),
            'dataset': lineage_chain.get('dataset_id'),
            'features': lineage_chain.get('feature_dataset_id'),
            'experiment': lineage_chain.get('experiment_id'),
            'config': lineage_chain.get('best_config_id')
        },
        'lineage_depth': 5,
        'complete': all([
            lineage_chain.get('snapshot_id'),
            lineage_chain.get('dataset_id'),
            lineage_chain.get('feature_dataset_id'),
            lineage_chain.get('experiment_id'),
            lineage_chain.get('best_config_id')
        ])
    }


def calibration_score(evaluation: ModelEvaluation) -> Dict[str, Any]:
    """Compute calibration quality score from ECE and Brier."""
    ece_score = max(0, 1 - (evaluation.ece / 0.10))
    brier_score = max(0, 1 - (evaluation.brier_score / 0.30))

    composite = (ece_score + brier_score) / 2

    return {
        'ece': evaluation.ece,
        'brier_score': evaluation.brier_score,
        'ece_score': ece_score,
        'brier_score_normalized': brier_score,
        'composite_calibration': composite,
        'grade': _calibration_grade(composite)
    }


def _calibration_grade(score: float) -> str:
    """Assign letter grade to calibration score."""
    if score >= 0.9:
        return 'A'
    elif score >= 0.8:
        return 'B'
    elif score >= 0.7:
        return 'C'
    elif score >= 0.6:
        return 'D'
    else:
        return 'F'


def risk_metrics(evaluation: ModelEvaluation) -> Dict[str, Any]:
    """Extract risk-focused metrics."""
    return {
        'max_drawdown': evaluation.max_drawdown,
        'sharpe_ratio': evaluation.sharpe_ratio,
        'sortino_ratio': evaluation.sortino_ratio,
        'profit_factor': evaluation.profit_factor,
        'win_rate': evaluation.win_rate,
        'risk_adjusted_return': evaluation.sharpe_ratio * (1 + evaluation.max_drawdown),
        'risk_category': _risk_category(evaluation.max_drawdown, evaluation.sharpe_ratio)
    }


def _risk_category(drawdown: float, sharpe: float) -> str:
    """Categorize model risk profile."""
    if drawdown >= -0.10 and sharpe >= 2.0:
        return 'LOW_RISK'
    elif drawdown >= -0.15 and sharpe >= 1.5:
        return 'MODERATE_RISK'
    elif drawdown >= -0.25 and sharpe >= 1.0:
        return 'HIGH_RISK'
    else:
        return 'EXTREME_RISK'
