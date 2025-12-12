"""
Централизованная конфигурация логирования для AI системы.

ЕДИНСТВЕННОЕ МЕСТО ДЛЯ НАСТРОЙКИ ЛОГИРОВАНИЯ ВО ВСЕМ ПРОЕКТЕ!

Для изменения уровня логирования измените LOG_LEVEL:
   - 'DEBUG' - все сообщения (самый подробный)
   - 'INFO' - информационные сообщения и выше
   - 'WARNING' - предупреждения и выше
   - 'ERROR' - только ошибки
   - 'CRITICAL' - только критические ошибки

Логирование НЕ зависит от параметра debug_mode при создании AIPlayer.
Параметр debug_mode используется только для визуализации и отладки UI.

ВНИМАНИЕ: Не настраивайте логирование в других файлах!
Все настройки логирования должны быть только здесь.
"""

import logging
from typing import Literal

# ============================================================================
# НАСТРОЙКИ УРОВНЯ ЛОГИРОВАНИЯ
# ============================================================================

# Доступные уровни: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
# Измените это значение, чтобы изменить уровень логирования во всей системе
# По умолчанию: 'DEBUG' для максимальной детализации
LOG_LEVEL: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'DEBUG'

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_log_level() -> int:
    """
    Возвращает уровень логирования на основе настроек из LOG_LEVEL.
    
    Логирование НЕ зависит от параметра debug_mode при создании AIPlayer.
    Все настройки логирования централизованы здесь.
    
    Returns:
        Уровень логирования (logging.DEBUG, logging.INFO, и т.д.)
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(LOG_LEVEL, logging.INFO)


def get_log_level_name() -> str:
    """
    Возвращает имя уровня логирования из LOG_LEVEL.
    
    Returns:
        Имя уровня логирования ('DEBUG', 'INFO', и т.д.)
    """
    return LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер с централизованной настройкой уровня логирования.
    
    ВСЕ модули должны использовать эту функцию вместо logging.getLogger(__name__),
    чтобы гарантировать использование централизованной конфигурации логирования.
    
    Args:
        name: Имя логгера (обычно __name__)
    
    Returns:
        Настроенный логгер с уровнем из LOG_LEVEL
    """
    logger = logging.getLogger(name)
    
    # Устанавливаем уровень из централизованной конфигурации
    # Если логгер уже имеет handlers, обновляем их уровни тоже
    log_level = get_log_level()
    logger.setLevel(log_level)
    
    # Устанавливаем уровень для всех существующих handlers
    for handler in logger.handlers:
        handler.setLevel(log_level)
    
    # Если нет handlers, настраиваем базовую конфигурацию через root logger
    # Это гарантирует, что сообщения будут записываться
    if not logger.handlers and not logging.getLogger().handlers:
        # Настраиваем базовое логирование только если root logger не настроен
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    return logger


def setup_root_logger() -> None:
    """
    Настраивает root logger для всего проекта.
    Вызывается один раз при запуске приложения.
    
    КРИТИЧНО: Устанавливает уровень для root logger, чтобы ВСЕ дочерние логгеры
    наследовали этот уровень (если их собственный уровень NOTSET).
    """
    log_level = get_log_level()
    
    # Получаем root logger
    root_logger = logging.getLogger()
    
    # Устанавливаем уровень для root logger
    # Это критически важно - все дочерние логгеры будут наследовать этот уровень
    root_logger.setLevel(log_level)
    
    # Обновляем уровень для всех существующих handlers root logger
    for handler in root_logger.handlers:
        handler.setLevel(log_level)
    
    # Если нет handlers, настраиваем базовую конфигурацию
    if not root_logger.handlers:
        # Создаем базовую конфигурацию для root logger
        # Это нужно для модулей, которые не имеют собственных handlers
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            force=True  # Перезаписываем существующую конфигурацию
        )


# Автоматически настраиваем root logger при импорте модуля
setup_root_logger()


