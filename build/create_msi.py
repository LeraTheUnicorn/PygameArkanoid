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
        if e.stderr:
            print(f"Error: {e.stderr}")
        else:
            print(f"Stdout: {e.stdout}")
        return False

def create_wxs_file(project_root, version="2.1.5"):
    """Create WiX source file"""
    # Check if required files exist
    required_files = [
        "dist/Arkanoid.exe"
   ]

    for file in required_files:
        if not (project_root / file).exists():
            print(f"[ERROR] Required file not found: {file}")
            return None

    print("[OK] All required files found")
    wxs_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="Arkanoid Game" Language="1049" Version="{version}"
           Manufacturer="Developer" UpgradeCode="12345678-1234-1234-1234-123456789012">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />

    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
    <MediaTemplate EmbedCab="yes" />

    <Feature Id="ProductFeature" Title="Arkanoid Game" Level="1">
      <ComponentGroupRef Id="ProductComponents" />
    </Feature>
  </Product>

  <Fragment>
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="Arkanoid">
          <Directory Id="ProgramMenuFolder" Name="Start Menu" />
          <Directory Id="DesktopFolder" Name="Desktop" />
       </Directory>
      </Directory>
    </Directory>
  </Fragment>

  <Fragment>
    <ComponentGroup Id="ProductComponents">
      <!-- Main executable -->
      <Component Id="MainExecutable" Directory="INSTALLFOLDER">
        <File Id="Arkanoid.exe" Source="dist/Arkanoid.exe" KeyPath="yes" />
        <Shortcut Id="StartMenuShortcut" Directory="ProgramMenuFolder" Name="Arkanoid Game" WorkingDirectory="INSTALLFOLDER" Advertise="yes" />
        <Shortcut Id="DesktopShortcut" Directory="DesktopFolder" Name="Arkanoid Game" WorkingDirectory="INSTALLFOLDER" Advertise="yes" />
       </Component>



      <!-- AI files -->

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
        print("[ERROR] WiX Toolset is not installed or not in PATH.")
        print("Please install WiX Toolset v3.11 or later from https://wixtoolset.org/")
        sys.exit(1)

    # Create WiX source file
    wxs_file = create_wxs_file(project_root)
    if wxs_file is None:
        print("[ERROR] Failed to create WiX source file - missing required files")
        sys.exit(1)
    print(f"[OK] Created WiX source file: {wxs_file}")

    # Compile WiX source
    wixobj_file = wxs_file.with_suffix('.wixobj')
    if not run_command(f'candle.exe "{wxs_file}"', cwd=project_root):
        print("[ERROR] Failed to compile WiX source")
        sys.exit(1)

    # Link MSI
    msi_file = project_root / f"Arkanoid_v{datetime.now().strftime('%Y%m%d')}.msi"
    if run_command(f'light.exe -b . "{wixobj_file}" -out "{msi_file}"', cwd=project_root):
        if msi_file.exists():
            size = msi_file.stat().st_size / (1024 * 1024)
            print(f"Size: {size:.2f} MB")
            print(f"Location: {msi_file}")
            print("\n[SUCCESS] MSI installer created successfully!")
        else:
            print("[ERROR] MSI file not found")
            sys.exit(1)
    else:
        print("[ERROR] Failed to create MSI")
        sys.exit(1)

    # Cleanup
    try:
        wxs_file.unlink()
        wixobj_file.unlink()
        print("[OK] Cleaned up temporary files")
    except:
        pass

if __name__ == "__main__":
    main()