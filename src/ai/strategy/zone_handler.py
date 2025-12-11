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
            Текущая позиция платформы (не двигаемся)
        """
        if not game_state:
            return self.screen_width // 2

        # КРИТИЧНО: НЕ сбрасываем отслеживание зоны разделения и целевую позицию,
        # так как мяч может временно попасть в зону кубиков (при отскоке),
        # но потом вернуться в зону разделения
        if ball_y < self.config.zones.ball_reset_height and not self.separation_zone_tracker.target_position_set:
            self.separation_zone_tracker.ball_entered_separation_zone = False
            self.separation_zone_tracker.target_position_set = False
            self.separation_zone_tracker.target_position = None

        return int(game_state.paddle_position.x)

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
            Оптимальная позиция платформы или None, если нужно продолжить расчет
        """
        if not game_state:
            return None

        separation_zone_start = zones["separation_zone_start"]
        paddle_zone_start = zones["paddle_zone_start"]

        # Если мяч в разделительной зоне, но движется вверх — не дёргаем платформу
        if separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y <= 0:
            return int(game_state.paddle_position.x)

        # Проверяем, вошел ли мяч в зону разделения
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

        # Если позиция уже зафиксирована в зоне разделения - возвращаем её БЕЗ пересчета
        if in_separation_zone and self.separation_zone_tracker.target_position_set:
            fixed_position = self.separation_zone_tracker.target_position
            if fixed_position is not None:
                saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
                current_vel_x = game_state.ball_velocity.x if game_state else 0

                if saved_vel_x is not None and abs(current_vel_x - saved_vel_x) <= self.config.ball.velocity_tolerance:
                    return int(fixed_position)
                else:
                    return int(fixed_position)

        # Если мяч только что вошел в зону разделения, отмечаем это
        if in_separation_zone and not self.separation_zone_tracker.ball_entered_separation_zone:
            self.separation_zone_tracker.ball_entered_separation_zone = True

        return None  # Продолжаем расчет позиции

    def handle_upward_movement(self, ball_y: float, game_state: Optional[GameState]) -> int:
        """
        Обрабатывает ситуацию, когда мяч движется вверх.

        Args:
            ball_y: Y-координата мяча
            game_state: Текущее состояние игры

        Returns:
            Оптимальная позиция платформы
        """
        # Мяч движется вверх — обрабатываем возможный отскок от потолка
        if ball_y < self.config.zones.ball_reset_height:
            # Обработка отскока от потолка - возвращаем текущую позицию
            # (более сложная логика может быть добавлена позже)
            if game_state:
                return int(game_state.paddle_position.x)
            return self.screen_width // 2

        # Иначе просто сопровождаем мяч
        if game_state:
            return int(game_state.ball_position.x)
        return self.screen_width // 2
