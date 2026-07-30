"""Recovery orchestrator for database schema recovery framework.

Coordinates the lifecycle of recovery components in a stateless and deterministic manner.
"""

import os
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Dict

from ml_service.migrations.recovery.schema_inspector import SchemaInspector
from ml_service.migrations.recovery.decision.analyzer import DecisionAnalyzer
from ml_service.migrations.recovery.executor import RecoveryExecutor, ApprovalRequiredError
from ml_service.migrations.recovery.reporter import RecoveryReporter
from ml_service.migrations.recovery.models import (
    DecisionContext,
    RecoveryDecision,
    SchemaDifference,
    ExecutionSummary,
    RecoveryRisk,
)
from ml_service.data.database import Database


class RecoveryOrchestrator:
    """Orchestrates database schema recovery workflows.

    Coordinates inspector, analyzer, executor, and reporter components.
    This orchestrator is stateless and performs no SQL execution or filesystem writes directly.
    """

    def __init__(
        self,
        db_path: str,
        migrations_dir: str,
        inspector_class=SchemaInspector,
        analyzer_class=DecisionAnalyzer,
        executor_class=RecoveryExecutor,
        reporter_class=RecoveryReporter,
    ) -> None:
        """Initialize the RecoveryOrchestrator.

        Args:
            db_path: Absolute path to the SQLite database.
            migrations_dir: Absolute path to the migrations directory.
            inspector_class: SchemaInspector class or mock/subclass.
            analyzer_class: DecisionAnalyzer class or mock/subclass.
            executor_class: RecoveryExecutor class or mock/subclass.
            reporter_class: RecoveryReporter class or mock/subclass.
        """
        # Accept either Database instance or string path for robustness
        if isinstance(db_path, str):
            self._db = Database(db_path=db_path)
            self._db_path = db_path
        else:
            self._db = db_path
            self._db_path = str(db_path.db_path) if hasattr(db_path, "db_path") else str(db_path)

        self._migrations_dir = migrations_dir
        self._inspector_class = inspector_class
        self._analyzer_class = analyzer_class
        self._executor_class = executor_class
        self._reporter_class = reporter_class

    def _derive_migration_state(self) -> Tuple[Tuple[str, ...], Tuple[str, ...], Dict[str, str]]:
        """Derives applied migrations, available migrations, and checksums from dependencies."""
        import sqlite3

        # 1. Load applied migrations from the schema_migrations ledger
        applied = []
        try:
            db_path = self._db_path
            # Open read-only connection
            db_uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(db_uri, uri=True)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
                )
                if cursor.fetchone():
                    cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY id ASC")
                    applied = [row[0] for row in cursor.fetchall()]
            finally:
                conn.close()
        except Exception:
            pass

        # 2. Scan migrations directory for available migrations and compute checksums
        available = []
        checksums = {}
        if self._migrations_dir:
            migration_paths = sorted(Path(self._migrations_dir).glob("*.sql"))
            for path in migration_paths:
                available.append(path.name)
                hasher = hashlib.sha256()
                try:
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
                    checksums[path.name] = hasher.hexdigest()
                except Exception:
                    pass

        return tuple(applied), tuple(available), checksums

    def run_diagnostics(self) -> Tuple[RecoveryDecision, ...]:
        """Runs the inspect and analysis workflow phase.

        Returns:
            Tuple of calculated RecoveryDecision records.
        """
        # Invoke SchemaInspector
        inspector = self._inspector_class(self._db)
        _ = inspector.capture_snapshot()

        # Retrieve differences from inspector if supported, otherwise empty tuple
        differences = ()
        if hasattr(inspector, "detect_differences"):
            differences = inspector.detect_differences()
        elif hasattr(inspector, "get_differences"):
            differences = inspector.get_differences()

        # Derive migration state internally
        applied_migrations, available_migrations, checksums = self._derive_migration_state()

        # Construct DecisionContext
        context = DecisionContext(
            applied_migration_names=applied_migrations,
            available_migration_files=available_migrations,
            migration_checksums=checksums,
        )

        # Invoke DecisionAnalyzer
        analyzer = self._analyzer_class(context)
        decisions = analyzer.analyze(differences)
        return decisions

    def apply_recovery(
        self,
        decisions: Tuple[RecoveryDecision, ...],
        operator: str,
        approval_token: Optional[str] = None,
    ) -> Tuple[ExecutionSummary, str]:
        """Applies the recovery decisions, executing transactions and saving audit logs.

        Args:
            decisions: Sequence of decisions to execute.
            operator: Identifier for the operator triggering the execution.
            approval_token: Manual validation token.

        Returns:
            Tuple containing the ExecutionSummary and report path.

        Raises:
            ApprovalRequiredError: If HIGH/CRITICAL actions lack valid token.
        """
        # Validate approval requirements
        env_token = os.environ.get("MQ_CTO_APPROVAL_TOKEN")
        for decision in decisions:
            if decision.risk in (RecoveryRisk.HIGH, RecoveryRisk.CRITICAL):
                if not approval_token or approval_token != env_token:
                    raise ApprovalRequiredError(
                        f"Action for {decision.difference.table_name or 'schema'} "
                        f"requires CTO approval. Mismatched or missing token."
                    )

        # Derive migration state internally
        applied_migrations, available_migrations, checksums = self._derive_migration_state()

        # Construct DecisionContext
        context = DecisionContext(
            applied_migration_names=applied_migrations,
            available_migration_files=available_migrations,
            migration_checksums=checksums,
        )

        # Invoke RecoveryExecutor
        executor = self._executor_class(context, self._db_path)
        results = executor.execute(decisions)

        # Invoke RecoveryReporter
        summary, report_path = self._reporter_class.write_report(
            results=results,
            operator=operator,
            output_dir="storage/reports/recovery_audit",
        )

        return summary, report_path

