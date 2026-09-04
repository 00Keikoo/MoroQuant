"""Phase 1 schema tests for Sprint 3.9D-16 research session persistence.

Tests:
- Table existence (research_sessions, research_experiments, research_runs)
- Primary key constraints
- Foreign key relationships
- NOT NULL constraints
- CHECK constraints on status fields
- Index existence
- Cascade deletion behavior
- Bootstrap idempotency
- Isolation from execution/trading infrastructure
"""

import sqlite3
import tempfile
from pathlib import Path

from ml_service.bootstrap.research_database import bootstrap_research_tables


def test_research_session_tables_exist():
    """Verify all three research session tables are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "research_sessions" in tables
        assert "research_experiments" in tables
        assert "research_runs" in tables

        conn.close()


def test_research_sessions_primary_key():
    """Verify session_id is unique primary key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES ('session-1', 'CREATED', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        try:
            cursor.execute("""
                INSERT INTO research_sessions (
                    session_id, status, config_json, created_at
                ) VALUES ('session-1', 'CREATED', '{}', '2024-01-01T00:00:00Z')
            """)
            conn.commit()
            assert False, "Expected PRIMARY KEY constraint violation"
        except sqlite3.IntegrityError:
            pass

        conn.close()


def test_research_sessions_not_null_constraints():
    """Verify required fields are NOT NULL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO research_sessions (session_id, status, config_json)
                VALUES ('session-1', 'CREATED', '{}')
            """)
            conn.commit()
            assert False, "Expected NOT NULL constraint violation on created_at"
        except sqlite3.IntegrityError:
            pass

        try:
            cursor.execute("""
                INSERT INTO research_sessions (session_id, config_json, created_at)
                VALUES ('session-1', '{}', '2024-01-01T00:00:00Z')
            """)
            conn.commit()
            assert False, "Expected NOT NULL constraint violation on status"
        except sqlite3.IntegrityError:
            pass

        conn.close()


