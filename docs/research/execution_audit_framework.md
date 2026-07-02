1. Research Goal

The goal of this research project is to design a mathematically rigorous, deterministic Execution AuditFramework for MoroQuant. While validation processes verify the integrity of the raw transaction data, thisframework interprets the path-dependent performance of the system to identify the precise drivers of alphadegradation. By analyzing the interaction between model signals, market dynamics (regimes), and executionpolicies (SL, TP, trailing stop, and break-even rules), the framework will isolate whether performance lossesstem from structural prediction failures or sub-optimal risk management policies.──────

2. Statistical Justification

Standard performance metrics (such as the Sharpe Ratio, Sortino Ratio, and Win Rate) are summary statisticsthat lack path-dependent detail. A strategy can generate a negative Sharpe Ratio due to a poor predictionmodel (low entry signal edge) or a poorly calibrated execution policy (e.g., exiting trades prematurely orsetting stops too wide).

To isolate these factors, we decompose trade trajectories using Maximum Adverse Excursion (MAE) and MaximumFavorable Excursion (MFE). These path-dependent parameters act as joint probability distributions of maximumpotential profit and risk. Modeling these distributions alongside entry confidence levels and market regimeclasses allows us to determine if execution rules are working against the model's predictive edge.──────

3. Mathematical Formulation

Let N be the total number of closed trades in the audit sample. For each trade i ∈ {1,…,N}:

•

S
 0,i

is the entry price.•Sclose,i

is the exit price.

• Dᵢ ∈ {1  (Long), - 1  (Short) } is the trade direction.•S        - Sclose,i    0,iP           = D ·───────────────realized,i    i      S0,i

is the realized return.

•

           S (t) - S
            i       0,i
P(t)  = D ·────────────
    i    i     S
                0,i

is the running return at time

t ∈ ⎡t       ,t      ⎤
    ⎣ entry,i  exit,i⎦

.

• MAEᵢ = minₜ P(t)ᵢ is the Maximum Adverse Excursion (typically ≤0).• MFEᵢ = maxₜ P(t)ᵢ is the Maximum Favorable Excursion (typically ≥0).──────

4. Audit Metrics

Average MAE & MFE

‾‾‾    1  N              ‾‾‾    1  N
MAE = ─── ∑   MAEᵢ  and  MFE = ─── ∑   MFEᵢ
       N i=1                    N i=1

Profit Capture Ratio (PCR)

       ⎧     ⎛        ⎛    P          ⎞⎞
       ⎪     ⎜        ⎜     realized,i⎟⎟
PCRᵢ = ⎨ max ⎜0.0,min ⎜1.0,───────────⎟⎟  if  MFEᵢ > 0
       ⎪     ⎝        ⎝       MFEᵢ    ⎠⎠
       ⎩               0.0                if  MFEᵢ ≤ 0

‾‾‾    1  N
PCR = ─── ∑   PCRᵢ
       N i=1

Profit Leakage (PL)

Profit Leakage measures the proportion of maximum favorable return that was given back before exit:

PLᵢ = MFEᵢ - max ⎛0.0,P          ⎞
                 ⎝     realized,i⎠

‾‾    1  N
PL = ─── ∑   PLᵢ
      N i=1

Execution Quality Score (EQS)

A metric assessing how well the execution policy protected the trade from maximum drawdown while realizingmaximum potential gains:

            ⎛           |MAEᵢ|      ⎞
EQSᵢ = PCRᵢ·⎜1.0 - ─────────────────⎟
            ⎝      |MAEᵢ| + MFEᵢ + ε⎠

Where ε = 10⁻⁶ prevents division by zero.

Execution Efficiency (EE)

        P
         realized,i
EEᵢ = ───────────────
      MFEᵢ - MAEᵢ + ε

Holding Time Distribution

Median Hold Time = Median ⎛{t       - t       }ᴺᵢ₌₁⎞
                          ⎝  exit,i    entry,i     ⎠

Drawdown Distribution

