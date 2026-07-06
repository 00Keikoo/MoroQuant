# Signal Behavior Audit
**MoroQuant ML Trading Platform**

This document presents evidence-based analysis of prediction directions, neutral distributions, regime behavior, and confidence distribution shapes across active production models and historical signal data.

---

## Part 1: Long Bias in Active Models

Active models exhibit a significant long bias: **67.86% Long** and **32.14% Short** of active signals (based on N=28 total active signals, consisting of 13 Long, 8 Short, and 7 Neutral signals). This bias is audited below across three key dimensions: pair contribution, timeframe contribution, and confidence distribution.

### 1. Pair Contribution (Symbol Breakdown)
Analysis of the 28 active signals across trading pairs shows uneven contribution to the directional distribution:

*   **HYPEUSDT:** 4 signals (100% Long | 0% Short | 0% Neutral)
*   **BTCUSDT:** 12 signals (50.00% Long | 25.00% Short | 25.00% Neutral)
*   **ETHUSDT:** 6 signals (50.00% Long | 50.00% Short | 0% Neutral)
*   **SOLUSDT:** 3 signals (0.00% Long | 33.33% Short | 66.67% Neutral)
*   **BNBUSDT:** 3 signals (0.00% Long | 33.33% Short | 66.67% Neutral)

*Evidence:* 
*   **BTCUSDT** and **HYPEUSDT** are the primary contributors to the Long bias, generating a combined **10 Long signals** (76.9% of all Long signals).
*   **SOLUSDT** and **BNBUSDT** generated **0 Long signals**, contributing only to Short and Neutral categories.

### 2. Timeframe Contribution
The long bias is highly timeframe-dependent:

*   **1h Timeframe (N=15 signals):** 2 Long (13.33%), 6 Short (40.00%), 7 Neutral (46.67%)
*   **4h Timeframe (N=13 signals):** 11 Long (84.62%), 2 Short (15.38%), 0 Neutral (0% Neutral)

*Evidence:* 
*   The **4h timeframe** is the primary driver of the Long bias, where **84.62%** of all predictions are Long.
*   Conversely, the **1h timeframe** exhibits a Short bias (75% of non-neutral signals are Short).

### 3. Confidence Contribution
Confidence distribution varies heavily by predicted direction:

*   **Long Signals:** Avg Confidence: **80.54%** | Min: 55% | Max: 93%
*   **Short Signals:** Avg Confidence: **55.50%** | Min: 35% | Max: 80%
*   **Neutral Signals:** Avg Confidence: **57.86%** | Min: 38% | Max: 71%

*Evidence:* Long signals are predicted with much higher average confidence (80.54%) than Short signals (55.50%), showing that the model's bias is present in both frequency and confidence assignment.

---

## Part 2: Neutral Distribution

The distribution of neutral signals across all 22,750 historical signals reveals extreme polarization between pairs:

### 1. Neutral Frequency by Pair
*   **ES_proxy:** 64.62% Neutral (126 of 195 signals)
*   **GC_proxy:** 55.30% Neutral (1,189 of 2,150 signals)
*   **BNBUSDT:** 45.10% Neutral (1,315 of 2,916 signals)
*   **BTCUSDT:** 11.32% Neutral (311 of 2,748 signals)
*   **SOLUSDT:** 0.07% Neutral (2 of 2,772 signals)
*   **ETHUSDT:** 0.04% Neutral (1 of 2,597 signals)
*   **All Other Pairs (15 symbols):** 0.00% Neutral (0 of 12,172 signals)

### 2. Classification of Pairs
*   **Excessive Neutral Pairs:** `ES_proxy` (64.62%), `GC_proxy` (55.30%), and `BNBUSDT` (45.10%) generate high rates of neutral signals.
*   **Almost-Never-Neutral / Never-Neutral Pairs:** `ETHUSDT` (0.04%), `SOLUSDT` (0.07%), and all other 15 symbols (0.00%) produce almost zero neutral signals, indicating binary long/short output behaviors.

