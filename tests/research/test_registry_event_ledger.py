"""Tests for Registry Event Ledger - Sprint 3.9D-10

Verify append-only ledger, deterministic ordering, and ADR-024 compliance.
"""

import pytest
import json
import tempfile
from pathlib import Path

from ml_service.research.registry_event_ledger import (
    RegistryEventRecord,
    RegistryEventLedger,
)
from ml_service.research.promotion_workflow.models import PromotionEvent


def test_no_sqlite_imports():
    """Verify no SQLite imports in registry_event_ledger package."""
    import ml_service.research.registry_event_ledger.service as service_mod
    import ml_service.research.registry_event_ledger.json_ledger as storage_mod
    import ml_service.research.registry_event_ledger.models as models_mod
    import inspect

    for mod in [service_mod, storage_mod, models_mod]:
        source = inspect.getsource(mod)
        forbidden = ["import sqlite", "from sqlite", "sqlite3"]
        for term in forbidden:
            assert term not in source.lower(), f"Found forbidden SQLite import: {term}"


def test_no_execution_imports():
    """Verify no execution layer imports in registry_event_ledger package."""
    import ml_service.research.registry_event_ledger.service as service_mod
    import ml_service.research.registry_event_ledger.json_ledger as storage_mod
    import inspect

    for mod in [service_mod, storage_mod]:
        source = inspect.getsource(mod)
        forbidden = ["PortfolioService", "ExecutionSimulator", "ml_service.execution"]
        for term in forbidden:
            assert term not in source, f"Found forbidden execution import: {term}"


def test_registry_event_record_immutable():
    """Verify RegistryEventRecord is immutable."""
    record = RegistryEventRecord(
        event_id="abc123",
        model_id="models/test.pkl",
        event_type="APPROVED",
        created_at="2026-08-07T12:00:00Z",
        payload_hash="def456",
    )

    with pytest.raises(AttributeError):
        record.event_type = "REJECTED"


def test_registry_event_record_validation():
    """Verify RegistryEventRecord validates inputs."""
    with pytest.raises(ValueError, match="event_id cannot be empty"):
        RegistryEventRecord(
            event_id="",
            model_id="test",
            event_type="APPROVED",
            created_at="2026-08-07T12:00:00Z",
            payload_hash="hash",
        )


def test_payload_hash_deterministic():
    """Verify payload hash is deterministic."""
    payload = {
        "model_id": "test",
        "decision": "APPROVED",
        "from_state": "VALIDATED",
        "to_state": "APPROVED",
    }

    hash1 = RegistryEventRecord.compute_payload_hash(payload)
    hash2 = RegistryEventRecord.compute_payload_hash(payload)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex


def test_payload_hash_order_independent():
    """Verify payload hash ignores key order."""
    payload1 = {"a": 1, "b": 2, "c": 3}
    payload2 = {"c": 3, "a": 1, "b": 2}

    hash1 = RegistryEventRecord.compute_payload_hash(payload1)
    hash2 = RegistryEventRecord.compute_payload_hash(payload2)

    assert hash1 == hash2


def create_test_event(model_id: str, from_state: str, to_state: str) -> PromotionEvent:
    """Helper to create test PromotionEvent."""
    return PromotionEvent(
        event_id=PromotionEvent.generate_event_id(model_id, from_state, to_state, "2026-08-07T12:00:00Z"),
        model_id=model_id,
        from_state=from_state,
        to_state=to_state,
        decision="APPROVED",
        reason_codes=("TEST_REASON",),
        created_at="2026-08-07T12:00:00Z",
    )


def test_append_event():
    """Verify event can be appended to ledger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        event = create_test_event("models/test.pkl", "VALIDATED", "APPROVED")
        record = ledger.append(event)

        assert record.event_id == event.event_id
        assert record.model_id == event.model_id
        assert record.event_type == "APPROVED"
        assert ledger_path.exists()


def test_retrieve_events():
    """Verify events can be retrieved from ledger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        event1 = create_test_event("models/btc.pkl", "VALIDATED", "APPROVED")
        event2 = create_test_event("models/eth.pkl", "APPROVED", "PRODUCTION")

        ledger.append(event1)
        ledger.append(event2)

        events = ledger.get_events()

        assert len(events) == 2
        assert events[0].model_id == "models/btc.pkl"
        assert events[1].model_id == "models/eth.pkl"


