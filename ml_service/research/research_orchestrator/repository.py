"""Repository layer for research orchestrator."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ml_service.research.research_orchestrator.types import (
    ResearchJob,
    JobState,
    JobConfig,
    JobStep,
    JobLog,
    StageType
)


class ResearchOrchestratorRepository:
    """SQLite repository for research job tracking."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "storage" / "database.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def save_job(self, job: ResearchJob) -> None:
        """Save research job."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO research_jobs (
                    job_id, state, config_json, created_at,
                    started_at, completed_at, created_by,
                    error_message, error_stage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                job.state.value,
                json.dumps({
                    'symbol': job.config.symbol,
                    'timeframe': job.config.timeframe,
                    'algorithm': job.config.algorithm,
                    'start_date': job.config.start_date,
                    'end_date': job.config.end_date,
                    'parameters': job.config.parameters
                }),
                job.created_at,
                job.started_at,
                job.completed_at,
                job.created_by,
                job.error_message,
                job.error_stage.value if job.error_stage else None
            ))
            conn.commit()
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[ResearchJob]:
        """Retrieve research job by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM research_jobs WHERE job_id = ?
            """, (job_id,))

            row = cursor.fetchone()
            if not row:
                return None

            config_dict = json.loads(row['config_json'])
            config = JobConfig(
                symbol=config_dict['symbol'],
                timeframe=config_dict['timeframe'],
                algorithm=config_dict['algorithm'],
                start_date=config_dict['start_date'],
                end_date=config_dict['end_date'],
                parameters=config_dict['parameters']
            )

            return ResearchJob(
                job_id=row['job_id'],
                state=JobState(row['state']),
                config=config,
                created_at=row['created_at'],
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                created_by=row['created_by'],
                error_message=row['error_message'],
                error_stage=StageType(row['error_stage']) if row['error_stage'] else None
            )
        finally:
            conn.close()

    def update_job_state(
        self,
        job_id: str,
        new_state: JobState,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        error_message: Optional[str] = None,
        error_stage: Optional[StageType] = None
    ) -> None:
        """Update job state and timestamps."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE research_jobs
                SET state = ?, started_at = COALESCE(?, started_at),
                    completed_at = ?, error_message = ?, error_stage = ?
                WHERE job_id = ?
            """, (
                new_state.value,
                started_at,
                completed_at,
                error_message,
                error_stage.value if error_stage else None,
                job_id
            ))
            conn.commit()
        finally:
            conn.close()

    def list_jobs(
        self,
        state: Optional[JobState] = None,
        limit: int = 50
    ) -> List[ResearchJob]:
        """List jobs, optionally filtered by state."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if state:
                cursor.execute("""
                    SELECT job_id FROM research_jobs
                    WHERE state = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (state.value, limit))
            else:
                cursor.execute("""
                    SELECT job_id FROM research_jobs
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

            return [self.get_job(row['job_id']) for row in cursor.fetchall()]
        finally:
            conn.close()

    def save_step(self, step: JobStep) -> None:
        """Save job step."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO research_job_steps (
                    step_id, job_id, stage_type, status,
                    started_at, completed_at, output_metadata_json,
                    error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step.step_id,
                step.job_id,
                step.stage_type.value,
                step.status,
                step.started_at,
                step.completed_at,
                json.dumps(step.output_metadata) if step.output_metadata else None,
                step.error_message
            ))
            conn.commit()
        finally:
            conn.close()

    def update_step(
        self,
        step_id: str,
        status: str,
        completed_at: Optional[str] = None,
        output_metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update step completion status."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE research_job_steps
                SET status = ?, completed_at = ?,
                    output_metadata_json = ?, error_message = ?
                WHERE step_id = ?
            """, (
                status,
                completed_at,
                json.dumps(output_metadata) if output_metadata else None,
                error_message,
                step_id
            ))
            conn.commit()
        finally:
            conn.close()

    def get_steps(self, job_id: str) -> List[JobStep]:
        """Get all steps for a job."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM research_job_steps
                WHERE job_id = ?
                ORDER BY started_at ASC
            """, (job_id,))

            steps = []
            for row in cursor.fetchall():
                output_metadata = None
                if row['output_metadata_json']:
                    output_metadata = json.loads(row['output_metadata_json'])

                steps.append(JobStep(
                    step_id=row['step_id'],
                    job_id=row['job_id'],
                    stage_type=StageType(row['stage_type']),
                    status=row['status'],
                    started_at=row['started_at'],
                    completed_at=row['completed_at'],
                    output_metadata=output_metadata,
                    error_message=row['error_message']
                ))
            return steps
        finally:
            conn.close()

    def save_log(self, log: JobLog) -> None:
        """Save execution log entry."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO research_job_logs (
                    log_id, job_id, timestamp, level, message, stage_type
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log.log_id,
                log.job_id,
                log.timestamp,
                log.level,
                log.message,
                log.stage_type.value if log.stage_type else None
            ))
            conn.commit()
        finally:
            conn.close()

    def get_logs(
        self,
        job_id: str,
        level: Optional[str] = None,
        limit: int = 1000
    ) -> List[JobLog]:
        """Get logs for a job."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if level:
                cursor.execute("""
                    SELECT * FROM research_job_logs
                    WHERE job_id = ? AND level = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (job_id, level, limit))
            else:
                cursor.execute("""
                    SELECT * FROM research_job_logs
                    WHERE job_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (job_id, limit))

            logs = []
            for row in cursor.fetchall():
                logs.append(JobLog(
                    log_id=row['log_id'],
                    job_id=row['job_id'],
                    timestamp=row['timestamp'],
                    level=row['level'],
                    message=row['message'],
                    stage_type=StageType(row['stage_type']) if row['stage_type'] else None
                ))
            return logs
        finally:
            conn.close()
