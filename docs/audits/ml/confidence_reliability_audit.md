# Confidence Reliability Audit Report

This audit evaluates the reliability, monotonicity, calibration, and threshold-based performance of the confidence scores assigned to trading signals.

---

## Part 1: Bucket Analysis

The table below summarizes signal distributions and reconstructed win rates across standard confidence intervals, utilizing all historical signals ($N = 22,752$).

| Confidence Bucket | Signal Count | Long % | Short % | Neutral % | Recon. Win Rate (Excl. Timeouts) | Recon. Win Rate (Incl. Timeouts) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **80%+** | 8,736 | 75.65% | 22.46% | 1.89% | 36.98% | 23.14% |
| **70-80%** | 6,238 | 44.21% | 40.85% | 14.94% | 28.92% | 13.66% |
| **60-70%** | 2,427 | 19.04% | 69.06% | 11.91% | 36.57% | 31.57% |
| **50-60%** | 2,161 | 20.31% | 79.55% | 0.14% | 61.10% | 21.72% |
| **40-50%** | 2,662 | 29.08% | 13.75% | 57.18% | 2.17% | 1.50% |

---

## Part 2: Monotonicity

### Success Probability vs. Confidence Correlation
The model's confidence scores **do not** exhibit monotonicity:
* **Excluding Timeouts:** The **50-60%** confidence bucket has the highest success probability (**61.10%**), which is significantly higher than all subsequent higher-confidence buckets (ranging from 28% to 37%).
* **Including Timeouts:** The **60-70%** confidence bucket yields the highest win rate (**31.57%**), but success probability drops sharply to **13.66%** in the 70-80% bucket, before slightly recovering to **23.14%** in the 80%+ bucket.

**Conclusion:** Higher assigned confidence does **not** imply a higher probability of success.

---

## Part 3: Overconfidence Analysis

### Expected Calibration Error (ECE)
Expected Calibration Error estimates quantify the average discrepancy between model confidence and actual win rates:
* **ECE (Excluding Timeouts):** **43.11%**
* **ECE (Including Timeouts):** **56.32%**

### Calibration Assessment
The models are **severely over-confident**:
* For the **80%+** bucket (average confidence ~92.4%), the actual win rate is only **36.98%** (excluding timeouts) or **23.14%** (including timeouts), representing a massive over-confidence gap of **55.4% to 69.3%**.
* For the **70-80%** bucket (average confidence ~75.7%), the win rate is **28.92%** (excl.) or **13.66%** (incl.), representing a gap of **46.8% to 62.1%**.
* The **only** instance of under-confidence (excluding timeouts) occurs in the **50-60%** bucket where the actual win rate is **61.10%** despite the average confidence being ~54.1%. However, when including timeouts, even this bucket is over-confident (win rate of 21.72%).

---

## Part 4: Confidence Threshold Simulation

Simulating trade execution filtering by confidence thresholds:

| Confidence Threshold | Trade Frequency (% of Total Signals) | Trade Count | Est. Win Rate (Excl. Timeouts) | Est. Win Rate (Incl. Timeouts) |
| :--- | :--- | :--- | :--- | :--- |
| **All Signals** | 100.00% | 22,752 | 35.88% | 20.39% |
| **Confidence > 50%** | 84.43% | 19,210 | 36.37% | 21.09% |
| **Confidence > 60%** | 76.02% | 17,297 | 35.19% | 21.26% |
| **Confidence > 70%** | 65.43% | 14,886 | 34.80% | 19.64% |
| **Confidence > 80%** | 33.17% | 7,547 | 36.63% | 20.72% |

*Note: Filtering signals with high confidence thresholds reduces the trade frequency by up to 66% (from 100% down to 33.17%) but fails to improve the win rate.*
