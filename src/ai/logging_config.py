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
    
    # НЕ создаем базовую конфигурацию с StreamHandler
    # Файловые handlers создаются в ai_player.py при инициализации
    # Это гарантирует, что логи идут только в файлы, а не в консоль
    
    return logger


def setup_root_logger() -> None:
    """
    Настраивает root logger для всего проекта.
    Вызывается один раз при запуске приложения.
    
    КРИТИЧНО: Устанавливает уровень для root logger, чтобы ВСЕ дочерние логгеры
    наследовали этот уровень (если их собственный уровень NOTSET).
    
    ВАЖНО: Не создает StreamHandler для консоли - все логи идут только в файлы.
    Сводная статистика после игры выводится через print() в ai_player.py.
    """
    log_level = get_log_level()
    
    # Получаем root logger
    root_logger = logging.getLogger()
    
    # Устанавливаем уровень для root logger
    # Это критически важно - все дочерние логгеры будут наследовать этот уровень
    root_logger.setLevel(log_level)
    
    # КРИТИЧНО: Удаляем все StreamHandler (консольные handlers) из root logger
    # Все логи должны идти только в файлы, а не в консоль
    handlers_to_remove = []
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handlers_to_remove.append(handler)
    
    for handler in handlers_to_remove:
        root_logger.removeHandler(handler)
        handler.close()
    
    # Обновляем уровень для всех оставшихся handlers root logger
    for handler in root_logger.handlers:
        handler.setLevel(log_level)
    
    # НЕ создаем базовую конфигурацию с StreamHandler
    # Файловые handlers создаются в ai_player.py при инициализации
    # Это гарантирует, что логи идут только в файлы, а не в консоль


# Автоматически настраиваем root logger при импорте модуля
setup_root_logger()


