import pytest
from dataclasses import FrozenInstanceError
from ml_service.research.models import ResearchSession, ResearchExperiment, ResearchRun
from ml_service.research.research_session import ResearchSessionManager
from ml_service.research.research_repository import ResearchRepository
from ml_service.research.research_service import ResearchService

@pytest.fixture
def service():
    repository = ResearchRepository()
    session_manager = ResearchSessionManager()
    return ResearchService(repository, session_manager)

def test_session_creation(service):
    config = {"symbol": "ETHUSDT", "epochs": 50}
    session = service.create_session(config=config, snapshot_id="snapshot_99")
    
    assert session.session_id is not None
    assert session.status == "CREATED"
    assert session.snapshot_id == "snapshot_99"
    assert session.experiments == ()
    
    # Check repository state
    retrieved = service.get_session(session.session_id)
    assert retrieved == session
    
    # Check existence
    assert service.has_session(session.session_id) is True

def test_duplicate_rejection(service):
    config = {"symbol": "ETHUSDT"}
    session_id = "duplicate_id"
    service.create_session(config=config, session_id=session_id)
    
    with pytest.raises(ValueError):
        service.create_session(config=config, session_id=session_id)

def test_retrieval_and_invalid_lookup(service):
    # Invalid lookup should raise KeyError
    with pytest.raises(KeyError):
        service.get_session("non_existent_id")
        
    assert service.has_session("non_existent_id") is False

def test_deletion(service):
    session = service.create_session(config={"symbol": "BTCUSDT"})
    session_id = session.session_id
    
    service.delete_session(session_id)
    
    assert service.has_session(session_id) is False
    with pytest.raises(KeyError):
        service.get_session(session_id)

def test_deterministic_ordering(service):
    s1 = service.create_session(config={"symbol": "A"}, session_id="SESS_A")
    s2 = service.create_session(config={"symbol": "C"}, session_id="SESS_C")
    s3 = service.create_session(config={"symbol": "B"}, session_id="SESS_B")
    
    sessions = service.list_sessions()
    assert len(sessions) == 3
    # Check sorted by session_id
    assert [s.session_id for s in sessions] == ["SESS_A", "SESS_B", "SESS_C"]

def test_immutability_preservation(service):
    session = service.create_session(config={"symbol": "BTCUSDT"})
    with pytest.raises(FrozenInstanceError):
        session.status = "RUNNING"  # type: ignore

def test_lifecycle_transitions(service):
    session = service.create_session(config={"symbol": "BTCUSDT"})
    session_id = session.session_id
    
    # Start session
    session = service.start_session(session_id)
    assert session.status == "RUNNING"
    assert service.get_session(session_id).status == "RUNNING"
    
    # Fail transition from invalid state
    with pytest.raises(ValueError):
        service.start_session(session_id)
        
    # Cancel session from RUNNING
    session = service.cancel_session(session_id)
    assert session.status == "CANCELLED"
    assert service.get_session(session_id).status == "CANCELLED"
