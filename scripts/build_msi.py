#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт сборки MSI инсталлятора игры Арканоид
"""

import os
import sys
import subprocess
import shutil

# Определяем корень проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_current_version():
    """Получает текущую версию из PyGameBall.py"""
    try:
        with open(
            os.path.join(project_root, "PyGameBall.py"), "r", encoding="utf-8"
        ) as f:
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


def build_msi():
    """Создает MSI инсталлятор"""
    try:
        print("Создаю MSI инсталлятор...")

        # Проверяем, существует ли exe файл
        version = get_current_version()
        exe_path = os.path.join(
            project_root, "FINAL_RELEASE", f"Arkanoid_v{version}.exe"
        )
        if not os.path.exists(exe_path):
            print(f"EXE файл {exe_path} не найден. Создаю...")
            exe_result = subprocess.run(
                ["python", os.path.join(project_root, "scripts", "build_spec.py")]
            )
            if exe_result.returncode != 0:
                print("Ошибка создания EXE")
                return False

        # Запускаем скрипт создания MSI
        result = subprocess.run(
            ["python", os.path.join(project_root, "scripts", "create_msi.py")]
        )

        # Копируем MSI в FINAL_RELEASE и проверяем
        build_msi_path = os.path.join(
            project_root, "build", f"Arkanoid_v{version}_Setup.msi"
        )
        final_dir = os.path.join(project_root, "FINAL_RELEASE")
        os.makedirs(final_dir, exist_ok=True)
        final_msi_path = os.path.join(final_dir, f"Arkanoid_v{version}_Setup.msi")
        if os.path.exists(build_msi_path):
            shutil.copy2(build_msi_path, final_msi_path)
            return True
        else:
            print("MSI файл не создан")
            return False

    except Exception as e:
        print(f"Ошибка при создании MSI: {e}")
        return False


def main():
    print("=== Сборка MSI инсталлятора Arkanoid ===")

    if build_msi():
        version = get_current_version()
        final_msi_path = os.path.join(
            project_root, "FINAL_RELEASE", f"Arkanoid_v{version}_Setup.msi"
        )
        print(f"\n✅ MSI инсталлятор готов: {final_msi_path}")
    else:
        print("\n❌ Ошибка сборки MSI инсталлятора")


if __name__ == "__main__":
    main()
