"""
Модуль для стратегий движения платформы.

Содержит классы для:
- Основной логики движения платформы
- Обработки зон (bricks zone, separation zone)
- Отслеживания целевой позиции
"""

from .paddle_movement import PaddleMovementStrategy
from .zone_handler import ZoneHandler
from .target_tracker import TargetTracker

__all__ = ["PaddleMovementStrategy", "ZoneHandler", "TargetTracker"]
