#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт автоматического создания MSI инсталлятора для игры Арканоид
Использует WiX Toolset для создания MSI файлов
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_wix_installation():
    """Проверяет наличие WiX Toolset"""
    try:
        # Проверяем candle.exe и light.exe
        result_candle = subprocess.run(['candle', '-?'], capture_output=True, text=True)
        result_light = subprocess.run(['light', '-?'], capture_output=True, text=True)
        return result_candle.returncode == 0 and result_light.returncode == 0
    except FileNotFoundError:
        return False


def create_wix_files():
    """Создает файлы WiX для MSI сборки"""

    # Создаем директории для WiX
    wix_dir = Path("wix_build")
    wix_dir.mkdir(exist_ok=True)

    # Содержимое Product.wxs
    product_wxs = '''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*"
           Name="Игра Арканоид"
           Language="1049"
           Version="1.6.1.0"
           Manufacturer="Разработчик"
           UpgradeCode="{12345678-1234-1234-1234-123456789012}">

    <Package InstallerVersion="200"
             Compressed="yes"
             InstallScope="perUser"
             Platform="x64" />

    <MediaTemplate EmbedCab="yes" />

    <Feature Id="ProductFeature"
             Title="Игра Арканоид"
             Level="1">
      <ComponentGroupRef Id="ProductComponents" />
      <ComponentRef Id="ApplicationShortcut" />
    </Feature>

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="LocalAppDataFolder">
        <Directory Id="GamesFolder" Name="Игры">
          <Directory Id="INSTALLFOLDER" Name="Арканоид" />
        </Directory>
      </Directory>

      <!-- Desktop directory -->
      <Directory Id="DesktopFolder" />
    </Directory>

    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="ProductComponents" Guid="*">
        <File Id="GameExecutable" Source="Arkanoid_v1.6.1.exe" KeyPath="yes">
          <Shortcut Id="GameStartMenuShortcut"
                    Directory="ProgramMenuDir"
                    Name="Арканоид"
                    Description="Игра Арканоид"
                    WorkingDirectory="INSTALLFOLDER" />
        </File>

        <File Id="SoundsFolder" Source="sounds" />
        <File Id="ImagesFolder" Source="images" />
        <File Id="HighscoresModule" Source="highscores.py" />
        <File Id="ReadmeFile" Source="README.md" />
      </Component>
    </DirectoryRef>

    <DirectoryRef Id="DesktopFolder">
      <Component Id="ApplicationShortcut" Guid="*">
        <Shortcut Id="DesktopApplicationShortcut"
                  Directory="DesktopFolder"
                  Name="Арканоид"
                  Description="Игра Арканоид"
                  WorkingDirectory="INSTALLFOLDER"
                  Target="[#GameExecutable]" />
        <RegistryValue Root="HKCU"
                       Key="Software\\Arkanoid"
                       Name="installed"
                       Type="integer"
                       Value="1"
                       KeyPath="yes" />
      </Component>
    </DirectoryRef>

    <DirectoryRef Id="ProgramMenuDir">
      <Directory Id="ProgramMenuDir" Name="Арканоид" />
    </DirectoryRef>

    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="CreateHighscoresFile" Guid="*">
        <CreateFolder />
        <util:PermissionEx xmlns:util="http://schemas.microsoft.com/wix/UtilExtension"
                           User="[LogonUser]"
                           GenericAll="yes" />
      </Component>
    </DirectoryRef>

    <ComponentGroup Id="ProductComponents">
      <ComponentRef Id="ProductComponents" />
      <ComponentRef Id="CreateHighscoresFile" />
    </ComponentGroup>

    <Property Id="ARPPRODUCTICON" Value="GameIcon.exe" />
    <Property Id="ARPHELPLINK" Value="https://github.com/developer/arkanoid" />
    <Property Id="ARPURLINFOABOUT" Value="https://github.com/developer/arkanoid" />

  </Product>
</Wix>'''

    # Записываем Product.wxs
    with open(wix_dir / "Product.wxs", "w", encoding="utf-8") as f:
        f.write(product_wxs)

    # Создаем icon.wxi для иконки
    icon_wxi = '''<?xml version="1.0" encoding="UTF-8"?>
<Include>
  <Icon Id="GameIcon.exe" SourceFile="icon.ico" />
</Include>'''

    with open(wix_dir / "icon.wxi", "w", encoding="utf-8") as f:
        f.write(icon_wxi)

    return wix_dir


def build_msi():
    """Собирает MSI файл с помощью WiX"""
    print("Создаю WiX файлы...")
    wix_dir = create_wix_files()

    print("Компилирую WiX исходники...")

    # Компилируем .wxs в .wixobj
    candle_cmd = ["candle", "-arch", "x64", str(wix_dir / "Product.wxs")]
    candle_result = subprocess.run(candle_cmd, capture_output=True, text=True)

    if candle_result.returncode != 0:
        print(f"Ошибка компиляции WiX: {candle_result.stderr}")
        return False

    # Компилируем .wixobj в .msi
    light_cmd = ["light", str(wix_dir / "Product.wixobj"), "-o", "Arkanoid_v1.6.1_Setup.msi"]
    light_result = subprocess.run(light_cmd, capture_output=True, text=True)

    if light_result.returncode != 0:
        print(f"Ошибка линковки MSI: {light_result.stderr}")
        return False

    print("MSI успешно создан!")
    return True


def main():
    print("=== Создание MSI инсталлятора для Arkanoid ===")

    if not check_wix_installation():
        print("WiX Toolset не найден!")
        print("Установите WiX с https://wixtoolset.org/releases/")
        print("Добавьте WiX в PATH или используйте абсолютные пути к candle.exe и light.exe")
        return False

    if build_msi():
        print("\nMSI инсталлятор готов к распространению!")
        print("Файл: Arkanoid_v1.6.1_Setup.msi")
        print("\nФункции инсталлятора:")
        print("- Установка в %LOCALAPPDATA%\\Games\\Arkanoid")
        print("- Создание ярлыка на рабочем столе")
        print("- Автоматическое создание папки для рекордов")
        print("- Правильная деинсталляция")
        return True
    else:
        print("\nОшибка создания MSI инсталлятора")
        return False


if __name__ == "__main__":
    main()