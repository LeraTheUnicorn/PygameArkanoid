#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт сборки исполняемого файла игры Арканоид
"""

import os
import sys
import shutil
import subprocess

# Определяем корень проекта и директорию скриптов
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = os.path.dirname(os.path.abspath(__file__))


def get_current_version():
    """Получает текущую версию из version.py"""
    try:
        sys.path.insert(0, project_root)
        from src.game.version import get_version_string

        return get_version_string()
    except Exception as e:
        print(f"Ошибка чтения версии из version.py: {e}")
        return "2.3.0000"


def build_executable():
    """Собирает исполняемый файл с помощью PyInstaller"""
    try:
        print("Начинаю сборку исполняемого файла...")

        # Создаём каталог для сборки внутри scripts/
        build_dir = os.path.join(scripts_dir, "build")
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
            "--specpath",
            build_dir,
            "--paths",
            os.path.join(project_root, "src"),
            "--add-data",
            f'{os.path.join(project_root, "src", "resources", "audio")};src/resources/audio',
            "--add-data",
            f'{os.path.join(project_root, "src", "resources", "images")};src/resources/images',
            "--add-data",
            f'{os.path.join(project_root, "src", "resources", "data")};src/resources/data',
            "--add-data",
            f'{os.path.join(project_root, "src", "game", "highscores.py")};src/game',
            "--add-data",
            f'{os.path.join(project_root, "src", "game", "settings.py")};src/game',
            "--add-data",
            f'{os.path.join(project_root, "src", "resources")};src/resources',
            "--hidden-import",
            "pygame",
            "--hidden-import",
            "numpy",
            "--hidden-import",
            "src.ai.ai_player",
            "--hidden-import",
            "src.game.highscores",
            "--hidden-import",
            "src.game.settings",
            "--exclude-module",
            "tkinter",
            "--exclude-module",
            "matplotlib",
            "--clean",
            os.path.join(project_root, "src", "game", "PyGameBall.py"),
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
