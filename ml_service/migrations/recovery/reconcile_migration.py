#!/usr/bin/env python3
"""
Recovery Utility for Metadata Reconciliation (Strategy A under ADR-023).
Allows recording an already-satisfied migration into schema_migrations safely.
"""

import sys
import re
import json
import argparse
import getpass
import hashlib
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from ml_service.data.database import get_database
from ml_service.utils.logger import get_logger

logger = get_logger()


def strip_sql_comments(sql: str) -> str:
    """Remove SQL comments from a statement while preserving the code."""
    result = []
    i = 0
    while i < len(sql):
        # Check for multi-line comment
        if i < len(sql) - 1 and sql[i:i+2] == '/*':
            i += 2
            while i < len(sql) - 1:
                if sql[i:i+2] == '*/':
                    i += 2
                    break
                i += 1
            continue

        # Check for single-line comment
        if i < len(sql) - 1 and sql[i:i+2] == '--':
            while i < len(sql) and sql[i] != '\n':
                i += 1
            if i < len(sql):
                result.append('\n')
                i += 1
            continue

        result.append(sql[i])
        i += 1

    return ''.join(result)


def parse_sql_requirements(sql_content: str) -> list:
    """
    Parses SQL migration statements and returns a list of requirements to check.
    Each requirement is a dict:
      {
        "type": "table" | "column" | "index",
        "table": str (for table/column),
        "column": str (for column),
        "index": str (for index)
      }
    """
    cleaned_sql = strip_sql_comments(sql_content)
    statements = [s.strip() for s in cleaned_sql.split(';') if s.strip()]
    requirements = []

    for stmt in statements:
        # Match ALTER TABLE ... ADD COLUMN ...
        alter_match = re.search(r"(?i)ALTER\s+TABLE\s+(\w+)\s+ADD\s+(?:COLUMN\s+)?(\w+)", stmt)
        if alter_match:
            table_name, col_name = alter_match.groups()
            requirements.append({
                "type": "column",
                "table": table_name,
                "column": col_name
            })
            continue

        # Match CREATE INDEX ... ON ...
        index_match = re.search(r"(?i)CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+ON\s+(\w+)", stmt)
        if index_match:
            idx_name, table_name = index_match.groups()
            requirements.append({
                "type": "index",
                "index": idx_name
            })
            continue

        # Match CREATE TABLE ...
        create_match = re.search(r"(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", stmt)
        if create_match:
            table_name = create_match.group(1)
            requirements.append({
                "type": "table",
                "table": table_name
            })
            # Extract column names inside parentheses
            start_idx = stmt.find('(')
            end_idx = stmt.rfind(')')
            if start_idx != -1 and end_idx != -1:
                cols_part = stmt[start_idx+1:end_idx].strip()
                # Split by comma but respect parenthesis depth
                parts = []
                current = []
                depth = 0
                for char in cols_part:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1
                    
                    if char == ',' and depth == 0:
                        parts.append(''.join(current).strip())
                        current = []
                    else:
                        current.append(char)
                if current:
                    parts.append(''.join(current).strip())

                for part in parts:
                    part_clean = re.sub(r'\s+', ' ', part).strip()
                    if not part_clean:
                        continue
                    upper_part = part_clean.upper()
                    is_constraint = False
                    for keyword in ['CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK']:
                        if upper_part.startswith(keyword):
                            is_constraint = True
                            break
                    if is_constraint:
                        continue
                    col_words = part_clean.split(' ')
                    if col_words:
                        col_name = col_words[0]
                        if col_name and not col_name.upper().startswith(('PRIMARY', 'FOREIGN', 'CONSTRAINT', 'CHECK', 'UNIQUE')):
                            requirements.append({
                                "type": "column",
                                "table": table_name,
                                "column": col_name
                            })
            continue

    return requirements


def check_table_exists(cursor, table_name: str) -> bool:
    """Check if a table exists in the database schema."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a specific table."""
    if not check_table_exists(cursor, table_name):
        return False
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    return column_name in columns


