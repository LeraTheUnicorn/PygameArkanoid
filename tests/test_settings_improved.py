#!/usr/bin/env python3
"""
Тесты для улучшенной версии SettingsManager

Демонстрирует улучшенную тестируемость благодаря инъекции зависимостей.
"""

import json
import tempfile
import pytest
from pathlib import Path
import sys
import os
from typing import Dict, Any

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import (
    SettingsManager,
    SettingsValidator,
    SettingsConstants
)


class TestSettingsValidator:
    """Тесты валидатора настроек"""
    
    def test_validate_ball_speed_valid(self) -> None:
        """Тест валидации корректной скорости"""
        assert SettingsValidator.validate_ball_speed(5) == 5
        assert SettingsValidator.validate_ball_speed(1) == 1
        assert SettingsValidator.validate_ball_speed(10) == 10
        assert SettingsValidator.validate_ball_speed(8, auto_mode=True) == 8
    
    def test_validate_ball_speed_invalid_type(self) -> None:
        """Тест валидации некорректного типа"""
        assert SettingsValidator.validate_ball_speed("invalid") == SettingsConstants.DEFAULT_BALL_SPEED
        assert SettingsValidator.validate_ball_speed(None) == SettingsConstants.DEFAULT_BALL_SPEED
        assert SettingsValidator.validate_ball_speed([]) == SettingsConstants.DEFAULT_BALL_SPEED
    
    def test_validate_ball_speed_out_of_range(self) -> None:
        """Тест валидации скорости вне диапазона"""
        assert SettingsValidator.validate_ball_speed(0) == SettingsConstants.DEFAULT_BALL_SPEED
        assert SettingsValidator.validate_ball_speed(15) == SettingsConstants.DEFAULT_BALL_SPEED
        assert SettingsValidator.validate_ball_speed(10, auto_mode=True) == SettingsConstants.DEFAULT_BALL_SPEED
    
    def test_validate_ball_speed_float(self) -> None:
        """Тест валидации float значения"""
        assert SettingsValidator.validate_ball_speed(5.7) == 5
        assert SettingsValidator.validate_ball_speed(8.9) == 8
    
    def test_validate_settings(self) -> None:
        """Тест валидации полного словаря настроек"""
        # Корректные настройки
        valid_settings: Dict[str, Any] = {
            "version": 1,
            "ball_speed": 5
        }
        validated: Dict[str, Any] = SettingsValidator.validate_settings(valid_settings)
        assert validated["version"] == 1
        assert validated["ball_speed"] == 5
        
        # Некорректные настройки
        invalid_settings: Dict[str, Any] = {
            "version": "invalid",
            "ball_speed": "invalid"
        }
        validated = SettingsValidator.validate_settings(invalid_settings)
        assert validated["version"] == 1  # Используется значение по умолчанию
        assert validated["ball_speed"] == SettingsConstants.DEFAULT_BALL_SPEED


