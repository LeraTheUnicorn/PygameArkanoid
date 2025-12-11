"""
Класс для оптимизированного логирования отладочной информации.

Использует счетчик кадров вместо random для предсказуемого логирования.
"""


class DebugLogger:
    """
    Оптимизированный логгер для отладочной информации.
    
    Использует счетчик кадров вместо random.random() для более
    предсказуемого и производительного логирования.
    """
    
    def __init__(self, log_interval: int = 100):
        """
        Инициализирует DebugLogger.
        
        Args:
            log_interval: Интервал логирования (каждый N-й кадр)
        """
        self._frame_counter: int = 0
        self._log_interval: int = log_interval
        # Глобальный счетчик кадров, который не сбрасывается (для interval_multiplier)
        self._global_frame_counter: int = 0
    
    def should_log(self) -> bool:
        """
        Проверяет, нужно ли логировать в текущем кадре.
        
        Returns:
            True, если нужно логировать, False иначе
        """
        self._frame_counter += 1
        self._global_frame_counter += 1
        if self._frame_counter >= self._log_interval:
            self._frame_counter = 0
            return True
        return False
    
    def should_log_with_multiplier(self, multiplier: int) -> bool:
        """
        Проверяет, нужно ли логировать с учетом множителя интервала.
        
        Args:
            multiplier: Множитель интервала (например, 10 означает логирование в 10 раз реже)
        
        Returns:
            True, если нужно логировать, False иначе
        """
        if multiplier <= 0:
            return False
        
        if multiplier == 1:
            # Для multiplier=1 используем стандартную логику с сбросом
            self._frame_counter += 1
            self._global_frame_counter += 1
            if self._frame_counter >= self._log_interval:
                self._frame_counter = 0
                return True
            return False
        
        # Для multiplier != 1 используем глобальный счетчик без сброса
        # Проверяем перед инкрементом, чтобы первый кадр (0) тоже учитывался
        effective_interval = self._log_interval * multiplier
        should_log = self._global_frame_counter % effective_interval == 0
        self._global_frame_counter += 1
        return should_log
    
    def reset(self) -> None:
        """Сбрасывает счетчик кадров."""
        self._frame_counter = 0
        self._global_frame_counter = 0
    
    def set_interval(self, interval: int) -> None:
        """
        Устанавливает новый интервал логирования.
        
        Args:
            interval: Новый интервал (каждый N-й кадр)
        """
        self._log_interval = max(1, interval)
    
    def get_interval(self) -> int:
        """Возвращает текущий интервал логирования."""
        return self._log_interval

