from typing import Dict, List, Optional, Any, Union, Tuple
from ml_service.research.models import ResearchSession, ResearchExperiment
from ml_service.research.research_session import ResearchSessionManager
from ml_service.research.research_repository import ResearchRepository

class ResearchService:
    """
    Business-level service that orchestrates ResearchSessionManager and ResearchRepository.
    Exposes operations for session creation, retrieval, deletion, existence checking,
    and lifecycle transitions, keeping the manager and repository state in sync.
    """
    def __init__(
        self,
        repository: ResearchRepository,
        session_manager: ResearchSessionManager
    ) -> None:
        self.repository = repository
        self.session_manager = session_manager

    def create_session(
        self,
        config: Union[Dict[str, Any], Tuple[Tuple[str, Union[str, int, float, bool, None]], ...]],
        session_id: Optional[str] = None,
        snapshot_id: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> ResearchSession:
        """
        Creates a new research session, registers it in the manager,
        and persists it to the repository.
        """
        if session_id is not None and self.has_session(session_id):
            raise ValueError(f"Session with ID '{session_id}' already exists.")

        session = self.session_manager.create_session(
            config=config,
            session_id=session_id,
            snapshot_id=snapshot_id,
            created_at=created_at
        )
        self.repository.create_session(session)
        return session

    def get_session(self, session_id: str) -> ResearchSession:
        """Retrieves a session from the repository."""
        return self.repository.get_session(session_id)

    def has_session(self, session_id: str) -> bool:
        """Checks if a session exists in the repository."""
        try:
            self.repository.get_session(session_id)
            return True
        except KeyError:
            return False

    def delete_session(self, session_id: str) -> None:
        """Deletes a session from both the manager and the repository."""
        if session_id in self.session_manager._sessions:
            del self.session_manager._sessions[session_id]
        self.repository.delete_session(session_id)

    def list_sessions(self) -> List[ResearchSession]:
        """Lists all sessions in a deterministic order (sorted by session_id)."""
        return self.repository.list_sessions()

    def start_session(self, session_id: str) -> ResearchSession:
        """Transitions a session's state to RUNNING."""
        session = self.get_session(session_id)
        if session_id not in self.session_manager._sessions:
            self.session_manager._sessions[session_id] = session

        updated_session = self.session_manager.start_session(session_id)
        self.repository.delete_session(session_id)
        self.repository.create_session(updated_session)
        return updated_session

    def complete_session(
        self,
        session_id: str,
        best_run_id: Optional[str] = None,
        experiments: Tuple[ResearchExperiment, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchSession:
        """Transitions a session's state to COMPLETED."""
        session = self.get_session(session_id)
        if session_id not in self.session_manager._sessions:
            self.session_manager._sessions[session_id] = session

        updated_session = self.session_manager.complete_session(
            session_id,
            best_run_id=best_run_id,
            experiments=experiments,
            completed_at=completed_at
        )
        self.repository.delete_session(session_id)
        self.repository.create_session(updated_session)
        return updated_session

    def fail_session(
        self,
        session_id: str,
        experiments: Tuple[ResearchExperiment, ...] = (),
        completed_at: Optional[str] = None
    ) -> ResearchSession:
        """Transitions a session's state to FAILED."""
        session = self.get_session(session_id)
        if session_id not in self.session_manager._sessions:
            self.session_manager._sessions[session_id] = session

        updated_session = self.session_manager.fail_session(
            session_id,
            experiments=experiments,
            completed_at=completed_at
        )
        self.repository.delete_session(session_id)
        self.repository.create_session(updated_session)
        return updated_session

    def cancel_session(self, session_id: str, completed_at: Optional[str] = None) -> ResearchSession:
        """Transitions a session's state to CANCELLED."""
        session = self.get_session(session_id)
        if session_id not in self.session_manager._sessions:
            self.session_manager._sessions[session_id] = session

        updated_session = self.session_manager.cancel_session(session_id, completed_at=completed_at)
        self.repository.delete_session(session_id)
        self.repository.create_session(updated_session)
        return updated_session
