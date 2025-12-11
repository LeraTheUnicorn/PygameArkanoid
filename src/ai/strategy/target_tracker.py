"""
Модуль для отслеживания целевой позиции платформы.

Содержит класс TargetTracker для управления состоянием целевой позиции.
"""

from typing import Optional, Any, TYPE_CHECKING

from ..config import AIConfig

if TYPE_CHECKING:
    from ..ai_player import SeparationZoneTracker


class TargetTracker:
    """Класс для отслеживания целевой позиции платформы."""

    def __init__(
        self,
        config: AIConfig,
        separation_zone_tracker: "SeparationZoneTracker",
    ):
        """
        Инициализация TargetTracker.

        Args:
            config: Конфигурация AI
            separation_zone_tracker: Трекер зоны разделения (dataclass)
        """
        self.config = config
        self.separation_zone_tracker = separation_zone_tracker

    def set_target_position(self, position: int, reason: str, logger: Optional[Any] = None) -> None:
        """
        Устанавливает целевую позицию, если она еще не установлена.

        Args:
            position: Целевая позиция
            reason: Причина установки позиции
            logger: Логгер для записи предупреждений
        """
        if self.separation_zone_tracker.target_position_set:
            old_pos = self.separation_zone_tracker.target_position
            if old_pos is not None and logger:
                logger.warning(
                    f"[RULE VIOLATION] ФЛАГ: Попытка установить позицию ПОВТОРНО ({reason})! "
                    f"Старая позиция={old_pos:.1f}, Новая позиция={position:.1f}, "
                    f"Разница={abs(old_pos - position):.1f}px"
                )
            self.separation_zone_tracker.game_restart_required = True
        else:
            self.separation_zone_tracker.target_position = position
            self.separation_zone_tracker.target_position_set = True
            if logger:
                logger.debug(
                    f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые ({reason})! "
                    f"target_position={position:.1f}"
                )

    def reset_target_position(self) -> None:
        """Сбрасывает целевую позицию."""
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False

    def get_target_position(self) -> Optional[int]:
        """
        Получает текущую целевую позицию.

        Returns:
            Целевая позиция или None
        """
        if self.separation_zone_tracker.target_position_set:
            return int(self.separation_zone_tracker.target_position) if self.separation_zone_tracker.target_position is not None else None
        return None

    def is_target_set(self) -> bool:
        """
        Проверяет, установлена ли целевая позиция.

        Returns:
            True, если позиция установлена
        """
        return self.separation_zone_tracker.target_position_set

    def check_wall_bounce(self, current_vel_x: float) -> bool:
        """
        Проверяет, произошел ли отскок от стены.

        Args:
            current_vel_x: Текущая X-скорость мяча

        Returns:
            True, если произошел отскок от стены
        """
        saved_vel_x = self.separation_zone_tracker.saved_ball_vel_x
        if saved_vel_x is None:
            return False

        return bool(abs(current_vel_x - saved_vel_x) > self.config.ball.velocity_tolerance)

    def update_saved_velocity(self, vel_x: float) -> None:
        """
        Обновляет сохраненную скорость мяча.

        Args:
            vel_x: X-скорость мяча
        """
        self.separation_zone_tracker.saved_ball_vel_x = vel_x
