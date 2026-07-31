import datetime
from typing import Dict, Tuple, Optional, Any, Union, List
from dataclasses import replace
import uuid

from ml_service.research.models import ResearchSession, ResearchExperiment, ResearchRun

def make_immutable(val: Any) -> Any:
    """Helper to convert nested dicts/lists to immutable tuples recursively."""
    if isinstance(val, dict):
        return tuple(sorted((k, make_immutable(v)) for k, v in val.items()))
    elif isinstance(val, (list, tuple)):
        return tuple(make_immutable(x) for x in val)
    return val

class ResearchSessionManager:
    """
    Manages the lifecycle, state transitions, and validation of Research Sessions.
    Enforces immutability, determinism, and strict state transition rules.
    """
    def __init__(self) -> None:
        self._sessions: Dict[str, ResearchSession] = {}

    def get_session(self, session_id: str) -> ResearchSession:
        """Retrieves a session by its ID. Raises KeyError if not found."""
        if session_id not in self._sessions:
            raise KeyError(f"Session with ID '{session_id}' not found.")
        return self._sessions[session_id]

    def create_session(
        self,
        config: Union[Dict[str, Any], Tuple[Tuple[str, Union[str, int, float, bool, None]], ...]],
        session_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> ResearchSession:
        """
        Creates and registers a new ResearchSession in 'CREATED' status.
        Ensures config is converted to a sorted, deterministic, immutable tuple.
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if created_at is None:
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        immutable_config = make_immutable(config)
        # Verify it's a tuple of (key, value) pairs
        if not isinstance(immutable_config, tuple) or not all(isinstance(x, tuple) and len(x) == 2 for x in immutable_config):
            # If not properly formatted, wrap it or structure it
            if isinstance(immutable_config, tuple):
                # If it's a flat tuple or other sequence, normalize it
                normalized_config = tuple(sorted((f"param_{i}", x) for i, x in enumerate(immutable_config)))
            else:
                normalized_config = (("config", immutable_config),)
        else:
            normalized_config = immutable_config

        session = ResearchSession(
            session_id=session_id,
            status="CREATED",
            config_snapshot=normalized_config,
            snapshot_id=snapshot_id,
            created_at=created_at,
            experiments=(),
            completed_at=None
        )

        self._sessions[session_id] = session
        return session

    def start_session(self, session_id: str) -> ResearchSession:
        """
        Transitions a session from 'CREATED' to 'RUNNING'.
        Raises ValueError for invalid state transitions.
        """
        session = self.get_session(session_id)
        if session.status != "CREATED":
            raise ValueError(f"Cannot start session '{session_id}' in status '{session.status}'. Only 'CREATED' is valid.")

        updated_session = replace(session, status="RUNNING")
        self._sessions[session_id] = updated_session
        return updated_session

    def complete_session(
        self,
        session_id: str,
        best_run_id: Optional[str] = None,
        experiments: Tuple[ResearchExperiment, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchSession:
        """
        Transitions a session from 'RUNNING' to 'COMPLETED'.
        Raises ValueError for invalid state transitions.
        """
        session = self.get_session(session_id)
        if session.status != "RUNNING":
            raise ValueError(f"Cannot complete session '{session_id}' in status '{session.status}'. Only 'RUNNING' is valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Enforce that passed experiments are tuples
        experiments_tuple = tuple(experiments)

        updated_session = replace(
            session,
            status="COMPLETED",
            best_run_id=best_run_id,
            experiments=experiments_tuple,
            completed_at=completed_at
        )
        self._sessions[session_id] = updated_session
        return updated_session

    def fail_session(
        self,
        session_id: str,
        experiments: Tuple[ResearchExperiment, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchSession:
        """
        Transitions a session from 'RUNNING' to 'FAILED'.
        Raises ValueError for invalid state transitions.
        """
        session = self.get_session(session_id)
        if session.status != "RUNNING":
            raise ValueError(f"Cannot fail session '{session_id}' in status '{session.status}'. Only 'RUNNING' is valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        experiments_tuple = tuple(experiments)

        updated_session = replace(
            session,
            status="FAILED",
            experiments=experiments_tuple,
            completed_at=completed_at
        )
        self._sessions[session_id] = updated_session
        return updated_session

    def cancel_session(self, session_id: str, completed_at: Optional[str] = None) -> ResearchSession:
        """
        Transitions a session from 'CREATED' or 'RUNNING' to 'CANCELLED'.
        Raises ValueError for invalid state transitions.
        """
        session = self.get_session(session_id)
        if session.status not in ("CREATED", "RUNNING"):
            raise ValueError(f"Cannot cancel session '{session_id}' in status '{session.status}'. Only 'CREATED' or 'RUNNING' are valid.")

        if completed_at is None:
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        updated_session = replace(
            session,
            status="CANCELLED",
            completed_at=completed_at
        )
        self._sessions[session_id] = updated_session
        return updated_session