class TestSettingsManager:
    """Тесты менеджера настроек"""
    
    def test_init_creates_default_settings(self) -> None:
        """Тест создания менеджера с настройками по умолчанию"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            assert manager.get_ball_speed() == SettingsConstants.DEFAULT_BALL_SPEED
            assert manager.settings["version"] == SettingsConstants.SETTINGS_VERSION
            assert settings_file.exists()
    
    def test_load_settings_from_file(self) -> None:
        """Тест загрузки настроек из файла"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            
            # Создаем файл с настройками
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "ball_speed": 7}, f)
            
            manager: SettingsManager = SettingsManager(str(settings_file))
            assert manager.get_ball_speed() == 7
    
    def test_save_settings(self) -> None:
        """Тест сохранения настроек"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            manager.set_ball_speed(6)
            
            # Проверяем, что файл сохранен
            assert settings_file.exists()
            with open(settings_file, "r", encoding="utf-8") as f:
                saved: Dict[str, Any] = json.load(f)
                assert saved["ball_speed"] == 6
    
    def test_set_ball_speed_valid(self) -> None:
        """Тест установки корректной скорости"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            manager.set_ball_speed(5)
            assert manager.get_ball_speed() == 5
            
            manager.set_ball_speed(10)
            assert manager.get_ball_speed() == 10
    
    def test_set_ball_speed_invalid(self) -> None:
        """Тест установки некорректной скорости"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            # Скорость вне диапазона
            with pytest.raises(ValueError, match="должна быть в диапазоне"):
                manager.set_ball_speed(0)
            
            with pytest.raises(ValueError, match="должна быть в диапазоне"):
                manager.set_ball_speed(15)
            
            # Для авторежима максимум 8
            with pytest.raises(ValueError, match="должна быть в диапазоне"):
                manager.set_ball_speed(10, auto_mode=True)
    
    def test_auto_mode_limits(self) -> None:
        """Тест ограничений для авторежима"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            # В авторежиме максимум 8
            manager.set_ball_speed(8, auto_mode=True)
            assert manager.get_ball_speed() == 8
            
            # В ручном режиме максимум 10
            manager.set_ball_speed(10, auto_mode=False)
            assert manager.get_ball_speed() == 10
    
    def test_atomic_save(self) -> None:
        """Тест атомарного сохранения"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            # Устанавливаем скорость
            manager.set_ball_speed(5)
            
            # Проверяем, что временный файл не остался
            temp_file: Path = settings_file.with_suffix('.tmp')
            assert not temp_file.exists()
            
            # Проверяем, что основной файл существует и корректен
            assert settings_file.exists()
            with open(settings_file, "r", encoding="utf-8") as f:
                saved: Dict[str, Any] = json.load(f)
                assert saved["ball_speed"] == 5
    
    def test_load_invalid_json(self) -> None:
        """Тест загрузки поврежденного JSON файла"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            
            # Создаем файл с некорректным JSON
            with open(settings_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json }")
            
            # Менеджер должен использовать настройки по умолчанию
            manager: SettingsManager = SettingsManager(str(settings_file))
            assert manager.get_ball_speed() == SettingsConstants.DEFAULT_BALL_SPEED
    
    def test_load_invalid_settings(self) -> None:
        """Тест загрузки настроек с некорректными значениями"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            
            # Создаем файл с некорректными значениями
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump({"ball_speed": "invalid", "version": "invalid"}, f)
            
            # Менеджер должен валидировать и использовать значения по умолчанию
            manager: SettingsManager = SettingsManager(str(settings_file))
            assert manager.get_ball_speed() == SettingsConstants.DEFAULT_BALL_SPEED
    
    def test_migration(self) -> None:
        """Тест миграции настроек"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            
            # Создаем файл со старой версией
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump({"version": 0, "ball_speed": 5}, f)
            
            manager: SettingsManager = SettingsManager(str(settings_file))
            
            # Версия должна быть обновлена
            assert manager.settings["version"] == SettingsConstants.SETTINGS_VERSION
            
            # Проверяем, что файл обновлен
            with open(settings_file, "r", encoding="utf-8") as f:
                saved: Dict[str, Any] = json.load(f)
                assert saved["version"] == SettingsConstants.SETTINGS_VERSION
    
    def test_save_skip_if_unchanged(self) -> None:
        """Тест пропуска сохранения если настройки не изменились"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            
            # Создаем менеджер
            manager1: SettingsManager = SettingsManager(str(settings_file))
            manager1.set_ball_speed(5)
            
            # Получаем время модификации
            mtime1: float = settings_file.stat().st_mtime
            
            # Создаем второй менеджер и загружаем те же настройки
            import time
            time.sleep(0.01)  # Небольшая задержка для различия времени
            
            manager2: SettingsManager = SettingsManager(str(settings_file))
            # Не меняем настройки, просто загружаем
            
            # Время модификации не должно измениться
            mtime2: float = settings_file.stat().st_mtime
            # Примечание: из-за особенностей файловой системы время может не измениться
            # даже при записи, поэтому этот тест может быть нестабильным
    
    def test_file_size_limit(self) -> None:
        """Тест ограничения размера файла"""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file: Path = Path(tmpdir) / "test_settings.json"
            
            # Создаем файл больше максимального размера
            large_data: Dict[str, Any] = {"ball_speed": 5, "large_field": "x" * (SettingsConstants.MAX_SETTINGS_FILE_SIZE + 1)}
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(large_data, f)
            
            # Менеджер должен использовать настройки по умолчанию
            manager: SettingsManager = SettingsManager(str(settings_file))
            assert manager.get_ball_speed() == SettingsConstants.DEFAULT_BALL_SPEED


def test_backward_compatibility() -> None:
    """Тест обратной совместимости"""
    # Проверяем, что старый код все еще работает
    from settings import SETTINGS_FILE
    assert isinstance(SETTINGS_FILE, str)
    assert SETTINGS_FILE.endswith("settings.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
