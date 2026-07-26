"""Unit tests for ArtifactWriter."""

import pytest
import json
import tempfile
import os
import stat
from pathlib import Path
import pandas as pd

from research.explainability.writer import ArtifactWriter


class TestArtifactWriter:
    """Test suite for ArtifactWriter immutability and serialization."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def writer(self, temp_output_dir):
        """Create ArtifactWriter instance."""
        return ArtifactWriter(temp_output_dir, enforce_immutability=True)

    def test_write_json_creates_file(self, writer):
        """Test JSON artifact is written to disk."""
        payload = {"test_key": "test_value", "numeric": 42}
        filepath = writer.write_json("test.json", payload)

        assert Path(filepath).exists()
        with open(filepath, 'r') as f:
            loaded = json.load(f)
        assert loaded == payload

    def test_write_json_computes_checksum(self, writer):
        """Test SHA256 checksum is computed for JSON files."""
        payload = {"test": "data"}
        writer.write_json("test.json", payload)

        checksums = writer.get_checksums()
        assert "test.json" in checksums
        assert len(checksums["test.json"]) == 64  # SHA256 hex length

    def test_write_json_enforces_readonly(self, writer):
        """Test written JSON file is set to read-only (0o444)."""
        payload = {"data": "test"}
        filepath = writer.write_json("test.json", payload)

        file_stat = os.stat(filepath)
        mode = stat.S_IMODE(file_stat.st_mode)

        expected_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        assert mode == expected_mode

    def test_write_json_readonly_prevents_modification(self, writer):
        """Test read-only file cannot be overwritten."""
        payload = {"original": "data"}
        filepath = writer.write_json("test.json", payload)

        with pytest.raises((PermissionError, OSError)):
            with open(filepath, 'w') as f:
                json.dump({"modified": "data"}, f)

    def test_write_parquet_creates_file(self, writer):
        """Test Parquet artifact is written to disk."""
        df = pd.DataFrame({
            'feature_a': [1.0, 2.0, 3.0],
            'feature_b': [4.0, 5.0, 6.0]
        })
        filepath = writer.write_parquet("test.parquet", df)

        assert Path(filepath).exists()
        loaded_df = pd.read_parquet(filepath)
        pd.testing.assert_frame_equal(loaded_df, df)

    def test_write_parquet_enforces_readonly(self, writer):
        """Test written Parquet file is set to read-only."""
        df = pd.DataFrame({'col': [1, 2, 3]})
        filepath = writer.write_parquet("test.parquet", df)

        file_stat = os.stat(filepath)
        mode = stat.S_IMODE(file_stat.st_mode)

        expected_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        assert mode == expected_mode

    def test_write_markdown_creates_file(self, writer):
        """Test Markdown artifact is written to disk."""
        content = "# Test Report\n\nThis is a test."
        filepath = writer.write_markdown("test.md", content)

        assert Path(filepath).exists()
        with open(filepath, 'r') as f:
            loaded = f.read()
        assert loaded == content

    def test_write_markdown_enforces_readonly(self, writer):
        """Test written Markdown file is set to read-only."""
        content = "# Test"
        filepath = writer.write_markdown("test.md", content)

        file_stat = os.stat(filepath)
        mode = stat.S_IMODE(file_stat.st_mode)

        expected_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        assert mode == expected_mode

    def test_immutability_disabled(self, temp_output_dir):
        """Test immutability can be disabled."""
        writer = ArtifactWriter(temp_output_dir, enforce_immutability=False)
        payload = {"data": "test"}
        filepath = writer.write_json("test.json", payload)

        with open(filepath, 'w') as f:
            json.dump({"modified": "data"}, f)

        with open(filepath, 'r') as f:
            loaded = json.load(f)
        assert loaded == {"modified": "data"}

    def test_get_manifest(self, writer):
        """Test artifact manifest generation."""
        writer.write_json("test1.json", {"a": 1})
        writer.write_parquet("test2.parquet", pd.DataFrame({'x': [1, 2]}))

        manifest = writer.get_manifest()

        assert "output_directory" in manifest
        assert "files" in manifest
        assert "checksums" in manifest
        assert len(manifest["files"]) == 2
        assert len(manifest["checksums"]) == 2

    def test_multiple_files_independent_checksums(self, writer):
        """Test multiple files have independent checksums."""
        writer.write_json("file1.json", {"data": "first"})
        writer.write_json("file2.json", {"data": "second"})

        checksums = writer.get_checksums()
        assert checksums["file1.json"] != checksums["file2.json"]
