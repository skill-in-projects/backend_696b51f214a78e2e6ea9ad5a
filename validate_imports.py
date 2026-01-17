#!/usr/bin/env python3
"""Import validation script for Python backend
This script validates that all controllers can be imported without errors.
Run during build phase to catch import-time errors before deployment.
"""
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import all controllers that should be available
try:
    from Controllers.TestController import router as test_router
    print("✓ Successfully imported Controllers.TestController")
except Exception as e:
    print(f"✗ Failed to import Controllers.TestController: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✓ All imports validated successfully")
sys.exit(0)
