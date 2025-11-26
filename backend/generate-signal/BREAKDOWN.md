# Signal Generation Module Breakdown

## Overview
The `scripts/generate_signal.py` file (1165 lines) has been refactored into modular components to improve maintainability, testability, and code organization.

## Original File Structure
- **File**: `backend/scripts/generate_signal.py`
- **Lines**: 1165
- **Main Components**: 20+ functions for technical analysis, regime detection, risk assessment, and signal generation

## New Modular Structure

### 1. `constants.py`
**Purpose**: Centralized constants and default values

**Contents**:
- Mathematical constants (PERCENTAGE_MULTIPLIER, RSI_NEUTRAL, etc.)
- Time horizons (HORIZON_5D, HORIZON_10D, HORIZON_20D, etc.)
- Kelly criterion constants
- Default fallback values

### 2. `technical_indicators.py`
**Purpose**: Technical analysis calculations

**Functions**:
- `calculate_rsi()`: Relative Strength Index calculation
- `calculate_bollinger_bands()`: Bollinger Bands with position calculation

**Key Features**:
- Configurable periods and multipliers
- Robust handling of insufficient data
- Returns normalized values for easy interpretation

### 3. `regime_detection.py`
**Purpose**: Market regime identification and transitions

**Functions**:
- `calculate_regime()`: Determines bullish/bearish/neutral regime
- `detect_regime_transition()`: Identifies regime changes (turning points, momentum shifts)
- `calculate_adaptive_threshold()`: Volatility-adjusted thresholds

**Key Features**:
- Multi-timeframe momentum analysis
- Trend consistency detection
- Adaptive regime boundaries based on volatility

### 4. `risk_assessment.py`
**Purpose**: Risk scoring and confidence calculations

**Functions**:
- `calculate_risk_score()`: Overall market risk (0-100 scale)
- `calculate_confidence_score()`: Signal confidence (0-1 scale)

**Key Features**:
- Tunable risk weights (volatility vs correlation)
- Stability-adjusted volatility scoring
- Confidence bonuses for trend consistency

### 5. `feature_engineering.py`
**Purpose**: Multi-timeframe feature calculation

**Functions**:
- `calculate_multi_timeframe_features()`: Computes all technical features for an asset

**Features Calculated**:
- Returns at multiple horizons (5d, 20d, 60d)
- Volatility metrics
- Price vs moving averages (SMA 20, SMA 50)
- RSI and Bollinger Band position

### 6. `asset_ranking.py`
**Purpose**: Asset scoring and ranking logic

**Functions**:
- `rank_assets()`: Composite scoring with momentum, trend, and mean reversion factors

**Scoring Components**:
- Risk-adjusted momentum
- Trend consistency multipliers
- Price momentum vs SMAs
- Mean reversion bonuses/penalties (oversold/overbought)

### 7. `mean_reversion.py`
**Purpose**: Mean reversion opportunity detection

**Functions**:
- `detect_mean_reversion_opportunity()`: Identifies oversold/overbought conditions
- `detect_downward_pressure()`: Early warning system for market crashes

**Key Features**:
- RSI + Bollinger Band confirmation
- Severity levels (severe/moderate/none)
- Multi-asset correlation analysis

### 8. `portfolio_allocation.py`
**Purpose**: Diversified capital allocation

**Functions**:
- `allocate_diversified()`: Proportional allocation with concentration limits

**Allocation Logic**:
- 3-asset diversification with tunable limits
- 2-asset fallback allocation
- Single-asset concentration when appropriate

### 9. `position_sizing.py`
**Purpose**: Position size calculation and scaling

**Functions**:
- `calculate_position_size()`: Confidence-based sizing
- `capital_scaling_adjustment()`: Reduces allocation for large capitals
- `calculate_half_kelly()`: Kelly Criterion-based sizing

**Key Features**:
- Half-Kelly for safety margin
- Multi-tier capital scaling
- Historical performance-based sizing

### 10. `circuit_breaker.py`
**Purpose**: Intra-month drawdown monitoring

**Functions**:
- `check_circuit_breaker()`: Monitors monthly drawdown limits

**Note**: Used for warnings only - strategy continues operating to learn from mistakes

### 11. `signal_logic.py`
**Purpose**: Core BUY/SELL/HOLD decision logic

**Functions**:
- `decide_action()`: Main decision function with comprehensive logic

**Decision Factors**:
- Regime score (bullish/bearish/neutral)
- Risk score thresholds
- Mean reversion opportunities
- Downward pressure detection
- Current cash allocation awareness

**Signal Types Generated**:
- Bullish momentum, bearish regime
- Mean reversion (oversold/overbought)
- Extreme risk protection
- Downward pressure (severe/moderate)
- Neutral cautious/high-risk

## Usage in Main File

The refactored `scripts/generate_signal.py` now imports and uses these modules:

```python
from backend.generate_signal.constants import *
from backend.generate_signal.technical_indicators import calculate_rsi, calculate_bollinger_bands
from backend.generate_signal.regime_detection import (
    calculate_regime, detect_regime_transition, calculate_adaptive_threshold
)
from backend.generate_signal.risk_assessment import calculate_risk_score, calculate_confidence_score
from backend.generate_signal.feature_engineering import calculate_multi_timeframe_features
from backend.generate_signal.asset_ranking import rank_assets
from backend.generate_signal.mean_reversion import detect_mean_reversion_opportunity, detect_downward_pressure
from backend.generate_signal.portfolio_allocation import allocate_diversified
from backend.generate_signal.position_sizing import (
    calculate_position_size, capital_scaling_adjustment, calculate_half_kelly
)
from backend.generate_signal.circuit_breaker import check_circuit_breaker
from backend.generate_signal.signal_logic import decide_action
```

## Benefits of Refactoring

1. **Separation of Concerns**: Each module handles one aspect of signal generation
2. **Testability**: Functions can be unit tested with mock data
3. **Configuration**: All tunable parameters accessed through config object
4. **Maintainability**: Easy to locate and update specific calculations
5. **Extensibility**: New indicators or signals can be added to appropriate modules
6. **Debugging**: Easier to trace issues to specific modules

## Testing Considerations

- Unit tests updated to import from new module paths
- All test mocks adjusted for new function signatures
- Integration tests verify end-to-end signal generation
- No functionality changes - only structural reorganization

## Key Design Decisions

1. **Config Dependency**: All tunable parameters passed via config object
2. **Pure Functions**: Most functions are stateless and deterministic
3. **Database Separation**: Database queries isolated to specific modules
4. **Type Hints**: Maintained where present in original code
5. **Error Handling**: Preserved original error handling patterns

## Migration Notes

- Main `generate_signal()` function preserved with same signature
- All database interactions unchanged
- Trading config parameters accessed identically
- Signal storage format unchanged
- Backward compatible with existing tests and workflows
