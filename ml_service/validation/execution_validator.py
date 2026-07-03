"""Execution Validator.

Validates paper trading execution metrics against deterministic rules.
Entry point for validation operations.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

from ml_service.utils.logger import get_logger

from .execution_report import ValidationReport
from .execution_rules import ALL_RULES

logger = get_logger()

_DB_PATH: Path = Path(__file__).parent.parent / "storage" / "database.db"


def _get_connection():
    """Get database connection with Row factory."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def validate_position(position: Dict) -> List:
    """Validate a single position against all rules.

    Args:
        position: Position dictionary with all required fields

    Returns:
        List of ValidationFailure objects (empty if all rules pass)
    """
    failures = []
    for rule_func in ALL_RULES:
        failure = rule_func(position)
        if failure:
            failures.append(failure)
    return failures


def validate_all_positions(
    verbose: bool = False, fail_fast: bool = False
) -> ValidationReport:
    """Validate all closed positions in the database.

    Args:
        verbose: Print detailed progress during validation
        fail_fast: Stop on first ERROR-level failure

    Returns:
        ValidationReport with complete results
    """
    conn = _get_connection()

    try:
        rows = conn.execute(
            """
            SELECT id, symbol, direction, entry_price, current_price, size_usdt, qty,
                   stop_loss, take_profit, signal_id, status, realized_pnl,
                   opened_at, closed_at, mae, mfe, mae_timestamp, mfe_timestamp,
                   eqs, profit_capture_ratio, final_exit_reason,
                   trailing_stop_enabled, trailing_stop_activated, sl_move_count,
                   break_even_triggered, confidence, regime, timeframe,
                   prob_short, prob_neutral, prob_long, execution_edge, skip_reason
            FROM paper_positions
            WHERE status != 'OPEN'
            """
        ).fetchall()
    finally:
        conn.close()

    report = ValidationReport()

    if verbose:
        print(f"\nValidating {len(rows)} closed positions...")

    for row in rows:
        position = dict(row)
        failures = validate_position(position)

        if failures:
            for failure in failures:
                report.add_failure(failure)
                if verbose:
                    print(
                        f"  Position {failure.position_id}: {failure.rule_violated} [{failure.severity}]"
                    )
                if fail_fast and failure.severity == "ERROR":
                    if verbose:
                        print("\nFail-fast mode: stopping on first ERROR")
                    report.print_summary()
                    return report
        else:
            report.add_pass()

    return report


def main():
    """CLI entry point for validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate paper trading execution metrics"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed progress"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first ERROR-level failure",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output report as JSON"
    )
    parser.add_argument(
        "--position-id",
        type=int,
        help="Validate a single position by ID",
    )

    args = parser.parse_args()

    if args.position_id:
        conn = _get_connection()
        try:
            row = conn.execute(
                """
                SELECT id, symbol, direction, entry_price, current_price, size_usdt, qty,
                       stop_loss, take_profit, signal_id, status, realized_pnl,
                       opened_at, closed_at, mae, mfe, mae_timestamp, mfe_timestamp,
                       eqs, profit_capture_ratio, final_exit_reason,
                       trailing_stop_enabled, trailing_stop_activated, sl_move_count,
                       break_even_triggered, confidence, regime, timeframe,
                       prob_short, prob_neutral, prob_long, execution_edge, skip_reason
                FROM paper_positions
                WHERE id = ? AND status != 'OPEN'
                """,
                (args.position_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            print(f"Position {args.position_id} not found or is still OPEN")
            sys.exit(1)

        position = dict(row)
        failures = validate_position(position)

        report = ValidationReport()
        if failures:
            for failure in failures:
                report.add_failure(failure)
        else:
            report.add_pass()

        if args.json:
            import json

            print(json.dumps(report.to_dict(), indent=2))
        else:
            report.print_summary()

        sys.exit(0 if report.failed == 0 else 1)

    report = validate_all_positions(verbose=args.verbose, fail_fast=args.fail_fast)

    if args.json:
        import json

        print(json.dumps(report.to_dict(), indent=2))
    else:
        report.print_summary()

    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
