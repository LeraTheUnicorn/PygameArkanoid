#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт сборки исполняемого файла игры Арканоид
"""

import os
import sys
import shutil
import subprocess

# Определяем корень проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def build_executable():
    """Собирает исполняемый файл с помощью PyInstaller"""
    try:
        print("Начинаю сборку исполняемого файла...")

        # Создаём каталог для сборки
        build_dir = os.path.join(project_root, "build")
        os.makedirs(build_dir, exist_ok=True)

        # Запускаем PyInstaller
        cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed",
            "--name",
            "Arkanoid_v" + get_current_version(),
            "--distpath",
            os.path.join(build_dir, "dist"),
            "--workpath",
            os.path.join(build_dir, "temp"),
            "--add-data",
            f'{os.path.join(project_root, "sounds")};sounds',
            "--add-data",
            f'{os.path.join(project_root, "images")};images',
            "--add-data",
            f'{os.path.join(project_root, "game_resources", "sounds")};sounds',
            "--add-data",
            f'{os.path.join(project_root, "game_resources", "images")};images',
            "--add-data",
            f'{os.path.join(project_root, "resources")};resources',
            "--hidden-import",
            "pygame",
            "--hidden-import",
            "numpy",
            "--exclude-module",
            "tkinter",
            "--exclude-module",
            "matplotlib",
            "--clean",
            os.path.join(project_root, "PyGameBall.py"),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("Сборка завершена успешно!")

            # Копируем в FINAL_RELEASE
            exe_name = f"Arkanoid_v{get_current_version()}.exe"
            dist_path = os.path.join(build_dir, "dist", exe_name)
            final_dir = os.path.join(project_root, "FINAL_RELEASE")
            os.makedirs(final_dir, exist_ok=True)
            root_path = os.path.join(final_dir, exe_name)

            if os.path.exists(dist_path):
                shutil.copy2(dist_path, root_path)
                print(f"Исполняемый файл скопирован в FINAL_RELEASE: {exe_name}")
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


def main():
    print("=== Сборка исполняемого файла Arkanoid ===")

    if build_executable():
        version = get_current_version()
        exe_path = os.path.join(
            project_root, "FINAL_RELEASE", f"Arkanoid_v{version}.exe"
        )
        print(f"\n✅ Исполняемый файл готов: {exe_path}")
    else:
        print("\n❌ Ошибка сборки исполняемого файла")


if __name__ == "__main__":
    main()
