#!/usr/bin/env python
"""
Script to install the agent_common package in development mode.
"""

import os
import subprocess
import sys


def main():
    """Install the agent_common package in development mode."""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Install package in development mode
    cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd, cwd=current_dir)
        print("Successfully installed agent_common in development mode")
    except subprocess.CalledProcessError as e:
        print(f"Error installing package: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
