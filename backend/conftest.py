"""
Pytest configuration file for wanLLMDB backend tests.

This file is automatically loaded by pytest and configures the test environment.
"""

import sys
from pathlib import Path

# Add the backend directory to Python path so 'app' module can be imported
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
