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

    print("🏗️  Building Arkanoid Game...")
    print("=" * 50)

    # Check if poetry is available
    if not run_command("poetry --version"):
        print("❌ Poetry is not installed. Please install Poetry first.")
        sys.exit(1)

    # Install dependencies
    print("\n📦 Installing dependencies...")
    if not run_command("poetry install --no-dev", cwd=project_root):
        sys.exit(1)

    # Run tests
    print("\n🧪 Running tests...")
    if not run_command("poetry run pytest tests/ -v", cwd=project_root):
        print("⚠️  Tests failed, but continuing with build...")

    # Build package
    print("\n📦 Building package...")
    if not run_command("poetry build", cwd=project_root):
        sys.exit(1)

    # Check build output
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        files = list(dist_dir.glob("*"))
        if files:
            print(f"\n✅ Build successful! Created {len(files)} package(s):")
            for file in files:
                print(f"  - {file.name}")
        else:
            print("\n⚠️  Build completed but no files found in dist/")
    else:
        print("\n❌ Build failed - dist/ directory not created")

    print("\n🎉 Build process completed!")

if __name__ == "__main__":
    main()