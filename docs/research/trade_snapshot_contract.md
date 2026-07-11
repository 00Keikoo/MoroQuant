# Trade Snapshot Contract Specification

**Sprint**: 4.9A  
**Status**: DESIGN COMPLETE  
**Auditor**: Antigravity

---

## 1. Immutable Contract Structure

At the exact microsecond a paper or live trade is executed, the platform creates an immutable snapshot object. This snapshot guarantees scientific reproducibility and prevents data drift from rewriting history.

```json
{
  "trade_snapshot_id": "snap_tr_9981a2f",
  "timestamp": 1783838202,
  "trade_details": {
    "trade_id": 981,
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 50025.0,
    "exit_price": 52000.0,
    "realized_pnl": 975.0,
    "size_usdt": 1000.0
  },
  "signal_snapshot": {
    "signal_id": 20084,
    "direction": "long",
    "raw_confidence": 85,
    "probabilities": {
      "short": 0.05,
      "neutral": 0.10,
      "long": 0.85
    }
  },
  "model_snapshot": {
    "model_version": "v1.4.2",
    "model_hash": "sha256_0f8b1a...",
    "git_commit": "c3f802a"
  },
  "feature_snapshot": {
    "feature_version": "v1.0",
    "feature_values": {
      "atr": 150.2,
      "rsi_14": 62.4,
      "funding_rate": 0.0001
    }
  },
  "validation_snapshot": {
    "oos_f1_weighted": 0.682,
    "oos_precision": 0.69,
    "oos_recall": 0.68
  },
  "calibration_snapshot": {
    "ece": 0.024,
    "brier_score": 0.012
  },
  "execution_snapshot": {
    "slippage_pct": 0.05,
    "latency_ms": 120,
    "policy": "TRAILING"
  }
}
```