def test_research_sessions_status_check_constraint():
    """Verify status CHECK constraint accepts canonical orchestrator lifecycle, failure states, and legacy states."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        invalid_statuses = [
            'INVALID_STATUS',
            'PENDING_BAD',
            'FAILED_',
            'QUEUED',
            'UNKNOWN',
            'COMPLETED_STAGE',
            '',
        ]
        for invalid_status in invalid_statuses:
            try:
                cursor.execute("""
                    INSERT INTO research_sessions (
                        session_id, status, config_json, created_at
                    ) VALUES ('session-inv', ?, '{}', '2024-01-01T00:00:00Z')
                """, (invalid_status,))
                conn.commit()
                assert False, f"Expected CHECK constraint violation on invalid status: {invalid_status}"
            except sqlite3.IntegrityError:
                pass

        canonical_statuses = [
            'PENDING',
            'SNAPSHOT',
            'REPLAY',
            'EXPERIMENT',
            'EVALUATION',
            'REPORTING',
            'BENCHMARK',
            'PROMOTION',
            'COMPLETED',
        ]
        for status in canonical_statuses:
            cursor.execute("""
                INSERT INTO research_sessions (
                    session_id, status, config_json, created_at
                ) VALUES (?, ?, '{}', '2024-01-01T00:00:00Z')
            """, (f"session-canonical-{status}", status))
            conn.commit()

        failure_statuses = [
            'FAILED/SNAPSHOT',
            'FAILED/REPLAY',
            'FAILED/EXPERIMENT',
            'FAILED/EVALUATION',
            'FAILED/REPORTING',
            'FAILED/BENCHMARK',
            'FAILED/PROMOTION',
        ]
        for status in failure_statuses:
            cursor.execute("""
                INSERT INTO research_sessions (
                    session_id, status, config_json, created_at
                ) VALUES (?, ?, '{}', '2024-01-01T00:00:00Z')
            """, (f"session-fail-{status.replace('/', '-')}", status))
            conn.commit()

        legacy_statuses = ['CREATED', 'RUNNING', 'FAILED', 'CANCELLED']
        for status in legacy_statuses:
            cursor.execute("""
                INSERT INTO research_sessions (
                    session_id, status, config_json, created_at
                ) VALUES (?, ?, '{}', '2024-01-01T00:00:00Z')
            """, (f"session-legacy-{status}", status))
            conn.commit()

        conn.close()


def test_research_experiments_status_check_constraint():
    """Verify research_experiments status CHECK constraint aligns with canonical lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES ('session-exp-check', 'PENDING', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        invalid_statuses = ['INVALID_STATUS', 'CREATED', 'RUNNING', 'COMPLETED', 'QUEUED', '']
        for invalid_status in invalid_statuses:
            try:
                cursor.execute("""
                    INSERT INTO research_experiments (
                        experiment_id, session_id, status, hypothesis_json, created_at
                    ) VALUES ('exp-inv', 'session-exp-check', ?, '{}', '2024-01-01T00:00:00Z')
                """, (invalid_status,))
                conn.commit()
                assert False, f"Expected CHECK constraint violation on invalid experiment status: {invalid_status}"
            except sqlite3.IntegrityError:
                pass

        valid_statuses = ['INITIALIZED', 'ACTIVE', 'EVALUATED', 'FAILED', 'CANCELLED']
        for valid_status in valid_statuses:
            cursor.execute("""
                INSERT INTO research_experiments (
                    experiment_id, session_id, status, hypothesis_json, created_at
                ) VALUES (?, 'session-exp-check', ?, '{}', '2024-01-01T00:00:00Z')
            """, (f"exp-{valid_status}", valid_status))
            conn.commit()

        conn.close()


def test_research_experiments_foreign_key():
    """Verify experiment references valid session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES ('session-1', 'CREATED', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        cursor.execute("""
            INSERT INTO research_experiments (
                experiment_id, session_id, status, hypothesis_json, created_at
            ) VALUES ('exp-1', 'session-1', 'INITIALIZED', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        try:
            cursor.execute("""
                INSERT INTO research_experiments (
                    experiment_id, session_id, status, hypothesis_json, created_at
                ) VALUES ('exp-2', 'invalid-session', 'INITIALIZED', '{}', '2024-01-01T00:00:00Z')
            """)
            conn.commit()
            assert False, "Expected FOREIGN KEY constraint violation"
        except sqlite3.IntegrityError:
            pass

        conn.close()


def test_research_runs_foreign_keys():
    """Verify run references valid experiment and session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES ('session-1', 'CREATED', '{}', '2024-01-01T00:00:00Z')
        """)
        cursor.execute("""
            INSERT INTO research_experiments (
                experiment_id, session_id, status, hypothesis_json, created_at
            ) VALUES ('exp-1', 'session-1', 'INITIALIZED', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        cursor.execute("""
            INSERT INTO research_runs (
                run_id, experiment_id, session_id, status,
                hyperparameters_json, metrics_json, created_at
            ) VALUES ('run-1', 'exp-1', 'session-1', 'CREATED', '{}', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        try:
            cursor.execute("""
                INSERT INTO research_runs (
                    run_id, experiment_id, session_id, status,
                    hyperparameters_json, metrics_json, created_at
                ) VALUES ('run-2', 'invalid-exp', 'session-1', 'CREATED', '{}', '{}', '2024-01-01T00:00:00Z')
            """)
            conn.commit()
            assert False, "Expected FOREIGN KEY constraint violation on experiment_id"
        except sqlite3.IntegrityError:
            pass

        conn.close()


def test_research_runs_cascade_deletion():
    """Verify cascade deletion works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES ('session-1', 'CREATED', '{}', '2024-01-01T00:00:00Z')
        """)
        cursor.execute("""
            INSERT INTO research_experiments (
                experiment_id, session_id, status, hypothesis_json, created_at
            ) VALUES ('exp-1', 'session-1', 'INITIALIZED', '{}', '2024-01-01T00:00:00Z')
        """)
        cursor.execute("""
            INSERT INTO research_runs (
                run_id, experiment_id, session_id, status,
                hyperparameters_json, metrics_json, created_at
            ) VALUES ('run-1', 'exp-1', 'session-1', 'CREATED', '{}', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        cursor.execute("DELETE FROM research_experiments WHERE experiment_id = 'exp-1'")
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM research_runs WHERE run_id = 'run-1'")
        count = cursor.fetchone()[0]
        assert count == 0, "Expected cascade delete to remove run"

        conn.close()


def test_research_session_indexes_exist():
    """Verify required indexes are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='research_sessions'
        """)
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_research_sessions_status" in indexes
        assert "idx_research_sessions_created_at" in indexes
        assert "idx_research_sessions_dataset_version_id" in indexes
        assert "idx_research_sessions_model_fingerprint" in indexes

        conn.close()


def test_bootstrap_idempotency():
    """Verify bootstrap can run multiple times without errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")

        bootstrap_research_tables(db_path)
        bootstrap_research_tables(db_path)
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "research_sessions" in tables
        assert "research_experiments" in tables
        assert "research_runs" in tables

        conn.close()


def test_research_schema_isolation():
    """Verify research session schema is isolated from execution infrastructure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES ('session-1', 'CREATED', '{}', '2024-01-01T00:00:00Z')
        """)
        conn.commit()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "research_sessions" in tables
        assert "paper_account" not in tables
        assert "portfolio" not in tables
        assert "execution" not in tables

        conn.close()


def test_orchestrator_lifecycle_persistence_contract():
    """Verify that every stage transition of ResearchSessionOrchestrator can be persisted to SQLite.

    Validates runtime contract compatibility:
    PENDING -> SNAPSHOT -> REPLAY -> EXPERIMENT -> EVALUATION -> REPORTING -> BENCHMARK -> PROMOTION -> COMPLETED
    and stage failure states (FAILED/<STAGE>).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        bootstrap_research_tables(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        session_id = "orch-session-lifecycle"

        # 1. PENDING (Initial session creation)
        cursor.execute("""
            INSERT INTO research_sessions (
                session_id, status, config_json, created_at
            ) VALUES (?, 'PENDING', '{"model_version_id": "model-v1"}', '2024-01-01T00:00:00Z')
        """, (session_id,))
        conn.commit()

        # 2. Sequential stage progression matching ResearchSessionOrchestrator
        stage_transitions = [
            ("SNAPSHOT", {"snapshot_id": "snap-1", "dataset_fingerprint": "fp_ds_001"}),
            ("REPLAY", {"replay_fingerprint": "fp_rep_001"}),
            ("EXPERIMENT", {"experiment_fingerprint": "fp_exp_001"}),
            ("EVALUATION", {"evaluation_fingerprint": "fp_eval_001"}),
            ("REPORTING", {}),
            ("BENCHMARK", {}),
            ("PROMOTION", {}),
            ("COMPLETED", {"model_fingerprint": "fp_mdl_001", "completed_at": "2024-01-01T01:00:00Z"}),
        ]

        for stage_status, metadata in stage_transitions:
            set_clauses = ["status = ?"]
            params = [stage_status]
            for col, val in metadata.items():
                set_clauses.append(f"{col} = ?")
                params.append(val)
            params.append(session_id)

            sql = f"UPDATE research_sessions SET {', '.join(set_clauses)} WHERE session_id = ?"
            cursor.execute(sql, params)
            conn.commit()

            cursor.execute("SELECT status FROM research_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            assert row is not None and row[0] == stage_status, f"Failed asserting stage {stage_status}"

        # 3. Stage failure states can be persisted directly upon stage exception
        stage_failures = [
            "FAILED/SNAPSHOT",
            "FAILED/REPLAY",
            "FAILED/EXPERIMENT",
            "FAILED/EVALUATION",
            "FAILED/REPORTING",
            "FAILED/BENCHMARK",
            "FAILED/PROMOTION",
        ]
        for fail_status in stage_failures:
            fail_session_id = f"orch-fail-{fail_status.replace('/', '-')}"
            cursor.execute("""
                INSERT INTO research_sessions (
                    session_id, status, config_json, created_at, completed_at
                ) VALUES (?, ?, '{}', '2024-01-01T00:00:00Z', '2024-01-01T00:05:00Z')
            """, (fail_session_id, fail_status))
            conn.commit()

            cursor.execute("SELECT status FROM research_sessions WHERE session_id = ?", (fail_session_id,))
            row = cursor.fetchone()
            assert row is not None and row[0] == fail_status, f"Failed asserting failure state {fail_status}"

        conn.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
