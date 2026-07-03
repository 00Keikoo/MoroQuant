# Regime Execution Policy Specification
**Status**: Research Specification v1.0  
**Last Updated**: 2026-07-03  

## 1. Objective
This specification defines the formal statistical framework for MoroQuant's Regime Execution Policy. The objective is to establish mathematically rigorous, deterministic rules to decide whether execution should be permitted, sized, or restricted under specific market regimes, replacing hardcoded heuristics with a dynamic, statistically validated policy.

---

## 2. Motivation
Historically, the system utilized a hardcoded configuration heuristic (`BLOCKED_REGIMES = ["choppy_low_vol", "choppy_normal_vol"]`) to block trade execution in specific market environments. While intuitively designed to avoid range-bound markets, this heuristic lacks formal statistical justification, does not adapt to changing market conditions, and violates MoroQuant's core principle that all execution decisions must derive from versioned, mathematically justified research. This specification establishes a robust framework to replace static blocking rules with a dynamic, evidence-based policy.

---

## 3. Statistical Justification
To justify blocking or modifying execution in a given regime $r$, we must reject the hypothesis that the strategy has a positive expected edge in that regime. 
Let $X_r = \{x_{r, 1}, x_{r, 2}, \dots, x_{r, N_r}\}$ be the set of realized trade returns (measured in R-multiples or percentage return) generated under regime $r$ over a historical evaluation window.

We formulate the null hypothesis $H_0$ and alternative hypothesis $H_1$ as:
$$H_0: \mathbb{E}[X_r] \le 0$$
$$H_1: \mathbb{E}[X_r] > 0$$

If we fail to reject $H_0$ at a designated significance level $\alpha$, there is insufficient statistical evidence to assert that trading within regime $r$ is profitable. In such cases, executing signals under regime $r$ represents an unjustified risk, providing the statistical basis for modifying or suspending execution.

---

## 4. Formal Definitions
* **Market Regime ($r$)**: A discrete state classification of the market environment (e.g., $r \in \{\text{trending\_high\_vol}, \text{choppy\_low\_vol}, \dots\}$) determined by structural indicators (ADX, ATR, Volatility Profile) at signal generation.
* **Trade Return ($x_i$)**: The net financial outcome of trade $i$ normalized by the initial risk at entry (R-multiple), defined as:
  $$x_i = \frac{P_{\text{exit}, i} - P_{\text{entry}, i}}{P_{\text{entry}, i} - P_{\text{SL}, i}} \times \text{Direction}_i$$
* **Expected Value ($EV_r$)**: The arithmetic mean of normalized trade returns within regime $r$:
  $$EV_r = \mathbb{E}[X_r]$$
* **Unsuitable Regime**: A regime $r$ where the null hypothesis $H_0$ cannot be rejected, or where $EV_r$ falls below a critical threshold under specified confidence bounds.

---

## 5. Mathematical Definitions & Statistical Inference

### 5.1 Sample Mean and Standard Deviation
For a sample of size $N_r$ in regime $r$:
$$\bar{x}_r = \frac{1}{N_r} \sum_{i=1}^{N_r} x_{r,i}$$
$$s_r = \sqrt{\frac{1}{N_r - 1} \sum_{i=1}^{N_r} (x_{r,i} - \bar{x}_r)^2}$$

### 5.2 Standard Error of the Mean (Autocorrelation Adjusted)
To account for potential positive serial correlation (which underestimates standard error in financial return series), we calculate the Ljung-Box Q-statistic at lag 1. If autocorrelation is statistically significant ($p < 0.05$), we apply the Newey-West standard error correction:
$$SE_{r,\text{adj}} = SE_r \times \sqrt{1 + 2\sum_{k=1}^{L} \left(1 - \frac{k}{L+1}\right)\rho_k}$$
where $SE_r = \frac{s_r}{\sqrt{N_r}}$, $L$ is the bandwidth parameter ($L = \lfloor 4(N_r/100)^{2/9} \rfloor$), and $\rho_k$ is the autocorrelation coefficient at lag $k$.

