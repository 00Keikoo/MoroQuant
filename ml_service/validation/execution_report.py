"""Validation Report Generator.

Formats and presents validation results for human and machine consumption.
"""

from dataclasses import dataclass, field
from typing import List

from .execution_rules import ValidationFailure


@dataclass
class ValidationReport:
    """Complete validation report for a set of positions."""

    passed: int = 0
    failed: int = 0
    warnings: int = 0
    failures: List[ValidationFailure] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        total = self.passed + self.failed
        if total == 0:
            return 100.0
        return (self.passed / total) * 100.0

    def add_failure(self, failure: ValidationFailure) -> None:
        """Add a validation failure to the report."""
        self.failures.append(failure)
        if failure.severity == "ERROR":
            self.failed += 1
        elif failure.severity == "WARNING":
            self.warnings += 1

    def add_pass(self) -> None:
        """Record a successful validation."""
        self.passed += 1

    def to_dict(self):
        """Convert report to dictionary format."""
        return {
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "success_rate": round(self.success_rate, 2),
            "failures": [
                {
                    "position_id": f.position_id,
                    "rule_violated": f.rule_violated,
                    "expected": f.expected,
                    "actual": f.actual,
                    "severity": f.severity,
                }
                for f in self.failures
            ],
        }

    def print_summary(self) -> None:
        """Print human-readable summary to console."""
        print("\n" + "=" * 80)
        print("EXECUTION VALIDATION REPORT")
        print("=" * 80)
        print(f"Passed:       {self.passed}")
        print(f"Failed:       {self.failed}")
        print(f"Warnings:     {self.warnings}")
        print(f"Success Rate: {self.success_rate:.2f}%")
        print("=" * 80)

        if self.failures:
            print("\nFAILURES:")
            print("-" * 80)

            errors = [f for f in self.failures if f.severity == "ERROR"]
            warnings = [f for f in self.failures if f.severity == "WARNING"]

            if errors:
                print(f"\nERRORS ({len(errors)}):")
                for f in errors:
                    print(f"\n  Position ID: {f.position_id}")
                    print(f"  Rule:        {f.rule_violated}")
                    print(f"  Expected:    {f.expected}")
                    print(f"  Actual:      {f.actual}")

            if warnings:
                print(f"\nWARNINGS ({len(warnings)}):")
                for f in warnings:
                    print(f"\n  Position ID: {f.position_id}")
                    print(f"  Rule:        {f.rule_violated}")
                    print(f"  Expected:    {f.expected}")
                    print(f"  Actual:      {f.actual}")

        print("\n" + "=" * 80)
