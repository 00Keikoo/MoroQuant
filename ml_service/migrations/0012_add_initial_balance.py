"""Add initial_balance column to paper_account table.

Sprint 2.2B - Backend Portfolio Normalization
Stores starting capital for accurate return % calculations.
"""

def upgrade(conn):
    """Add initial_balance column with default value from STARTING_BALANCE."""
    conn.execute("""
        ALTER TABLE paper_account
        ADD COLUMN initial_balance REAL DEFAULT 10000.0
    """)
    conn.commit()


def downgrade(conn):
    """Remove initial_balance column."""
    # SQLite doesn't support DROP COLUMN directly in older versions
    # Create new table without the column, copy data, rename
    conn.execute("""
        CREATE TABLE paper_account_new (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            balance REAL NOT NULL DEFAULT 10000.0,
            equity REAL NOT NULL DEFAULT 10000.0,
            unrealized_pnl REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        INSERT INTO paper_account_new (id, balance, equity, unrealized_pnl, updated_at)
        SELECT id, balance, equity, unrealized_pnl, updated_at
        FROM paper_account
    """)

    conn.execute("DROP TABLE paper_account")
    conn.execute("ALTER TABLE paper_account_new RENAME TO paper_account")
    conn.commit()
