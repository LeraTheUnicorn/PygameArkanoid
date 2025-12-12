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

    def set_target_position(self, position: int, reason: str, logger: Optional[Any] = None, current_pos: Optional[int] = None) -> None:
        """
        Устанавливает целевую позицию, если она еще не установлена.
        
        ✅ ИСПРАВЛЕНО: Добавлена проверка максимального расстояния до цели (200px).

        Args:
            position: Целевая позиция
            reason: Причина установки позиции
            logger: Логгер для записи предупреждений
            current_pos: Текущая позиция платформы (для проверки расстояния)
        """
        # ✅ ДОБАВЛЕНО: Проверка максимального расстояния до цели
        # УВЕЛИЧЕНО до 250px для большей гибкости (проверка достижимости уже есть в paddle_movement)
        MAX_TARGET_DISTANCE = 250  # пикселей
        
        if current_pos is not None:
            distance = abs(position - current_pos)
            if distance > MAX_TARGET_DISTANCE:
                # Корректируем цель, чтобы расстояние не превышало MAX_TARGET_DISTANCE
                if position > current_pos:
                    position = current_pos + MAX_TARGET_DISTANCE
                else:
                    position = current_pos - MAX_TARGET_DISTANCE
                if logger:
                    logger.debug(
                        f"[TARGET DISTANCE] Расстояние до цели большое ({distance:.1f}px > {MAX_TARGET_DISTANCE}px), "
                        f"корректируем до {position:.1f}px (reason: {reason})"
                    )
        
        if self.separation_zone_tracker.target_position_set:
            old_pos = self.separation_zone_tracker.target_position
            if old_pos is not None:
                # КРИТИЧНО: Если позиция та же самая (разница < 5px) - это не нарушение,
                # просто игнорируем попытку установить ту же позицию
                position_diff = abs(old_pos - position)
                if position_diff < 5:
                    if logger:
                        logger.debug(
                            f"[POSITION UPDATE] Попытка установить ту же позицию ({reason})! "
                            f"Старая позиция={old_pos:.1f}, Новая позиция={position:.1f}, "
                            f"Разница={position_diff:.1f}px - игнорируем"
                        )
                    return  # Игнорируем - позиция уже установлена
                
                # КРИТИЧНО: Если позиция отличается значительно - это нарушение правила
                # Вместо перезапуска игры просто сбрасываем целевую позицию и устанавливаем новую
                if logger:
                    logger.warning(
                        f"[RULE VIOLATION] Попытка установить ДРУГУЮ позицию ({reason})! "
                        f"Старая позиция={old_pos:.1f}, Новая позиция={position:.1f}, "
                        f"Разница={position_diff:.1f}px - сбрасываем и устанавливаем новую"
                    )
                # Сбрасываем старую позицию и устанавливаем новую
                self.reset_target_position()
                self.separation_zone_tracker.target_position = position
                self.separation_zone_tracker.target_position_set = True
                if logger:
                    logger.debug(
                        f"[POSITION RESET] Позиция сброшена и установлена заново ({reason})! "
                        f"target_position={position:.1f}"
                    )
            else:
                # Старая позиция была None - просто устанавливаем новую
                self.separation_zone_tracker.target_position = position
                self.separation_zone_tracker.target_position_set = True
                if logger:
                    logger.debug(
                        f"[POSITION FIXED] Позиция установлена ({reason})! "
                        f"target_position={position:.1f}"
                    )
        else:
            self.separation_zone_tracker.target_position = position
            self.separation_zone_tracker.target_position_set = True
            if logger:
                logger.debug(
                    f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые ({reason})! "
                    f"target_position={position:.1f}"
                )

    def reset_target_position(self) -> None:
        """✅ ИСПРАВЛЕНО: Сбрасывает целевую позицию И сохраненную скорость."""
        self.separation_zone_tracker.target_position_set = False
        self.separation_zone_tracker.target_position = None
        self.separation_zone_tracker.paddle_moved_after_set = False
        self.separation_zone_tracker.paddle_reached_target = False
        # ✅ ДОБАВЛЕНО: Также сбрасываем сохраненную скорость для переобнаружения отскоков
        self.separation_zone_tracker.saved_ball_vel_x = None

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
        return bool(self.separation_zone_tracker.target_position_set)

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

    def get_saved_velocity(self) -> Optional[float]:
        """
        Получает сохраненную скорость мяча.

        Returns:
            Сохраненная X-скорость мяча или None
        """
        return self.separation_zone_tracker.saved_ball_vel_x
    
    def on_ball_bounce(self, logger: Optional[Any] = None) -> None:
        """
        ✅ ДОБАВЛЕНО: Вызывается при каждом отскоке мяча для пересчета цели.
        
        Args:
            logger: Логгер для записи информации
        """
        if self.is_target_set():
            if logger:
                logger.debug(
                    f"[BALL BOUNCE] Обнаружен отскок мяча, сбрасываем целевую позицию для пересчета"
                )
            self.reset_target_position()
    
    def validate_target_distance(self, current_pos: int, target_pos: int, max_reachable_distance: Optional[float] = None) -> int:
        """
        ✅ ДОБАВЛЕНО: Проверка физической достижимости цели.
        
        Args:
            current_pos: Текущая позиция платформы
            target_pos: Целевая позиция
            max_reachable_distance: Максимально достижимое расстояние (если None, используется MAX_TARGET_DISTANCE)
        
        Returns:
            Скорректированная целевая позиция
        """
        MAX_TARGET_DISTANCE = 200  # пикселей
        
        distance = abs(target_pos - current_pos)
        max_distance = max_reachable_distance if max_reachable_distance is not None else MAX_TARGET_DISTANCE
        
        if distance > max_distance:
            # Корректируем цель к ближайшей достижимой позиции
            if target_pos > current_pos:
                return current_pos + int(max_distance)
            else:
                return current_pos - int(max_distance)
        
        return target_pos
