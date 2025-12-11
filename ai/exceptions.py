"""
Кастомные исключения для AI системы.
"""


class AIPlayerError(Exception):
    """Базовое исключение для AIPlayer."""
    pass


class InvalidStateError(AIPlayerError):
    """Ошибка недопустимого состояния игры."""
    pass


class ConfigurationError(AIPlayerError):
    """Ошибка конфигурации AI."""
    pass


class PredictionError(AIPlayerError):
    """Ошибка при предсказании траектории или позиции."""
    pass


class LearningError(AIPlayerError):
    """Ошибка в системе обучения."""
    pass


class DataError(AIPlayerError):
    """Ошибка при работе с данными (загрузка/сохранение)."""
    pass

