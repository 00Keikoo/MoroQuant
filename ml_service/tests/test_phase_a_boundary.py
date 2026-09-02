"""
Architecture Boundary Test: Research → Execution

Verifies that research module does not import execution infrastructure.
Following ADR-024 and Sprint 3.9D-15 design constraints.
"""

import ast
import os
from pathlib import Path


FORBIDDEN_IMPORTS_IN_RESEARCH = [
    "ml_service.portfolio.service",
    "ml_service.portfolio.ledger",
    "ml_service.portfolio.position",
    "ml_service.portfolio.equity",
    "ml_service.portfolio.margin",
    "ml_service.simulation.execution.simulator",
    "ml_service.simulation.execution.matching_engine",
    "ml_service.simulation.execution.slippage",
    "ml_service.simulation.execution.commission",
    "ml_service.simulation.execution.latency",
    "ml_service.simulation.execution.liquidity",
    "ml_service.simulation.integration.execution_adapter",
    "ml_service.simulation.integration.portfolio_adapter",
    "ml_service.simulation.integration.simulation_portfolio_runner",
]


def extract_imports_from_file(file_path: Path) -> list:
    """Extract all import statements from a Python file."""
    with open(file_path, 'r') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def test_research_does_not_import_execution_infrastructure():
    """
    Verify research module does not import execution infrastructure.

    Research must consume execution outcomes, not construct execution services.
    """
    research_dir = Path("ml_service/research")
    violations = []

    for py_file in research_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        imports = extract_imports_from_file(py_file)

        for forbidden in FORBIDDEN_IMPORTS_IN_RESEARCH:
            if forbidden in imports:
                violations.append(f"{py_file}: imports {forbidden}")

    assert not violations, (
        f"Research module imports execution infrastructure:\n" +
        "\n".join(violations)
    )


def test_research_can_import_backtest_runner():
    """
    Verify research can import BacktestRunner from simulation.backtest.

    BacktestRunner is the boundary interface research uses to consume
    execution outcomes.
    """
    research_orchestrator = Path("ml_service/research/backtest_workflow/orchestrator.py")

    imports = extract_imports_from_file(research_orchestrator)

    assert "ml_service.simulation.backtest.runner" in imports, (
        "Research orchestrator must import BacktestRunner from simulation.backtest"
    )


def test_backtest_runner_owns_execution_dependencies():
    """
    Verify BacktestRunner owns execution infrastructure dependencies.

    BacktestRunner in simulation.backtest can import execution services.
    """
    backtest_runner = Path("ml_service/simulation/backtest/runner.py")

    imports = extract_imports_from_file(backtest_runner)

    expected_execution_imports = [
        "ml_service.portfolio.service",
        "ml_service.simulation.execution.simulator",
        "ml_service.simulation.integration.simulation_portfolio_runner",
    ]

    for expected in expected_execution_imports:
        assert expected in imports, (
            f"BacktestRunner must import {expected}"
        )


if __name__ == "__main__":
    print("Running architecture boundary tests...")

    try:
        test_research_does_not_import_execution_infrastructure()
        print("✓ Research does not import execution infrastructure")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_research_can_import_backtest_runner()
        print("✓ Research can import BacktestRunner")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    try:
        test_backtest_runner_owns_execution_dependencies()
        print("✓ BacktestRunner owns execution dependencies")
    except AssertionError as e:
        print(f"✗ {e}")
        exit(1)

    print("\nAll architecture boundary tests passed!")
