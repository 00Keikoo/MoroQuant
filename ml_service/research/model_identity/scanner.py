"""
Model Registry Identity Scanner
"""

import pickle
from pathlib import Path

from .models import ModelIdentity
from .parser import parse_model_filename
from .fingerprint import feature_fingerprint


class ModelArtifactScanner:


    def __init__(self, model_directory):

        self.model_directory = Path(model_directory)



    def scan(self):

        results=[]

        for file in self.model_directory.glob("*.pkl"):

            if file.name.endswith(
                "_calibration.pkl"
            ):
                continue


            identity = self.inspect(file)

            results.append(identity)


        return tuple(results)



    def inspect(self, file):

        with open(file,"rb") as f:
            artifact = pickle.load(f)


        metadata = artifact.get(
            "metadata",
            {}
        )


        features = metadata.get(
            "feature_cols",
            []
        )


        calibration = (
            file.parent /
            f"{file.stem}_calibration.pkl"
        )


        validation = (
            "validation" in metadata
        )


        if validation and calibration.exists():
            status="GOVERNANCE_READY"

        elif validation:
            status="VALIDATED"

        else:
            status="DISCOVERED"


        parsed = parse_model_filename(
            file.name
        )


        return ModelIdentity(

            artifact_path=str(file),

            symbol=parsed["symbol"],
            timeframe=parsed["timeframe"],
            model_type=parsed["model_type"],
            asset_class=parsed["asset_class"],

            feature_count=len(features),

            feature_fingerprint=
                feature_fingerprint(features),

            trained_at=
                parsed["trained_at"],

            validation_available=
                validation,

            calibration_available=
                calibration.exists(),

            sample_count=
                metadata.get(
                    "n_samples",
                    0
                ),

            lifecycle_status=status
        )
