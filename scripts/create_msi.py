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

# Определяем корень проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_wix_installation():
    """Проверяет наличие WiX Toolset"""
    try:
        # Проверяем wix.exe
        result_wix = subprocess.run(
            ["wix", "--version"], capture_output=True, text=True
        )
        return result_wix.returncode == 0
    except FileNotFoundError:
        return False


def get_current_version():
    """Получает текущую версию из PyGameBall.py"""
    try:
        with open(
            os.path.join(project_root, "PyGameBall.py"), "r", encoding="utf-8"
        ) as f:
            for line in f:
                if line.startswith("VERSION ="):
                    return line.split('"')[1]
    except:
        return "1.6.1"
    return "1.6.1"


def create_wix_files():
    """Создает файлы WiX для MSI сборки"""

    # Создаем директории для WiX
    build_dir = os.path.join(project_root, "build")
    os.makedirs(build_dir, exist_ok=True)
    wix_dir = Path(os.path.join(build_dir, "wix"))
    wix_dir.mkdir(exist_ok=True)

    # Получаем текущую версию
    version = get_current_version()
    
    # Ищем exe файл в разных местах
    exe_path = None
    possible_paths = [
        os.path.join(project_root, f"Arkanoid_v{version}.exe"),  # корень проекта
        os.path.join(project_root, "FINAL_RELEASE", f"Arkanoid_v{version}.exe"),  # FINAL_RELEASE
        os.path.join(project_root, "dist", f"Arkanoid_v{version}.exe"),  # dist (PyInstaller)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            exe_path = path
            break
    
    if not exe_path:
        print(f"Ошибка: exe файл Arkanoid_v{version}.exe не найден!")
        return None

    # Содержимое Product.wxs
    product_wxs = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"
     xmlns:util="http://wixtoolset.org/schemas/v4/wxs/util">
  <Package Name="Игра Арканоид"
           Language="1049"
           Version="{version}.0"
           Manufacturer="Разработчик"
           UpgradeCode="12345678-1234-1234-1234-123456789012"
           Codepage="65001">

     <MediaTemplate EmbedCab="yes" />

     <Feature Id="ProductFeature"
              Title="Игра Арканоид"
              Level="1">
       <ComponentGroupRef Id="ProductComponents" />
       <ComponentRef Id="ApplicationShortcut" />
     </Feature>

     <StandardDirectory Id="LocalAppDataFolder">
       <Directory Id="GamesFolder" Name="Игры">
         <Directory Id="INSTALLFOLDER" Name="Арканоид">
           <Component Id="ProductComponents" Guid="11111111-1111-1111-1111-111111111111">
             <File Id="GameExecutable" Source="{exe_path.replace(chr(92), chr(92)*2)}" KeyPath="yes">
               <Shortcut Id="GameStartMenuShortcut"
                         Directory="ProgramMenuDir"
                         Name="Арканоид"
                         Description="Игра Арканоид"
                         WorkingDirectory="INSTALLFOLDER"
                         Icon="GameIcon.exe" />
             </File>
             <File Id="HighscoresData" Source="{os.path.join(project_root, 'resources', 'highscores.json').replace(chr(92), chr(92)*2)}" />
             <File Id="SettingsData" Source="{os.path.join(project_root, 'resources', 'settings.json').replace(chr(92), chr(92)*2)}" />
           </Component>

           <Component Id="CreateHighscoresFile" Guid="22222222-2222-2222-2222-222222222222">
             <CreateFolder />
           </Component>
         </Directory>
       </Directory>
     </StandardDirectory>

     <StandardDirectory Id="DesktopFolder">
       <Component Id="ApplicationShortcut" Guid="33333333-3333-3333-3333-333333333333">
         <Shortcut Id="DesktopApplicationShortcut"
                   Directory="DesktopFolder"
                   Name="Арканоид"
                   Description="Игра Арканоид"
                   WorkingDirectory="INSTALLFOLDER"
                   Target="[#GameExecutable]"
                   Icon="GameIcon.exe" />
         <RegistryValue Root="HKCU"
                        Key="Software\\Arkanoid"
                        Name="installed"
                        Type="integer"
                        Value="1"
                        KeyPath="yes" />
       </Component>
     </StandardDirectory>

     <StandardDirectory Id="ProgramMenuFolder">
       <Directory Id="ProgramMenuDir" Name="Арканоид" />
     </StandardDirectory>

     <ComponentGroup Id="ProductComponents">
       <ComponentRef Id="ProductComponents" />
       <ComponentRef Id="CreateHighscoresFile" />
     </ComponentGroup>

     <Property Id="ARPPRODUCTICON" Value="GameIcon.exe" />
     <Property Id="ARPHELPLINK" Value="https://github.com/developer/arkanoid" />
     <Property Id="ARPURLINFOABOUT" Value="https://github.com/developer/arkanoid" />

   </Package>
</Wix>"""

    # Записываем Product.wxs
    with open(wix_dir / "Product.wxs", "w", encoding="utf-8") as f:
        f.write(product_wxs)

    # Создаем icon.wxi для иконки
    icon_wxi = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Fragment>
    <Icon Id="GameIcon.exe" SourceFile="{os.path.join(project_root, 'resources', 'icon.ico').replace(chr(92), chr(92)*2)}" />
  </Fragment>
</Wix>"""

    with open(wix_dir / "icon.wxi", "w", encoding="utf-8") as f:
        f.write(icon_wxi)

    return wix_dir


def build_msi():
    """Собирает MSI файл с помощью WiX"""
    version = get_current_version()
    build_dir = os.path.join(project_root, "build")
    os.makedirs(build_dir, exist_ok=True)
    
    # Проверяем наличие exe файла
    exe_path = os.path.join(project_root, f"Arkanoid_v{version}.exe")
    final_release_path = os.path.join(project_root, "FINAL_RELEASE", f"Arkanoid_v{version}.exe")
    
    if not os.path.exists(exe_path) and not os.path.exists(final_release_path):
        print("Exe файл не найден. Создаю exe файл...")
        try:
            # Импортируем и запускаем скрипт создания exe
            sys.path.append(os.path.join(project_root, "scripts"))
            from build_spec import get_version as build_get_version, main as build_main
            
            # Создаем exe файл
            subprocess.run([sys.executable, os.path.join(project_root, "scripts", "build_spec.py")], 
                         check=True, cwd=project_root)
            print("Exe файл создан успешно!")
        except Exception as e:
            print(f"Ошибка создания exe файла: {e}")
            return False
    
    print("Создаю WiX файлы...")
    wix_dir = create_wix_files()

    print("Компилирую WiX исходники...")

    # Собираем MSI с помощью wix.exe
    msi_name = os.path.join(build_dir, f"Arkanoid_v{version}_Setup.msi")
    wix_cmd = [
        "wix",
        "build",
        "-arch",
        "x64",
        "-ext",
        "WixToolset.Util.wixext",
        "-o",
        msi_name,
        str(wix_dir / "Product.wxs"),
        str(wix_dir / "icon.wxi"),
    ]
    wix_result = subprocess.run(wix_cmd, capture_output=True, text=True)

    if wix_result.returncode != 0:
        print(f"Ошибка сборки MSI: {wix_result.stderr}")
        return False

    print(f"MSI успешно создан: {msi_name}")
    return True


def main():
    print("=== Создание MSI инсталлятора для Arkanoid ===")

    if not check_wix_installation():
        print("WiX Toolset не найден!")
        print(
            "Установите WiX v6.0 или новее с https://github.com/wixtoolset/wix/releases/"
        )
        print("Добавьте WiX в PATH: C:\\Program Files\\WiX Toolset v6.0\\bin")
        return False

    if build_msi():
        print("\nMSI инсталлятор готов к распространению!")
        print(f"Файл: Arkanoid_v{get_current_version()}_Setup.msi")
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
