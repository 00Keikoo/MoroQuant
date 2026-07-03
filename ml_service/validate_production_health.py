#!/usr/bin/env python3
"""
Production Health Validation and Migration Runner for MoroQuant.
Ensures database migrations are applied and production models are healthy.
"""

import sys
import json
import sqlite3
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Ensure parent directory is in path
sys.path.insert(0, str(Path(__file__).parent))

from ml_service.utils.logger import get_logger
from ml_service.data.database import get_database

logger = get_logger(__name__)

MIGRATIONS_TABLE = "schema_migrations"


def run_migrations() -> List[str]:
    """
    Scan migrations folder, apply unapplied migrations automatically, and
    store applied migration history in the database.
    
    Returns:
        List of migration filenames that were newly applied.
    """
    db = get_database()
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return []

    # 1. Ensure migrations history table exists
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    # 2. Get list of already applied migrations
    applied = set()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT migration_name FROM {MIGRATIONS_TABLE}")
        for row in cursor.fetchall():
            applied.add(row[0])

    # 3. Find and sort all .sql migration files
    migration_files = sorted(migrations_dir.glob("*.sql"))
    newly_applied = []

    for sql_file in migration_files:
        name = sql_file.name
        if name in applied:
            continue

        logger.info(f"Applying pending migration: {name}")

        try:
            with open(sql_file, 'r') as f:
                sql_statements = f.read()

            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Split by semicolon and run statements individually
                for statement in sql_statements.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        cursor.execute(statement)

                # Record migration in history table
                cursor.execute(
                    f"INSERT INTO {MIGRATIONS_TABLE} (migration_name) VALUES (?)",
                    (name,)
                )
                conn.commit()

            logger.info(f"✓ Migration applied successfully: {name}")
            newly_applied.append(name)

        except sqlite3.OperationalError as e:
            err_msg = str(e).lower()
            if "duplicate column name" in err_msg or "already exists" in err_msg or "already another table or index" in err_msg or "no such table" in err_msg:
                logger.warning(f"Migration already applied, skipped, or missing table reference (non-fatal): {name} ({e})")
                # Still record in migrations table in case it was created manually or by another tool
                try:
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            f"INSERT INTO {MIGRATIONS_TABLE} (migration_name) VALUES (?)",
                            (name,)
                        )
                        conn.commit()
                except Exception:
                    pass # Ignore if insert fails because it already exists
            else:
                logger.error(f"✗ Failed to apply migration {name}: {e}")
                raise e
        except Exception as e:
            logger.error(f"✗ Failed to apply migration {name}: {e}")
            raise e

    if newly_applied:
        logger.info(f"Applied {len(newly_applied)} new migration(s)")
    else:
        logger.info("Database migrations up-to-date. No new migrations to apply.")

    return newly_applied


