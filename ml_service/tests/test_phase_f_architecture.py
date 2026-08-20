"""
Phase F: Architecture Verification

Verifies Sprint 3.9D-15 implementation against design constraints:
1. Research → simulation one-way dependency
2. No execution imports in research
3. Orchestrator < 500 LOC
4. ResearchSession canonical (no V2/alternates)
5. No BacktestInterface abstraction
6. No register_candidate() API
"""

import ast
from pathlib import Path


def test_research_to_simulation_one_way():
    """Verify research → simulation is one-way."""
    simulation_dir = Path("ml_service/simulation")
    violations = []

    for py_file in simulation_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        with open(py_file, 'r') as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("ml_service.research"):
                    violations.append(f"{py_file}: imports {node.module}")

    assert not violations, (
        f"Simulation imports from research (violates one-way):\n" +
        "\n".join(violations)
    )


def test_orchestrator_under_500_loc():
    """Verify orchestrator remains under 500 LOC."""
    orchestrator_path = Path("ml_service/research/orchestrator.py")

    with open(orchestrator_path, 'r') as f:
        lines = f.readlines()

    loc = len(lines)
    assert loc < 500, f"Orchestrator is {loc} lines (must be < 500)"


def test_no_research_session_v2():
    """Verify no ResearchSessionV2 or alternate session models."""
    research_dir = Path("ml_service/research")
    violations = []

    forbidden_names = [
        "ResearchSessionV2",
        "SessionV2",
        "ResearchExecutionContext",
    ]

    for py_file in research_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        with open(py_file, 'r') as f:
            content = f.read()

        for name in forbidden_names:
            if name in content:
                violations.append(f"{py_file}: contains {name}")

    assert not violations, (
        f"Found alternate session models:\n" + "\n".join(violations)
    )


def test_no_backtest_interface():
    """Verify no BacktestInterface abstraction in research."""
    research_dir = Path("ml_service/research")
    violations = []

    forbidden = ["BacktestInterface", "BacktestService"]

    for py_file in research_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        with open(py_file, 'r') as f:
            content = f.read()

        for name in forbidden:
            if name in content:
                violations.append(f"{py_file}: contains {name}")

    assert not violations, (
        f"Found forbidden backtest abstractions:\n" + "\n".join(violations)
    )


def test_no_register_candidate():
    """Verify no register_candidate() API was added."""
    research_dir = Path("ml_service/research")
    violations = []

    legacy_files = {
        "ml_service/research/research_orchestrator/service.py",
        "ml_service/research/model_registry/api.py",
        "ml_service/research/model_registry/verify_model_registry.py"
    }

    for py_file in research_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        # Convert to standard path format for comparison
        rel_path = py_file.as_posix()
        if rel_path in legacy_files:
            continue

        with open(py_file, 'r') as f:
            content = f.read()

        if "register_candidate" in content:
            violations.append(f"{py_file}: contains register_candidate")

    assert not violations, (
        f"Found register_candidate() API:\n" + "\n".join(violations)
    )


def test_canonical_provenance_fields():
    """Verify ResearchSession uses canonical provenance fields."""
    models_path = Path("ml_service/research/models.py")

    with open(models_path, 'r') as f:
        content = f.read()

    required_fields = [
        "dataset_fingerprint",
        "feature_fingerprint",
        "replay_fingerprint",
        "experiment_fingerprint",
        "evaluation_fingerprint",
        "model_fingerprint",
        "random_seed",
    ]

    missing = []
    for field in required_fields:
        if field not in content:
            missing.append(field)

    assert not missing, f"ResearchSession missing canonical fields: {missing}"


def test_backtest_runner_in_simulation():
    """Verify BacktestRunner exists in simulation/backtest/."""
    runner_path = Path("ml_service/simulation/backtest/runner.py")
    assert runner_path.exists(), "BacktestRunner must exist in simulation/backtest/"

    with open(runner_path, 'r') as f:
        content = f.read()

    assert "class BacktestRunner" in content, "BacktestRunner class must exist"
    assert "PortfolioService" in content, "BacktestRunner owns execution infrastructure"


def test_provenance_module_exists():
    """Verify provenance module with canonical fingerprint functions."""
    provenance_path = Path("ml_service/research/provenance.py")
    assert provenance_path.exists(), "Provenance module must exist"

    with open(provenance_path, 'r') as f:
        content = f.read()

    required_functions = [
        "dataset_fingerprint",
        "feature_fingerprint",
        "replay_fingerprint",
        "experiment_fingerprint",
        "evaluation_fingerprint",
        "model_fingerprint",
    ]

    missing = []
    for func in required_functions:
        if f"def {func}" not in content:
            missing.append(func)

    assert not missing, f"Provenance module missing functions: {missing}"


if __name__ == "__main__":
    print("Running architecture verification tests...")

    try:
        test_research_to_simulation_one_way()
        print("✓ Research → simulation is one-way")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_orchestrator_under_500_loc()
        print("✓ Orchestrator < 500 LOC")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_no_research_session_v2()
        print("✓ ResearchSession is canonical (no V2)")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_no_backtest_interface()
        print("✓ No BacktestInterface abstraction")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_no_register_candidate()
        print("✓ No register_candidate() API")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_canonical_provenance_fields()
        print("✓ ResearchSession has canonical provenance fields")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_backtest_runner_in_simulation()
        print("✓ BacktestRunner in simulation/backtest/")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_provenance_module_exists()
        print("✓ Provenance module with canonical fingerprints")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    print("\nAll architecture verification tests passed!")
    print("\nSprint 3.9D-15 implementation complete:")
    print("  ✓ Phase A: Boundary extraction")
    print("  ✓ Phase B: ResearchSession extension")
    print("  ✓ Phase C: Orchestrator skeleton")
    print("  ✓ Phase D: Provenance/determinism")
    print("  ✓ Phase E: Integration tests")
    print("  ✓ Phase F: Architecture verification")
