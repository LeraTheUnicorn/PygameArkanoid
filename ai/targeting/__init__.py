"""
Модуль для прицеливания и выбора целей.

Содержит классы для:
- Выбора целевых кирпичей
- Расчет позиций для прицеливания
- Анализ траекторий для попадания
"""

from .target_selector import TargetSelector
from .position_calculator import PositionCalculator

__all__ = ["TargetSelector", "PositionCalculator"]
