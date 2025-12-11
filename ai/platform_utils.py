"""
Утилиты для определения платформы и окружения выполнения.

Содержит функции для проверки, запущено ли приложение как скомпилированный
исполняемый файл или как скрипт Python.
"""

import sys


def is_frozen() -> bool:
    """
    Проверяет, является ли приложение скомпилированным исполняемым файлом.
    
    Поддерживает следующие компиляторы:
    - PyInstaller: устанавливает sys.frozen = True
    - cx_Freeze: устанавливает sys.frozen = True
    - py2exe: устанавливает sys.frozen = True и sys._MEIPASS
    - py2app (macOS): устанавливает sys.frozen = True
    
    Returns:
        True, если приложение скомпилировано, False если запущено как скрипт Python
    """
    # PyInstaller, cx_Freeze, py2exe устанавливают sys.frozen
    if getattr(sys, "frozen", False):
        return True
    
    # PyInstaller также создает sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        return True
    
    # py2exe может создавать sys.frozendllhandle
    if hasattr(sys, "frozendllhandle"):
        return True
    
    return False