def check_index_exists(cursor, index_name: str) -> bool:
    """Check if an index exists in the database schema."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def check_migration_recorded(cursor, migration_name: str) -> bool:
    """Check if a migration is already recorded in schema_migrations."""
    try:
        cursor.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_name = ?",
            (migration_name,)
        )
        return cursor.fetchone() is not None
    except Exception:
        return False


def calculate_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_recovery_log(migration_name: str, operator: str, result: str, inserted: bool, rollback: bool, checksum: str):
    """Write recovery execution details to a json log file."""
    # Extract migration identifier (e.g. '029')
    match = re.match(r"^(\d+)", migration_name)
    log_name = f"recovery_{match.group(1)}.json" if match else f"recovery_{Path(migration_name).stem}.json"
    
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_name

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "operator": operator,
        "migration": migration_name,
        "verification result": result,
        "inserted": inserted,
        "rollback": rollback,
        "checksum": checksum
    }

    with open(log_path, 'w') as f:
        json.dump(log_data, f, indent=2)
    logger.info(f"Recovery log written to {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Reconcile metadata migrations under Strategy A.")
    parser.add_argument("--migration", required=True, help="Migration filename (e.g., 029_enrich_execution_audit.sql)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Dry run validation")
    group.add_argument("--execute", action="store_true", help="Execute the recovery reconciliation")

    args = parser.parse_args()
    migration_name = args.migration

    # Resolve migration file path
    migrations_dir = project_root / "ml_service" / "migrations"
    migration_file = migrations_dir / migration_name

    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        sys.exit(1)

    # Read migration content
    with open(migration_file, 'r') as f:
        sql_content = f.read()

    requirements = parse_sql_requirements(sql_content)
    checksum = calculate_checksum(migration_file)
    operator = getpass.getuser()

    # Inspect database
    db = get_database()
    
    physical_schema_pass = True
    metadata_exists = False
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Verify physical schema satisfaction
        for req in requirements:
            req_type = req["type"]
            if req_type == "table":
                if not check_table_exists(cursor, req["table"]):
                    physical_schema_pass = False
                    logger.error(f"Missing physical table: {req['table']}")
            elif req_type == "column":
                if not check_column_exists(cursor, req["table"], req["column"]):
                    physical_schema_pass = False
                    logger.error(f"Missing physical column: {req['table']}.{req['column']}")
            elif req_type == "index":
                if not check_index_exists(cursor, req["index"]):
                    physical_schema_pass = False
                    logger.error(f"Missing physical index: {req['index']}")
        
        # Check metadata ledger
        metadata_exists = check_migration_recorded(cursor, migration_name)

    # Print Dry Run output
    if args.dry_run:
        print("Migration:")
        print(migration_name)
        print()
        print("Physical Schema:")
        print("PASS" if physical_schema_pass else "FAIL")
        print()
        print("Metadata:")
        print("APPLIED" if metadata_exists else "MISSING")
        print()
        print("Recovery:")
        if not physical_schema_pass:
            recovery_status = "DENIED"
        elif metadata_exists:
            recovery_status = "NO-OP"
        else:
            recovery_status = "WOULD INSERT"
        print(recovery_status)
        print()
        print("Transaction:")
        print("NOT EXECUTED")
        print()
        print("No database changes.")
        
        if not physical_schema_pass:
            print(f"\nRecovery denied. Physical schema does not satisfy migration {migration_name}.")
            sys.exit(1)
        sys.exit(0)

    # Execute Mode
    if args.execute:
        if not physical_schema_pass:
            print(f"Recovery denied. Physical schema does not satisfy migration {migration_name}.")
            write_recovery_log(migration_name, operator, "FAIL", False, False, checksum)
            sys.exit(1)

        if metadata_exists:
            print(f"Migration {migration_name} is already recorded in schema_migrations. Clean exit.")
            sys.exit(0)

        # Prompt for confirmation
        print("Type:")
        print("I UNDERSTAND")
        print("to continue.")
        try:
            confirm = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

        if confirm != "I UNDERSTAND":
            print("Abort.")
            sys.exit(1)

        # Run transaction
        success = False
        rollback = False
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN")
            try:
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                    (migration_name,)
                )
                conn.commit()
                success = True
            except Exception as e:
                conn.rollback()
                rollback = True
                logger.error(f"Transaction failed, rolled back: {e}")

        if success:
            print(f"Recovery executed successfully. Recorded {migration_name} in schema_migrations.")
            write_recovery_log(migration_name, operator, "PASS", True, False, checksum)
            sys.exit(0)
        else:
            print("Recovery execution failed.")
            write_recovery_log(migration_name, operator, "PASS", False, rollback, checksum)
            sys.exit(1)


if __name__ == "__main__":
    main()
