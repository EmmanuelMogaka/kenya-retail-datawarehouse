"""conftest.py - setup that pytest reads automatically before running the tests.

Our code lives in the src folder, so we tell Python where to find it.
Without this, 'from db import ...' inside the tests would fail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))