def test_deterministic_ordering():
    """Verify events are ordered by created_at deterministically."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        event1 = PromotionEvent(
            event_id="e1",
            model_id="models/m1.pkl",
            from_state="VALIDATED",
            to_state="APPROVED",
            decision="APPROVED",
            reason_codes=("R1",),
            created_at="2026-08-07T10:00:00Z",
        )

        event2 = PromotionEvent(
            event_id="e2",
            model_id="models/m2.pkl",
            from_state="VALIDATED",
            to_state="APPROVED",
            decision="APPROVED",
            reason_codes=("R2",),
            created_at="2026-08-07T09:00:00Z",
        )

        event3 = PromotionEvent(
            event_id="e3",
            model_id="models/m3.pkl",
            from_state="VALIDATED",
            to_state="APPROVED",
            decision="APPROVED",
            reason_codes=("R3",),
            created_at="2026-08-07T11:00:00Z",
        )

        ledger.append(event1)
        ledger.append(event2)
        ledger.append(event3)

        events = ledger.get_events()

        assert len(events) == 3
        assert events[0].created_at == "2026-08-07T09:00:00Z"
        assert events[1].created_at == "2026-08-07T10:00:00Z"
        assert events[2].created_at == "2026-08-07T11:00:00Z"


def test_get_model_history():
    """Verify model-specific history retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        btc_event1 = PromotionEvent(
            event_id="b1",
            model_id="models/btc.pkl",
            from_state="VALIDATED",
            to_state="APPROVED",
            decision="APPROVED",
            reason_codes=("R1",),
            created_at="2026-08-07T10:00:00Z",
        )

        eth_event = PromotionEvent(
            event_id="e1",
            model_id="models/eth.pkl",
            from_state="VALIDATED",
            to_state="APPROVED",
            decision="APPROVED",
            reason_codes=("R2",),
            created_at="2026-08-07T11:00:00Z",
        )

        btc_event2 = PromotionEvent(
            event_id="b2",
            model_id="models/btc.pkl",
            from_state="APPROVED",
            to_state="PRODUCTION",
            decision="APPROVED",
            reason_codes=("R3",),
            created_at="2026-08-07T12:00:00Z",
        )

        ledger.append(btc_event1)
        ledger.append(eth_event)
        ledger.append(btc_event2)

        btc_history = ledger.get_model_history("models/btc.pkl")

        assert len(btc_history) == 2
        assert btc_history[0].event_id == "b1"
        assert btc_history[1].event_id == "b2"
        assert btc_history[0].event_id == "b1"
        assert btc_history[1].event_id == "b2"


def test_latest_event():
    """Verify latest event retrieval for model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        event1 = PromotionEvent(
            event_id="e1",
            model_id="models/test.pkl",
            from_state="VALIDATED",
            to_state="APPROVED",
            decision="APPROVED",
            reason_codes=("R1",),
            created_at="2026-08-07T10:00:00Z",
        )

        event2 = PromotionEvent(
            event_id="e2",
            model_id="models/test.pkl",
            from_state="APPROVED",
            to_state="PRODUCTION",
            decision="APPROVED",
            reason_codes=("R2",),
            created_at="2026-08-07T11:00:00Z",
        )

        ledger.append(event1)
        ledger.append(event2)

        latest = ledger.latest_event("models/test.pkl")

        assert latest is not None
        assert latest.event_id == "e2"
        assert latest.created_at == "2026-08-07T11:00:00Z"


def test_latest_event_no_history():
    """Verify latest_event returns None for unknown model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        latest = ledger.latest_event("models/nonexistent.pkl")

        assert latest is None


