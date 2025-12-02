#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для создания исполняемого файла игры Арканоид с помощью PyInstaller
"""

import os
import sys
import shutil
from pathlib import Path


# Получаем версию из основного файла игры
def get_version():
    """Извлекает версию из файла PyGameBall.py"""
    try:
        version_file = os.path.join(project_root, "PyGameBall.py")
        with open(version_file, "r", encoding="utf-8") as f:
            for line in f:
                if "VERSION =" in line:
                    # Ищем строку вида VERSION = "1.6.5"
                    parts = line.split('"')
                    if len(parts) >= 2:
                        return parts[1]
                    # Если нет кавычек, пробуем найти после =
                    version_part = line.split("=")[1].strip()
                    if version_part.startswith('"') and version_part.endswith('"'):
                        return version_part.strip('"')
    except Exception as e:
        print(f"Ошибка чтения версии: {e}")
    return "1.6.5"


# Определяем корень проекта (на уровень выше папки scripts)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Переходим в корень проекта для корректной работы
os.chdir(project_root)

# Создаем команды для PyInstaller
version = get_version()
exe_name = f"Arkanoid_v{version}"  # Без .exe - PyInstaller добавит сам

print(f"Создание исполняемого файла: {exe_name}.exe")
print(f"Версия: {version}")
print(f"Корень проекта: {project_root}")
print("Используются ресурсы из папки resources/")

# Ресурсы находятся в папке resources/

# Команда PyInstaller - без переносов строк для Windows
cmd_parts = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    f"--name={exe_name}",
    f'--workpath={os.path.join(project_root, "build", "work")}',
    f'--distpath={os.path.join(project_root, "build", "dist")}',
    f'--add-data="{os.path.join(project_root, "resources", "audio")};resources/audio"',
    f'--add-data="{os.path.join(project_root, "resources", "images")};resources/images"',
    f'--add-data="{os.path.join(project_root, "resources", "data")};resources/data"',
    f'--add-data="{os.path.join(project_root, "highscores.py")};."',
    f'--add-data="{os.path.join(project_root, "settings.py")};."',
    "--hidden-import=pygame",
    "--hidden-import=numpy",
    "--hidden-import=pygame.sndarray",
    "--hidden-import=pygame.mixer",
    "--exclude-module=tkinter",
    "--exclude-module=matplotlib",
    "--exclude-module=scipy",
    "--exclude-module=PIL",
    "--exclude-module=IPython",
    "--exclude-module=jupyter",
    "--exclude-module=notebook",
    "--exclude-module=pytest",
    "--exclude-module=unittest",
    "--clean",
    f'"{os.path.join(project_root, "PyGameBall.py")}"',
]

cmd = " ".join(cmd_parts)

print("Выполняю команду сборки...")
print(cmd)
os.system(cmd)

# Копируем готовый exe в корневую папку
dist_dir = os.path.join(project_root, "build", "dist")
if os.path.exists(dist_dir):
    exe_path = os.path.join(dist_dir, f"{exe_name}.exe")
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, os.path.join(project_root, f"{exe_name}.exe"))
        print(f"Исполняемый файл скопирован в корневую папку: {exe_name}.exe")
        print("Исполняемый файл успешно создан с использованием папки resources/")
        print("Сборка завершена успешно!")
    else:
        print(f"Ошибка: файл {exe_path} не найден в dist")
else:
    print("Ошибка: директория dist не найдена")
