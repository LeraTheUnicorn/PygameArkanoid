"""
Конфигурация для AI игрока.

Содержит все константы и настройки для работы AI системы.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class GameZones:
    """Конфигурация игровых зон."""
    bricks_zone_end: int = 210  # Верхняя граница зоны с кубиками
    ball_diameter: int = 16  # Диаметр мяча
    paddle_zone_offset: int = 60  # Отступ от низа экрана до начала зоны платформы
    ball_reset_height: int = 50  # Высота, выше которой сбрасывается отслеживание зоны разделения
    
    @property
    def separation_zone_start(self) -> int:
        """Начало зоны разделения (между кубиками и платформой)."""
        return self.bricks_zone_end + self.ball_diameter
    
    def paddle_zone_start(self, screen_height: int) -> int:
        """Начало зоны платформы."""
        return screen_height - self.paddle_zone_offset


@dataclass(frozen=True)
class PaddleConfig:
    """Конфигурация платформы."""
    width: int = 120  # Ширина платформы
    safe_margin: int = 30  # Безопасный отступ от края экрана
    min_movement_distance: int = 5  # Минимальное расстояние для движения (пиксели)
    zone_size: int = 40  # Размер зоны платформы (ширина / 3)
    zone_half: int = 20  # Половина зоны платформы
    edge_proximity_threshold: int = 40  # Порог близости к краю экрана для прямого прицеливания


@dataclass(frozen=True)
class BrickConfig:
    """Конфигурация кирпичей."""
    default_width: int = 60  # Ширина кирпича по умолчанию
    default_height: int = 30  # Высота кирпича по умолчанию
    precision_targeting_threshold: int = 10  # Порог количества кирпичей для точного прицеливания


@dataclass(frozen=True)
class BallConfig:
    """Конфигурация мяча."""
    diameter: int = 16  # Диаметр мяча
    radius: int = 8  # Радиус мяча
    default_speed: int = 5  # Скорость мяча по умолчанию
    velocity_tolerance: float = 0.1  # Допустимое отклонение скорости для определения отскока


@dataclass(frozen=True)
class AIConfig:
    """Основная конфигурация AI."""
    zones: GameZones = field(default_factory=GameZones)
    paddle: PaddleConfig = field(default_factory=PaddleConfig)
    brick: BrickConfig = field(default_factory=BrickConfig)
    ball: BallConfig = field(default_factory=BallConfig)
    
    # Параметры обучения и логирования
    debug_log_interval: int = 100  # Интервал логирования отладочной информации
    loop_detection_threshold: int = 5  # Порог повторений для обнаружения зацикливания
    max_empty_bounces: int = 1  # Максимум отбитий в пустоту подряд
    
    # Параметры прицеливания
    precision_priority_threshold: int = 10  # Порог для приоритета точного прицеливания
    success_probability_threshold: float = 0.5  # Порог вероятности успеха
    low_success_probability_threshold: float = 0.2  # Низкий порог вероятности успеха
    confidence_default: float = 0.7  # Значение уверенности по умолчанию
    
    # Параметры логирования
    debug_log_chance: float = 0.1  # Вероятность логирования отладочной информации (10%)
    
    # Параметры зон платформы для прицеливания
    paddle_zone_left_center: int = -40  # Центр левой зоны платформы
    paddle_zone_center: int = 0  # Центр центральной зоны платформы
    paddle_zone_right_center: int = 40  # Центр правой зоны платформы
    paddle_zone_offset_range: tuple = (-40, 41)  # Диапазон смещений для тестирования
    paddle_zone_offset_step: int = 10  # Шаг смещения для тестирования
    
    # Параметры истории целей
    recent_targets_max: int = 5  # Максимальное количество последних целей для отслеживания
    successful_hits_max: int = 100  # Максимальное количество успешных ударов в истории
    successful_hits_keep: int = 50  # Количество успешных ударов для сохранения после очистки