### 5.3 Non-Parametric Bootstrap Confidence Intervals
Because financial returns exhibit fat tails (high kurtosis) that violate the normality assumptions of Student's t-test, confidence intervals are constructed using the **Percentile Bootstrap Method**:
1. Draw $B = 1000$ bootstrap samples $X^*_b$ from $X_r$ with replacement.
2. Compute the bootstrap sample mean $\bar{x}^*_b$ for each sample.
3. Sort the bootstrap means to obtain the empirical distribution.
4. Define the $(1 - \alpha)$ confidence interval $[LCI_r, \,\, UCI_r]$ as the $\alpha/2$ and $1 - \alpha/2$ percentiles of the sorted bootstrap means. For $\alpha = 0.05$:
   $$LCI_r = \bar{x}^*_{(B \cdot 0.025)}$$
   $$UCI_r = \bar{x}^*_{(B \cdot 0.975)}$$

---

## 6. Decision Rules
MoroQuant adopts a **Hybrid Execution Policy** that evaluates regimes using structural rules (statically defined) and performance-based bounds (dynamically calculated).

```
                             [ Evaluate Signal Regime ]
                                         │
                                         ▼
                            /─────────────────────────\
                           <  Is Regime Structurally   > ─── Yes ───► [ BLOCK EXECUTION ]
                            \   Blocked in Database?  /
                                         │
                                         No
                                         ▼
                            /─────────────────────────\
                           <    Sample Size Nr >= 100  > ─── No ────► [ PERMIT EXECUTION ]
                            \   for dynamic review?   /               (Baseline Risk)
                                         │
                                         Yes
                                         ▼
                            /─────────────────────────\
                           <        UCI_r < 0         > ─── Yes ───► [ BLOCK EXECUTION ]
                            \                         /
                                         │
                                         No
                                         ▼
                            /─────────────────────────\
                           <        LCI_r < 0         > ─── Yes ───► [ RESTRICT EXECUTION ]
                            \                         /               (Reduce Sizing / Scale Risk)
                                         │
                                         No
                                         ▼
                               [ PERMIT EXECUTION ]
                               (Full Risk Allocation)
```

1. **Structural Block (Static Override)**: If a regime is manually flagged as structurally untradable due to system design limits (e.g., API constraints or execution infrastructure gaps), execution is blocked.
2. **Dynamic Review**: For regimes with sufficient sample sizes ($N_r \ge 100$):
   * **Rule A (Execution Block)**: If the Upper Confidence Interval bound ($UCI_r$) is less than $0.0$, execution is completely blocked. This signifies a 97.5% statistical confidence that the expected return is negative.
   * **Rule B (Execution Sizing Reduction)**: If $UCI_r \ge 0.0$ but the Lower Confidence Interval bound ($LCI_r$) is less than $0.0$, execution is allowed but the trade size must be scaled down by a factor $S_r$:
     $$S_r = \max\left(0.1, \,\, 1.0 - \frac{|LCI_r|}{\bar{x}_r}\right)$$

---

## 7. Required Inputs
For each candidate trade signal, the execution engine requires:
1. `signal_id`: Unique identifier of the generated signal.
2. `regime`: Detected market phase label (e.g., `"choppy_low_vol"`).
3. `confidence`: Prediction model confidence score.
4. `historical_trades`: A sequence of historical trade outcomes matching the current regime $r$ over a rolling window $W$ (default: $W = 150$ trades or 90 days, whichever is larger).

---

## 8. Required Outputs
The policy engine must output an execution decision object:
1. `execution_permitted`: Boolean flag (`True` / `False`).
2. `sizing_multiplier`: Floating-point scalar $S_r \in [0.0, 1.0]$ representing risk allocation scaling.
3. `statistical_metadata`: Dictionary containing computed $N_r$, $\bar{x}_r$, $LCI_r$, $UCI_r$, and autocorrelation diagnostics.

---

## 9. Required Sample Sizes
To prevent premature classification based on statistical noise:
* **Minimum Sample Size ($N_{\text{min}}$)**: No dynamic adjustments or blocks may be applied unless a regime has recorded at least **100 closed trades** ($N_r \ge 100$). This threshold guarantees that the non-parametric bootstrap distribution has sufficient data points to accurately estimate the tail percentiles (percentile bootstrap intervals are unstable for small sample sizes).
* **Insufficient Data Fallback**: If $N_r < 100$, the regime's historical expected value is considered unproven. Sizing defaults to a baseline multiplier of $1.0$ (or $0.5$ if structurally flagged as high risk) until $N_{\text{min}}$ is met.

---

