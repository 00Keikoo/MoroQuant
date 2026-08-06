# Sprint 3.9B-3B — TechnicalIndicatorCalculator Implementation

**Status**: ✅ COMPLETE  
**Date**: 2026-08-06  
**Sprint Type**: Adapter Implementation  
**ADR Compliance**: ADR-024

---

## Executive Summary

Implemented TechnicalIndicatorCalculator adapter connecting the FeatureCalculator abstraction to existing indicator calculation logic in ml_service.features.indicators. The adapter maintains ADR-024 compliance with pure-functional, deterministic calculation using immutable inputs and outputs.

**Key Achievement**: Production-ready technical indicator integration without duplicating calculation logic.

---

## Files Created

### Core Implementation

```
ml_service/research/strategy/features/calculator/
└── technical_indicators.py              # TechnicalIndicatorCalculator adapter
```

### Test Suite

```
tests/research/strategy/features/calculator/
└── test_technical_indicators.py        # 20 validation tests
```

### Documentation

```
docs/sprints/
└── Sprint_3.9B-3B_Implementation_Report.md
```

---

## Architecture Integration

### Component Responsibilities

**TechnicalIndicatorCalculator** (New)
- Converts FeatureContext window to DataFrame format
- Delegates indicator calculation to add_all_indicators()
- Extracts latest row as feature tuple
- Filters NaN values for clean output

**Integration Point**

```
FeatureContext
      ↓
TechnicalIndicatorCalculator.calculate()
      ↓
_convert_to_dataframe()
      ↓
add_all_indicators() [reused from ml_service.features.indicators]
      ↓
_extract_features()
      ↓
Tuple[Tuple[str, float], ...]
```

---

## Implementation Details

### TechnicalIndicatorCalculator

```python
class TechnicalIndicatorCalculator(FeatureCalculator):
    def __init__(
        self,
        ema_periods: Tuple[int, ...] = (9, 21, 50, 200),
        rsi_period: int = 14,
        macd_params: Tuple[int, int, int] = (12, 26, 9),
        atr_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_period: int = 20,
    ):
        # Store indicator parameters
        ...

    def calculate(self, context: FeatureContext) -> Tuple[Tuple[str, float], ...]:
        # Convert window to DataFrame
        # Apply indicators via add_all_indicators()
        # Extract and return feature tuple
        ...
```

### Key Design Decisions

1. **No Indicator Duplication**
   - Reuses add_all_indicators() from ml_service.features.indicators
   - Maintains single source of truth for indicator calculations
   - Adapter pattern separates interface from implementation

2. **MarketSnapshot to DataFrame Conversion**
   - Uses mid_price as close price
   - Derives high from ask, low from bid (when available)
   - Handles missing bid/ask gracefully (falls back to mid_price)
   - Ensures chronological ordering with timestamp index

3. **NaN Filtering**
   - Filters out NaN and non-finite values
   - Excludes raw OHLCV columns from output
   - Returns only clean, usable features

4. **Configurable Indicator Parameters**
   - All indicator periods/parameters exposed as constructor args
   - Immutable configuration (stored as instance attributes)
   - Enables strategy-specific indicator tuning

---

## Test Coverage

### Test Suite Results

**Location**: `tests/research/strategy/features/calculator/test_technical_indicators.py`

**Tests Implemented**: 20 tests across 8 test classes

```bash
========================= 20 passed, 1 warning in 5.74s =========================
```

### Test Breakdown by Category

#### 1. Initialization Tests (2 tests)
- ✅ `test_default_initialization` - Default parameters correct
- ✅ `test_custom_initialization` - Custom parameters accepted

#### 2. Calculation Tests (5 tests)
- ✅ `test_empty_window_returns_empty_tuple` - Empty window handled
- ✅ `test_single_snapshot_returns_empty_tuple` - Insufficient data handled
- ✅ `test_calculate_generates_expected_features` - Expected indicators present
- ✅ `test_features_are_finite_numbers` - All values finite and valid
- ✅ `test_no_ohlcv_columns_in_output` - Raw OHLCV excluded

