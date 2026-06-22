"""Production model compatibility audit script."""

import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).parent))

from models.trainer import get_feature_columns, prepare_features
from models.governance import get_model_directories, load_model_metadata


def load_model_package(model_path: str) -> Optional[Dict]:
    """Load full model package."""
    try:
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error loading {model_path}: {e}")
        return None


def extract_symbol_timeframe(filename: str) -> tuple:
    """Extract symbol and timeframe from filename."""
    parts = filename.replace('.pkl', '').split('_')
    if len(parts) >= 2:
        symbol = parts[0]
        timeframe = parts[1]
        return symbol, timeframe
    return None, None


def get_current_features(symbol: str, timeframe: str) -> List[str]:
    """Generate current feature list based on code."""
    # Create dummy dataframe to trigger feature generation
    df = pd.DataFrame({
        'timestamp': range(500),
        'open': [100.0] * 500,
        'high': [101.0] * 500,
        'low': [99.0] * 500,
        'close': [100.0] * 500,
        'volume': [1000.0] * 500,
    })

    try:
        # Prepare features to get actual column names
        df_features = prepare_features(df, symbol=symbol)

        # Get feature columns from current code
        current_features = get_feature_columns(df_features)

        return current_features
    except Exception as e:
        print(f"Error generating features for {symbol} {timeframe}: {e}")
        return []


def check_feature_compatibility(model_features: List[str], current_features: List[str]) -> Dict:
    """Check compatibility between model and current features."""
    model_set = set(model_features)
    current_set = set(current_features)

    missing_in_current = model_set - current_set
    extra_in_current = current_set - model_set

    compatible = len(missing_in_current) == 0

    return {
        'compatible': compatible,
        'model_feature_count': len(model_features),
        'current_feature_count': len(current_features),
        'missing_features': sorted(list(missing_in_current)),
        'extra_features': sorted(list(extra_in_current)),
    }


def check_governance_compliance(model_path: str, dirs: Dict) -> Dict:
    """Check if model was promoted through governance."""
    model_file = Path(model_path)
    production_dir = dirs['production']

    # Check if file is in production directory
    in_production = model_file.parent == production_dir

    # Check if corresponding candidate exists or existed in archive
    candidates_dir = dirs['candidates']
    archive_dir = dirs['archive']

    candidate_exists = (candidates_dir / model_file.name).exists()

    # Check archive for candidate trace
    archived_candidate = list(archive_dir.glob(f"{model_file.stem}*"))

    governance_compliant = in_production and (candidate_exists or len(archived_candidate) > 0)

    return {
        'in_production_dir': in_production,
        'candidate_exists': candidate_exists,
        'archived_candidate_count': len(archived_candidate),
        'governance_compliant': governance_compliant,
    }


def audit_production_models():
    """Audit all production models."""
    dirs = get_model_directories()
    production_dir = dirs['production']

    if not production_dir.exists():
        print("Production directory does not exist")
        return

    # Get all production model files
    model_files = [
        f for f in production_dir.glob("*.pkl")
        if not f.name.endswith("_calibration.pkl")
    ]

    print(f"Found {len(model_files)} production models")

    audit_results = []

    for model_file in sorted(model_files):
        print(f"\nAuditing: {model_file.name}")

        symbol, timeframe = extract_symbol_timeframe(model_file.name)

        if not symbol or not timeframe:
            print(f"  Could not parse symbol/timeframe from {model_file.name}")
            continue

        # Load model metadata
        metadata = load_model_metadata(str(model_file))

        if not metadata:
            print(f"  Failed to load metadata")
            audit_results.append({
                'symbol': symbol,
                'timeframe': timeframe,
                'filename': model_file.name,
                'error': 'failed_to_load_metadata',
            })
            continue

        # Extract metadata fields
        model_type = metadata.get('model_type', 'unknown')
        trained_at = metadata.get('trained_at', 'unknown')
        model_features = metadata.get('feature_cols', [])

        print(f"  Model type: {model_type}")
        print(f"  Trained at: {trained_at}")
        print(f"  Model feature count: {len(model_features)}")

        # Get current features
        current_features = get_current_features(symbol, timeframe)
        print(f"  Current feature count: {len(current_features)}")

        # Check compatibility
        compatibility = check_feature_compatibility(model_features, current_features)

        print(f"  Compatible: {compatibility['compatible']}")
        if not compatibility['compatible']:
            print(f"  Missing features: {len(compatibility['missing_features'])}")
            if compatibility['missing_features']:
                print(f"    {', '.join(compatibility['missing_features'][:5])}...")

        # Check governance compliance
        governance = check_governance_compliance(str(model_file), dirs)
        print(f"  Governance compliant: {governance['governance_compliant']}")

        audit_results.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'filename': model_file.name,
            'model_type': model_type,
            'trained_at': trained_at,
            'model_feature_count': len(model_features),
            'current_feature_count': len(current_features),
            'compatible': compatibility['compatible'],
            'missing_features': compatibility['missing_features'],
            'extra_features': compatibility['extra_features'],
            'governance_compliant': governance['governance_compliant'],
            'in_production_dir': governance['in_production_dir'],
            'candidate_exists': governance['candidate_exists'],
            'archived_candidate_count': governance['archived_candidate_count'],
        })

    # Save results
    output_path = Path(__file__).parent / 'production_model_audit_results.json'
    with open(output_path, 'w') as f:
        json.dump(audit_results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Audit complete. Results saved to {output_path}")
    print(f"{'='*60}")

    # Summary statistics
    total = len(audit_results)
    compatible = sum(1 for r in audit_results if r.get('compatible', False))
    incompatible = total - compatible
    governance_compliant = sum(1 for r in audit_results if r.get('governance_compliant', False))
    governance_non_compliant = total - governance_compliant

    print(f"\nSUMMARY:")
    print(f"  Total models: {total}")
    print(f"  Compatible: {compatible}")
    print(f"  Incompatible: {incompatible}")
    print(f"  Governance compliant: {governance_compliant}")
    print(f"  Governance non-compliant: {governance_non_compliant}")

    return audit_results


if __name__ == '__main__':
    audit_production_models()