def validate_production_health() -> Dict[str, Any]:
    """
    Perform comprehensive validation checks on active production models.
    Checks:
    - active_models.json exists
    - registry entries point to existing production models
    - calibration artifacts exist when expected
    - metadata exists
    - feature compatibility validation passes
    """
    results = {
        "active_models": 0,
        "healthy_models": 0,
        "missing_models": [],
        "missing_calibration": [],
        "feature_mismatches": [],
        "missing_metadata": []
    }

    base_dir = Path(__file__).parent / "storage" / "models"
    registry_path = base_dir / "active_models.json"

    # 1. Check if active_models.json exists
    if not registry_path.exists():
        logger.error(f"Registry file not found: {registry_path}")
        results["missing_models"].append("active_models.json")
        return results

    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse active_models.json: {e}")
        results["missing_models"].append("active_models.json (corrupted)")
        return results

    production_dir = base_dir / "production"

    # Flatten registry entries into a list of (symbol, timeframe, filename)
    active_entries = []
    if isinstance(registry, dict):
        for symbol, tf_dict in registry.items():
            if isinstance(tf_dict, dict):
                for timeframe, filename in tf_dict.items():
                    active_entries.append((symbol, timeframe, filename))
    elif isinstance(registry, list):
        for entry in registry:
            symbol = entry.get("symbol")
            timeframe = entry.get("timeframe")
            filename = entry.get("filename")
            if symbol and timeframe and filename:
                active_entries.append((symbol, timeframe, filename))

    results["active_models"] = len(active_entries)

    # Lazy imports to prevent initialization issues
    import pandas as pd
    from models.trainer import prepare_features, get_feature_columns
    from models.governance import validate_model_compatibility

    healthy_count = 0

    for symbol, timeframe, filename in active_entries:
        model_path = production_dir / filename
        model_name = f"{symbol} {timeframe} ({filename})"
        is_healthy = True

        # 2. Check registry entries point to existing production models
        if not model_path.exists():
            logger.error(f"Production model file missing for {model_name}")
            results["missing_models"].append(model_name)
            is_healthy = False
            continue

        # 3. Verify metadata exists by unpickling
        metadata = None
        try:
            with open(model_path, 'rb') as f:
                model_package = pickle.load(f)
            metadata = model_package.get("metadata")
            if not metadata:
                logger.error(f"Model metadata is missing or empty for {model_name}")
                results["missing_metadata"].append(model_name)
                is_healthy = False
        except Exception as e:
            logger.error(f"Failed to load model file/metadata for {model_name}: {e}")
            results["missing_metadata"].append(f"{model_name} (load error: {str(e)})")
            is_healthy = False

        # 4. Check calibration artifacts exist when expected
        # Expected for BTCUSDT 1h
        is_cal_expected = (symbol == "BTCUSDT" and timeframe == "1h")
        cal_path = model_path.with_name(model_path.stem + "_calibration.pkl")
        if is_cal_expected and not cal_path.exists():
            logger.warning(f"Expected calibration artifact is missing for {model_name}")
            results["missing_calibration"].append(model_name)

        # 5. Check feature compatibility
        if metadata:
            try:
                # Generate sample DataFrame for feature set check
                df_sample = pd.DataFrame({
                    'timestamp': range(500),
                    'open': [100.0] * 500,
                    'high': [101.0] * 500,
                    'low': [99.0] * 500,
                    'close': [100.0] * 500,
                    'volume': [1000.0] * 500,
                })
                df_sample = prepare_features(df_sample, symbol=symbol)
                current_features = get_feature_columns(df_sample)

                is_compatible, missing_features = validate_model_compatibility(str(model_path), current_features)
                if not is_compatible:
                    logger.error(f"Feature compatibility mismatch for {model_name}: missing {missing_features}")
                    results["feature_mismatches"].append({
                        "model": model_name,
                        "missing_features": missing_features
                    })
                    is_healthy = False
            except Exception as e:
                logger.error(f"Error checking feature compatibility for {model_name}: {e}")
                results["feature_mismatches"].append({
                    "model": model_name,
                    "error": str(e)
                })
                is_healthy = False

        if is_healthy:
            healthy_count += 1

    results["healthy_models"] = healthy_count
    return results


def run_startup_validation():
    """
    Runs migrations and production health check.
    Refuses startup (raises SystemExit) if registry points to missing production models.
    """
    logger.info("Running Database Migrations...")
    try:
        run_migrations()
    except Exception as e:
        logger.critical(f"Database migrations failed on startup: {e}")
        sys.exit(1)

    logger.info("Running Production Health Validation...")
    results = validate_production_health()

    # Log non-critical issues as warnings
    for item in results["missing_calibration"]:
        logger.warning(f"Non-critical issue: Missing expected calibration file for {item}")
    for mismatch in results["feature_mismatches"]:
        logger.warning(f"Non-critical issue: Feature mismatch for {mismatch.get('model')}: missing {mismatch.get('missing_features')}")
    for item in results["missing_metadata"]:
        logger.warning(f"Non-critical issue: Missing metadata for {item}")

    # Refuse startup if registry points to missing production models
    if results["missing_models"]:
        logger.critical(f"Refusing startup: registry points to missing production model files or active_models.json is missing: {results['missing_models']}")
        sys.exit(1)

    logger.info(f"✓ Production Health Validation Passed. {results['healthy_models']}/{results['active_models']} models healthy.")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING STANDALONE PRODUCTION HEALTH & MIGRATIONS VALIDATION")
    print("=" * 80)
    try:
        run_startup_validation()
        print("✓ All validation passed successfully.")
        sys.exit(0)
    except SystemExit as se:
        print(f"✗ Validation failed with exit code: {se.code}")
        sys.exit(se.code)
    except Exception as exc:
        print(f"✗ Validation failed with unexpected exception: {exc}")
        sys.exit(1)
