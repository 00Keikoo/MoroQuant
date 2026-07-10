"""Verification tests for Model Registry implementation."""

import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from ml_service.research.model_registry.service import ModelRegistryService
from ml_service.research.model_registry.repository import ModelRegistryRepository
from ml_service.research.model_registry.model_types import (
    RegistrationRequest,
    ModelEvaluation,
    ModelLifecycleState
)
from ml_service.bootstrap.research_database import bootstrap_research_tables


class ModelRegistryVerification:
    """Verification test suite for Model Registry."""

    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / "test_registry.db"
        self.storage_dir = self.test_dir / "models"
        self.storage_dir.mkdir(exist_ok=True)

        bootstrap_research_tables(str(self.db_path))

        self.repository = ModelRegistryRepository(str(self.db_path))
        self.service = ModelRegistryService(self.repository)

        self.passed = 0
        self.failed = 0

    def _create_test_model_artifact(self, model_version_id: str) -> str:
        """Create a test model artifact directory."""
        model_path = self.storage_dir / model_version_id
        model_path.mkdir(exist_ok=True)

        model_bin = model_path / "model.bin"
        model_bin.write_text(f"test_model_weights_{model_version_id}")

        return str(model_path)

    def _print_result(self, test_name: str, passed: bool, message: str = ""):
        """Print test result."""
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}")
        if message:
            print(f"      {message}")

        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def test_register_model(self):
        """Test registering a new model candidate."""
        try:
            storage_path = self._create_test_model_artifact("mdl_test_btc_v1.0.0")

            request = RegistrationRequest(
                model_id="mdl_test_btc",
                version_bump="minor",
                storage_path=storage_path,
                hyperparameters={"max_depth": 6, "learning_rate": 0.05},
                lineage={
                    "snapshot_id": "snap_20260710",
                    "dataset_id": "ds_btc_v1.0.0",
                    "feature_dataset_id": "fds_rsi14_v1.0.0",
                    "experiment_id": "exp_btc_001",
                    "best_config_id": "cfg_001"
                },
                symbol="BTCUSD",
                timeframe="1h",
                algorithm="xgboost",
                git_commit="abc123"
            )

            metadata = self.service.register_candidate(request)

            if metadata.model_version_id == "mdl_test_btc_v1.0.0":
                if metadata.lifecycle_state == ModelLifecycleState.CANDIDATE:
                    if metadata.fingerprint:
                        self._print_result("Register Model", True)
                        return metadata
                    else:
                        self._print_result("Register Model", False, "No fingerprint generated")
                else:
                    self._print_result("Register Model", False, f"Wrong state: {metadata.lifecycle_state}")
            else:
                self._print_result("Register Model", False, f"Wrong ID: {metadata.model_version_id}")

        except Exception as e:
            self._print_result("Register Model", False, str(e))

        return None

    def test_duplicate_rejection(self, original_metadata):
        """Test that duplicate fingerprints are rejected."""
        try:
            request = RegistrationRequest(
                model_id="mdl_test_btc",
                version_bump="minor",
                storage_path=original_metadata.storage_path,
                hyperparameters=original_metadata.hyperparameters,
                lineage={
                    "snapshot_id": "snap_20260710",
                    "dataset_id": "ds_btc_v1.0.0",
                    "feature_dataset_id": "fds_rsi14_v1.0.0",
                    "experiment_id": "exp_btc_001",
                    "best_config_id": "cfg_001"
                },
                symbol="BTCUSD",
                timeframe="1h",
                algorithm="xgboost"
            )

            try:
                self.service.register_candidate(request)
                self._print_result("Duplicate Rejection", False, "Duplicate was accepted")
            except ValueError as e:
                if "fingerprint" in str(e).lower():
                    self._print_result("Duplicate Rejection", True)
                else:
                    self._print_result("Duplicate Rejection", False, f"Wrong error: {e}")

        except Exception as e:
            self._print_result("Duplicate Rejection", False, str(e))

    def test_version_increment(self):
        """Test version incrementing."""
        try:
            storage_path = self._create_test_model_artifact("mdl_version_test_v1.1.0")

            request = RegistrationRequest(
                model_id="mdl_version_test",
                version_bump="minor",
                storage_path=storage_path,
                hyperparameters={"param": 1},
                lineage={
                    "snapshot_id": "snap_001",
                    "dataset_id": "ds_001",
                    "feature_dataset_id": "fds_001",
                    "experiment_id": "exp_001",
                    "best_config_id": "cfg_001"
                },
                symbol="ETHUSD",
                timeframe="1h",
                algorithm="lgbm"
            )

            metadata = self.service.register_candidate(request)

            if metadata.version == "1.0.0":
                self._print_result("Version Increment", True)
            else:
                self._print_result("Version Increment", False, f"Expected 1.0.0, got {metadata.version}")

        except Exception as e:
            self._print_result("Version Increment", False, str(e))

    def test_candidate_to_validated(self, model_version_id: str):
        """Test Candidate -> Validated transition."""
        try:
            evaluation = ModelEvaluation(
                sharpe_ratio=1.8,
                max_drawdown=-0.12,
                ece=0.03,
                brier_score=0.18,
                win_rate=0.62,
                profit_factor=1.9,
                sortino_ratio=2.1,
                trade_count=150
            )

            success = self.service.evaluate_and_validate(
                model_version_id,
                evaluation,
                "test_reviewer"
            )

            metadata = self.service.get_model(model_version_id)

            if metadata.lifecycle_state == ModelLifecycleState.VALIDATED:
                if metadata.evaluation and metadata.evaluation.is_approved:
                    if metadata.is_frozen:
                        self._print_result("Candidate → Validated", True)
                        return True
                    else:
                        self._print_result("Candidate → Validated", False, "Model not frozen")
                else:
                    self._print_result("Candidate → Validated", False, "Evaluation not approved")
            else:
                self._print_result("Candidate → Validated", False, f"Wrong state: {metadata.lifecycle_state}")

        except Exception as e:
            self._print_result("Candidate → Validated", False, str(e))

        return False

    def test_validated_to_production(self, model_version_id: str):
        """Test Validated -> Production transition."""
        try:
            self.service.promote_to_production(model_version_id, "test_promoter")

            metadata = self.service.get_model(model_version_id)

            if metadata.lifecycle_state == ModelLifecycleState.PRODUCTION:
                self._print_result("Validated → Production", True)
                return True
            else:
                self._print_result("Validated → Production", False, f"Wrong state: {metadata.lifecycle_state}")

        except Exception as e:
            self._print_result("Validated → Production", False, str(e))

        return False

    def test_production_uniqueness(self):
        """Test one-production-model rule."""
        try:
            storage_path_1 = self._create_test_model_artifact("mdl_prod_test_v1.0.0")
            storage_path_2 = self._create_test_model_artifact("mdl_prod_test_v2.0.0")

            request_1 = RegistrationRequest(
                model_id="mdl_prod_test",
                version_bump="minor",
                storage_path=storage_path_1,
                hyperparameters={"version": 1},
                lineage={
                    "snapshot_id": "snap_prod_001",
                    "dataset_id": "ds_prod_001",
                    "feature_dataset_id": "fds_prod_001",
                    "experiment_id": "exp_prod_001",
                    "best_config_id": "cfg_prod_001"
                },
                symbol="SOLUSD",
                timeframe="4h",
                algorithm="catboost"
            )

            metadata_1 = self.service.register_candidate(request_1)

            evaluation = ModelEvaluation(
                sharpe_ratio=2.0,
                max_drawdown=-0.10,
                ece=0.02,
                brier_score=0.15,
                win_rate=0.65,
                profit_factor=2.1,
                sortino_ratio=2.5,
                trade_count=200
            )

            self.service.evaluate_and_validate(metadata_1.model_version_id, evaluation, "reviewer")
            self.service.promote_to_production(metadata_1.model_version_id, "promoter")

            request_2 = RegistrationRequest(
                model_id="mdl_prod_test",
                version_bump="major",
                storage_path=storage_path_2,
                hyperparameters={"version": 2},
                lineage={
                    "snapshot_id": "snap_prod_002",
                    "dataset_id": "ds_prod_002",
                    "feature_dataset_id": "fds_prod_002",
                    "experiment_id": "exp_prod_002",
                    "best_config_id": "cfg_prod_002"
                },
                symbol="SOLUSD",
                timeframe="4h",
                algorithm="catboost"
            )

            metadata_2 = self.service.register_candidate(request_2)
            self.service.evaluate_and_validate(metadata_2.model_version_id, evaluation, "reviewer")
            self.service.promote_to_production(metadata_2.model_version_id, "promoter")

            old_model = self.service.get_model(metadata_1.model_version_id)
            new_model = self.service.get_model(metadata_2.model_version_id)

            if old_model.lifecycle_state == ModelLifecycleState.ARCHIVED:
                if new_model.lifecycle_state == ModelLifecycleState.PRODUCTION:
                    production = self.service.get_production_model("SOLUSD", "4h", "catboost")
                    if production.model_version_id == metadata_2.model_version_id:
                        self._print_result("Production Uniqueness", True)
                        return True
                    else:
                        self._print_result("Production Uniqueness", False, "Wrong production model")
                else:
                    self._print_result("Production Uniqueness", False, "New model not in production")
            else:
                self._print_result("Production Uniqueness", False, f"Old model not archived: {old_model.lifecycle_state}")

        except Exception as e:
            self._print_result("Production Uniqueness", False, str(e))

        return False

    def test_archive(self):
        """Test archiving a model."""
        try:
            storage_path = self._create_test_model_artifact("mdl_archive_test_v1.0.0")

            request = RegistrationRequest(
                model_id="mdl_archive_test",
                version_bump="minor",
                storage_path=storage_path,
                hyperparameters={"test": 1},
                lineage={
                    "snapshot_id": "snap_arch_001",
                    "dataset_id": "ds_arch_001",
                    "feature_dataset_id": "fds_arch_001",
                    "experiment_id": "exp_arch_001",
                    "best_config_id": "cfg_arch_001"
                },
                symbol="ADAUSD",
                timeframe="1d",
                algorithm="rf"
            )

            metadata = self.service.register_candidate(request)
            self.service.archive_model(metadata.model_version_id, "test_archiver")

            archived = self.service.get_model(metadata.model_version_id)

            if archived.lifecycle_state == ModelLifecycleState.ARCHIVED:
                self._print_result("Archive", True)
            else:
                self._print_result("Archive", False, f"Wrong state: {archived.lifecycle_state}")

        except Exception as e:
            self._print_result("Archive", False, str(e))

    def test_fingerprint_consistency(self, model_version_id: str):
        """Test fingerprint consistency check."""
        try:
            metadata_1 = self.service.get_model(model_version_id)
            metadata_2 = self.service.get_model(model_version_id)

            if metadata_1.fingerprint == metadata_2.fingerprint:
                self._print_result("Fingerprint Consistency", True)
            else:
                self._print_result("Fingerprint Consistency", False, "Fingerprints don't match")

        except Exception as e:
            self._print_result("Fingerprint Consistency", False, str(e))

    def test_lineage_retrieval(self, model_version_id: str):
        """Test lineage chain retrieval."""
        try:
            lineage = self.service.get_lineage_chain(model_version_id)

            required_fields = [
                'snapshot_id', 'dataset_id', 'feature_dataset_id',
                'experiment_id', 'best_config_id'
            ]

            if all(field in lineage for field in required_fields):
                if lineage['snapshot_id'] == 'snap_20260710':
                    self._print_result("Lineage Retrieval", True)
                else:
                    self._print_result("Lineage Retrieval", False, "Wrong lineage data")
            else:
                self._print_result("Lineage Retrieval", False, "Missing lineage fields")

        except Exception as e:
            self._print_result("Lineage Retrieval", False, str(e))

    def test_invalid_transition(self):
        """Test that invalid transitions are rejected."""
        try:
            storage_path = self._create_test_model_artifact("mdl_invalid_v1.0.0")

            request = RegistrationRequest(
                model_id="mdl_invalid",
                version_bump="minor",
                storage_path=storage_path,
                hyperparameters={"test": 1},
                lineage={
                    "snapshot_id": "snap_inv_001",
                    "dataset_id": "ds_inv_001",
                    "feature_dataset_id": "fds_inv_001",
                    "experiment_id": "exp_inv_001",
                    "best_config_id": "cfg_inv_001"
                },
                symbol="DOTUSD",
                timeframe="15m",
                algorithm="mlp"
            )

            metadata = self.service.register_candidate(request)

            try:
                self.service.promote_to_production(metadata.model_version_id, "promoter")
                self._print_result("Invalid Transition Rejection", False, "Invalid transition was allowed")
            except ValueError as e:
                if "transition" in str(e).lower() or "promote" in str(e).lower():
                    self._print_result("Invalid Transition Rejection", True)
                else:
                    self._print_result("Invalid Transition Rejection", False, f"Wrong error: {e}")

        except Exception as e:
            self._print_result("Invalid Transition Rejection", False, str(e))

    def run_all_tests(self):
        """Run all verification tests."""
        print("\n" + "="*60)
        print("MODEL REGISTRY VERIFICATION SUITE")
        print("="*60 + "\n")

        print("Running tests...\n")

        metadata = self.test_register_model()
        if metadata:
            self.test_duplicate_rejection(metadata)
            self.test_fingerprint_consistency(metadata.model_version_id)
            self.test_lineage_retrieval(metadata.model_version_id)

            if self.test_candidate_to_validated(metadata.model_version_id):
                self.test_validated_to_production(metadata.model_version_id)

        self.test_version_increment()
        self.test_production_uniqueness()
        self.test_archive()
        self.test_invalid_transition()

        print("\n" + "="*60)
        print(f"RESULTS: {self.passed} PASSED, {self.failed} FAILED")
        print("="*60 + "\n")

        return self.failed == 0

    def cleanup(self):
        """Clean up test artifacts."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)


if __name__ == "__main__":
    verifier = ModelRegistryVerification()
    try:
        success = verifier.run_all_tests()
        exit(0 if success else 1)
    finally:
        verifier.cleanup()
