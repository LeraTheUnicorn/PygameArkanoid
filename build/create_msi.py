#!/usr/bin/env python3
"""
Script to create MSI installer for Arkanoid Game using WiX Toolset
Creates a proper Windows installer that installs to a dedicated folder
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

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

def create_wxs_file(project_root, version="2.1.5"):
    """Create WiX source file"""
    # Check if required files exist
    required_files = [
        "PyGameBall.py",
        "highscores.py",
        "settings.py",
        "resources/data/highscores.json",
        "resources/data/settings.json",
        "ai/models/ai_model.json",
        "ai/ai_player.py",
        "ai/game_state.py",
        "ai/learning_system.py",
        "ai/performance_logger.py",
        "ai/position_optimizer.py",
        "ai/trajectory_predictor.py",
        "ai/__init__.py",
        "README.MD",
        "docs/changelog.md",
        "docs/LICENSE.txt"
    ]

    for file in required_files:
        if not (project_root / file).exists():
            print(f"❌ Required file not found: {file}")
            return None

    print("✓ All required files found")
    wxs_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="Arkanoid Game" Language="1049" Version="{version}"
           Manufacturer="Developer" UpgradeCode="12345678-1234-1234-1234-123456789012">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />

    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
    <MediaTemplate />

    <Feature Id="ProductFeature" Title="Arkanoid Game" Level="1">
      <ComponentGroupRef Id="ProductComponents" />
    </Feature>

    <Property Id="WIXUI_INSTALLDIR" Value="INSTALLFOLDER" />
    <UIRef Id="WixUI_InstallDir" />

    <WixVariable Id="WixUILicenseRtf" Value="docs/LICENSE.txt" />
  </Product>

  <Fragment>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="Arkanoid">
          <Directory Id="RESOURCES" Name="resources" />
          <Directory Id="AI" Name="ai" />
          <Directory Id="DOCS" Name="docs" />
        </Directory>
      </Directory>
    </Directory>
  </Fragment>

  <Fragment>
    <ComponentGroup Id="ProductComponents">
      <!-- Main executable -->
      <Component Id="MainExecutable" Directory="INSTALLFOLDER">
        <File Id="PyGameBall.py" Source="PyGameBall.py" KeyPath="yes" />
      </Component>

      <!-- Python files -->
      <Component Id="Highscores" Directory="INSTALLFOLDER">
        <File Id="highscores.py" Source="highscores.py" />
      </Component>
      <Component Id="Settings" Directory="INSTALLFOLDER">
        <File Id="settings.py" Source="settings.py" />
      </Component>

      <!-- AI files -->
      <Component Id="AIPlayer" Directory="AI">
        <File Id="ai_player.py" Source="ai/ai_player.py" />
      </Component>
      <Component Id="AIGameState" Directory="AI">
        <File Id="game_state.py" Source="ai/game_state.py" />
      </Component>
      <Component Id="AILearning" Directory="AI">
        <File Id="learning_system.py" Source="ai/learning_system.py" />
      </Component>
      <Component Id="AILogger" Directory="AI">
        <File Id="performance_logger.py" Source="ai/performance_logger.py" />
      </Component>
      <Component Id="AIOptimizer" Directory="AI">
        <File Id="position_optimizer.py" Source="ai/position_optimizer.py" />
      </Component>
      <Component Id="AITrajectory" Directory="AI">
        <File Id="trajectory_predictor.py" Source="ai/trajectory_predictor.py" />
      </Component>
      <Component Id="AIInit" Directory="AI">
        <File Id="__init__.py" Source="ai/__init__.py" />
      </Component>

      <!-- Resources -->
      <Component Id="ResourcesData" Directory="RESOURCES">
        <File Id="highscores.json" Source="resources/data/highscores.json" />
        <File Id="settings.json" Source="resources/data/settings.json" />
      </Component>

      <!-- AI components -->
      <Component Id="AIModel" Directory="AI">
        <File Id="ai_model.json" Source="ai/models/ai_model.json" />
      </Component>

      <!-- Documentation -->
      <Component Id="Readme" Directory="DOCS">
        <File Id="README.MD" Source="README.MD" />
      </Component>
      <Component Id="Changelog" Directory="DOCS">
        <File Id="changelog.md" Source="docs/changelog.md" />
      </Component>
      <Component Id="License" Directory="DOCS">
        <File Id="LICENSE.txt" Source="docs/LICENSE.txt" />
      </Component>
    </ComponentGroup>
  </Fragment>
</Wix>'''

    wxs_path = project_root / "Arkanoid.wxs"
    with open(wxs_path, 'w', encoding='utf-8') as f:
        f.write(wxs_content)

    return wxs_path

def main():
    """Create MSI installer"""
    project_root = Path(__file__).parent.parent

    print("Creating MSI installer...")
    print("=" * 50)

    # Check if WiX is available
    if not run_command("candle.exe -? >nul 2>&1", cwd=project_root):
        print("❌ WiX Toolset is not installed or not in PATH.")
        print("Please install WiX Toolset v3.11 or later from https://wixtoolset.org/")
        sys.exit(1)

    # Create WiX source file
    wxs_file = create_wxs_file(project_root)
    if wxs_file is None:
        print("❌ Failed to create WiX source file - missing required files")
        sys.exit(1)
    print(f"✓ Created WiX source file: {wxs_file}")

    # Compile WiX source
    wixobj_file = wxs_file.with_suffix('.wixobj')
    if not run_command(f'candle.exe "{wxs_file}"', cwd=project_root):
        print("❌ Failed to compile WiX source")
        sys.exit(1)

    # Link MSI
    msi_file = project_root / f"Arkanoid_v{datetime.now().strftime('%Y%m%d')}.msi"
    if run_command(f'light.exe "{wixobj_file}" -out "{msi_file}"', cwd=project_root):
        if msi_file.exists():
            size = msi_file.stat().st_size / (1024 * 1024)
            print(f"📁 Size: {size:.2f} MB")
            print(f"📁 Location: {msi_file}")
            print("\n✅ MSI installer created successfully!")
        else:
            print("❌ MSI file not found")
            sys.exit(1)
    else:
        print("❌ Failed to create MSI")
        sys.exit(1)

    # Cleanup
    try:
        wxs_file.unlink()
        wixobj_file.unlink()
        print("✓ Cleaned up temporary files")
    except:
        pass

if __name__ == "__main__":
    main()