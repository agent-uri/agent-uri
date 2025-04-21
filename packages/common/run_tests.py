#!/usr/bin/env python
"""
Script to run tests for the agent_common package.
"""

import os
import sys
import pytest


def main():
    """Run the tests for the agent_common package."""
    # Ensure the current directory is in the Python path
    sys.path.insert(0, os.path.abspath("."))

    # Run pytest with the configuration from pytest.ini
    # You can pass additional arguments to pytest via command line
    args = ["-v"]  # Default to verbose output
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    result = pytest.main(args)
    sys.exit(result)


if __name__ == "__main__":
    main()
