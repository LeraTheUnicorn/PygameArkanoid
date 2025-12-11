"""
Система управления настройками игры Арканоид
Сохраняет и загружает настройки в файл
"""

import json
import os
import sys
from typing import Dict, Any


def get_game_directory() -> str:
    """
    Определяет каталог игры.
    При запуске из студии разработки использует local_game_files,
    иначе использует директорию exe файла или текущую директорию.
    """
    # Проверяем, запущено ли приложение как exe или как скрипт Python
    if not getattr(sys, "frozen", False):
        # Если приложение запущено как скрипт Python (из студии разработки)
        # Используем каталог local_game_files в корне проекта
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_game_dir = os.path.join(current_dir, "local_game_files")
        return local_game_dir

    # Для exe файлов используем директорию exe файла
    return os.path.dirname(sys.executable)


def get_settings_file_path() -> str:
    """Возвращает полный путь к файлу настроек"""
    game_dir = get_game_directory()
    resources_dir = os.path.join(game_dir, "resources")

    # Создаем каталог, если он не существует
    if not os.path.exists(resources_dir):
        try:
            os.makedirs(resources_dir, exist_ok=True)
        except (OSError, PermissionError):
            # Если не удается создать каталог, используем текущую директорию
            resources_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "resources"
            )
            if not os.path.exists(resources_dir):
                os.makedirs(resources_dir, exist_ok=True)

    return os.path.join(resources_dir, "data", "settings.json")


# Путь к файлу настроек
SETTINGS_FILE: str = get_settings_file_path()


class SettingsManager:
    def __init__(self) -> None:
        self.settings: Dict[str, Any] = {
            "ball_speed": 15
        }  # Скорость мяча по умолчанию (среднее для авторежима 1-30)
        self.load_settings()
        self.save_settings()  # Создать файл, если не существует

    def load_settings(self) -> None:
        """Загружает настройки из файла"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded_settings: Dict[str, Any] = json.load(f)
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
        speed = self.settings.get("ball_speed", 15)
        return int(speed) if isinstance(speed, (int, float)) else 15

    def set_ball_speed(self, speed: int, auto_mode: bool = False) -> None:
        """
        Устанавливает скорость мяча с учетом режима игры.
        
        Ограничения скорости основаны на ограничении времени расчета:
        - FPS = 60 (16.67 мс на кадр)
        - Расчет траектории: ~1-5 мс
        - Запас для стабильности: ~5 мс
        - Максимальная скорость: 25 для авторежима (адекватное поведение)
        """
        # Максимальная скорость с учетом ограничения 16.67 мс на расчет
        # При скорости > 25 расчеты могут превышать 16.67 мс
        # КРИТИЧНО: Максимальная скорость ограничена временем движения платформы
        # Зона разделения: 314 пикселей, время движения платформы: 35.6 кадров
        # Максимальная скорость: 314 / 35.6 = 8.8, с запасом: 8
        max_speed = 8 if auto_mode else 10
        if 1 <= speed <= max_speed:
            self.settings["ball_speed"] = speed
            self.save_settings()
        else:
            mode_text = "авторежиме" if auto_mode else "ручном режиме"
            raise ValueError(
                f"Скорость мяча должна быть в диапазоне от 1 до {max_speed} в {mode_text}"
            )
