"""Core explainability service orchestrator."""

import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .types import DiagnosticRunContext, DiagnosticRunResult, DiagnosticConfig
from .providers.base import BaseDiagnosticProvider
from .writer import ArtifactWriter
from .report import ReportGenerator

logger = logging.getLogger(__name__)


class ExplainabilityService:
    """Core entrypoint coordinator for explainability computations."""

    def __init__(
        self,
        dataset_service: Any,
        model_registry_service: Any,
        feature_service: Any
    ):
        """Initialize explainability service.

        Args:
            dataset_service: Service for retrieving validation datasets
            model_registry_service: Service for retrieving model binaries
            feature_service: Service for retrieving feature schemas
        """
        self.dataset_service = dataset_service
        self.model_registry_service = model_registry_service
        self.feature_service = feature_service
        self.providers: Dict[str, BaseDiagnosticProvider] = {}

    def register_provider(
        self,
        name: str,
        provider: BaseDiagnosticProvider
    ) -> None:
        """Register diagnostic compute provider.

        Args:
            name: Provider identifier (e.g., 'shap', 'correlation')
            provider: Provider instance implementing BaseDiagnosticProvider
        """
        self.providers[name] = provider
        logger.info(f"Registered provider: {name}")

    def execute_diagnostics(
        self,
        model_version_id: str,
        dataset_version_id: str,
        output_dir: str,
        config: Optional[DiagnosticConfig] = None
    ) -> Dict[str, Any]:
        """Trigger execution of active providers and generate reports.

        Args:
            model_version_id: Identifies candidate model
            dataset_version_id: Identifies validation dataset split
            output_dir: Root storage path for diagnostic artifacts
            config: Execution tuning options

        Returns:
            Dict[str, Any] containing:
                - run_id: str (UUID)
                - status: str (e.g. "completed", "failed")
                - start_time: str (ISO timestamp)
                - end_time: str (ISO timestamp)
                - artifact_manifest: Dict[str, str] (filename -> sha256)
                - output_paths: Dict[str, str] (artifact key -> absolute path)
                - execution_duration_sec: float
                - max_memory_kb: Optional[int]
                - errors: List[str]

        Raises:
            ValueError: If required services are not available
            RuntimeError: If diagnostic execution fails
        """
        if config is None:
            config = DiagnosticConfig()

        start_time = datetime.utcnow()
        run_id = self._generate_run_id()

        run_output_dir = Path(output_dir) / model_version_id / run_id
        run_output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting diagnostic run {run_id}")

        try:
            model, model_hash = self._load_model(model_version_id)
            X, y, dataset_hash = self._load_dataset(dataset_version_id)
            feature_names, feature_version_id = self._load_feature_names(
                X,
                config.feature_dataset_version_id if config else None
            )

            run_context = DiagnosticRunContext(
                run_id=run_id,
                model_version_id=model_version_id,
                dataset_version_id=dataset_version_id,
                feature_dataset_version_id=feature_version_id,
                model_binary_hash=model_hash,
                dataset_hash=dataset_hash,
                timestamp=start_time.isoformat() + "Z"
            )

            provider_results = self._execute_providers(
                model, X, y, feature_names, config
            )

            writer = ArtifactWriter(
                str(run_output_dir),
                enforce_immutability=config.enforce_immutability
            )

            artifact_paths = self._write_artifacts(
                writer, provider_results, run_context, config, start_time
            )

            report_content = self._generate_report(
                run_context, provider_results, {}
            )
            report_path = writer.write_markdown('diagnostics_report.md', report_content)
            artifact_paths['diagnostics_report.md'] = report_path

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = {
                'run_id': run_id,
                'status': 'completed',
                'start_time': start_time.isoformat() + 'Z',
                'end_time': end_time.isoformat() + 'Z',
                'artifact_manifest': writer.get_checksums(),
                'output_paths': artifact_paths,
                'execution_duration_sec': duration,
                'max_memory_kb': self._get_current_memory_usage(),
                'errors': []
            }

            logger.info(f"Diagnostic run {run_id} completed in {duration:.2f}s")
            return result

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Diagnostic run {run_id} failed: {str(e)}")

            return {
                'run_id': run_id,
                'status': 'failed',
                'start_time': start_time.isoformat() + 'Z',
                'end_time': end_time.isoformat() + 'Z',
                'artifact_manifest': {},
                'output_paths': {},
                'execution_duration_sec': duration,
                'max_memory_kb': None,
                'errors': [str(e)]
            }

    def _generate_run_id(self) -> str:
        """Generate unique run identifier."""
        return f"run_{uuid.uuid4().hex[:10]}"

    def _load_model(self, model_version_id: str) -> tuple:
        """Load model binary and compute hash.

        Args:
            model_version_id: Model version identifier

        Returns:
            Tuple of (model_binary, hash_string)
        """
        if hasattr(self.model_registry_service, 'get_model_binary'):
            model = self.model_registry_service.get_model_binary(model_version_id)
            model_hash = self._compute_model_hash(model)
            return model, model_hash
        else:
            raise ValueError("Model registry service not configured properly")

    def _load_dataset(self, dataset_version_id: str) -> tuple:
        """Load validation dataset and compute hash.

        Args:
            dataset_version_id: Dataset version identifier

        Returns:
            Tuple of (X, y, dataset_hash)
        """
        if hasattr(self.dataset_service, 'get_dataset'):
            X, y = self.dataset_service.get_dataset(dataset_version_id)
            dataset_hash = self._compute_dataset_hash(X, y)
            return X, y, dataset_hash
        else:
            raise ValueError("Dataset service not configured properly")

    def _load_feature_names(self, X: Any, feature_version_id: str = None) -> tuple:
        """Load and validate feature names from Feature Store.

        Args:
            X: Feature matrix
            feature_version_id: Feature version identifier

        Returns:
            Tuple of (feature_names, feature_version_id)
        """
        if hasattr(X, 'columns'):
            feature_names_from_data = list(X.columns)
        else:
            n_features = X.shape[1] if hasattr(X, 'shape') else 0
            feature_names_from_data = [f'feature_{i}' for i in range(n_features)]

        if hasattr(self.feature_service, 'get_feature_schema'):
            try:
                if feature_version_id and feature_version_id != "auto":
                    schema_names = self.feature_service.get_feature_schema(feature_version_id)

                    if len(schema_names) != len(feature_names_from_data):
                        logger.warning(
                            f"Feature schema length ({len(schema_names)}) doesn't match "
                            f"data columns ({len(feature_names_from_data)}). Using data columns."
                        )
                        return feature_names_from_data, "auto"

                    return schema_names, feature_version_id
                else:
                    return feature_names_from_data, "auto"
            except Exception as e:
                logger.warning(f"Failed to retrieve feature schema: {e}. Using data columns.")
                return feature_names_from_data, "auto"
        else:
            logger.warning("Feature service does not support get_feature_schema. Using data columns.")
            return feature_names_from_data, "auto"

    def _execute_providers(
        self,
        model: Any,
        X: Any,
        y: Any,
        feature_names: List[str],
        config: DiagnosticConfig
    ) -> Dict[str, Dict[str, Any]]:
        """Execute all active diagnostic providers.

        Args:
            model: Trained model
            X: Feature matrix
            y: Target vector
            feature_names: List of feature names
            config: Diagnostic configuration

        Returns:
            Dict mapping provider names to results
        """
        results = {}

        for provider_name in config.active_providers:
            if provider_name not in self.providers:
                logger.warning(f"Provider '{provider_name}' not registered, skipping")
                continue

            provider = self.providers[provider_name]
            logger.info(f"Executing provider: {provider_name}")

            try:
                result = provider.execute_with_telemetry(
                    model, X, y, feature_names
                )
                results[provider_name] = result
                logger.info(
                    f"Provider '{provider_name}' completed in "
                    f"{provider.execution_time:.2f}s"
                )
            except Exception as e:
                logger.error(f"Provider '{provider_name}' failed: {str(e)}")
                results[provider_name] = {'error': str(e)}

        return results

    def _write_artifacts(
        self,
        writer: ArtifactWriter,
        results: Dict[str, Dict[str, Any]],
        context: DiagnosticRunContext,
        config: DiagnosticConfig,
        start_time: datetime
    ) -> Dict[str, str]:
        """Write diagnostic artifacts to disk.

        Args:
            writer: ArtifactWriter instance
            results: Provider results
            context: Run context metadata
            config: Diagnostic configuration
            start_time: Execution start time for telemetry

        Returns:
            Dict mapping artifact names to file paths
        """
        artifact_paths = {}

        if 'shap' in results and 'shap_dataframe' in results['shap']:
            shap_df = results['shap'].pop('shap_dataframe')
            path = writer.write_parquet(
                'shap_summary.parquet',
                shap_df,
                compression=config.compression
            )
            artifact_paths['shap_summary.parquet'] = path

        feature_importance_dict = None
        if 'shap' in results and 'feature_importance' in results['shap']:
            feature_importance_dict = results['shap']['feature_importance']
        elif 'permutation' in results and 'feature_importance' in results['permutation']:
            feature_importance_dict = results['permutation']['feature_importance']

        if feature_importance_dict:
            importance_payload = {
                'version': '1.0',
                'importances': feature_importance_dict,
                'metrics_sum': sum(feature_importance_dict.values())
            }
            path = writer.write_json('feature_importance.json', importance_payload)
            artifact_paths['feature_importance.json'] = path

        if 'correlation' in results:
            corr_payload = {
                'features': results['correlation'].get('feature_names', []),
                'pearson': results['correlation'].get('pearson_matrix', []),
                'spearman': results['correlation'].get('spearman_matrix', []),
                'high_correlation_pairs': results['correlation'].get('high_correlation_pairs', [])
            }
            path = writer.write_json('correlation_matrix.json', corr_payload)
            artifact_paths['correlation_matrix.json'] = path

        if 'stability' in results:
            path = writer.write_json('stability_report.json', results['stability'])
            artifact_paths['stability_report.json'] = path

        current_time = datetime.utcnow()
        execution_duration = (current_time - start_time).total_seconds()

        max_memory_kb = self._get_current_memory_usage()

        metadata_payload = {
            'run_id': context.run_id,
            'timestamp': context.timestamp,
            'lineage': {
                'model_version_id': context.model_version_id,
                'model_binary_hash': context.model_binary_hash,
                'dataset_version_id': context.dataset_version_id,
                'dataset_hash': context.dataset_hash,
                'feature_dataset_version_id': context.feature_dataset_version_id
            },
            'runtime_telemetry': {
                'execution_duration_sec': execution_duration,
                'max_memory_kb': max_memory_kb
            },
            'provider_versions': self._get_provider_versions()
        }
        path = writer.write_json('diagnostic_metadata.json', metadata_payload)
        artifact_paths['diagnostic_metadata.json'] = path

        return artifact_paths

    def _generate_report(
        self,
        context: DiagnosticRunContext,
        results: Dict[str, Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """Generate markdown report.

        Args:
            context: Run context
            results: Provider results
            metadata: Execution metadata

        Returns:
            Markdown report string
        """
        generator = ReportGenerator()
        context_dict = {
            'run_id': context.run_id,
            'timestamp': context.timestamp,
            'model_version_id': context.model_version_id,
            'dataset_version_id': context.dataset_version_id,
            'feature_dataset_version_id': context.feature_dataset_version_id,
            'model_binary_hash': context.model_binary_hash,
            'dataset_hash': context.dataset_hash
        }
        return generator.generate_report(context_dict, results, metadata)

    def _compute_model_hash(self, model: Any) -> str:
        """Compute hash of model binary."""
        import hashlib
        return hashlib.sha256(str(model).encode()).hexdigest()

    def _compute_dataset_hash(self, X: Any, y: Any) -> str:
        """Compute hash of dataset."""
        import hashlib
        import numpy as np

        if hasattr(X, 'values'):
            X_bytes = X.values.tobytes()
        else:
            X_bytes = np.asarray(X).tobytes()

        if hasattr(y, 'values'):
            y_bytes = y.values.tobytes()
        else:
            y_bytes = np.asarray(y).tobytes()

        combined = X_bytes + y_bytes
        return hashlib.sha256(combined).hexdigest()

    def _get_provider_versions(self) -> Dict[str, str]:
        """Get versions of registered providers."""
        versions = {}
        try:
            import shap
            versions['shap'] = shap.__version__
        except:
            pass
        return versions

    def _get_current_memory_usage(self) -> int:
        """Get current process memory usage in KB.

        Returns:
            Memory usage in kilobytes
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return int(memory_info.rss / 1024)
        except ImportError:
            logger.warning("psutil not available, cannot measure memory usage")
            return 0
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return 0
