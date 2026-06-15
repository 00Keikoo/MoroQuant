"""Probability calibration for multiclass trading models.

Three methods compared:
  - 'raw'      : identity (baseline, no calibration)
  - 'platt'    : per-class sigmoid (logistic regression on raw probs)
  - 'isotonic' : per-class isotonic regression (monotone non-parametric)

Multiclass is handled one-vs-rest: each class gets its own 1-D calibrator
fitted on (p_class, y == class). Output is renormalized so the per-row
probability vector sums to 1.

Metrics reported per method:
  - Brier score   : mean squared error over the one-hot target matrix
  - Log loss      : sklearn.metrics.log_loss on the multiclass prob matrix
  - ECE           : 10-bin expected calibration error on the predicted class
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from ..utils.logger import get_logger

logger = get_logger()

CLASS_LABELS = (0, 1, 2)  # short, neutral, long
EPS = 1e-12


# ---------------------------------------------------------------------------
# Fit / apply
# ---------------------------------------------------------------------------


def _fit_platt(p_class: np.ndarray, y_binary: np.ndarray) -> LogisticRegression:
    """Logistic regression on raw probability for a single class."""
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
    lr.fit(p_class.reshape(-1, 1), y_binary.astype(int))
    return lr


def _fit_isotonic(p_class: np.ndarray, y_binary: np.ndarray) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(p_class, y_binary.astype(float))
    return iso


def fit_calibrator(method: str, probas: np.ndarray, y: np.ndarray) -> Dict:
    """Fit one calibrator per class. Returns a dict ready for save_calibrator."""
    if method == "raw":
        return {"method": "raw", "per_class": None}

    per_class: Dict[int, object] = {}
    for c_idx, c in enumerate(CLASS_LABELS):
        p_c = probas[:, c_idx]
        y_c = (y == c).astype(int)
        if y_c.sum() == 0 or y_c.sum() == len(y_c):
            per_class[c] = None  # degenerate class — fall back to identity
            continue
        if method == "platt":
            per_class[c] = _fit_platt(p_c, y_c)
        elif method == "isotonic":
            per_class[c] = _fit_isotonic(p_c, y_c)
        else:
            raise ValueError(f"Unknown method: {method}")

    return {"method": method, "per_class": per_class}


def apply_calibrator(cal: Dict, probas: np.ndarray) -> np.ndarray:
    """Apply a fitted calibrator to a (n, 3) probability matrix."""
    if cal["method"] == "raw" or cal.get("per_class") is None:
        return probas

    out = np.zeros_like(probas, dtype=float)
    for c_idx, c in enumerate(CLASS_LABELS):
        model = cal["per_class"].get(c)
        if model is None:
            out[:, c_idx] = probas[:, c_idx]
            continue
        if isinstance(model, LogisticRegression):
            out[:, c_idx] = model.predict_proba(probas[:, c_idx].reshape(-1, 1))[:, 1]
        else:  # IsotonicRegression
            out[:, c_idx] = model.predict(probas[:, c_idx])

    row_sum = out.sum(axis=1, keepdims=True)
    row_sum = np.where(row_sum < EPS, 1.0, row_sum)
    return out / row_sum


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _one_hot(y: np.ndarray) -> np.ndarray:
    oh = np.zeros((len(y), len(CLASS_LABELS)), dtype=float)
    for c_idx, c in enumerate(CLASS_LABELS):
        oh[y == c, c_idx] = 1.0
    return oh


def brier_multiclass(probas: np.ndarray, y: np.ndarray) -> float:
    oh = _one_hot(y)
    return float(np.mean(np.sum((probas - oh) ** 2, axis=1)))


def log_loss_safe(probas: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(probas, EPS, 1.0 - EPS)
    p = p / p.sum(axis=1, keepdims=True)
    return float(log_loss(y, p, labels=list(CLASS_LABELS)))


def expected_calibration_error(
    probas: np.ndarray, y: np.ndarray, n_bins: int = 10
) -> float:
    """ECE on the model's top-class confidence."""
    conf = probas.max(axis=1)
    pred = probas.argmax(axis=1)
    correct = (pred == y).astype(float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        if i == n_bins - 1:
            mask = (conf >= lo) & (conf <= hi)
        else:
            mask = (conf >= lo) & (conf < hi)
        if not mask.any():
            continue
        bin_conf = conf[mask].mean()
        bin_acc = correct[mask].mean()
        ece += (mask.sum() / n) * abs(bin_conf - bin_acc)
    return float(ece)


def metric_bundle(probas: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    return {
        "brier": brier_multiclass(probas, y),
        "log_loss": log_loss_safe(probas, y),
        "ece": expected_calibration_error(probas, y),
    }


# ---------------------------------------------------------------------------
# Reliability diagram
# ---------------------------------------------------------------------------


def reliability_curve(
    probas: np.ndarray, y: np.ndarray, n_bins: int = 10
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (bin_centers, bin_accuracy, bin_count) for the predicted class."""
    conf = probas.max(axis=1)
    pred = probas.argmax(axis=1)
    correct = (pred == y).astype(float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    centers, accs, counts = [], [], []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (conf >= lo) & (conf < hi) if i < n_bins - 1 else (conf >= lo) & (conf <= hi)
        if not mask.any():
            centers.append((lo + hi) / 2)
            accs.append(np.nan)
            counts.append(0)
        else:
            centers.append(conf[mask].mean())
            accs.append(correct[mask].mean())
            counts.append(int(mask.sum()))
    return np.array(centers), np.array(accs), np.array(counts)


def plot_reliability(
    method_to_probas: Dict[str, np.ndarray],
    y: np.ndarray,
    title: str,
    out_path: Path,
    n_bins: int = 10,
) -> None:
    """One PNG with one subplot per method. Quietly no-ops if matplotlib missing."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        logger.warning(f"matplotlib unavailable, skipping reliability plot: {e}")
        return

    methods = list(method_to_probas.keys())
    fig, axes = plt.subplots(1, len(methods), figsize=(4.5 * len(methods), 4.2), sharey=True)
    if len(methods) == 1:
        axes = [axes]

    for ax, method in zip(axes, methods):
        probas = method_to_probas[method]
        centers, accs, counts = reliability_curve(probas, y, n_bins=n_bins)
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.6, label="perfect")
        valid = ~np.isnan(accs)
        ax.plot(centers[valid], accs[valid], "o-", label=method)
        for cx, cy, ct in zip(centers, accs, counts):
            if ct > 0 and not np.isnan(cy):
                ax.annotate(str(ct), (cx, cy), fontsize=7, alpha=0.7, xytext=(2, 2),
                            textcoords="offset points")
        ece = expected_calibration_error(probas, y, n_bins=n_bins)
        ax.set_title(f"{method}  (ECE={ece:.3f})")
        ax.set_xlabel("Predicted confidence")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Empirical accuracy")
    fig.suptitle(title)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def calibration_path_for(model_path: str) -> Path:
    """Convention: alongside <model>.pkl we keep <model>_calibration.pkl."""
    p = Path(model_path)
    return p.with_name(p.stem + "_calibration.pkl")


def save_calibration_artifact(
    model_path: str,
    chosen_method: str,
    calibrators: Dict[str, Dict],
    metrics: Dict[str, Dict[str, float]],
    holdout_size: int,
) -> str:
    """Persist all three calibrators + metrics next to the model pkl."""
    out = calibration_path_for(model_path)
    payload = {
        "chosen_method": chosen_method,
        "calibrators": calibrators,    # {'raw': {...}, 'platt': {...}, 'isotonic': {...}}
        "metrics": metrics,            # {'raw': {...}, 'platt': {...}, 'isotonic': {...}}
        "holdout_size": holdout_size,
        "class_labels": list(CLASS_LABELS),
    }
    with open(out, "wb") as f:
        pickle.dump(payload, f)
    logger.info(f"Saved calibration artifact: {out.name} (chosen={chosen_method})")
    return str(out)


def load_calibration_artifact(model_path: str) -> Optional[Dict]:
    p = calibration_path_for(model_path)
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# Convenience: fit + score all three on one (probas, y) pair
# ---------------------------------------------------------------------------


def fit_and_score_all(
    probas: np.ndarray, y: np.ndarray
) -> Tuple[Dict[str, Dict], Dict[str, Dict[str, float]], Dict[str, np.ndarray]]:
    """Fit raw/Platt/isotonic on (probas, y), score each on the same data,
    return (calibrators, metrics, calibrated_probas)."""
    calibrators: Dict[str, Dict] = {}
    metrics: Dict[str, Dict[str, float]] = {}
    calibrated: Dict[str, np.ndarray] = {}

    for method in ("raw", "platt", "isotonic"):
        cal = fit_calibrator(method, probas, y)
        cp = apply_calibrator(cal, probas)
        calibrators[method] = cal
        calibrated[method] = cp
        metrics[method] = metric_bundle(cp, y)

    return calibrators, metrics, calibrated


def pick_best_method(metrics: Dict[str, Dict[str, float]]) -> str:
    """Lowest ECE wins. Ties broken by lower log loss, then Brier."""
    def key(m):
        v = metrics[m]
        return (v["ece"], v["log_loss"], v["brier"])
    return min(metrics.keys(), key=key)
