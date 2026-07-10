-- Generic execution decisions audit table
-- Persists every execution attempt (ACCEPTED or REJECTED)
-- ACCEPTED decisions link to paper_positions
-- REJECTED decisions store reason code

CREATE TABLE IF NOT EXISTS execution_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Core fields
    symbol TEXT NOT NULL,
    direction TEXT,
    decision TEXT NOT NULL CHECK(decision IN ('ACCEPTED', 'REJECTED')),
    reason TEXT,

    -- Foreign keys
    signal_id INTEGER,
    position_id INTEGER,

    -- Signal metadata (captured at decision time)
    confidence INTEGER,
    regime TEXT,
    timeframe TEXT,
    prob_short REAL,
    prob_neutral REAL,
    prob_long REAL,
    execution_edge REAL,

    -- Pricing metadata
    signal_price REAL,
    execution_price REAL,
    slippage_pct REAL,
    execution_latency_ms INTEGER,

    -- Audit timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (signal_id) REFERENCES signals(id),
    FOREIGN KEY (position_id) REFERENCES paper_positions(id)
);

CREATE INDEX IF NOT EXISTS idx_execution_decisions_symbol
    ON execution_decisions(symbol);

CREATE INDEX IF NOT EXISTS idx_execution_decisions_decision
    ON execution_decisions(decision);

CREATE INDEX IF NOT EXISTS idx_execution_decisions_created_at
    ON execution_decisions(created_at);

CREATE INDEX IF NOT EXISTS idx_execution_decisions_reason
    ON execution_decisions(reason)
    WHERE decision = 'REJECTED';
