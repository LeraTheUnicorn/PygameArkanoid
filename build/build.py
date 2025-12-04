#!/usr/bin/env python3
"""
Build script for Arkanoid Game
Handles packaging and preparation for distribution
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main build function"""
    project_root = Path(__file__).parent.parent

    print("Building Arkanoid Game...")
    print("=" * 50)

    # Check if venv is available
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable

    # Install dependencies
    print("\nInstalling dependencies...")
    if not run_command(f"{python_cmd} -m pip install -r requirements.txt", cwd=project_root):
        sys.exit(1)

    # Run tests
    print("\nRunning tests...")
    if not run_command(f"{python_cmd} -m pytest tests/ -v", cwd=project_root):
        print("Warning: Tests failed, but continuing with build...")

    # Build package
    print("\nBuilding package...")
    if not run_command(f"{python_cmd} -m pip install build", cwd=project_root):
        sys.exit(1)
    
    if not run_command(f"{python_cmd} -m build", cwd=project_root):
        sys.exit(1)

    # Check build output
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        files = list(dist_dir.glob("*"))
        if files:
            print(f"\nBuild successful! Created {len(files)} package(s):")
            for file in files:
                print(f"  - {file.name}")
        else:
            print("\nWarning: Build completed but no files found in dist/")
    else:
        print("\nError: Build failed - dist/ directory not created")

    print("\nBuild process completed!")

if __name__ == "__main__":
    main()