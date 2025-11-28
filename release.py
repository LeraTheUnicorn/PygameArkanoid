#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт автоматического релиза игры Арканоид
Обновляет версию во всех файлах и создает исполняемый файл
"""

import re
import os
import sys
import shutil
from datetime import datetime
import subprocess

def increment_version(version):
    """Увеличивает версию на минорную версию"""
    parts = version.split('.')
    if len(parts) >= 3:
        major, minor, patch = parts[0], parts[1], parts[2]
        new_patch = str(int(patch) + 1)
        return f"{major}.{minor}.{new_patch}"
    return version

def update_version_in_file(file_path, pattern, new_version):
    """Обновляет версию в файле по регулярному выражению"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated_content = re.sub(pattern, f'"{new_version}"', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"Обновлена версия в {file_path}")
        return True
    except Exception as e:
        print(f"Ошибка при обновлении {file_path}: {e}")
        return False

def update_readme_version(file_path, new_version):
    """Обновляет версию в README.md"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Обновляем бейдж версии
        content = re.sub(
            r'!\[Версия\]\(https://img\.shields\.io/badge/version-\d+\.\d+\.\d+-blue\.svg\)',
            f'![Версия](https://img.shields.io/badge/version-{new_version}-blue.svg)',
            content
        )
        
        # Обновляем текст "Текущая версия"
        content = re.sub(
            r'### Текущая версия: \d+\.\d+\.\d+',
            f'### Текущая версия: {new_version}',
            content
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Обновлена версия в README.md")
        return True
    except Exception as e:
        print(f"Ошибка при обновлении README.md: {e}")
        return False

def create_changelog_entry(version):
    """Создает запись в changelog"""
    try:
        with open('changelog.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        new_entry = f"""# История изменений

## [{version}] - {date_str}

### Новые функции и улучшения

- Релиз исполняемой версии игры
- Автоматическая сборка с PyInstaller
- Включены все зависимости и ресурсы

### Технические улучшения

- Оптимизирована сборка исполняемого файла
- Улучшена переносимость игры
- Добавлен автоматизированный процесс релиза