## 10. Statistical Confidence Requirements
* The significance level for hypothesis testing is set to $\alpha = 0.05$ (95% confidence level).
* Bootstrap replicates must satisfy $B \ge 1000$ to ensure convergence of the interval boundaries.

---

## 11. Expected Value Analysis
Every 24 hours, the expected value $EV_r$ for each active market regime must be recalculated. If a regime's performance demonstrates $UCI_r < 0.0$, it indicates the strategy is failing to capture alpha in that regime. 
The expected value decomposition must isolate:
* **Gross Edge**: Expected return before friction.
* **Net Edge**: Expected return after slippage and execution costs.
A regime may only be unblocked if its Net Edge satisfies $EV_r > 0$ with statistical significance.

---

## 12. Regime Transition Policy
* **Symmetric Transition Bounds**: To prevent state chattering and ensure statistical rigor, symmetric criteria are applied to both blocking and recovery.
* **Transition to Blocked**: A regime transition from Allowed $\rightarrow$ Blocked occurs immediately if $UCI_r < 0.0$ at the rolling 24-hour evaluation.
* **Transition to Allowed (Recovery)**: A blocked regime is reinstated to Allowed (or Restricted) only if backtested performance over a validation sample of size $N_{\text{test}} \ge 50$ shows:
  $$LCI_{r, \text{test}} \ge 0.0 \quad (\alpha = 0.05 \text{ confidence level})$$
  This requires statistically significant proof of recovery at the same confidence level before reinstatement.

---

## 13. Execution Policy
* **Blocked Regimes**: Sizing multiplier $S_r = 0.0$. Signals are logged, categorized as "Regime Blocked", and bypassed.
* **Restricted Regimes**: Sizing multiplier $0.1 \le S_r < 1.0$. Sizing is scaled dynamically based on bootstrap error bounds.
* **Unrestricted Regimes**: Sizing multiplier $S_r = 1.0$.

---

## 14. Relationship with Execution Audit Framework
This Regime Execution Policy serves as an operational extension of the [Execution Audit Framework](execution_audit_framework.md). 
1. The **Execution Audit Framework** functions as an offline monitoring and reporting engine that calculates path-dependent parameters (MAE, MFE, expected value, and regime failure).
2. The audit output feeds the parameters (expected value, variance, sample counts) directly into the **Regime Execution Policy**.
3. **Approval Flow**: Any automated transition recommendation to block or unblock a regime must generate a signed audit proposal. This proposal requires human administrator approval via the Trade Dashboard before updating the active production parameters.

---

## 15. Failure Modes
* **Regime Classification Drift**: If the underlying ML classifier changes its definitions, historical trade counts for that regime label become invalid, leading to incorrect statistical significance.
* **Sample Deprivation**: Rare regimes (e.g., extreme volatility shocks) may take months to accumulate $N_{\text{min}} \ge 100$, delaying necessary risk interventions.

---

## 16. Limitations
* **Bootstrap Bias**: Standard percentile bootstrap intervals can be biased if the underlying distribution is heavily skewed. When skewness exceeds $1.5$ in magnitude, a bias-corrected and accelerated (BCa) bootstrap interval should be used.
* **Regime Overlap**: Markets do not transition cleanly; brief periods of mixed indicators may lead to misclassified trades.

---

## 17. References
1. Efron, B., & Tibshirani, R. J. (1994). *An Introduction to the Bootstrap*. CRC Press.
2. Newey, W. K., & West, K. D. (1987). *A Simple, Positive Semi-definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix*. Econometrica.
3. MoroQuant Research. (2026). *[Execution Audit Framework](execution_audit_framework.md)*.

---

## 18. Revision History
* **v1.0 (Draft)**: Initial release defining the mathematical and decision rules using Student's t-test and a minimum sample size of 30.
* **v1.1 (Pending Final Approval)**: 
  * Replaced Student's t-test with a Non-Parametric Percentile Bootstrap approach to account for heavy tails (leptokurtosis) in trading returns.
  * Increased minimum sample size threshold $N_{\text{min}}$ from 30 to 100 to ensure bootstrap stability.
  * Fixed unit mismatch in Rule A (changed threshold from $0.05$ significance check to $UCI_r < 0.0$ R-multiple return check).
  * Harmonized regime transition policy to require symmetric statistical significance ($\alpha = 0.05$) for both blocking and unblocking.
  * Added Newey-West standard error adjustments for cases with significant autocorrelation.
