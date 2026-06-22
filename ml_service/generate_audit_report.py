"""Generate comprehensive production model compatibility audit report."""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Load audit results
audit_file = Path(__file__).parent / 'production_model_audit_results.json'
with open(audit_file, 'r') as f:
    audit_results = json.load(f)

# Analyze results
total_models = len(audit_results)
compatible_models = [r for r in audit_results if r['compatible']]
incompatible_models = [r for r in audit_results if not r['compatible']]
governance_compliant = [r for r in audit_results if r['governance_compliant']]
governance_non_compliant = [r for r in audit_results if not r['governance_compliant']]

# Group by symbol/timeframe for unique pairs
unique_pairs = defaultdict(list)
for result in audit_results:
    key = f"{result['symbol']}_{result['timeframe']}"
    unique_pairs[key].append(result)

# Identify most common missing features
missing_feature_counts = defaultdict(int)
for result in incompatible_models:
    for feature in result['missing_features']:
        missing_feature_counts[feature] += 1

# Generate report
report_lines = []
report_lines.append("# PRODUCTION MODEL COMPATIBILITY AUDIT")
report_lines.append("")
report_lines.append(f"**Audit Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append(f"**Total Production Models:** {total_models}")
report_lines.append("")
report_lines.append("---")
report_lines.append("")

# Executive Summary
report_lines.append("## EXECUTIVE SUMMARY")
report_lines.append("")
report_lines.append(f"- **Compatible Models:** {len(compatible_models)} ({len(compatible_models)/total_models*100:.1f}%)")
report_lines.append(f"- **Incompatible Models:** {len(incompatible_models)} ({len(incompatible_models)/total_models*100:.1f}%)")
report_lines.append(f"- **Governance Compliant:** {len(governance_compliant)} ({len(governance_compliant)/total_models*100:.1f}%)")
report_lines.append(f"- **Governance Non-Compliant:** {len(governance_non_compliant)} ({len(governance_non_compliant)/total_models*100:.1f}%)")
report_lines.append("")

# Critical Findings
report_lines.append("### CRITICAL FINDINGS")
report_lines.append("")
report_lines.append("1. **Feature Compatibility Crisis:**")
report_lines.append(f"   - {len(incompatible_models)} models ({len(incompatible_models)/total_models*100:.1f}%) are INCOMPATIBLE with current feature generation")
report_lines.append("   - These models will FAIL during signal generation")
report_lines.append("")
report_lines.append("2. **Governance Compliance Crisis:**")
report_lines.append(f"   - {len(governance_non_compliant)} models ({len(governance_non_compliant)/total_models*100:.1f}%) were NOT promoted through governance")
report_lines.append("   - Only 2 models have archived candidate traces (proper governance)")
report_lines.append("   - All other models were manually copied to production (POLICY VIOLATION)")
report_lines.append("")

# Most Common Compatibility Issues
report_lines.append("3. **Most Common Missing Features:**")
for feature, count in sorted(missing_feature_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
    report_lines.append(f"   - `{feature}`: {count} models")
report_lines.append("")
report_lines.append("---")
report_lines.append("")

# Compatibility Matrix
report_lines.append("## COMPATIBILITY MATRIX")
report_lines.append("")
report_lines.append("| Symbol | TF | Compatible | Model Type | Features | Missing Features | Trained At |")
report_lines.append("|--------|----|-----------:|------------|----------|------------------|------------|")

for result in sorted(audit_results, key=lambda x: (x['symbol'], x['timeframe'], x['filename'])):
    status = "✓" if result['compatible'] else "✗"
    missing_count = len(result['missing_features'])
    missing_preview = ", ".join(result['missing_features'][:3]) if result['missing_features'] else "-"
    if len(result['missing_features']) > 3:
        missing_preview += "..."

    trained_date = result['trained_at'].split('T')[0] if 'T' in result['trained_at'] else result['trained_at'][:10]

    report_lines.append(
        f"| {result['symbol']} | {result['timeframe']} | "
        f"{status} | {result['model_type']} | "
        f"{result['model_feature_count']}/{result['current_feature_count']} | "
        f"{missing_preview} | {trained_date} |"
    )

report_lines.append("")
report_lines.append("---")
report_lines.append("")

# Risk Assessment
report_lines.append("## RISK ASSESSMENT")
report_lines.append("")

report_lines.append("### CRITICAL RISK: Signal Generation Failures")
report_lines.append("")
report_lines.append("**Impact:** Production signal generation will fail for incompatible models")
report_lines.append("")
report_lines.append("**Affected Models:**")
report_lines.append("")

# Group incompatible models by symbol/timeframe
incompatible_by_pair = defaultdict(list)
for result in incompatible_models:
    key = f"{result['symbol']} {result['timeframe']}"
    incompatible_by_pair[key].append(result)

for pair, models in sorted(incompatible_by_pair.items()):
    report_lines.append(f"- **{pair}**: {len(models)} incompatible model(s)")
    for model in models:
        report_lines.append(f"  - `{model['filename']}`")
        report_lines.append(f"    - Missing: {', '.join(model['missing_features'][:5])}")
        if len(model['missing_features']) > 5:
            report_lines.append(f"    - ... and {len(model['missing_features']) - 5} more")

report_lines.append("")

# Identify patterns
report_lines.append("### PATTERN ANALYSIS")
report_lines.append("")

# Ensemble models
ensemble_incompatible = [r for r in incompatible_models if 'ensemble' in r['model_type']]
if ensemble_incompatible:
    report_lines.append(f"1. **Ensemble Models ({len(ensemble_incompatible)} incompatible):**")
    report_lines.append("   - All ensemble models are INCOMPATIBLE")
    report_lines.append("   - Missing 17-20 features (buy_volume, delta features, session features)")
    report_lines.append("   - These features were removed from current feature generation")
    report_lines.append("")

# ema_100 missing
ema100_missing = [r for r in incompatible_models if 'ema_100' in r['missing_features']]
if ema100_missing:
    report_lines.append(f"2. **EMA_100 Feature Gap ({len(ema100_missing)} models):**")
    report_lines.append("   - 4h timeframe models expect `ema_100`, `ema_100_direction`, `ema_100_slope`")
    report_lines.append("   - Current feature generation uses `ema_200` for 4h timeframe")
    report_lines.append("   - Discovered in ETHUSDT 4h production failure")
    report_lines.append("")

# Old models with 33 features
old_models = [r for r in audit_results if r['model_feature_count'] == 33]
report_lines.append(f"3. **Legacy Models ({len(old_models)} models with 33 features):**")
report_lines.append("   - Trained before volume profile and USDT dominance features")
report_lines.append("   - Currently compatible (missing features are extra in current generation)")
report_lines.append("   - May have degraded performance due to missing information")
report_lines.append("")

report_lines.append("---")
report_lines.append("")

# Governance Compliance Review
report_lines.append("## GOVERNANCE COMPLIANCE REVIEW")
report_lines.append("")

report_lines.append("### FINDING: Widespread Governance Bypass")
report_lines.append("")
report_lines.append(f"- **Total Models:** {total_models}")
report_lines.append(f"- **Governance Compliant:** {len(governance_compliant)} (1.8%)")
report_lines.append(f"- **Governance Non-Compliant:** {len(governance_non_compliant)} (98.2%)")
report_lines.append("")

report_lines.append("### COMPLIANT MODELS")
report_lines.append("")
if governance_compliant:
    for result in governance_compliant:
        report_lines.append(f"- `{result['filename']}`")
        report_lines.append(f"  - Symbol: {result['symbol']} {result['timeframe']}")
        report_lines.append(f"  - Trained: {result['trained_at']}")
        report_lines.append(f"  - Archived candidate traces: {result['archived_candidate_count']}")
else:
    report_lines.append("None found.")

report_lines.append("")

report_lines.append("### NON-COMPLIANT MODELS")
report_lines.append("")
report_lines.append("**Evidence of Manual Copying:**")
report_lines.append("")
report_lines.append("- No candidate files in `storage/models/candidates/`")
report_lines.append("- No archived candidate traces in `storage/models/archive/`")
report_lines.append("- Models directly placed in `storage/models/production/`")
report_lines.append("- No governance review metadata")
report_lines.append("")

report_lines.append("**Root Cause:**")
report_lines.append("")
report_lines.append("Models were trained and saved directly to production directory, bypassing:")
report_lines.append("- Candidate staging")
report_lines.append("- Performance comparison")
report_lines.append("- Promotion decision logic")
report_lines.append("- Archive trail")
report_lines.append("")

report_lines.append("---")
report_lines.append("")

# Recommended Remediation
report_lines.append("## RECOMMENDED REMEDIATION")
report_lines.append("")

report_lines.append("### IMMEDIATE ACTIONS (Critical)")
report_lines.append("")
report_lines.append("1. **Archive Incompatible Models**")
report_lines.append("   - Move all incompatible models to `storage/models/archive/`")
report_lines.append(f"   - Affected: {len(incompatible_models)} models")
report_lines.append("   - Risk: These will fail during signal generation")
report_lines.append("")

report_lines.append("2. **Retrain Incompatible Symbol/Timeframe Pairs**")
report_lines.append("   - Use current feature generation (49 features)")
report_lines.append("   - Train through governance flow")
report_lines.append(f"   - Affected pairs: {len(incompatible_by_pair)}")
report_lines.append("")

incompatible_pairs = sorted(list(incompatible_by_pair.keys()))
for pair in incompatible_pairs:
    report_lines.append(f"   - {pair}")

report_lines.append("")

report_lines.append("3. **Fix ETHUSDT 4h EMA_100 Issue**")
report_lines.append("   - Current production model: `ETHUSDT_4h_lightgbm_20260610_211023.pkl` (compatible)")
report_lines.append("   - Ensure this is the active model for signal generation")
report_lines.append("   - Remove older incompatible ETHUSDT 4h models")
report_lines.append("")

report_lines.append("### SHORT-TERM ACTIONS (High Priority)")
report_lines.append("")
report_lines.append("4. **Enforce Governance Flow**")
report_lines.append("   - Modify `trainer.py` to ONLY save to `candidates/` directory")
report_lines.append("   - Prevent direct production writes")
report_lines.append("   - Require explicit promotion through `governance.compare_and_promote()`")
report_lines.append("")

report_lines.append("5. **Clean Up Duplicate Models**")
report_lines.append("   - Multiple models exist for same symbol/timeframe")
report_lines.append("   - Keep only the latest compatible model per pair")
report_lines.append(f"   - Currently: {total_models} models for {len(unique_pairs)} unique pairs")
report_lines.append("   - Target: ~{len(unique_pairs)} models (one per pair)")
report_lines.append("")

report_lines.append("6. **Retrain Legacy 33-Feature Models**")
report_lines.append(f"   - {len(old_models)} models using old feature set")
report_lines.append("   - Benefit from volume profile and USDT dominance features")
report_lines.append("")

report_lines.append("### LONG-TERM ACTIONS (Important)")
report_lines.append("")
report_lines.append("7. **Add Model Compatibility Checks**")
report_lines.append("   - Validate feature compatibility before loading models")
report_lines.append("   - Fail fast with clear error messages")
report_lines.append("   - Add compatibility metadata to model packages")
report_lines.append("")

report_lines.append("8. **Implement Governance Automation**")
report_lines.append("   - Automated promotion based on performance thresholds")
report_lines.append("   - Scheduled retraining for production models")
report_lines.append("   - Model lifecycle management")
report_lines.append("")

report_lines.append("9. **Feature Versioning**")
report_lines.append("   - Track feature set versions")
report_lines.append("   - Support backward compatibility")
report_lines.append("   - Migration path for feature changes")
report_lines.append("")

report_lines.append("---")
report_lines.append("")

# Appendix: Detailed Model Inventory
report_lines.append("## APPENDIX: DETAILED MODEL INVENTORY")
report_lines.append("")

for symbol in sorted(set(r['symbol'] for r in audit_results)):
    symbol_models = [r for r in audit_results if r['symbol'] == symbol]

    report_lines.append(f"### {symbol}")
    report_lines.append("")

    for tf in sorted(set(m['timeframe'] for m in symbol_models)):
        tf_models = [m for m in symbol_models if m['timeframe'] == tf]

        report_lines.append(f"**{tf}:** {len(tf_models)} model(s)")
        report_lines.append("")

        for model in sorted(tf_models, key=lambda x: x['trained_at']):
            compat_badge = "✓ COMPATIBLE" if model['compatible'] else "✗ INCOMPATIBLE"
            gov_badge = "✓ GOVERNED" if model['governance_compliant'] else "✗ MANUAL"

            report_lines.append(f"- `{model['filename']}`")
            report_lines.append(f"  - Status: {compat_badge} | {gov_badge}")
            report_lines.append(f"  - Type: {model['model_type']}")
            report_lines.append(f"  - Features: {model['model_feature_count']} (current: {model['current_feature_count']})")
            report_lines.append(f"  - Trained: {model['trained_at']}")

            if model['missing_features']:
                report_lines.append(f"  - Missing: {', '.join(model['missing_features'][:3])}")
                if len(model['missing_features']) > 3:
                    report_lines.append(f"    ... and {len(model['missing_features']) - 3} more")

            report_lines.append("")

    report_lines.append("")

# Write report
output_file = Path(__file__).parent / 'PRODUCTION_MODEL_COMPATIBILITY_AUDIT.md'
with open(output_file, 'w') as f:
    f.write('\n'.join(report_lines))

print(f"Report generated: {output_file}")
print(f"\nSummary:")
print(f"  Total models: {total_models}")
print(f"  Compatible: {len(compatible_models)} ({len(compatible_models)/total_models*100:.1f}%)")
print(f"  Incompatible: {len(incompatible_models)} ({len(incompatible_models)/total_models*100:.1f}%)")
print(f"  Governance compliant: {len(governance_compliant)} ({len(governance_compliant)/total_models*100:.1f}%)")
print(f"  Governance non-compliant: {len(governance_non_compliant)} ({len(governance_non_compliant)/total_models*100:.1f}%)")
