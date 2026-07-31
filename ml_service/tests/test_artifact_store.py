"""Unit tests for Artifact Store."""

import pytest
import tempfile
import shutil
from pathlib import Path
from ml_service.research.model_registry.artifact_store import ArtifactStore


@pytest.fixture
def temp_store():
    """Setup a temporary directory for ArtifactStore testing."""
    temp_dir = tempfile.mkdtemp()
    store = ArtifactStore(base_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir)


def test_artifact_store_write_read(temp_store):
    """Verify writing and reading files inside artifact bundles."""
    bundle = {
        "model.bin": b"\x80binary_data_weights",
        "metadata.json": '{"algorithm": "xgboost"}',
        "metrics/loss.csv": "epoch,loss\n1,0.5\n2,0.2"
    }

    assert not temp_store.artifact_exists("mv-1")
    temp_store.write_artifact("mv-1", bundle)
    assert temp_store.artifact_exists("mv-1")

    # Read and verify content matches
    read_bundle = temp_store.read_artifact("mv-1")
    assert read_bundle["model.bin"] == b"\x80binary_data_weights"
    assert read_bundle["metadata.json"] == '{"algorithm": "xgboost"}'
    assert read_bundle["metrics/loss.csv"] == "epoch,loss\n1,0.5\n2,0.2"



def test_artifact_store_overwrite_rejection(temp_store):
    """Verify that overwrites are rejected with FileExistsError."""
    bundle = {"model.bin": b"weights"}
    temp_store.write_artifact("mv-1", bundle)

    with pytest.raises(FileExistsError):
        temp_store.write_artifact("mv-1", bundle)


def test_artifact_store_checksum_and_verification(temp_store):
    """Verify deterministic checksum calculation and tampering verification."""
    bundle = {
        "a.txt": "hello",
        "b.txt": "world"
    }
    temp_store.write_artifact("mv-1", bundle)

    checksum1 = temp_store.compute_checksum("mv-1")
    assert len(checksum1) == 64
    assert temp_store.verify_checksum("mv-1", checksum1)

    # Re-writing same files in different order produces identical checksum (determinism)
    shutil.rmtree(temp_store.resolve_artifact_path("mv-1"))
    
    bundle_reversed = {
        "b.txt": "world",
        "a.txt": "hello"
    }
    temp_store.write_artifact("mv-1", bundle_reversed)
    checksum2 = temp_store.compute_checksum("mv-1")
    assert checksum1 == checksum2


def test_artifact_store_freeze_and_unfreeze(temp_store):
    """Verify file permissions locking (freeze/unfreeze)."""
    bundle = {"model.bin": "content"}
    temp_store.write_artifact("mv-1", bundle)

    # Freeze bundle
    temp_store.freeze_artifact("mv-1")
    
    # Try modifying file (should raise PermissionError/OSError)
    file_path = Path(temp_store.resolve_artifact_path("mv-1")) / "model.bin"
    
    with pytest.raises(OSError):
        file_path.write_text("modified")

    # Unfreeze and modify
    temp_store.unfreeze_artifact("mv-1")
    file_path.write_text("modified")
    assert file_path.read_text() == "modified"


def test_artifact_store_invalid_lookups(temp_store):
    """Verify invalid path lookups and missing artifact errors."""
    with pytest.raises(FileNotFoundError):
        temp_store.read_artifact("non-existent")

    with pytest.raises(FileNotFoundError):
        temp_store.compute_checksum("non-existent")

    with pytest.raises(FileNotFoundError):
        temp_store.freeze_artifact("non-existent")
