"""Research Analytics Implementation - Sprint 3.9C-6

Computes standardized statistical metrics over EvaluationResult streams.
"""

import math
from typing import List, Tuple
from ml_service.research.evaluation.models import EvaluationResult
from ml_service.research.reporting.interfaces import ResearchAnalytics
from ml_service.research.reporting.models import ResearchReport


class DefaultResearchAnalytics(ResearchAnalytics):
    """Default implementation of ResearchAnalytics computing standard quantitative metrics.

    Calculates win rate, average return, cumulative return, profit factor, max drawdown,
    Sharpe ratio, and Sortino ratio without portfolio or database coupling.
    """

    def evaluate(self, results: List[EvaluationResult], experiment_id: str) -> ResearchReport:
        """Evaluate a list of evaluation results and return an immutable ResearchReport.

        Args:
            results: List of individual evaluation scorecards.
            experiment_id: Unique identifier for the experiment/model configuration.

        Returns:
            ResearchReport: The compiled immutable research analytics scorecard.
        """
        if not results:
            return ResearchReport(
                experiment_id=experiment_id,
                total_signals=0,
                win_rate=0.0,
                average_return=0.0,
                total_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                profit_factor=0.0,
                metrics=()
            )

        total_signals = len(results)

        # 1. Win Rate
        correct_signals = sum(1 for r in results if r.is_correct)
        win_rate = correct_signals / total_signals

        # 2. Returns
        returns = [r.forward_return for r in results]
        average_return = sum(returns) / total_signals

        # Cumulative/Total Return (standard additive return sum)
        total_return = sum(returns)

        # 3. Profit Factor
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]
        total_profit = sum(wins)
        total_loss = abs(sum(losses))

        if total_loss > 0:
            profit_factor = total_profit / total_loss
        else:
            profit_factor = float('inf') if total_profit > 0 else 0.0

        # 4. Max Drawdown (Path-dependent metric: requires chronological sorting)
        sorted_results = sorted(results, key=lambda x: x.signal_timestamp)
        equity = 1.0
        peak = 1.0
        max_drawdown = 0.0

        # Multiplicative equity curve simulation
        for r in sorted_results:
            equity *= (1.0 + r.forward_return)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0.0
            if dd > max_drawdown:
                max_drawdown = dd

        # Additive equity curve simulation as an extra metric
        add_equity = 1.0
        add_peak = 1.0
        max_add_dd = 0.0
        for r in sorted_results:
            add_equity += r.forward_return
            if add_equity > add_peak:
                add_peak = add_equity
            add_dd = (add_peak - add_equity) / add_peak if add_peak > 0 else 0.0
            if add_dd > max_add_dd:
                max_add_dd = add_dd

        # 5. Sharpe Ratio & Sortino Ratio
        if total_signals > 1:
            # Mean and Population Standard Deviation
            mean_return = average_return
            variance = sum((x - mean_return) ** 2 for x in returns) / total_signals
            std_return = math.sqrt(variance)

            # Annualized Sharpe (standard 252 multiplier)
            sharpe_ratio = (mean_return / std_return) * math.sqrt(252) if std_return > 0 else 0.0

            # Sortino Downside Deviation (using negative returns relative to their own mean)
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                neg_mean = sum(negative_returns) / len(negative_returns)
                neg_variance = sum((x - neg_mean) ** 2 for x in negative_returns) / len(negative_returns)
                downside_std = math.sqrt(neg_variance)
                sortino_ratio = (mean_return / downside_std) * math.sqrt(252) if downside_std > 0 else 0.0
            else:
                sortino_ratio = sharpe_ratio
        else:
            sharpe_ratio = 0.0
            sortino_ratio = 0.0

        # Compile extra metrics into tuple of key-value pairs
        metrics_list = [
            ("total_signals", float(total_signals)),
            ("correct_signals", float(correct_signals)),
            ("total_profit", float(total_profit)),
            ("total_loss", float(total_loss)),
            ("max_drawdown_additive", float(max_add_dd)),
        ]
        metrics = tuple(metrics_list)

        return ResearchReport(
            experiment_id=experiment_id,
            total_signals=total_signals,
            win_rate=win_rate,
            average_return=average_return,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            metrics=metrics
        )
