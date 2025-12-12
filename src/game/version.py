"""
Централизованное управление версией проекта Арканоид

Этот файл является единственным источником истины для версии проекта.
Все остальные файлы должны импортировать версию отсюда.

Версия автоматически увеличивается при каждом запуске (увеличивается BUILD номер).
"""

import os
import re
from pathlib import Path
from typing import Tuple

# Путь к текущему файлу
_VERSION_FILE: Path = Path(__file__)

# Версия в формате X.Y.ZZZZ
# X - мажорная версия (революционные изменения)
# Y - минорная версия (новые функции, исправления UI)
# ZZZZ - 4-значный индекс сборки (увеличивается автоматически при каждом запуске)

# Начальные значения (будут обновлены при загрузке)
VERSION_MAJOR: int = 2
VERSION_MINOR: int = 3
VERSION_BUILD: int = 161
VERSION: str = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD:04d}"
VERSION_FULL: str = VERSION
VERSION_BUILD_STRING: str = VERSION


def _load_version_from_file() -> None:
    """Загружает версию из файла и увеличивает BUILD номер"""
    global VERSION_MAJOR, VERSION_MINOR, VERSION_BUILD, VERSION, VERSION_FULL, VERSION_BUILD_STRING

    try:
        # Читаем текущий файл
        with open(_VERSION_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Извлекаем текущие значения версии
        major_match = re.search(r"VERSION_MAJOR\s*=\s*(\d+)", content)
        minor_match = re.search(r"VERSION_MINOR\s*=\s*(\d+)", content)
        build_match = re.search(r"VERSION_BUILD\s*=\s*(\d+)", content)

        if major_match and minor_match and build_match:
            VERSION_MAJOR = int(major_match.group(1))
            VERSION_MINOR = int(minor_match.group(1))
            VERSION_BUILD = int(build_match.group(1))

            # Увеличиваем BUILD номер
            VERSION_BUILD += 1

            # Обновляем VERSION и VERSION_BUILD_STRING
            VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD:04d}"
            VERSION_BUILD_STRING = VERSION
            VERSION_FULL = VERSION

            # Обновляем файл с новой версией
            content = re.sub(
                r"VERSION_BUILD\s*=\s*\d+", f"VERSION_BUILD = {VERSION_BUILD}", content
            )
            content = re.sub(r'VERSION\s*=\s*"[^"]+"', f'VERSION = "{VERSION}"', content)
            content = re.sub(
                r'VERSION_BUILD_STRING\s*=\s*"[^"]+"',
                f'VERSION_BUILD_STRING = "{VERSION_BUILD_STRING}"',
                content,
            )
            content = re.sub(
                r'VERSION_FULL\s*=\s*"[^"]+"', f'VERSION_FULL = "{VERSION_FULL}"', content
            )

            # Сохраняем обновленный файл
            with open(_VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # Если не удалось распарсить, используем значения по умолчанию
            VERSION_BUILD += 1
            VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD:04d}"
            VERSION_BUILD_STRING = VERSION
            VERSION_FULL = VERSION

    except Exception as e:
        # В случае ошибки используем значения по умолчанию и увеличиваем BUILD
        VERSION_BUILD += 1
        VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD:04d}"
        VERSION_BUILD_STRING = VERSION
        VERSION_FULL = VERSION
        # Не прерываем выполнение, просто логируем ошибку
        import sys

        if not getattr(sys, "frozen", False):  # Не выводим в exe
            print(f"[WARNING] Не удалось обновить версию в файле: {e}")


# Автоматически загружаем и обновляем версию при импорте модуля
_load_version_from_file()


def get_version() -> str:
    """Возвращает текущую версию"""
    return VERSION


def get_version_tuple() -> Tuple[int, int, int]:
    """Возвращает версию как кортеж (major, minor, build)"""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_BUILD)


def get_version_string() -> str:
    """Возвращает версию как строку в формате X.Y.ZZZZ"""
    return VERSION_BUILD_STRING


def get_version_for_poetry() -> str:
    """Возвращает версию в формате Poetry (X.Y.Z, где Z = BUILD)"""
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_BUILD}"
