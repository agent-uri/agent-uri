#!/usr/bin/env python3
"""
Development environment setup for agent-server SDK.

This script installs all required dependencies, including the other
agent-uri packages in development mode.
"""

import os
import sys
import subprocess
from pathlib import Path


def install_package(package_path, editable=True):
    """Install a package in development mode."""
    cmd = [sys.executable, "-m", "pip", "install"]
    
    if editable:
        cmd.append("-e")
    
    cmd.append(str(package_path))
    
    print(f"Installing {package_path}...")
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"Error installing {package_path}", file=sys.stderr)
        return False
    
    return True


def install_requirements(package_path):
    """Install package requirements."""
    req_file = os.path.join(package_path, "requirements.txt")
    if os.path.exists(req_file):
        print(f"Installing requirements from {req_file}...")
        cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            print(f"Error installing requirements from {req_file}", 
                  file=sys.stderr)
            return False
    
    return True


def main():
    """Main installation function."""
    # Get the absolute path to the packages directory
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    packages_dir = script_dir.parent
    
    if not packages_dir.exists() or not packages_dir.is_dir():
        print(f"Packages directory not found: {packages_dir}", file=sys.stderr)
        return 1
    
    print(f"Installing packages from: {packages_dir}")
    print("=" * 50)
    
    # First install required external packages directly
    print("Installing external requirements...")
    external_reqs = [
        "pydantic>=1.8.2",
        "jsonschema>=4.0.0",
        "requests>=2.25.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "websockets>=10.0",
        "pytest>=6.0.0",
        "pytest-asyncio>=0.15.0",
        "pytest-cov>=2.12.0"
    ]
    
    subprocess.run([
        sys.executable, "-m", "pip", "install", *external_reqs
    ])
    print("-" * 50)
    
    # Order to install the packages in - critical for dependencies
    packages_order = [
        "uri-parser",   # Contains agent_uri module
        "descriptor",   # Contains agent_descriptor module
        "resolver",     # Contains agent_resolver module
        "transport",    # Contains agent_transport module
        "server"        # This package - contains agent_server module
    ]
    
    # Install each package in order
    for package_name in packages_order:
        package_path = packages_dir / package_name
        
        if not package_path.exists() or not package_path.is_dir():
            print(f"Package directory not found: {package_path}",
                  file=sys.stderr)
            continue
        
        # Try installing the package itself directly
        success = install_package(package_path)
        if not success:
            print(f"Failed to install {package_name}", file=sys.stderr)
            return 1
        
        print(f"Successfully installed {package_name}")
        print("-" * 50)
    
    print("All packages installed successfully!")
    print("You can now run tests with: python run_tests.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
