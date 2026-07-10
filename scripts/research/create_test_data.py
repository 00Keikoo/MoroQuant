"""Create test data for Research Dashboard verification."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml_service.research.experiment_registry.storage import (
    init_schema,
    insert_experiment,
    insert_config,
    insert_result
)
from ml_service.research.dataset_manager.repository import DatasetRepository
from ml_service.research.dataset_manager.types import (
    DatasetMetadata,
    TimeBounds,
    DatasetSchema,
    LifecycleState
)
from ml_service.research.feature_store.repository import FeatureRepository
from ml_service.research.feature_store.feature_types import (
    FeatureDefinition,
    FeatureVersion,
    FeatureDatasetMetadata,
    FeatureLifecycleState
)


def create_test_data():
    """Create test experiments, datasets, and features."""
    print("Creating test data...")

    # Initialize schemas
    init_schema()
    dataset_repo = DatasetRepository()
    feature_repo = FeatureRepository()

    # Create test dataset
    dataset = DatasetMetadata(
        dataset_id="ds_test_v1.0.0",
        version="v1.0.0",
        fingerprint="abc123def456",
        snapshot_id="snap_001",
        created_at="2026-07-09T00:00:00Z",
        time_bounds=TimeBounds(
            start_time="2026-07-01T00:00:00Z",
            end_time="2026-07-08T00:00:00Z"
        ),
        lifecycle_state=LifecycleState.FROZEN,
        storage_path="/storage/datasets/ds_test_v1.0.0.parquet",
        schema=DatasetSchema(
            features=["price", "volume"],
            targets=["signal"],
            data_types={"price": "float64", "volume": "float64", "signal": "int64"}
        ),
        is_frozen=True
    )
    dataset_repo.save(dataset)
    print(f"✓ Created dataset: {dataset.dataset_id}")

    # Create test feature definition
    feature_def = FeatureDefinition(
        feature_name="rsi_14",
        description="14-period RSI",
        formula_ref="ml_service.features.rsi",
        created_at="2026-07-09T00:00:00Z"
    )
    feature_repo.save_definition(feature_def)
    print(f"✓ Created feature definition: {feature_def.feature_name}")

    # Create test feature version
    feature_version = FeatureVersion(
        feature_version_id="rsi_14_v1.0.0",
        feature_name="rsi_14",
        version="v1.0.0",
        parameters={"period": 14},
        created_at="2026-07-09T00:00:00Z"
    )
    feature_repo.save_version(feature_version)
    print(f"✓ Created feature version: {feature_version.feature_version_id}")

    # Create test feature dataset
    feature_dataset = FeatureDatasetMetadata(
        feature_dataset_id="fds_rsi_14_v1.0.0_ds_test_v1.0.0",
        source_dataset_id="ds_test_v1.0.0",
        feature_version_id="rsi_14_v1.0.0",
        fingerprint="fed654cba321",
        created_at="2026-07-09T00:00:00Z",
        lifecycle_state=FeatureLifecycleState.FROZEN,
        storage_path="/storage/features/fds_rsi_14_v1.0.0.parquet",
        is_frozen=True
    )
    feature_repo.save_dataset(feature_dataset)
    print(f"✓ Created feature dataset: {feature_dataset.feature_dataset_id}")

    # Create test experiments
    experiments = [
        {
            "experiment_id": "exp_trend_001",
            "snapshot_id": "snap_001",
            "configs": [
                {
                    "config_id": "cfg_001",
                    "threshold_long": 0.015,
                    "threshold_short": -0.015,
                    "regime_filter": None
                }
            ],
            "results": [
                {
                    "config_id": "cfg_001",
                    "pnl": 0.321,
                    "winrate": 0.542,
                    "sharpe": 1.85,
                    "max_drawdown": -0.124,
                    "consistency_score": 0.73,
                    "trade_count": 142
                }
            ]
        },
        {
            "experiment_id": "exp_trend_002",
            "snapshot_id": "snap_001",
            "configs": [
                {
                    "config_id": "cfg_002",
                    "threshold_long": 0.020,
                    "threshold_short": -0.020,
                    "regime_filter": None
                }
            ],
            "results": [
                {
                    "config_id": "cfg_002",
                    "pnl": 0.410,
                    "winrate": 0.587,
                    "sharpe": 2.10,
                    "max_drawdown": -0.098,
                    "consistency_score": 0.81,
                    "trade_count": 128
                }
            ]
        }
    ]

    for exp in experiments:
        insert_experiment(
            exp["experiment_id"],
            exp["snapshot_id"],
            "2026-07-09T00:00:00Z"
        )

        for cfg in exp["configs"]:
            insert_config(
                exp["experiment_id"],
                cfg["config_id"],
                cfg["threshold_long"],
                cfg["threshold_short"],
                cfg["regime_filter"]
            )

        for result in exp["results"]:
            insert_result(
                exp["experiment_id"],
                result["config_id"],
                result["pnl"],
                result["winrate"],
                result["sharpe"],
                result["max_drawdown"],
                result["consistency_score"],
                result["trade_count"]
            )

        print(f"✓ Created experiment: {exp['experiment_id']}")

    print("\n✓ Test data creation complete")


if __name__ == "__main__":
    create_test_data()
