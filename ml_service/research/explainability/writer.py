"""Immutable artifact writer for diagnostic outputs."""

import json
import hashlib
import os
import stat
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ArtifactWriter:
    """Utility for writing immutable diagnostic artifacts to disk."""

    def __init__(self, output_dir: str, enforce_immutability: bool = True):
        """Initialize artifact writer.

        Args:
            output_dir: Root directory for artifact storage
            enforce_immutability: Whether to set files to read-only (chmod 0444)
        """
        self.output_dir = Path(output_dir)
        self.enforce_immutability = enforce_immutability
        self._checksums: Dict[str, str] = {}

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(
        self,
        filename: str,
        payload: Dict[str, Any],
        compute_checksum: bool = True
    ) -> str:
        """Write JSON artifact to disk.

        Args:
            filename: Target filename (e.g., 'feature_importance.json')
            payload: Dictionary to serialize
            compute_checksum: Whether to compute SHA256 hash

        Returns:
            Absolute path to written file
        """
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2)

        if compute_checksum:
            checksum = self._compute_sha256(filepath)
            self._checksums[filename] = checksum

        if self.enforce_immutability:
            self._set_readonly(filepath)

        logger.info(f"Written JSON artifact: {filepath}")
        return str(filepath)

    def write_parquet(
        self,
        filename: str,
        dataframe: pd.DataFrame,
        compression: str = 'snappy',
        compute_checksum: bool = True
    ) -> str:
        """Write Parquet artifact to disk.

        Args:
            filename: Target filename (e.g., 'shap_summary.parquet')
            dataframe: DataFrame to serialize
            compression: Compression codec ('snappy', 'gzip', 'brotli')
            compute_checksum: Whether to compute SHA256 hash

        Returns:
            Absolute path to written file
        """
        filepath = self.output_dir / filename

        dataframe.to_parquet(
            filepath,
            engine='pyarrow',
            compression=compression,
            index=False
        )

        if compute_checksum:
            checksum = self._compute_sha256(filepath)
            self._checksums[filename] = checksum

        if self.enforce_immutability:
            self._set_readonly(filepath)

        logger.info(f"Written Parquet artifact: {filepath}")
        return str(filepath)

    def write_markdown(
        self,
        filename: str,
        content: str,
        compute_checksum: bool = True
    ) -> str:
        """Write Markdown report to disk.

        Args:
            filename: Target filename (e.g., 'diagnostics_report.md')
            content: Markdown content string
            compute_checksum: Whether to compute SHA256 hash

        Returns:
            Absolute path to written file
        """
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            f.write(content)

        if compute_checksum:
            checksum = self._compute_sha256(filepath)
            self._checksums[filename] = checksum

        if self.enforce_immutability:
            self._set_readonly(filepath)

        logger.info(f"Written Markdown artifact: {filepath}")
        return str(filepath)

    def _compute_sha256(self, filepath: Path) -> str:
        """Compute SHA256 hash of file contents.

        Args:
            filepath: Path to file

        Returns:
            Hexadecimal SHA256 hash string
        """
        sha256_hash = hashlib.sha256()

        with open(filepath, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def _set_readonly(self, filepath: Path) -> None:
        """Set file permissions to read-only (0o444).

        Args:
            filepath: Path to file
        """
        os.chmod(filepath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        logger.debug(f"Set read-only permissions on {filepath}")

    def get_checksums(self) -> Dict[str, str]:
        """Get computed checksums for all written files.

        Returns:
            Dict mapping filename to SHA256 checksum
        """
        return self._checksums.copy()

    def get_manifest(self) -> Dict[str, Any]:
        """Get full artifact manifest with paths and checksums.

        Returns:
            Dict containing file paths and checksums
        """
        manifest = {
            'output_directory': str(self.output_dir),
            'files': {},
            'checksums': self._checksums.copy()
        }

        for filename in self._checksums.keys():
            filepath = self.output_dir / filename
            if filepath.exists():
                manifest['files'][filename] = str(filepath)

        return manifest
