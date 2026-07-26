"""Integration tests for ExplainabilityService."""

import pytest
import tempfile
import os
import stat
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

from research.explainability import (
    ExplainabilityService,
    ShapProvider,
    CorrelationProvider,
    PermutationProvider,
    StabilityProvider,
    DiagnosticConfig
)


class MockDatasetService:
    """Mock dataset service for testing."""

    def get_dataset(self, dataset_version_id):
        """Return synthetic dataset."""
        X, y = make_classification(
            n_samples=200,
            n_features=8,
            n_informative=5,
            n_redundant=2,
            random_state=42
        )
        X_df = pd.DataFrame(
            X,
            columns=[f'feature_{i}' for i in range(8)]
        )
        y_series = pd.Series(y)
        return X_df, y_series


class MockModelRegistry:
    """Mock model registry for testing."""

    def __init__(self):
        X, y = make_classification(
            n_samples=200,
            n_features=8,
            n_informative=5,
            random_state=42
        )
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        self.model.fit(X, y)

    def get_model_binary(self, model_version_id):
        """Return trained model."""
        return self.model


class MockFeatureService:
    """Mock feature service for testing."""

    def get_feature_schema(self, feature_version_id):
        """Return feature schema."""
        return [f'feature_{i}' for i in range(8)]


class TestExplainabilityServiceIntegration:
    """Integration tests for complete explainability pipeline."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def service(self):
        """Create ExplainabilityService with mock dependencies."""
        dataset_service = MockDatasetService()
        model_registry = MockModelRegistry()
        feature_service = MockFeatureService()

        service = ExplainabilityService(
            dataset_service=dataset_service,
            model_registry_service=model_registry,
            feature_service=feature_service
        )

        service.register_provider('correlation', CorrelationProvider(config={}))
        service.register_provider(
            'permutation',
            PermutationProvider(config={'permutation_repetitions': 5})
        )
        service.register_provider(
            'stability',
            StabilityProvider(config={})
        )

        return service

    def test_complete_diagnostic_pipeline(self, service, temp_output_dir):
        """Test complete diagnostic run generates all artifacts."""
        config = DiagnosticConfig(
            active_providers=['correlation', 'permutation']
        )

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        assert result["status"] == 'completed'
        assert result["run_id"] is not None
        assert result["execution_duration_sec"] > 0

        assert 'correlation_matrix.json' in result["artifact_manifest"]
        assert 'diagnostic_metadata.json' in result["artifact_manifest"]
        assert 'diagnostics_report.md' in result["output_paths"]

    def test_artifact_immutability_enforcement(self, service, temp_output_dir):
        """Test artifacts are written as read-only."""
        config = DiagnosticConfig(
            active_providers=['correlation'],
            enforce_immutability=True
        )

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        for filepath in result['output_paths'].values():
            file_stat = os.stat(filepath)
            mode = stat.S_IMODE(file_stat.st_mode)
            expected_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            assert mode == expected_mode

    def test_artifacts_cannot_be_modified(self, service, temp_output_dir):
        """Test read-only artifacts raise PermissionError on write."""
        config = DiagnosticConfig(
            active_providers=['correlation'],
            enforce_immutability=True
        )

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        json_path = result['output_paths'].get('correlation_matrix.json')
        assert json_path is not None

        with pytest.raises((PermissionError, OSError)):
            with open(json_path, 'w') as f:
                f.write('modified content')

    def test_lineage_preservation(self, service, temp_output_dir):
        """Test diagnostic metadata preserves lineage."""
        config = DiagnosticConfig(active_providers=['correlation'])

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        metadata_path = result['output_paths']['diagnostic_metadata.json']
        assert Path(metadata_path).exists()

        import json
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        assert metadata['lineage']['model_version_id'] == 'test_model_v1'
        assert metadata['lineage']['dataset_version_id'] == 'test_dataset_v1'
        assert len(metadata['lineage']['model_binary_hash']) == 64
        assert len(metadata['lineage']['dataset_hash']) == 64

    def test_report_generation(self, service, temp_output_dir):
        """Test markdown report is generated correctly."""
        config = DiagnosticConfig(active_providers=['correlation', 'permutation'])

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        report_path = result['output_paths']['diagnostics_report.md']
        assert Path(report_path).exists()

        with open(report_path, 'r') as f:
            report_content = f.read()

        assert '# Model Diagnostics Report' in report_content
        assert 'Diagnostic Run ID' in report_content
        assert 'Lineage & Provenance' in report_content
        assert 'test_model_v1' in report_content

    def test_checksum_consistency(self, service, temp_output_dir):
        """Test checksums are computed and stored correctly."""
        config = DiagnosticConfig(active_providers=['correlation'])

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        assert len(result["artifact_manifest"]) > 0
        for filename, checksum in result["artifact_manifest"].items():
            assert len(checksum) == 64

    def test_provider_failure_handling(self, service, temp_output_dir):
        """Test service handles provider failures gracefully."""
        service.register_provider('correlation', CorrelationProvider(config={}))

        config = DiagnosticConfig(active_providers=['correlation', 'nonexistent'])

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        assert result["status"] == 'completed'

    def test_multiple_providers_execution(self, service, temp_output_dir):
        """Test multiple providers execute successfully."""
        config = DiagnosticConfig(
            active_providers=['correlation', 'permutation']
        )

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        assert 'correlation_matrix.json' in result["output_paths"]
        assert 'diagnostics_report.md' in result["output_paths"]
        assert result["execution_duration_sec"] > 0

    def test_output_directory_structure(self, service, temp_output_dir):
        """Test diagnostic run creates proper directory structure."""
        config = DiagnosticConfig(active_providers=['correlation'])

        result = service.execute_diagnostics(
            model_version_id='test_model_v1',
            dataset_version_id='test_dataset_v1',
            output_dir=temp_output_dir,
            config=config
        )

        expected_dir = Path(temp_output_dir) / 'test_model_v1' / result['run_id']
        assert expected_dir.exists()
        assert expected_dir.is_dir()