#### 3. Determinism Tests (2 tests)
- ✅ `test_calculate_is_deterministic` - Same input → same output
- ✅ `test_calculate_is_deterministic_across_instances` - Consistent across instances

#### 4. NaN Handling Tests (2 tests)
- ✅ `test_missing_bid_ask_handled_gracefully` - Missing bid/ask handled
- ✅ `test_zero_volume_handled_gracefully` - Zero volume handled

#### 5. No Lookahead Tests (1 test)
- ✅ `test_features_only_use_historical_data` - No future data leakage

#### 6. Dependency Isolation Tests (3 tests)
- ✅ `test_no_database_dependency` - No SQLAlchemy imports
- ✅ `test_no_portfolio_dependency` - No portfolio/execution imports
- ✅ `test_only_allowed_imports` - Only permitted modules imported

#### 7. DataFrame Conversion Tests (3 tests)
- ✅ `test_converts_snapshots_to_dataframe` - Correct OHLCV structure
- ✅ `test_high_low_derived_from_bid_ask` - Bid/ask → high/low mapping
- ✅ `test_high_low_swapped_if_inverted` - Handles inverted bid/ask

#### 8. Integration Tests (2 tests)
- ✅ `test_integrates_with_feature_builder` - DefaultFeatureBuilder integration
- ✅ `test_builder_uses_calculator_output` - Correct delegation

---

## ADR-024 Compliance

### ✅ Immutable Domain Objects

- Input: `FeatureContext` is frozen dataclass
- Output: Tuple of tuples (immutable)
- No mutation of context or window snapshots
- DataFrame creation is local/temporary (not exposed)

### ✅ Pure Calculation

- `calculate()` is pure function
- No side effects or external state access
- Deterministic output enforced by tests
- Same context always produces same features

### ✅ Deterministic Replay

- Same `FeatureContext` → identical feature values
- No hidden state or randomness
- Verified across multiple invocations
- Verified across calculator instances

### ✅ No Runtime Persistence

Calculator has zero persistence:
- ❌ No database access (verified by test)
- ❌ No file I/O
- ❌ No external API calls
- ❌ No portfolio state access (verified by test)

### ✅ Dependency Isolation

Only permitted dependencies:
- ✅ pandas, numpy (data manipulation)
- ✅ ml_service.features.indicators (calculation logic)
- ✅ FeatureContext, FeatureCalculator (domain interfaces)
- ❌ No database, portfolio, or execution dependencies

---

## Feature Set Generated

### Indicators Produced

The calculator generates features from all indicators in add_all_indicators():

**EMA Indicators**
- `ema_9`, `ema_21`, `ema_50`, `ema_200`
- `ema_9_slope`, `ema_21_slope`, `ema_50_slope`, `ema_200_slope`
- `ema_9_direction`, `ema_21_direction`, `ema_50_direction`, `ema_200_direction`
- `ema_alignment_score`

**Momentum Indicators**
- `rsi` (Relative Strength Index)
- `macd`, `macd_signal`, `macd_histogram`

**Volatility Indicators**
- `atr` (Average True Range)
- `bb_upper`, `bb_middle`, `bb_lower` (Bollinger Bands)
- `bb_bandwidth`, `bb_percent`

**Volume Indicators**
- `vwap` (Volume Weighted Average Price)
- `price_to_vwap`
- `volume_ratio`

**Volume Profile**
- `poc_distance` (Point of Control distance)
- `vah_distance`, `val_distance` (Value Area High/Low)
- `price_in_value_area`
- `volume_nodes`

**Order Flow**
- `buy_volume`, `sell_volume`
- `delta`, `delta_ma`, `cumulative_delta`
- `delta_ratio`, `delta_divergence`

**Total**: ~40+ features per snapshot (exact count depends on NaN filtering)

---

## Usage Examples

### Basic Usage

