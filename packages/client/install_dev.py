#!/usr/bin/env python3
"""
Development environment setup for agent-client SDK.

This script installs all required dependencies, including the other
agent-uri packages in development mode.
"""

import os
import sys
import subprocess
from pathlib import Path

# Package installation order matters due to dependencies
PACKAGES = [
    "uri-parser",
    "descriptor", 
    "resolver",
    "transport",
    "client"
]

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
    
    # Install each package in order
    for package_name in PACKAGES:
        package_path = packages_dir / package_name
        
        if not package_path.exists() or not package_path.is_dir():
            print(f"Package directory not found: {package_path}", file=sys.stderr)
            continue
        
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
