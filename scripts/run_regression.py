#!/usr/bin/env python3
"""
Simplified script to run regression tests
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework.main import app

if __name__ == "__main__":
    app()