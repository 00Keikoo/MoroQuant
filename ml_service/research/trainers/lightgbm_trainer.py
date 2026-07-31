"""LightGBM Trainer implementation for MoroQuant Research Platform."""

import hashlib
import json
import os
from typing import Any, Optional, Dict, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from ml_service.research.models import DatasetSnapshot, FeatureSnapshot, ResearchRun
from ml_service.research.trainers.base_trainer import (
    BaseTrainer,
    TrainerConfig,
    TrainingMetrics,
    ArtifactMetadata,
    TrainingResult,
)


@dataclass(frozen=True)
class LightGBMTrainingMetrics(TrainingMetrics):
    """Immutable metrics subclass for LightGBM extending TrainingMetrics with classification statistics."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    roc_auc: Optional[float] = None


class LightGBMTrainer(BaseTrainer):
    """
    Concrete implementation of BaseTrainer for LightGBM models.
    Provides real training and validation using the official lightgbm library.
    """

    def __init__(self) -> None:
        self._dataset: Optional[DatasetSnapshot] = None
        self._features: Optional[FeatureSnapshot] = None
        self._config: Optional[TrainerConfig] = None
        self._run: Optional[ResearchRun] = None
        self._is_prepared: bool = False
        self._is_trained: bool = False
        self._metrics: Optional[LightGBMTrainingMetrics] = None
        self._artifact: Optional[ArtifactMetadata] = None
        self._model: Optional[lgb.Booster] = None
        self._feature_cols: list[str] = []
        self._target_col: Optional[str] = None
        self._lgb_train: Optional[lgb.Dataset] = None
        self._lgb_val: Optional[lgb.Dataset] = None

    def validate(self, dataset: Any, features: Any, config: TrainerConfig, run: Any = None) -> None:
        """
        Validate inputs, configuration, and research run state before starting.
        Raises ValueError if validation fails.
        """
        if dataset is None or not isinstance(dataset, DatasetSnapshot):
            raise ValueError("DatasetSnapshot must be provided and must be an instance of DatasetSnapshot.")

        if features is None or not isinstance(features, FeatureSnapshot):
            raise ValueError("FeatureSnapshot must be provided and must be an instance of FeatureSnapshot.")

        if config is None or not isinstance(config, TrainerConfig):
            raise ValueError("TrainerConfig must be provided and must be an instance of TrainerConfig.")

        # Check model type
        if config.model_type != "lightgbm":
            raise ValueError(f"Invalid model_type '{config.model_type}'. Expected 'lightgbm'.")

        # Validate that TrainingConfig is present
        if not config.training_parameters or len(config.training_parameters) == 0:
            raise ValueError("Training parameters must be present and non-empty.")

        # Validate that Model Parameters are present
        if not config.hyperparameters or len(config.hyperparameters) == 0:
            raise ValueError("Model hyperparameters must be present and non-empty.")

        # Validate target column specified in training parameters
        train_params_dict = dict(config.training_parameters)
        target_col = train_params_dict.get("target_column")
        if target_col is not None and not isinstance(target_col, str):
            raise ValueError("target_column parameter must be a string.")

        # Validate ResearchRun state if provided
        if run is not None:
            if not isinstance(run, ResearchRun):
                raise ValueError("ResearchRun must be an instance of ResearchRun.")
            if not run.run_id:
                raise ValueError("ResearchRun must have a valid run_id.")
            if not run.experiment_id:
                raise ValueError("ResearchRun must have a valid experiment_id.")

    def prepare(self, dataset: Any, features: Any, config: TrainerConfig, run: Any = None) -> None:
        """
        Prepare the trainer by loading datasets, validating dimensions, and constructing lgb.Dataset.
        """
        self.validate(dataset, features, config, run)
        
        self._dataset = dataset
        self._features = features
        self._config = config
        self._run = run

        # 1. Read files and check fingerprints
        if not os.path.exists(dataset.file_path):
            raise FileNotFoundError(f"Dataset snapshot file not found: {dataset.file_path}")
        if not os.path.exists(features.file_path):
            raise FileNotFoundError(f"Feature snapshot file not found: {features.file_path}")

        with open(dataset.file_path, "rb") as f:
            dataset_hash = hashlib.sha256(f.read()).hexdigest()
        if dataset_hash != dataset.fingerprint:
            raise ValueError(f"Dataset fingerprint mismatch. Expected {dataset.fingerprint}, got {dataset_hash}")

        with open(features.file_path, "rb") as f:
            features_hash = hashlib.sha256(f.read()).hexdigest()
        if features_hash != features.fingerprint:
            raise ValueError(f"Features fingerprint mismatch. Expected {features.fingerprint}, got {features_hash}")

        dataset_df = pd.read_parquet(dataset.file_path)
        features_df = pd.read_parquet(features.file_path)

        # 2. Align dataset and features
        join_keys = ["timestamp", "symbol"] if "symbol" in dataset_df.columns and "symbol" in features_df.columns else ["timestamp"]
        merged_df = pd.merge(dataset_df, features_df, on=join_keys, how="inner")

        if merged_df.empty:
            raise ValueError("Merged dataframe is empty after alignment.")

        # 3. Determine target column
        train_params_dict = dict(config.training_parameters)
        target_col = train_params_dict.get("target_column")
        if target_col is None:
            for col in ["target", "label", "y"]:
                if col in merged_df.columns:
                    target_col = col
                    break
        if target_col is None or target_col not in merged_df.columns:
            raise ValueError(f"Target column '{target_col}' not found in the dataset.")

        self._target_col = target_col

        # 4. Extract feature columns
        self._feature_cols = [c for c in features_df.columns if c not in join_keys and c != target_col]
        if not self._feature_cols:
            raise ValueError("No feature columns found after aligning features and dataset.")

        X = merged_df[self._feature_cols]
        y = merged_df[self._target_col]

        # 5. Verify dimensions and labels
        if X.empty:
            raise ValueError("Feature matrix X is empty.")
        if len(y) != len(X):
            raise ValueError("Dimension mismatch between features and targets.")
        if y.isnull().any():
            raise ValueError("Targets contain NaN/null values.")

        # 6. Split data chronologically
        val_ratio = float(train_params_dict.get("validation_split_ratio", 0.2))
        split_idx = int(len(merged_df) * (1 - val_ratio))
        if split_idx <= 0 or split_idx >= len(merged_df):
            split_idx = max(1, len(merged_df) - 1)

        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        # 7. Construct lgb.Dataset
        self._lgb_train = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
        self._lgb_val = lgb.Dataset(X_val, label=y_val, reference=self._lgb_train, free_raw_data=False)

        self._is_prepared = True

    def train(self, dataset: Any, features: Any, config: TrainerConfig, run: Any = None) -> TrainingResult:
        """
        Execute primary model fitting using deterministic configuration.
        """
        if not self._is_prepared:
            self.prepare(dataset, features, config, run)

        # 1. Parse and build deterministic hyperparameters dict
        params = dict(config.hyperparameters)
        params["seed"] = config.seed
        params["verbose"] = -1
        # Set default objective if missing
        if "objective" not in params:
            params["objective"] = "binary"

        # 2. Get training parameters
        train_params_dict = dict(config.training_parameters)
        epochs = int(train_params_dict.get("epochs", train_params_dict.get("num_boost_round", 10)))
        
        # 3. Train model
        evals_result = {}
        self._model = lgb.train(
            params=params,
            train_set=self._lgb_train,
            num_boost_round=epochs,
            valid_sets=[self._lgb_train, self._lgb_val],
            valid_names=["train", "validation"],
            callbacks=[lgb.record_evaluation(evals_result)]
        )

        self._is_trained = True

        # 4. Extract loss histories and round to 8 decimal places to avoid floating-point variance
        loss_history = ()
        val_loss_history = ()
        if "train" in evals_result and evals_result["train"]:
            metric_name = list(evals_result["train"].keys())[0]
            loss_history = tuple(round(float(x), 8) for x in evals_result["train"][metric_name])
        if "validation" in evals_result and evals_result["validation"]:
            metric_name = list(evals_result["validation"].keys())[0]
            val_loss_history = tuple(round(float(x), 8) for x in evals_result["validation"][metric_name])

        # 5. Evaluate on train/validation for initial metrics
        val_labels = self._lgb_val.get_label()
        val_preds = self._model.predict(self._lgb_val.get_data())

        y_true = (val_labels > 0.5).astype(int)
        y_pred = (val_preds > 0.5).astype(int)

        accuracy = float(accuracy_score(y_true, y_pred))
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        try:
            roc_auc = float(roc_auc_score(y_true, val_preds))
        except Exception:
            roc_auc = None

        # Standard MoroQuant Scorecard Calculations
        sim_returns = (2 * y_pred - 1) * val_labels
        mean_ret = np.mean(sim_returns)
        std_ret = np.std(sim_returns)
        sharpe = float(mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

        ece = self._calculate_ece(y_true, val_preds)
        brier = float(np.mean((val_preds - val_labels) ** 2))
        
        cum_returns = np.cumsum(sim_returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = float(np.max(running_max - cum_returns)) if len(cum_returns) > 0 else 0.0

        self._metrics = LightGBMTrainingMetrics(
            loss_history=loss_history,
            val_loss_history=val_loss_history,
            sharpe=round(sharpe, 4),
            ece=round(ece, 4),
            brier=round(brier, 4),
            drawdown=round(drawdown, 4),
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            roc_auc=round(roc_auc, 4) if roc_auc is not None else None
        )

        # 6. Generate checksum and virtual artifact path
        sorted_hparams = sorted(config.hyperparameters, key=lambda x: x[0])
        sorted_train_params = sorted(config.training_parameters, key=lambda x: x[0])
        model_str = self._model.model_to_string()
        
        serialized_config = {
            "model_type": config.model_type,
            "seed": config.seed,
            "hyperparameters": sorted_hparams,
            "training_parameters": sorted_train_params,
            "model_str": model_str
        }
        config_json = json.dumps(serialized_config, sort_keys=True)
        checksum = hashlib.sha256(config_json.encode("utf-8")).hexdigest()

        file_path = f"/storage/models/lightgbm_{checksum[:16]}.json"
        size_bytes = len(config_json.encode("utf-8"))

        self._artifact = ArtifactMetadata(
            checksum=checksum,
            file_path=file_path,
            size_bytes=size_bytes,
            permissions="chmod 444"
        )

        return TrainingResult(
            status="SUCCESS",
            metrics=self._metrics,
            artifacts=self._artifact
        )

    def evaluate(self, dataset: Any) -> LightGBMTrainingMetrics:
        """
        Evaluate the fitted model on the provided dataset snapshot and return classification metrics.
        """
        if not self._is_trained or self._model is None or self._config is None or self._features is None:
            raise ValueError("Cannot evaluate: Trainer has not been trained yet.")

        if dataset is None or not isinstance(dataset, DatasetSnapshot):
            raise ValueError("DatasetSnapshot must be provided for evaluation.")

        if not os.path.exists(dataset.file_path):
            raise FileNotFoundError(f"Evaluation dataset file not found: {dataset.file_path}")

        # Load and align
        eval_dataset_df = pd.read_parquet(dataset.file_path)
        features_df = pd.read_parquet(self._features.file_path)

        join_keys = ["timestamp", "symbol"] if "symbol" in eval_dataset_df.columns and "symbol" in features_df.columns else ["timestamp"]
        merged_eval = pd.merge(eval_dataset_df, features_df, on=join_keys, how="inner")

        if merged_eval.empty:
            raise ValueError("Evaluation data is empty after merge.")

        X_eval = merged_eval[self._feature_cols]
        y_eval = merged_eval[self._target_col]

        preds = self._model.predict(X_eval)

        y_true = (y_eval > 0.5).astype(int)
        y_pred = (preds > 0.5).astype(int)

        accuracy = float(accuracy_score(y_true, y_pred))
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        try:
            roc_auc = float(roc_auc_score(y_true, preds))
        except Exception:
            roc_auc = None

        # MoroQuant Scorecard Calculations
        sim_returns = (2 * y_pred - 1) * y_eval
        mean_ret = np.mean(sim_returns)
        std_ret = np.std(sim_returns)
        sharpe = float(mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

        ece = self._calculate_ece(y_true, preds)
        brier = float(np.mean((preds - y_eval) ** 2))

        cum_returns = np.cumsum(sim_returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = float(np.max(running_max - cum_returns)) if len(cum_returns) > 0 else 0.0

        return LightGBMTrainingMetrics(
            loss_history=self._metrics.loss_history,
            val_loss_history=self._metrics.val_loss_history,
            sharpe=round(sharpe, 4),
            ece=round(ece, 4),
            brier=round(brier, 4),
            drawdown=round(drawdown, 4),
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            roc_auc=round(roc_auc, 4) if roc_auc is not None else None
        )

    def collect_metrics(self) -> LightGBMTrainingMetrics:
        """
        Collect training history and final evaluation metrics.
        """
        if not self._is_trained or self._metrics is None:
            raise ValueError("Cannot collect metrics: Trainer has not been trained yet.")
        return self._metrics

    def generate_artifact(self) -> ArtifactMetadata:
        """
        Serialize model weights and parameters to a deterministic artifact payload.
        """
        if not self._is_trained or self._artifact is None:
            raise ValueError("Cannot generate artifact: Trainer has not been trained yet.")
        return self._artifact

    def save_artifacts(self) -> ArtifactMetadata:
        """
        Exposes serialize logic.
        """
        return self.generate_artifact()

    def generate_artifacts(self) -> dict:
        """
        Produce in-memory model serialization, feature importance, metadata, and metrics.
        Does not write to permanent storage.
        """
        if not self._is_trained or self._model is None or self._config is None:
            raise ValueError("Cannot generate artifacts: Trainer has not been trained yet.")

        model_str = self._model.model_to_string()
        importance = self._model.feature_importance(importance_type="split").tolist()
        feature_names = self._model.feature_name()
        importance_dict = dict(zip(feature_names, importance))

        metadata = {
            "model_type": "lightgbm",
            "seed": self._config.seed,
            "feature_names": self._feature_cols,
            "hyperparameters": dict(self._config.hyperparameters),
            "training_parameters": dict(self._config.training_parameters)
        }

        metrics_dict = {
            "sharpe": self._metrics.sharpe,
            "ece": self._metrics.ece,
            "brier": self._metrics.brier,
            "drawdown": self._metrics.drawdown,
            "accuracy": self._metrics.accuracy,
            "precision": self._metrics.precision,
            "recall": self._metrics.recall,
            "f1": self._metrics.f1,
            "roc_auc": self._metrics.roc_auc,
        }

        return {
            "model": model_str,
            "feature_importance": importance_dict,
            "metadata": metadata,
            "metrics": metrics_dict
        }

    def cleanup(self) -> None:
        """
        Release temporary datasets and in-memory booster instances.
        """
        self._dataset = None
        self._features = None
        self._config = None
        self._run = None
        self._is_prepared = False
        self._is_trained = False
        self._metrics = None
        self._artifact = None
        self._model = None
        self._feature_cols = []
        self._target_col = None
        self._lgb_train = None
        self._lgb_val = None

    def _calculate_ece(self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
        """Calculate Expected Calibration Error (ECE) for predictions."""
        prob_min, prob_max = 0.0, 1.0
        bin_boundaries = np.linspace(prob_min, prob_max, n_bins + 1)
        ece = 0.0
        for i in range(n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            prop_in_bin = np.mean(in_bin)
            if prop_in_bin > 0:
                accuracy_in_bin = np.mean(y_true[in_bin])
                avg_confidence_in_bin = np.mean(y_prob[in_bin])
                ece += prop_in_bin * np.abs(avg_confidence_in_bin - accuracy_in_bin)
        return float(ece)
