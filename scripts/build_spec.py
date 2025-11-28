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
        with open('PyGameBall.py', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VERSION ='):
                    return line.split('"')[1]
    except:
        return "1.6.1"  # резервная версия
    return "1.6.1"

# Создаем команды для PyInstaller
version = get_version()
exe_name = f"Arkanoid_v{version}.exe"

print(f"Создание исполняемого файла: {exe_name}")
print(f"Версия: {version}")

# Создаем временную директорию для ресурсов
resource_dir = "game_resources"
os.makedirs(resource_dir, exist_ok=True)

# Копируем ресурсы во временную директорию
if os.path.exists("sounds"):
    shutil.copytree("sounds", f"{resource_dir}/sounds", dirs_exist_ok=True)

if os.path.exists("images"):
    shutil.copytree("images", f"{resource_dir}/images", dirs_exist_ok=True)

# Копируем необходимые файлы
shutil.copy("highscores.py", resource_dir)

# Команда PyInstaller
cmd = f'''pyinstaller --onefile --windowed --name="{exe_name}" ^
    --add-data "{resource_dir}/sounds;sounds" ^
    --add-data "{resource_dir}/images;images" ^
    --add-data "{resource_dir}/highscores.py;." ^
    --hidden-import=pygame ^
    --hidden-import=numpy ^
    --hidden-import=pygame.sndarray ^
    --hidden-import=pygame.mixer ^
    --exclude-module=tkinter ^
    --exclude-module=matplotlib ^
    --exclude-module=scipy ^
    --exclude-module=PIL ^
    --exclude-module=IPython ^
    --exclude-module=jupyter ^
    --exclude-module=notebook ^
    --exclude-module=pytest ^
    --exclude-module=unittest ^
    --clean ^
    PyGameBall.py'''

print("Выполняю команду сборки...")
print(cmd)
os.system(cmd)

# Копируем готовый exe в корневую папку
dist_dir = "dist"
if os.path.exists(dist_dir):
    exe_path = os.path.join(dist_dir, f"{exe_name}.exe")
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, f"./{exe_name}.exe")
        print(f"Исполняемый файл скопирован в корневую папку: {exe_name}.exe")
        
        # Удаляем временную директорию ресурсов
        if os.path.exists(resource_dir):
            shutil.rmtree(resource_dir)
            
        print("Сборка завершена успешно!")
    else:
        print(f"Ошибка: файл {exe_path} не найден в dist")
else:
    print("Ошибка: директория dist не найдена")
