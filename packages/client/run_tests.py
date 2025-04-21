#!/usr/bin/env python3
"""
Test runner for the agent-client SDK.

This script provides a convenient way to run tests for the agent-client SDK.
It supports running all tests, specific test modules, or individual test methods,
as well as generating code coverage reports.
"""

import os
import sys
import argparse
import subprocess


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for agent-client SDK")
    parser.add_argument(
        "-a", "--all", action="store_true",
        help="Run all tests"
    )
    parser.add_argument(
        "-m", "--module", type=str, default=None,
        help="Run tests in a specific module (e.g., test_auth)"
    )
    parser.add_argument(
        "-t", "--test", type=str, default=None,
        help="Run a specific test method (e.g., test_auth.py::TestAuthProvider::test_base_methods)"
    )
    parser.add_argument(
        "-c", "--coverage", action="store_true",
        help="Generate code coverage report"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Increase verbosity"
    )
    return parser.parse_args()


def run_tests(args):
    """Run tests based on command line arguments."""
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test target
    if args.all or (not args.module and not args.test):
        # Run all tests by default
        cmd.append("agent_client/tests/")
    elif args.test:
        cmd.append(args.test)
    elif args.module:
        cmd.append(f"agent_client/tests/{args.module}.py")
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=agent_client",
            "--cov-report=term",
            "--cov-report=html:coverage_html"
        ])
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run the command
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    # Make sure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Parse arguments and run tests
    args = parse_args()
    sys.exit(run_tests(args))
