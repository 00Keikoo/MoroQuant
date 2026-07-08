"""Types for evaluation engine."""

from dataclasses import dataclass
from typing import List


@dataclass
class StrategyScore:
    """Enriched strategy evaluation with all quant metrics."""
    config_id: str

    # Core metrics from StrategyResult
    total_return: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    trade_count: int

    # Additional computed metrics
    profit_factor: float
    sortino_ratio: float
    expectancy: float

    # Risk-adjusted composite score
    final_score: float


@dataclass
class EvaluationResult:
    """Complete evaluation result for an experiment."""
    experiment_id: str
    strategy_scores: List[StrategyScore]
    ranking: List[str]  # config_ids sorted best to worst
    best_strategy_id: str
    worst_strategy_id: str
    overall_risk_score: float
