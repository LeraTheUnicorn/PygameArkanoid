"""
Система управления настройками игры Арканоид
Сохраняет и загружает настройки в файл
"""

import json
import os
import sys
from typing import Dict


def get_game_directory():
    """
    Определяет каталог игры.
    Использует текущую директорию проекта для хранения файлов настроек.
    """
    # Используем директорию, где находится скрипт
    if getattr(sys, "frozen", False):
        # Если приложение запущено как exe (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Если приложение запущено как скрипт Python
        return os.path.dirname(os.path.abspath(__file__))


def get_settings_file_path():
    """Возвращает полный путь к файлу настроек"""
    game_dir = get_game_directory()
    resources_dir = os.path.join(game_dir, "resources")

    # Создаем каталог, если он не существует
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir, exist_ok=True)

    return os.path.join(resources_dir, "settings.json")


# Путь к файлу настроек
SETTINGS_FILE = get_settings_file_path()


class SettingsManager:
    def __init__(self):
        self.settings = {"ball_speed": 5}  # Скорость мяча по умолчанию
        self.load_settings()
        self.save_settings()  # Создать файл, если не существует

    def load_settings(self) -> None:
        """Загружает настройки из файла"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError):
            # Если файл поврежден, используем значения по умолчанию
            pass

    def save_settings(self) -> None:
        """Сохраняет настройки в файл"""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except IOError:
            print("Ошибка сохранения настроек")

    def get_ball_speed(self) -> int:
        """Возвращает скорость мяча"""
        return self.settings["ball_speed"]

    def set_ball_speed(self, speed: int) -> None:
        """Устанавливает скорость мяча"""
        if 1 <= speed <= 10:  # Ограничение скорости от 1 до 10
            self.settings["ball_speed"] = speed
            self.save_settings()
        else:
            raise ValueError("Скорость мяча должна быть в диапазоне от 1 до 10")
