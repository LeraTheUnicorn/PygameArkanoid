"""
Модуль для обработки игровых зон.

Содержит класс ZoneHandler для обработки различных зон игры (зона кубиков, зона разделения).
"""

from typing import Optional, Dict, Any

from ..game_state import GameState
from ..config import AIConfig


class ZoneHandler:
    """Класс для обработки игровых зон."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        config: AIConfig,
        separation_zone_tracker: Any,  # SeparationZoneTracker dataclass
    ):
        """
        Инициализация ZoneHandler.

        Args:
            screen_width: Ширина экрана
            screen_height: Высота экрана
            config: Конфигурация AI
            separation_zone_tracker: Трекер зоны разделения (dataclass)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config = config
        self.separation_zone_tracker = separation_zone_tracker

    def calculate_zones(self) -> Dict[str, float]:
        """
        Рассчитывает границы игровых зон.

        Returns:
            Словарь с границами зон
        """
        separation_zone_start = self.separation_zone_tracker.separation_zone_start
        paddle_zone_start = self.separation_zone_tracker.paddle_zone_start

        return {
            "separation_zone_start": separation_zone_start,
            "paddle_zone_start": paddle_zone_start,
        }

    def handle_bricks_zone(self, ball_y: float, game_state: Optional[GameState]) -> int:
        """
        Обрабатывает ситуацию, когда мяч находится в зоне кубиков.

        Args:
            ball_y: Y-координата мяча
            game_state: Текущее состояние игры

        Returns:
            Направление движения платформы (-1, 0, 1). Возвращает 0 (не двигаемся).
        """
        # КРИТИЧНО: НЕ сбрасываем отслеживание зоны разделения и целевую позицию,
        # так как мяч может временно попасть в зону кубиков (при отскоке),
        # но потом вернуться в зону разделения
        if game_state and ball_y < self.config.zones.ball_reset_height and not self.separation_zone_tracker.target_position_set:
            self.separation_zone_tracker.ball_entered_separation_zone = False
            self.separation_zone_tracker.target_position_set = False
            self.separation_zone_tracker.target_position = None

        # В зоне кубиков платформа не двигается
        return 0

    def handle_separation_zone(
        self, ball_y: float, ball_vel_y: float, zones: Dict[str, float], game_state: Optional[GameState]
    ) -> Optional[int]:
        """
        Обрабатывает ситуацию, когда мяч находится в зоне разделения.

        Args:
            ball_y: Y-координата мяча
            ball_vel_y: Y-скорость мяча
            zones: Словарь с границами зон
            game_state: Текущее состояние игры

        Returns:
            Направление движения платформы (-1, 0, 1) или None, если нужно продолжить расчет
        """
        if not game_state:
            return None

        separation_zone_start = zones["separation_zone_start"]
        paddle_zone_start = zones["paddle_zone_start"]

        # Если мяч в разделительной зоне, но движется вверх — не двигаем платформу
        if separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y <= 0:
            return 0

        # Проверяем, вошел ли мяч в зону разделения
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

        # Если позиция уже зафиксирована в зоне разделения - возвращаем None,
        # чтобы paddle_movement.py обработал движение к зафиксированной позиции
        if in_separation_zone and self.separation_zone_tracker.target_position_set:
            # Проверяем, не изменилась ли скорость (отскок от стены)
            fixed_position = self.separation_zone_tracker.target_position
            if fixed_position is not None:
                saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
                current_vel_x = game_state.ball_velocity.x if game_state else 0

                # Если скорость изменилась - сбрасываем цель (это обработается в paddle_movement.py)
                if saved_vel_x is not None and abs(current_vel_x - saved_vel_x) > self.config.ball.velocity_tolerance:
                    return None  # Продолжаем расчет - цель будет сброшена в paddle_movement.py
                # Иначе возвращаем None, чтобы paddle_movement.py обработал движение к зафиксированной позиции
                return None

        # Если мяч только что вошел в зону разделения, отмечаем это
        if in_separation_zone and not self.separation_zone_tracker.ball_entered_separation_zone:
            self.separation_zone_tracker.ball_entered_separation_zone = True

        return None  # Продолжаем расчет позиции

    def handle_upward_movement(self, ball_y: float, game_state: Optional[GameState], current_x: int) -> int:
        """
        Обрабатывает ситуацию, когда мяч движется вверх.

        Args:
            ball_y: Y-координата мяча
            game_state: Текущее состояние игры
            current_x: Текущая X-координата платформы

        Returns:
            Направление движения платформы (-1, 0, 1)
        """
        # Мяч движется вверх — обрабатываем возможный отскок от потолка
        if ball_y < self.config.zones.ball_reset_height:
            # Обработка отскока от потолка - не двигаемся
            return 0

        # Иначе просто сопровождаем мяч
        if game_state:
            ball_x = game_state.ball_position.x
            distance = ball_x - current_x
            tolerance = 5
            if abs(distance) <= tolerance:
                return 0
            return 1 if distance > 0 else -1
        
        return 0
