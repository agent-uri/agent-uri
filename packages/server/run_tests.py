#!/usr/bin/env python3
"""
Run tests for the agent-server package.

This script runs the test suite for the agent-server package using pytest.
"""

import os
import sys
import subprocess


def run_tests():
    """Run the test suite."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Define pytest command using python -m
    cmd = [
        sys.executable, 
        "-m", 
        "pytest", 
        "agent_server/tests", 
        "-v"
    ]
    
    # Add coverage options if pytest-cov is available
    try:
        import pytest_cov
        cmd.extend(["--cov=agent_server", "--cov-report=term-missing"])
    except ImportError:
        print("pytest-cov not found, skipping coverage report")
    
    # Add any command-line arguments passed to this script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    # Run pytest
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    # Return pytest's exit code
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
