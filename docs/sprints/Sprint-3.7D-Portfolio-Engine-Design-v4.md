# Sprint 3.7D Design Specification: Portfolio Engine (Design Version 4.0)

**Status**: MATHEMATICAL CORRECTION  
**Role**: Principal Quant Architect  
**Engineering Contract ID**: MoroQuant-Sprint-3.7D-Contract-v4.0  
**Target Implementation Agent**: Claude Code  

---

## 1. Executive Summary & Purpose

The MoroQuant Portfolio Engine is the core financial accounting engine of the simulation and trading platform. Building upon the Sprint 3.7D architecture, this Version 4.0 specification establishes **mathematically correct accounting rules**, **consistent liquidation pricing formulations**, and a **robust cash account state machine**.

The core architecture operates under the principle of **Pure Functional Accounting**:
* Operates as a pure function: consumes event streams and computes a deterministic, immutable `Portfolio` state.
* The ledger serves as the **Single Source of Truth** for all cash movements (deposits, withdrawals, trading debits, fee charges, funding adjustments).
* Eliminates divergence between backtesting simulations and live/paper trading via a unified calculation core.

---

## 2. Core Architectural Design (Shared Portfolio Core)

The Portfolio Core acts as a shared, pure functional domain logic layer. Specialized adapters feed historical or real-time event packets into this core to compute state transitions.

```
                         +-----------------------------------+
                         |           Portfolio Core          |
                         |   (Pure Functional Accounting)    |
                         |  - Position / PnL / Equity Calc   |
                         |  - Margin & Exposure Calculations  |
                         +-----------------------------------+
                                           ^
                                           |
                  +------------------------+------------------------+
                  |                                                 |
     +--------------------------+                      +--------------------------+
     |    Simulation Adapter    |                      |  Paper Trading Adapter   |
     |                          |                      |                          |
     | - Consumes Historical    |                      | - Consumes Real-Time     |
     |   Fill Events (In-Memory)|                      |   Fills (SQLite-backed)  |
     +--------------------------+                      +--------------------------+
```

### Architectural Rules:
1. **Identical Math Logic**: Both adapters must route execution data through the exact same mathematical engines for PnL, equity, margin, exposure, and liquidation calculations.
2. **Adapter Isolation**: Adapters vary only in event latency and persistence store:
   * **Simulation**: Historical batch execution updates portfolio states in memory.
   * **Paper Trading**: Real-time signal matching events trigger database-backed transaction logs, mapped directly into the shared Portfolio Core entities.

---

## 3. Updated Domain Aggregates & Value Objects

The updated domain models incorporate position-level margin parameters and correct the tracking of asset holdings.

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class AccountType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    FUTURES = "FUTURES"