```python
from ml_service.research.strategy.features import DefaultFeatureBuilder
from ml_service.research.strategy.features.calculator import TechnicalIndicatorCalculator

# Create calculator with default parameters
calculator = TechnicalIndicatorCalculator()

# Create builder with calculator
builder = DefaultFeatureBuilder(window_size=100, calculator=calculator)

# Build features from context
snapshot = builder.build(context)

# Access features
for feature_name, feature_value in snapshot.features:
    print(f"{feature_name}: {feature_value}")
```

### Custom Indicator Parameters

```python
# Create calculator with custom parameters
calculator = TechnicalIndicatorCalculator(
    ema_periods=(10, 20, 50),      # Fewer EMAs
    rsi_period=21,                  # Longer RSI period
    bb_period=15,                   # Shorter Bollinger Bands
    bb_std=1.5                      # Tighter bands
)

builder = DefaultFeatureBuilder(calculator=calculator)
```

### Integration with Strategy

```python
class MyStrategy(Strategy):
    def __init__(self):
        calculator = TechnicalIndicatorCalculator()
        self.feature_builder = DefaultFeatureBuilder(calculator=calculator)
        
    def on_data(self, context: FeatureContext) -> Optional[Order]:
        snapshot = self.feature_builder.build(context)
        
        # Access specific features
        features_dict = dict(snapshot.features)
        rsi = features_dict.get('rsi')
        ema_9 = features_dict.get('ema_9')
        
        # Make trading decision based on features
        if rsi < 30 and ema_9 > ema_21:
            return create_buy_order(...)
```

---

## Package Exports

### Updated `ml_service/research/strategy/features/calculator/__init__.py`

```python
from ml_service.research.strategy.features.calculator.interfaces import FeatureCalculator
from ml_service.research.strategy.features.calculator.noop import NoOpFeatureCalculator
from ml_service.research.strategy.features.calculator.technical_indicators import TechnicalIndicatorCalculator

__all__ = [
    "FeatureCalculator",
    "NoOpFeatureCalculator",
    "TechnicalIndicatorCalculator",  # NEW
]
```

---

## Design Constraints Maintained

### What This Sprint Does NOT Change

1. **No Modification to Indicator Logic**
   - add_all_indicators() remains unchanged
   - No duplication of indicator calculations
   - Single source of truth preserved

2. **No Breaking Changes**
   - Existing NoOpFeatureCalculator still default
   - Backward compatible integration
   - Opt-in adoption via dependency injection

3. **No New Indicator Types**
   - Uses existing indicator suite
   - No new indicator implementations
   - Reuses proven calculations

4. **No Database or Portfolio Coupling**
   - Calculator remains pure
   - No runtime persistence
   - No external dependencies

---

## Verification Commands

### Import Validation

```bash
python3 -c "from ml_service.research.strategy.features.calculator import TechnicalIndicatorCalculator"
```

### Run Tests

```bash
python3 -m pytest tests/research/strategy/features/calculator/test_technical_indicators.py -v
```

**Expected Output**: 20 passed

### Test Feature Generation

```python
from ml_service.research.strategy.features.calculator import TechnicalIndicatorCalculator
from ml_service.research.strategy.features.context import FeatureContext
from ml_service.simulation.models import MarketSnapshot
from datetime import datetime

# Create sample context
snapshots = [
    MarketSnapshot(
        timestamp=datetime(2024, 1, 1, 0, i),
        symbol="BTCUSDT",
        mid_price=50000.0 + i * 10,
        volume=1000.0
    )
    for i in range(100)
]

context = FeatureContext(
    symbol="BTCUSDT",
    timestamp=snapshots[-1].timestamp.isoformat() + 'Z',
    window=tuple(snapshots)
)

# Calculate features
calculator = TechnicalIndicatorCalculator()
features = calculator.calculate(context)

print(f"Generated {len(features)} features")
for name, value in features[:5]:
    print(f"  {name}: {value:.2f}")
```

---

## Integration Status

### Upstream Dependencies

- ✅ FeatureCalculator interface (Sprint 3.9B-3A)
- ✅ FeatureContext (Sprint 3.9B-2A)
- ✅ add_all_indicators() (existing ml_service.features.indicators)
- ✅ MarketSnapshot (existing simulation layer)

