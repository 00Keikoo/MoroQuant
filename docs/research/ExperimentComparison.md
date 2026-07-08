# Experiment Comparison Engine Design

## Overview
The Experiment Comparison Engine provides quantitative tools to compare, rank, and select machine learning trading models. Rather than relying solely on overall backtest profitability, the comparison engine analyzes risk-adjusted metrics, classification calibration, performance stability across market regimes, and the robustness of the model's features.

---

## 1. Risk-Adjusted and Performance Metrics
The engine calculates standard quantitative metrics to evaluate performance:

- **Sharpe Ratio (Annualized)**: Measures excess return per unit of total risk.
  $$\text{Sharpe} = \frac{\mathbb{E}[R_p - R_f]}{\sigma_p} \times \sqrt{N}$$
  where $R_p$ is portfolio return, $R_f$ is risk-free rate, $\sigma_p$ is volatility of returns, and $N$ is trading periods per year.
- **Sortino Ratio (Annualized)**: Focuses only on negative returns (downside deviation).
  $$\text{Sortino} = \frac{\mathbb{E}[R_p - R_f]}{\sigma_{down}} \times \sqrt{N}$$
  where $\sigma_{down}$ is the standard deviation of negative portfolio returns.
- **Calmar Ratio**: Measures return relative to maximum drawdown.
  $$\text{Calmar} = \frac{\text{Annualized Return}}{\lvert \text{Max Drawdown} \rvert}$$
- **Profit Factor**: Ratio of gross profits to gross losses.
  $$\text{Profit Factor} = \frac{\sum \text{Profits}}{\sum \text{Losses}}$$
- **Win Rate**: The proportion of trades that resulting in positive return.
- **Max Drawdown (Max DD)**: Peak-to-trough drop in the equity curve.
  $$\text{MDD} = \max_{\tau \in [0, T]} \left( \frac{H_\tau - Y_\tau}{H_\tau} \right)$$
  where $H_\tau$ is the historical peak equity up to time $\tau$, and $Y_\tau$ is the current equity.

---

## 2. Model Calibration and Probabilistic Evaluation
Because MoroQuant's models output probability estimates for direction classification, we evaluate model calibration to prevent overconfidence in execution sizing:

- **ECE (Expected Calibration Error)**: Measures the gap between predicted probabilities and actual outcomes.
  $$\text{ECE} = \sum_{m=1}^{M} \frac{\lvert B_m \rvert}{N} \left\lvert \text{acc}(B_m) - \text{conf}(B_m) \right\rvert$$
  where predictions are divided into $M$ equally spaced bins $B_m$, and $\text{acc}$ and $\text{conf}$ are accuracy and confidence of bin $B_m$.
- **Brier Score**: Measures the accuracy of probabilistic predictions (equivalent to mean squared error).
  $$\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2$$
  where $p_i$ is the predicted probability and $y_i$ is the actual binary outcome ($0$ or $1$).

---

## 3. Regime Performance and Market Conditions
A model that performs well in a trending market might experience significant losses in a mean-reverting market. The engine segments backtest returns by market regime indices:

| Market Condition | Regime Classification Method | Metric Target |
| :--- | :--- | :--- |
| **High Volatility Trend** | ATR ratio > 1.5 AND ADX > 25 | Maximize Sharpe, minimize Calmar erosion |
| **Low Volatility Trend** | ATR ratio < 0.8 AND ADX > 20 | Consistent Profit Factor |
| **High Volatility Range** | ATR ratio > 1.5 AND ADX < 15 | Win Rate validation |
| **Low Volatility Range** | ATR ratio < 0.8 AND ADX < 15 | Avoid execution over-trading (decay) |

The comparison dashboard plots a **Radar Chart** displaying the Sharpe ratio across these regimes for comparison.

---

## 4. Feature Importance Comparison
The engine compares feature dependencies between models to detect overfitting or data drift dependencies:
- **SHAP (SHapley Additive exPlanations) Values**: Measures each feature's contribution to the prediction output.
- **Gain Importance**: Measures the relative contribution of each feature to the tree-split loss reduction.
- **Stability Index**: Calculates if feature importance is concentrated in a few features or spread out, which provides more resilience to market shifts.

---

## 5. Robustness and Stability Testing
To ensure the model is robust to market shifts, the comparison engine runs stress tests:

```
[Candidate Model]
       │
       ├────────► Monte Carlo Permutation (Resample return order 10,000x)
       │
       ├────────► Historical Replay (Test against historical crises)
       │
       └────────► Parameter Sensitivity (Vary TP/SL limits by +/- 15%)
```

- **Monte Carlo Permutation**: Permutes the order of backtest trades $10,000$ times to compute the distribution of potential max drawdowns and calculate a $95\%$ Value at Risk (VaR).
- **Historical Replay**: Replays execution logs against specific market events (e.g., FTX crash, March 2020 liquidity shock) to verify risk mitigation rules.
- **Parameter Sensitivity Analysis**: Evaluates how performance changes when TP/SL targets are varied by $\pm 5\%, 10\%, 15\%$. High sensitivity indicates the model may be overfitted.