"""

        # Вставляем новую запись после заголовка
        content = content.replace('# История изменений\n\n', new_entry)
        
        with open('changelog.md', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Создана запись в changelog для версии {version}")
        return True
    except Exception as e:
        print(f"Ошибка при создании changelog записи: {e}")
        return False

def get_current_version():
    """Получает текущую версию из PyGameBall.py"""
    try:
        with open('PyGameBall.py', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VERSION ='):
                    return line.split('"')[1]
    except:
        return "1.6.1"
    return "1.6.1"

def build_executable():
    """Собирает исполняемый файл с помощью PyInstaller"""
    try:
        print("Начинаю сборку исполняемого файла...")
        
        # Запускаем PyInstaller
        cmd = [
            'pyinstaller',
            '--onefile',
            '--windowed',
            '--name', 'Arkanoid_v' + get_current_version(),
            '--add-data', 'sounds;sounds',
            '--add-data', 'images;images',
            '--hidden-import', 'pygame',
            '--hidden-import', 'numpy',
            '--exclude-module', 'tkinter',
            '--exclude-module', 'matplotlib',
            '--clean',
            'PyGameBall.py'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Сборка завершена успешно!")
            
            # Копируем в корневую папку
            exe_name = f"Arkanoid_v{get_current_version()}.exe"
            dist_path = os.path.join('dist', exe_name)
            root_path = exe_name
            
            if os.path.exists(dist_path):
                shutil.copy2(dist_path, root_path)
                print(f"Исполняемый файл скопирован в корневую папку: {exe_name}")
                return True
            else:
                print(f"Файл {dist_path} не найден")
                return False
        else:
            print(f"Ошибка сборки: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Ошибка при сборке: {e}")
        return False

def build_installer():
    """Создает инсталлятор с помощью Inno Setup"""
    try:
        print("Создаю инсталлятор...")
        
        # Проверяем наличие Inno Setup
        result = subprocess.run(['where', 'iscc.exe'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Inno Setup не найден. Скачайте с https://jrsoftware.org/isinfo.php")
            return False
        
        # Создаем иконку
        print("Создаю иконку...")
        icon_result = subprocess.run(['python', 'create_icon.py'], capture_output=True, text=True)
        if icon_result.returncode != 0:
            print("Предупреждение: не удалось создать иконку")
        
        # Компилируем инсталлятор
        installer_result = subprocess.run(['iscc', 'create_installer.iss'], capture_output=True, text=True)
        if installer_result.returncode == 0:
            print("Инсталлятор создан успешно!")
            return True
        else:
            print(f"Ошибка создания инсталлятора: {installer_result.stderr}")
            return False
            
    except Exception as e:
        print(f"Ошибка при создании инсталлятора: {e}")
        return False

def build_msi():
    """Создает MSI инсталлятор с помощью WiX"""
    try:
        print("Создаю MSI инсталлятор...")

        # Проверяем наличие WiX
        result = subprocess.run(['wix', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("WiX Toolset не найден. Установите с https://github.com/wixtoolset/wix/releases/")
            return False

        # Импортируем и запускаем скрипт создания MSI
        import create_msi
        return create_msi.build_msi()

    except Exception as e:
        print(f"Ошибка при создании MSI: {e}")
        return False

def main():
    """Основная функция релиза"""
    print("=== Автоматический релиз игры Арканоид ===")
    
    # Получаем текущую версию
    current_version = get_current_version()
    print(f"Текущая версия: {current_version}")
    
    # Увеличиваем версию
    new_version = increment_version(current_version)
    print(f"Новая версия: {new_version}")
    
    # Выбор типа инсталлятора
    print("\nВыберите тип инсталлятора:")
    print("1. Только исполняемый файл (Arkanoid_vX.X.X.exe)")
    print("2. EXE инсталлятор (Arkanoid_vX.X.X_Setup.exe) - требует Inno Setup")
    print("3. MSI инсталлятор (Arkanoid_vX.X.X_Setup.msi) - требует WiX Toolset")
    print("4. Все типы")
    
    installer_choice = input("Выберите опцию (1-4): ").strip()
    
    # Подтверждение
    confirm = input(f"Продолжить релиз версии {new_version}? (y/N): ")
    if confirm.lower() != 'y':
        print("Релиз отменен.")
        return
    
    print("\n=== Обновление версий ===")
    
    # Обновляем версию во всех файлах
    files_updated = []
    
    # PyGameBall.py
    if update_version_in_file('PyGameBall.py', r'VERSION = "\d+\.\d+\.\d+"', new_version):
        files_updated.append('PyGameBall.py')
    
    # pyproject.toml
    if update_version_in_file('pyproject.toml', r'version = "\d+\.\d+\.\d+"', new_version):
        files_updated.append('pyproject.toml')
    
    # README.md
    if update_readme_version('README.md', new_version):
        files_updated.append('README.md')

    # create_installer.iss
    if update_version_in_file('create_installer.iss', r'#define MyAppVersion "\d+\.\d+\.\d+"', new_version):
        files_updated.append('create_installer.iss')
    
    # Создаем changelog запись
    if create_changelog_entry(new_version):
        files_updated.append('changelog.md')
    
    print(f"\nОбновлены файлы: {', '.join(files_updated)}")
    
    # Собираем в зависимости от выбора
    print("\n=== Сборка ===")
    
    success_count = 0
    total_count = 0
    
    # Всегда собираем исполняемый файл
    total_count += 1
    if build_executable():
        success_count += 1
    
    if installer_choice in ['2', '4']:
        total_count += 1
        if build_installer():
            success_count += 1
    
    if installer_choice in ['3', '4']:
        total_count += 1
        if build_msi():
            success_count += 1
    
    # Итоговый отчет
    print(f"\n=== Результат релиза ===")
    print(f"Успешно создано: {success_count}/{total_count}")
    
    if success_count > 0:
        print(f"\n✅ Релиз версии {new_version} завершен!")
        
        files_created = []
        files_created.append(f"Arkanoid_v{new_version}.exe")
        
        if installer_choice in ['2', '4'] and os.path.exists(f"installer/Arkanoid_v{new_version}_Setup.exe"):
            files_created.append(f"Arkanoid_v{new_version}_Setup.exe (EXE инсталлятор)")
        
        if installer_choice in ['3', '4'] and os.path.exists(f"Arkanoid_v{new_version}_Setup.msi"):
            files_created.append(f"Arkanoid_v{new_version}_Setup.msi (MSI инсталлятор)")
        
        print(f"Готовые файлы:")
        for file in files_created:
            print(f"  - {file}")
            
    else:
        print(f"\n❌ Релиз завершился с ошибками")

if __name__ == "__main__":
    main()