Max Drawdown (Trade  i

Risk-to-Reward Distribution (Realized vs. Intended)

                │Target  - S   │
                │      i    0,i│
Intended R:R  = ────────────────
            i    │Stop  - S   │
                 │    i    0,i│

                 P          ·𝕀⎛P           > 0⎞
                  realized,i  ⎝ realized,i    ⎠
Realized R:Rᵢ = ────────────────────────────────
                │P          │·𝕀⎛P           < 0⎞
                │ realized,i│  ⎝ realized,i    ⎠

Model/Execution (M/E) Classification Matrix

Trades are categorized into one of four states based on a prediction threshold

θ
 signal

(e.g., 1.0% or 1 × average trading fee) and an execution capture threshold

θ
 pcr

(typically 0.50):

         ⎧ MC/EC                         if  MFEᵢ ≥ θ        AND  PCRᵢ ≥ θ
         ⎪                                           signal               pcr
         ⎪ MC/EW                         if  MFEᵢ ≥ θ        AND  PCRᵢ < θ
         ⎪                                           signal               pcr
Classᵢ = ⎨ MW/EC          if  MFEᵢ < θ        AND  P           = MAEᵢ  (Stopped out cleanly)
         ⎪                            signal        realized,i
         ⎪ MW/EW  if  MFEᵢ < θ        AND  P           < MAEᵢ - Slippage         (Bad execution/slip)
         ⎩                    signal        realized,i                  allowed

Expected Value (EV) Decomposition

     ⎛           ‾     ⎞   ⎛           ‾     ⎞   ⎛           ‾     ⎞   ⎛           ‾     ⎞
EV = ⎝%(MC/EC) × RMC/EC⎠ + ⎝%(MC/EW) × RMC/EW⎠ + ⎝%(MW/EC) × RMW/EC⎠ + ⎝%(MW/EW) × RMW/EW⎠

Where

‾
Rclass

is the mean realized return of that specific category.──────

5. Failure Pattern Detection

The system evaluates the metrics using deterministic rules to identify specific operational issues:

                  ┌──────────────────────────────┐
                  │   Execution Audit Engine     │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
 ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
 │Trailing Early │       │ Stop Loss Wide│       │Profit Leakage │
 ├───────────────┤       ├───────────────┤       ├───────────────┤
 │ MFE >= 2%     │       │ MAE < -4%     │       │ Avg PCR < 35% │
 │ PCR < 30%     │       │ Exit == SL    │       │ Avg PL > 1.5% │
 └───────────────┘       └───────────────┘       └───────────────┘

Trailing Too Early:

MFEᵢ ≥ 2 × Intended Targetᵢ  AND  PCRᵢ < 0.30  AND  Exit Reasonᵢ = 'Trailing Stop'

Trailing Too Late:

MFEᵢ ≥ 1.5 × Intended Targetᵢ  AND  PLᵢ > 0.8 × MFEᵢ  AND  Exit Reasonᵢ = 'Stop Loss' (at a loss)

Stop-Loss (SL) Too Tight:

|MAEᵢ| ≥ |Stopᵢ|  AND  Exit Reasonᵢ = 'Stop Loss'  AND  MFE          ≥ Targetᵢ

                                                           t>t    ,i
                                                              exit

(Requires tracking post-exit asset trajectories for a time window equal to the strategy's average holdingtime).4. Stop-Loss (SL) Too Wide:

‾‾‾               ‾‾‾
MAElosses > 2.5 × MFEwins  AND  Exit Reason = 'Stop Loss'

5. Take-Profit (TP) Too Close (Under-targeting):

Exit Reasonᵢ = 'Take Profit'  AND  MFE          ≥ 2 × P
                                      t>t    ,i        realized,i
                                         exit

6. Take-Profit (TP) Too Far (Over-targeting):

MFEᵢ ≥ 0.9 × Targetᵢ  AND  P           ≤ 0.0  AND  Exit Reasonᵢ = 'Stop Loss'
                            realized,i

7. Severe Profit Leakage:

‾‾‾              ‾‾         ‾‾‾‾‾‾‾‾‾
PCR < 0.35  AND  PL > 1.5 × P
                             realized

8. Fat-Tail Losses:

Kurtosis ⎛{P          }ᴺᵢ₌₁⎞ > 4.0  AND  Skewness ⎛{P          }ᴺᵢ₌₁⎞ < -1.5
         ⎝  realized,i     ⎠                      ⎝  realized,i     ⎠

9. Regime Failure:

EV          < 0.0  AND  Win Rate          < 0.30
  Regime  R                     Regime  R

10. Confidence Failure:

ρ⎛Confidence,P        ⎞ ≤ 0.0  (Spearman correlation between confidence score and return is

neutral/negative)⎝            realized⎠

Execution Drift:

EEₜ < EEₜ₋₁ - 1.96 × SD (EEₜ₋₁)

──────

6. Recommendation Engine

The engine generates operational recommendations based on the following deterministic rules:

• Rule 1: Optimize Trailing Stop Distance• Condition: Ratio(MC/EW) ≥ 0.25 AND

‾‾         ‾‾‾
PL ≥ 0.5 × MFE

*   *Recommendation:* **TIGHTEN_TRAILING_STOP_TRIGGER.** The system is giving back more than half of its

maximum favorable run before exit. Tighten the trailing stop activation threshold.

• Rule 2: Adjust Take-Profit Target• Condition: Ratio(MC/EW) ≥ 0.30 AND TP Too Far Count ≥ 0.40 × N• Recommendation: LOWER_TAKE_PROFIT_LIMIT. The price frequently approaches the target (within 90%) butreverses and hits the stop loss before closing. Lower the TP target closer to the entry distribution peak.• Rule 3: Calibrate Stop-Loss Limits• Condition: SL Too Tight Count ≥ 0.30 × N AND

‾‾‾
MAE ≈ Stop Loss Distance

*   *Recommendation:* **WIDEN_STOP_LOSS_AND_SCALE_SIZING.** The strategy is stopped out by noise before the

price moves in the predicted direction. Widen the stop-loss limit and reduce the position sizingproportionally to maintain constant risk.

• Rule 4: Address Execution Slippage• Condition: Ratio(MW/EW) ≥ 0.15 AND Mean Slippage ≥ 0.0020 (20 bps)• Recommendation: TRANSITION_TO_LIMIT_ORDERS. High slippage during stops or market exits is degradingperformance. Use limit or post-only order configurations for exits.• Rule 5: Apply Dynamic Sizing based on Confidence• Condition:

ρ⎛Confidence,P        ⎞ ≥ 0.30
 ⎝            realized⎠

AND

EV               < 0.0
  Low Confidence

*   *Recommendation:* **APPLY_CONFIDENCE_VOLUME_GATE.** The entry confidence metrics correlate with trade

success. Scale down volume or skip execution when confidence falls below the median validation threshold.──────

7. Validation Method

To verify that this audit framework generates accurate reports, it must be run against synthetic trade datarepresenting known failure states:

Lookahead Test Case: Generate trade trajectories where price data is sampled after the exit timestamp. Theframework must return  MFE = realized return  for all trades, flagging a lookahead exception.

Slippage Test Case: Inject random slippage of 10 to 50 bps on the exit price of synthetic trades. Theframework must correctly classify the degraded returns under  MW/EW  and flag the slippage count.

Low Sampling Test Case: Input trade runs generated at hourly sampling intervals versus tick-level data.The framework must measure and report the variance discrepancy (

2       2σ     - σtick    hourly

) to validate the under-sampling bias correction.──────

8. Possible Failure Cases

• Coarse Sampling Bias: If the database records MAE and MFE using hourly snapshots instead of tick-by-tick orhigh-frequency order book data, the calculated PCR and EQS will be artificially high, masking executioninefficiencies.• Post-Exit Horizon Limitations: Measuring "Stop-Loss Too Tight" requires retrieving market data after aposition has closed. If the market data pipeline does not support querying historical data beyond the activeposition lifespan, the framework will be unable to validate if a trade reversed in the predicted direction.• Asymmetric Liquidity Assumptions: The audit assumes that the paper execution policy can be replicated inproduction. Under large size constraints, market impact on exit (especially during liquidations) can distortthe realized PnL relative to the paper model, causing the audit classifications to diverge from liveperformance.
