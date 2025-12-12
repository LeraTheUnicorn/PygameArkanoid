"""
Кастомный FileHandler для ротации логов по количеству строк.
Создает новые файлы каждые 500 строк.
"""

import logging
import os
from typing import Optional


class RotatingLinesFileHandler(logging.FileHandler):
    """
    FileHandler, который создает новый файл каждые N строк.
    
    Файлы именуются с инкрементным номером:
    ai_player_1.log, ai_player_2.log, ai_player_3.log и т.д.
    """
    
    def __init__(
        self,
        base_filename: str,
        max_lines: int = 500,
        mode: str = 'a',
        encoding: Optional[str] = 'utf-8',
        delay: bool = False,
        errors: Optional[str] = None
    ):
        """
        Инициализация ротирующего handler'а.
        
        Args:
            base_filename: Базовое имя файла (без расширения и номера)
            max_lines: Максимальное количество строк в одном файле
            mode: Режим открытия файла ('a' для append)
            encoding: Кодировка файла
            delay: Отложенное открытие файла
            errors: Обработка ошибок кодировки
        """
        self.base_filename = base_filename
        self.max_lines = max_lines
        self.current_file_number = 1
        self.current_line_count = 0
        
        # Всегда начинаем с файла номер 1 при новом запуске
        # Формируем имя текущего файла
        current_filename = self._get_current_filename()
        
        # Инициализируем базовый FileHandler
        super().__init__(
            current_filename,
            mode=mode,
            encoding=encoding,
            delay=delay,
            errors=errors
        )
    
    def _get_current_filename(self) -> str:
        """Возвращает имя текущего файла с номером."""
        base, ext = os.path.splitext(self.base_filename)
        return f"{base}_{self.current_file_number}{ext}"
    
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Записывает запись в лог.
        Создает новый файл, если достигнут лимит строк.
        """
        # Проверяем, нужно ли создать новый файл
        if self.current_line_count >= self.max_lines:
            self._rotate_file()
        
        # Записываем запись
        super().emit(record)
        self.current_line_count += 1
    
    def _rotate_file(self) -> None:
        """Создает новый файл для логирования."""
        # Закрываем текущий файл
        self.close()
        
        # Увеличиваем номер файла
        self.current_file_number += 1
        self.current_line_count = 0
        
        # Открываем новый файл
        new_filename = self._get_current_filename()
        self.baseFilename = new_filename
        self.stream = self._open()
