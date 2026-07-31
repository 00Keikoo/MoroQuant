"""Artifact Store layer for handling directory bundles in the filesystem."""

import os
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Union


class ArtifactStore:
    """ArtifactStore managing directory-based artifact bundles with permissions and checksums."""

    def __init__(self, base_dir: Union[str, Path] = "storage/models"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def resolve_artifact_path(self, model_version_id: str) -> str:
        """Resolve the absolute directory path of the artifact bundle."""
        if not model_version_id:
            raise ValueError("model_version_id cannot be empty")
        return str(self.base_dir / model_version_id)

    def artifact_exists(self, model_version_id: str) -> bool:
        """Check if the artifact bundle directory exists."""
        path = Path(self.resolve_artifact_path(model_version_id))
        return path.exists() and path.is_dir()

    def write_artifact(
        self,
        model_version_id: str,
        bundle: Dict[str, Union[str, bytes]]
    ) -> None:
        """Write a dictionary of files to the artifact bundle directory, rejecting overwrites."""
        target_dir = Path(self.resolve_artifact_path(model_version_id))
        
        if self.artifact_exists(model_version_id):
            raise FileExistsError(f"Artifact bundle for version '{model_version_id}' already exists")
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for filename, content in bundle.items():
                file_path = target_dir / filename
                # Ensure parent subdirectories inside the bundle exist if any
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if isinstance(content, bytes):
                    file_path.write_bytes(content)
                else:
                    file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            # Cleanup on failure (fail-fast cleanup)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise e

    def read_artifact(self, model_version_id: str) -> Dict[str, Union[str, bytes]]:
        """Read all files in the artifact bundle directory."""
        if not self.artifact_exists(model_version_id):
            raise FileNotFoundError(f"Artifact bundle for version '{model_version_id}' does not exist")
            
        target_dir = Path(self.resolve_artifact_path(model_version_id))
        bundle: Dict[str, Union[str, bytes]] = {}
        
        for file_path in target_dir.rglob("*"):
            if file_path.is_file():
                relative_name = str(file_path.relative_to(target_dir))
                try:
                    # Attempt text load, fallback to bytes
                    content = file_path.read_text(encoding="utf-8")
                    bundle[relative_name] = content
                except UnicodeDecodeError:
                    content_bytes = file_path.read_bytes()
                    bundle[relative_name] = content_bytes
                    
        return bundle

    def compute_checksum(self, model_version_id: str) -> str:
        """Compute deterministic double checksum of all files sorted by relative path."""
        if not self.artifact_exists(model_version_id):
            raise FileNotFoundError(f"Artifact bundle for version '{model_version_id}' does not exist")
            
        target_dir = Path(self.resolve_artifact_path(model_version_id))
        hashes: List[str] = []
        
        # Walk recursively and sort relative paths for determinism
        all_files = sorted(
            [f for f in target_dir.rglob("*") if f.is_file()],
            key=lambda x: str(x.relative_to(target_dir))
        )
        
        for file_path in all_files:
            rel_path = str(file_path.relative_to(target_dir))
            # Compute file hash
            file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            # Combine path and file hash
            combined = hashlib.sha256(f"{rel_path}:{file_hash}".encode("utf-8")).hexdigest()
            hashes.append(combined)
            
        # Final hash of concatenated sub-hashes
        final_payload = "".join(hashes)
        return hashlib.sha256(final_payload.encode("utf-8")).hexdigest()

    def verify_checksum(self, model_version_id: str, expected_checksum: str) -> bool:
        """Verify the current directory state matches the expected checksum."""
        try:
            current = self.compute_checksum(model_version_id)
            return current == expected_checksum
        except FileNotFoundError:
            return False

    def freeze_artifact(self, model_version_id: str) -> None:
        """Apply OS-level read-only permissions recursively on the directory."""
        if not self.artifact_exists(model_version_id):
            raise FileNotFoundError(f"Artifact bundle for version '{model_version_id}' does not exist")
            
        target_dir = Path(self.resolve_artifact_path(model_version_id))
        
        # Apply 0o555 for directories and 0o444 for files recursively
        os.chmod(target_dir, 0o555)
        for root, dirs, files in os.walk(target_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o555)
            for f in files:
                os.chmod(os.path.join(root, f), 0o444)

    def unfreeze_artifact(self, model_version_id: str) -> None:
        """Restore write privileges to all files and directories recursively."""
        if not self.artifact_exists(model_version_id):
            raise FileNotFoundError(f"Artifact bundle for version '{model_version_id}' does not exist")
            
        target_dir = Path(self.resolve_artifact_path(model_version_id))
        
        # Apply 0o755 for directories and 0o644 for files recursively
        os.chmod(target_dir, 0o755)
        for root, dirs, files in os.walk(target_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)
