"""
Утилиты для определения платформы и окружения выполнения.

Содержит функции для проверки, запущено ли приложение как скомпилированный
исполняемый файл или как скрипт Python.
"""

import sys
import os


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


def get_ai_directory() -> str:
    """
    Определяет каталог для AI файлов (логи и модели).
    Для разработки: ai в корне проекта
    Для exe: каталог установки Windows или директория exe файла
    """
    # Для разработки (запуск из IDE) всегда используем ai в корне проекта
    if not is_frozen():
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ai_dir = os.path.join(current_dir, "ai")
        return ai_dir

    # Для exe файлов пытаемся использовать LOCALAPPDATA
    try:
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            game_dir = os.path.join(localappdata, "Games", "Arkanoid")
            ai_dir = os.path.join(game_dir, "ai")
            # Создаем директории если их нет
            try:
                os.makedirs(ai_dir, exist_ok=True)
            except (OSError, PermissionError):
                pass
            return ai_dir
    except:
        pass

    # Fallback для exe: директория exe файла
    exe_dir = os.path.dirname(sys.executable)
    ai_dir = os.path.join(exe_dir, "ai")
    try:
        os.makedirs(ai_dir, exist_ok=True)
    except (OSError, PermissionError):
        pass
    return ai_dir

