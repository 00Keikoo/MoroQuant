"""DEPRECATED: Use ml_service.lab.experiments instead.

This module is a compatibility wrapper. The Experiment Registry now lives
exclusively in the Lab subsystem per ADR-017.
"""

from ml_service.lab.experiments import ExperimentContract

__all__ = ['ExperimentContract']