def test_corrupted_file_handling():
    """Verify ledger tolerates corrupted JSON lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"

        with open(ledger_path, "w") as f:
            f.write('{"record": {"event_id": "e1", "model_id": "m1", "event_type": "APPROVED", "created_at": "2026-08-07T10:00:00Z", "payload_hash": "hash1"}, "payload": {"decision": "APPROVED"}}\n')
            f.write('CORRUPTED LINE\n')
            f.write('{"record": {"event_id": "e2", "model_id": "m2", "event_type": "APPROVED", "created_at": "2026-08-07T11:00:00Z", "payload_hash": "hash2"}, "payload": {"decision": "APPROVED"}}\n')

        ledger = RegistryEventLedger(str(ledger_path))
        events = ledger.get_events()

        assert len(events) == 2
        assert events[0].event_id == "e1"
        assert events[1].event_id == "e2"


def test_empty_ledger():
    """Verify empty ledger returns empty lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        events = ledger.get_events()
        history = ledger.get_model_history("models/test.pkl")
        latest = ledger.latest_event("models/test.pkl")

        assert events == []
        assert history == []
        assert latest is None


def test_append_only_behavior():
    """Verify ledger is append-only (no updates or deletes)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        event1 = create_test_event("models/test.pkl", "VALIDATED", "APPROVED")
        event2 = create_test_event("models/test.pkl", "APPROVED", "PRODUCTION")

        ledger.append(event1)
        events_after_first = ledger.get_events()

        ledger.append(event2)
        events_after_second = ledger.get_events()

        assert len(events_after_first) == 1
        assert len(events_after_second) == 2
        assert events_after_second[0].event_id == events_after_first[0].event_id


def test_record_serialization():
    """Verify RegistryEventRecord serialization round-trip."""
    record = RegistryEventRecord(
        event_id="abc123",
        model_id="models/test.pkl",
        event_type="APPROVED",
        created_at="2026-08-07T12:00:00Z",
        payload_hash="def456",
    )

    data = record.to_dict()
    reconstructed = RegistryEventRecord.from_dict(data)

    assert reconstructed == record


def test_storage_creates_parent_dirs():
    """Verify storage creates parent directories if needed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "nested" / "path" / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        event = create_test_event("models/test.pkl", "VALIDATED", "APPROVED")
        ledger.append(event)

        assert ledger_path.exists()
        assert ledger_path.parent.exists()


def test_multiple_models_interleaved():
    """Verify ledger handles multiple models with interleaved events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = RegistryEventLedger(str(ledger_path))

        events = [
            PromotionEvent("e1", "models/btc.pkl", "VALIDATED", "APPROVED", "APPROVED", ("R1",), "2026-08-07T10:00:00Z"),
            PromotionEvent("e2", "models/eth.pkl", "VALIDATED", "APPROVED", "APPROVED", ("R2",), "2026-08-07T10:30:00Z"),
            PromotionEvent("e3", "models/btc.pkl", "APPROVED", "PRODUCTION", "APPROVED", ("R3",), "2026-08-07T11:00:00Z"),
            PromotionEvent("e4", "models/sol.pkl", "VALIDATED", "APPROVED", "APPROVED", ("R4",), "2026-08-07T11:30:00Z"),
            PromotionEvent("e5", "models/eth.pkl", "APPROVED", "PRODUCTION", "APPROVED", ("R5",), "2026-08-07T12:00:00Z"),
        ]

        for event in events:
            ledger.append(event)

        btc_history = ledger.get_model_history("models/btc.pkl")
        eth_history = ledger.get_model_history("models/eth.pkl")
        sol_history = ledger.get_model_history("models/sol.pkl")

        assert len(btc_history) == 2
        assert len(eth_history) == 2
        assert len(sol_history) == 1

        all_events = ledger.get_events()
        assert len(all_events) == 5
        assert all_events[0].created_at == "2026-08-07T10:00:00Z"
        assert all_events[4].created_at == "2026-08-07T12:00:00Z"
