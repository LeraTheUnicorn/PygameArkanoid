#!/usr/bin/env python3
"""
Script to create executables for Arkanoid Game using PyInstaller
Creates platform-specific executables without MSI installers
"""

import subprocess
import sys
import os
from pathlib import Path
import platform

def run_command(command, cwd=None):
    """Run a shell command"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[OK] {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Create executables for current platform"""
    project_root = Path(__file__).parent.parent
    current_platform = platform.system().lower()

    print(f"Creating executables for {current_platform}...")
    print("=" * 50)

    # Check if PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Installing...")
        if not run_command("pip install pyinstaller", cwd=project_root):
            print("Failed to install PyInstaller")
            sys.exit(1)

    # Determine output name based on platform
    if current_platform == "windows":
        exe_name = "Arkanoid.exe"
    elif current_platform == "linux":
        exe_name = "Arkanoid"
    elif current_platform == "darwin":  # macOS
        exe_name = "Arkanoid"
    else:
        exe_name = "Arkanoid"

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",  # Single executable file
        "--windowed",  # No console window
        "--name", exe_name,
        "--add-data", f"resources{os.pathsep}resources",  # Include resources
        "--add-data", f"ai{os.pathsep}ai",  # Include AI modules
        "--add-data", f"src{os.pathsep}src",  # Include src modules
        "src/game/PyGameBall.py"
    ]

    print(f"\nBuilding executable: {exe_name}")
    if run_command(" ".join(cmd), cwd=project_root):
        # Check if executable was created
        dist_dir = project_root / "dist"
        exe_path = dist_dir / exe_name
        if exe_path.exists():
            size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
            print(f"Size: {size:.2f} MB")
            print(f"Location: {exe_path}")
        else:
            print("Warning: Executable not found in dist/")

        print("\nExecutable creation completed!")
    else:
        print("\nExecutable creation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()