### Downstream Consumers

- ✅ DefaultFeatureBuilder (via dependency injection)
- ⏳ Future: Strategy implementations using technical indicators
- ⏳ Future: ML model training with indicator features

### Breaking Changes

**None**. This sprint adds functionality:
- TechnicalIndicatorCalculator is new, not replacing anything
- NoOpFeatureCalculator remains default
- Opt-in adoption via constructor parameter

---

## Performance Considerations

### Computational Cost

- **DataFrame conversion**: O(n) where n = window size
- **Indicator calculation**: Depends on indicators used
  - EMA: O(n) per period
  - RSI: O(n)
  - Bollinger Bands: O(n)
  - Volume Profile: O(n × buckets)
  - VWAP: O(n)

### Memory Usage

- Temporary DataFrame: ~8 bytes/cell × columns × rows
- Example: 100 snapshots × 6 OHLCV cols = 4.8KB
- Feature tuple: ~50 bytes/feature × 40 features = 2KB
- Total overhead: ~7KB per calculate() call

### Optimization Opportunities (Future)

1. **Incremental Calculation**
   - Cache intermediate indicator values
   - Only recalculate new data points
   - Requires stateful calculator variant

2. **Selective Indicators**
   - Allow disabling unused indicators
   - Reduce calculation overhead
   - Requires configuration API

3. **Vectorization**
   - Already using pandas/numpy (vectorized)
   - pandas-ta library uses optimized operations
   - Minimal room for improvement

---

## Known Limitations

### 1. Minimum Window Size

- Most indicators require 20-50 snapshots minimum
- Insufficient data returns empty tuple
- Strategies must handle empty feature case

### 2. NaN Handling

- Early snapshots may have NaN indicators
- Filtered from output (missing features early in window)
- Strategies should check feature availability

### 3. OHLC Derivation

- Uses mid_price for open/close
- Derives high/low from bid/ask if available
- Less accurate than true OHLC bars
- Acceptable for minute-level data

### 4. Fixed Indicator Set

- All indicators from add_all_indicators() calculated
- No selective calculation (yet)
- Minor performance overhead if only few features used

---

## Next Steps

### Immediate Follow-up

1. **Strategy Integration**
   - Update existing strategies to use TechnicalIndicatorCalculator
   - Replace manual indicator calculations
   - Leverage full indicator suite

2. **ML Pipeline Integration**
   - Connect features to model training
   - Feature selection and importance analysis
   - Hyperparameter tuning for indicator periods

### Future Enhancements

1. **Selective Indicator Calculation**
   - Configuration to enable/disable indicators
   - Reduce computational overhead
   - API: `TechnicalIndicatorCalculator(enabled_indicators=['rsi', 'ema'])`

2. **Custom Indicator Support**
   - Pluggable indicator functions
   - Strategy-specific feature engineering
   - API: `calculator.add_custom_indicator(fn)`

3. **Feature Validation**
   - Schema validation for feature names
   - Value range checks
   - Type safety enforcement

4. **Incremental Calculation**
   - Stateful calculator variant
   - Cache intermediate values
   - Only recalculate new snapshots

---

## Conclusion

Sprint 3.9B-3B successfully implemented the TechnicalIndicatorCalculator adapter with:

1. **Zero Duplication** - Reuses existing add_all_indicators() logic
2. **ADR-024 Compliance** - Pure, deterministic, dependency-isolated
3. **Comprehensive Testing** - 20 tests covering all requirements
4. **Clean Integration** - Works seamlessly with FeatureBuilder
5. **Production Ready** - Handles edge cases and validates output

The adapter establishes the bridge between the feature calculation abstraction and proven indicator logic, enabling strategy implementations to leverage technical indicators through a clean, type-safe interface.

---

**Sprint Complete**: ✅  
**Tests Passing**: ✅ 20/20  
**ADR-024 Compliant**: ✅  
**Ready for Strategy Integration**: ✅
