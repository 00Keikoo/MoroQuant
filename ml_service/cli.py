#!/usr/bin/env python3
"""CLI entry point for ML trading system."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml_service.cli.commands import cli

if __name__ == "__main__":
    cli()