---

## Part 3: Regime Analysis

An audit of prediction directions across market regimes shows distinct patterns of behavior:

### 1. Distribution of Directions by Regime (All Signals)
*   **choppy_low_vol (N=18):** 6 Long (33.33%), 7 Short (38.89%), 5 Neutral (27.78%)
*   **choppy_normal_vol (N=14):** 8 Long (57.14%), 3 Short (21.43%), 3 Neutral (21.43%)
*   **transitioning_normal_vol (N=9):** 3 Long (33.33%), 4 Short (44.44%), 2 Neutral (22.22%)
*   **trending_normal_vol (N=3):** 2 Long (66.67%), 1 Short (33.33%), 0 Neutral (0.00%)

### 2. Active Model Behavior by Regime
For the 28 active production signals, directions are distributed as follows:

*   **trending_normal_vol:** **100% Long** (2 Long, 0 Short, 0 Neutral) | Avg Confidence: 83.0%
*   **transitioning_normal_vol:** **37.5% Long, 37.5% Short, 25.0% Neutral** (3 Long, 3 Short, 2 Neutral) | Avg Long Confidence: **93.0%** | Avg Short Confidence: 41.0%
*   **choppy_normal_vol:** **50% Long, 30% Short, 20% Neutral** (5 Long, 3 Short, 2 Neutral) | Avg Long Confidence: 70.6% | Avg Short Confidence: 68.0%
*   **choppy_low_vol:** **37.5% Long, 25.0% Short, 37.5% Neutral** (3 Long, 2 Short, 3 Neutral) | Avg Long Confidence: 83.0% | Avg Short Confidence: 58.5%

*Evidence:* Active models adapt their direction and confidence profiles according to regime:
*   In `trending_normal_vol`, the models are purely long-biased.
*   In `transitioning_normal_vol`, direction is balanced, but the model assigns extremely high confidence to Longs (93.0%) compared to Shorts (41.0%).

---

## Part 4: Confidence Shape

Below is the distribution of confidence values across both historical and active signals, evaluated against reconstructed outcome win rates to assess calibration:

### 1. Confidence Bucket Distributions
*   **Under 40% Confidence:** 528 signals (2.32% of historical) | 3 active signals (10.71%)
*   **40-50% Confidence:** 2,661 signals (11.70% of historical) | 2 active signals (7.14%)
*   **50-60% Confidence:** 2,161 signals (9.50% of historical) | 5 active signals (17.86%)
*   **60-70% Confidence:** 2,427 signals (10.67% of historical) | 3 active signals (10.71%)
*   **70-80% Confidence:** 6,238 signals (27.42% of historical) | 3 active signals (10.71%)
*   **80%+ Confidence:** 8,735 signals (38.39% of historical) | 12 active signals (42.86%)

### 2. Confidence Calibration & Error Analysis
Comparing the confidence buckets against reconstructed outcome win rates (excluding timeouts) yields:

*   **80%+ Bucket:** Assigned Confidence: $\ge$ 80% | Actual Win Rate: **36.98%** (Severe Over-confidence)
*   **70-80% Bucket:** Assigned Confidence: 70–80% | Actual Win Rate: **28.92%** (Severe Over-confidence)
*   **60-70% Bucket:** Assigned Confidence: 60–70% | Actual Win Rate: **36.57%** (Over-confidence)
*   **50-60% Bucket:** Assigned Confidence: 50–60% | Actual Win Rate: **61.10%** (Under-confidence)
*   **40-50% Bucket:** Assigned Confidence: 40–50% | Actual Win Rate: **2.17%** (Over-confidence)

### 3. Conclusion on Confidence Shape
The models are overall **severely over-confident**:
*   The majority of signals (**65.81%** of historical, **53.57%** of active) are generated in the high-confidence $70\%+$ buckets.
*   However, the actual win rates for these high-confidence buckets are very low (~29% to 37%).
*   The only bucket exhibiting under-confidence is the 50-60% bucket, which represents a minority of generated signals.