class PositionType(Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    FUTURES = "FUTURES"

class RiskMode(Enum):
    NONE = "NONE"                     # Used for Spot
    MARGIN = "MARGIN"                 # Collateralized without liquidation
    LIQUIDATION_ENABLED = "LIQUIDATION_ENABLED"  # Margined futures/leverage

class MarginMode(Enum):
    CROSS = "CROSS"                   # Portfolio-level margin sharing
    ISOLATED = "ISOLATED"             # Position-level margin isolation

class PortfolioLifecycle(Enum):
    EMPTY = "EMPTY"
    ACTIVE = "ACTIVE"
    MARGIN_CALL = "MARGIN_CALL"
    LIQUIDATED = "LIQUIDATED"
    CLOSED = "CLOSED"

class PositionLifecycle(Enum):
    OPENING = "OPENING"
    OPEN = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"

class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRADE_DEBIT = "TRADE_DEBIT"
    TRADE_CREDIT = "TRADE_CREDIT"
    FEE_CHARGE = "FEE_CHARGE"
    FUNDING_ADJUSTMENT = "FUNDING_ADJUSTMENT"

@dataclass(frozen=True)
class LedgerEntry:
    """Ledger transaction representing the single source of truth for cash movements."""
    entry_id: str
    timestamp: datetime
    transaction_type: TransactionType
    asset: str
    amount: float
    description: str

@dataclass(frozen=True)
class CashAccount:
    """Cash ledger segments within the portfolio."""
    ledger_cash_balance: float   # Net ledger cash (includes deposits, withdrawals, fees, realized PnL, funding)
    available_cash: float        # Cash available to open new positions / withdraw
    reserved_cash: float         # Cash reserved for pending open orders / initial margin allocation
    locked_cash: float           # Cash locked as collateral for active positions (sum of allocated margin)

@dataclass(frozen=True)
class PositionMarginContext:
    """Position-level margin configuration and collateralization state."""
    leverage: float
    initial_margin_ratio: float      # e.g., 0.10 for 10x leverage (1/leverage)
    maintenance_margin_ratio: float  # e.g., 0.05 for 5% MMR
    allocated_margin: float          # Isolated collateral assigned to this position

@dataclass(frozen=True)
class MarginAccount:
    """Margin and collateral ledger parameters."""
    risk_mode: RiskMode
    margin_mode: MarginMode
    initial_margin: float        # Total initial margin required for all positions
    maintenance_margin: float    # Total maintenance margin required for all positions
    margin_ratio: float          # maintenance_margin / total_equity
    liquidation_buffer: float    # Distance to liquidation threshold (margin space)
    liquidation_price: Dict[str, float]  # Calculated liquidation price per symbol

@dataclass(frozen=True)
class AssetHolding:
    """Tracks non-leveraged spot asset inventory."""
    symbol: str
    quantity: float
    mark_price: float
    market_value: float

@dataclass(frozen=True)
class Position:
    """An active trading position with exposure."""
    symbol: str
    position_type: PositionType
    status: PositionLifecycle
    quantity: float              # Positive = Long, Negative = Short
    average_entry_price: float
    average_exit_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin_required: float
    margin_context: Optional[PositionMarginContext]  # Active margin context (leverage, ratios, allocated margin)
    opened_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class EquitySnapshot:
    timestamp: datetime
    ledger_cash: float
    holdings_value: float
    unrealized_pnl: float
    total_equity: float

@dataclass(frozen=True)
class ExposureSnapshot:
    timestamp: datetime
    asset_allocation: Dict[str, float]  # Percentage allocation per asset
    gross_exposure: float                # Long value + Short value
    net_exposure: float                  # Long value - Short value
    leverage: float                      # gross_exposure / total_equity
    buying_power: float                  # Remaining capital space for trades

@dataclass(frozen=True)
class Portfolio:
    portfolio_id: str
    account_type: AccountType
    lifecycle: PortfolioLifecycle
    ledger: List[LedgerEntry]
    cash_ledger: CashAccount
    margin_ledger: MarginAccount
    positions: Dict[str, Position]
    holdings: Dict[str, AssetHolding]
    equity: float
    last_updated: datetime
```

---

## 4. Revised Mathematical Formulations

### 4.1 Universal Equity Formula

To ensure correct financial accounting across both Spot and Margined/Derivative portfolios, the portfolio equity calculation must account for cash, spot holdings, and position-level unrealized PnL:

$$\text{Equity} = \text{Ledger Cash Balance} + \sum \text{Asset Holdings Market Value} + \sum \text{Position Unrealized PnL}$$

#### Application by Account Type:
* **SPOT Accounts**:
  $$\text{Equity}_{\text{spot}} = \text{Ledger Cash Balance} + \sum \text{Asset Holdings Market Value}$$
  *(Unrealized PnL for spot assets is captured in the change of the holdings' market value relative to acquisition price, while the cash debit is recorded in the ledger)*
* **MARGIN / FUTURES Accounts**:
  $$\text{Equity}_{\text{futures}} = \text{Ledger Cash Balance} + \sum \text{Position Unrealized PnL}$$
  *(Derivative positions carry zero asset value but generate positive/negative unrealized PnL from mark-to-market valuations)*

---

### 4.2 Maintenance Margin Definition

Maintenance Margin ($MM$) is dynamically calculated based on **Current Mark Price** rather than entry price:

$$\text{Maintenance Margin} = \text{Mark Price} \times |\text{Quantity}| \times \text{Maintenance Margin Ratio}$$

This definition guarantees that as prices move, the minimum required collateral moves proportionally with the gross risk.

---

### 4.3 Liquidation Mathematics

Liquidation occurs when portfolio/position equity falls below the required Maintenance Margin.

#### 1. Cross Margin Mode (Portfolio-Level Risk)
Under Cross Margin, liquidation is triggered when:
$$\text{Margin Ratio} = \frac{\sum \text{Maintenance Margin}}{\text{Equity}} \ge 1.0$$

The liquidation price for a single position is calculated as:

$$\text{LP}_{\text{long}} = \text{Average Entry Price} \times \frac{1 - \text{Initial Margin Ratio}}{1 - \text{Maintenance Margin Ratio}}$$

$$\text{LP}_{\text{short}} = \text{Average Entry Price} \times \frac{1 + \text{Initial Margin Ratio}}{1 + \text{Maintenance Margin Ratio}}$$

#### 2. Isolated Margin Mode (Position-Specific Risk)
Under Isolated Margin, liquidation is triggered when the position-level Margin Ratio reaches $1.0$. The liquidation price is directly adjusted by changing the `allocated_margin` to the position:

$$\text{LP}_{\text{long, isolated}} = \frac{\text{Average Entry Price} - \frac{\text{Allocated Margin}}{\text{Quantity}}}{1 - \text{Maintenance Margin Ratio}}$$

$$\text{LP}_{\text{short, isolated}} = \frac{\text{Average Entry Price} + \frac{\text{Allocated Margin}}{|\text{Quantity}|}}{1 + \text{Maintenance Margin Ratio}}$$

---

## 5. Cash Account State Machine

```
              [Available Cash]
                     │
         OrderCreated│
                     ▼
              [Reserved Cash]
                     │
          OrderFilled│
                     ▼
               [Locked Cash]
                     │
       PositionClosed│
                     ▼
              [Available Cash] (Adjusted for PnL & Fees)
```

### 5.1 Exact Transitions

| Event | `available_cash` | `reserved_cash` | `locked_cash` | `ledger_cash_balance` |
| :--- | :--- | :--- | :--- | :--- |
| **OrderCreated** | Decreased by Order Margin | Increased by Order Margin | Unchanged | Unchanged |
| **OrderCancelled** | Increased by Order Margin | Decreased by Order Margin | Unchanged | Unchanged |
| **OrderFilled (Spot Buy)** | Unchanged | Decreased by Order Cost | Unchanged | Decreased by (Order Cost + Fee) |
| **OrderFilled (Futures Open)**| Unchanged | Decreased by Initial Margin | Increased by Initial Margin | Decreased by Fee |
| **PositionClosed (Futures)** | Increased by (Locked Margin + Realized PnL - Fee) | Unchanged | Decreased by Locked Margin | Increased by (Realized PnL - Fee) |

---

## 6. Event Contracts

State updates output the following event structures:

```python
@dataclass(frozen=True)
class OrderCreated:
    portfolio_id: str
    order_id: str
    symbol: str
    margin_to_reserve: float
    timestamp: datetime

@dataclass(frozen=True)
class OrderFilled:
    portfolio_id: str
    order_id: str
    symbol: str
    quantity: float
    price: float
    timestamp: datetime

@dataclass(frozen=True)
class FeeCharged:
    portfolio_id: str
    order_id: str
    fee_amount: float
    asset: str
    timestamp: datetime

@dataclass(frozen=True)
class FundingApplied:
    portfolio_id: str
    symbol: str
    amount: float
    timestamp: datetime

@dataclass(frozen=True)
class PositionOpened:
    portfolio_id: str
    position: Position
    timestamp: datetime

@dataclass(frozen=True)
class PositionUpdated:
    portfolio_id: str
    position: Position
    pnl_delta: float
    timestamp: datetime

@dataclass(frozen=True)
class PositionClosed:
    portfolio_id: str
    position: Position
    realized_pnl: float
    timestamp: datetime

@dataclass(frozen=True)
class EquityUpdated:
    portfolio_id: str
    snapshot: EquitySnapshot

@dataclass(frozen=True)
class MarginUpdated:
    portfolio_id: str
    margin_ledger: MarginAccount
    timestamp: datetime

@dataclass(frozen=True)
class LiquidationTriggered:
    portfolio_id: str
    symbol: str
    liquidation_price: float
    trigger_equity: float
    timestamp: datetime
```

---

## 7. Mathematical & Financial Validation Examples

### Example 1: Spot BTC Purchase (Equity Validation)
* **Initial State**:
  * `AccountType` = SPOT
  * `ledger_cash_balance` = 10,000 USDT
  * `holdings` = {}
* **Event**: Buy 0.1 BTC at 50,000 USDT. Fee is 0.1% (5 USDT).
* **Ledger Entries**:
  * Entry 1 (Trade Debit): -5,000 USDT
  * Entry 2 (Fee Charge): -5 USDT
* **State Updates**:
  * `ledger_cash_balance` = 10,000 - 5,000 - 5 = **4,995 USDT**
  * `holdings["BTC"]` = AssetHolding(quantity=0.1, mark_price=50,000, market_value=5,000)
* **Equity Calculation**:
  $$\text{Equity} = 4,995 \text{ (Cash)} + 5,000 \text{ (Holdings Value)} = \mathbf{9,995} \text{ USDT}$$

---

### Example 2: Long Futures Liquidation (Cross Margin)
* **Initial State**:
  * `AccountType` = FUTURES, Cross Margin Mode
  * `ledger_cash_balance` = 1,000 USDT
  * IMR = 0.10, MMR = 0.05
* **Action**: Open Long 1 BTC at 10,000 USDT (Leverage = 10x)
  * Position Size = 10,000 USDT
  * Initial Margin Required = 1,000 USDT
* **Liquidation Price Calculation**:
  $$\text{LP}_{\text{long}} = 10,000 \times \frac{1 - 0.10}{1 - 0.05} = \mathbf{9,473.68} \text{ USDT}$$
* **Verification at Mark Price = 9,473.68 USDT**:
  * `unrealized_pnl` = 1 × (9,473.68 - 10,000) = **-526.32 USDT**
  * `Equity` = 1,000 - 526.32 = **473.68 USDT**
  * `Maintenance Margin` = 9,473.68 × 1 × 0.05 = **473.68 USDT**
  * `Margin Ratio` = 473.68 / 473.68 = **1.0** (Liquidation triggers precisely at 1.0)

---

### Example 3: Short Futures Liquidation (Cross Margin)
* **Initial State**:
  * `AccountType` = FUTURES, Cross Margin Mode
  * `ledger_cash_balance` = 1,000 USDT
  * IMR = 0.10, MMR = 0.05
* **Action**: Open Short 1 BTC at 10,000 USDT (Leverage = 10x, Qty = -1.0)
* **Liquidation Price Calculation**:
  $$\text{LP}_{\text{short}} = 10,000 \times \frac{1 + 0.10}{1 + 0.05} = \mathbf{10,476.19} \text{ USDT}$$
* **Verification at Mark Price = 10,476.19 USDT**:
  * `unrealized_pnl` = -1 × (10,476.19 - 10,000) = **-476.19 USDT**
  * `Equity` = 1,000 - 476.19 = **523.81 USDT**
  * `Maintenance Margin` = 10,476.19 × 1 × 0.05 = **523.81 USDT**
  * `Margin Ratio` = 523.81 / 523.81 = **1.0** (Liquidation triggers precisely at 1.0)

---

### Example 4: Isolated Margin Collateral Increase
* **Initial State**:
  * `AccountType` = FUTURES, Isolated Margin Mode
  * `ledger_cash_balance` = 5,000 USDT
  * Open Long 1 BTC at 10,000 USDT. IMR = 0.10, MMR = 0.05.
  * `allocated_margin` = 1,000 USDT
  * Initial $\text{LP}_{\text{long, isolated}} = \frac{10,000 - 1,000}{1 - 0.05} = \mathbf{9,473.68} \text{ USDT}$
* **Action**: Add 500 USDT collateral to the position.
  * `allocated_margin` becomes 1,500 USDT.
  * `available_cash` decreases by 500 USDT.
* **New Liquidation Price Calculation**:
  $$\text{LP}_{\text{long, isolated}} = \frac{10,000 - 1,500}{1 - 0.05} = \frac{8,500}{0.95} = \mathbf{8,947.37} \text{ USDT}$$
  *(Liquidation price decreases, giving the position more breathing room)*

---

### Example 5: Fee & Funding Lifecycles
* **Fee Charge (Spot)**: Buy 10,000 USDT of Spot BTC. Fee = 10 USDT.
  * Ledger writes: `-10,000 TRADE_DEBIT`, `-10 FEE_CHARGE`
  * `ledger_cash_balance` decreases by 10,010 USDT.
* **Funding Payment (Futures)**: Hold Long 1 BTC (10,000 USDT) with a funding rate of 0.01% (to pay).
  * Ledger writes: `-1 FUNDING_ADJUSTMENT`
  * `ledger_cash_balance` decreases by 1 USDT.
  * Cash balance remains the single source of truth for these debits.

---

**Document Version**: 4.0  
**Last Updated**: 2026-08-02  
**Status**: MATHEMATICALLY RESOLVED  
