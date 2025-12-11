"""
Модуль для стратегии движения платформы.

Содержит класс PaddleMovementStrategy с разделенной логикой движения платформы.
"""

import time
from typing import Optional, Dict, Any

from ..game_state import GameState
from ..config import AIConfig
from ..position_optimizer import PositionOptimizer
from ..learning_system import LearningSystem
from .zone_handler import ZoneHandler
from .target_tracker import TargetTracker


class PaddleMovementStrategy:
    """Класс для стратегии движения платформы с разделенной логикой."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        paddle_width: int,
        config: AIConfig,
        position_optimizer: PositionOptimizer,
        learning_system: LearningSystem,
        zone_handler: ZoneHandler,
        target_tracker: TargetTracker,
        get_optimal_paddle_position_func: Any,  # Функция для получения оптимальной позиции
        loop_prevention_system: Dict[str, Any],
        smoothness_system: Dict[str, Any],
        separation_zone_tracker: Any,
        logger: Any,
        log_paddle_movement_func: Any,
        should_log_debug_func: Any,
        current_game_state: Optional[GameState] = None,
    ):
        """
        Инициализация PaddleMovementStrategy.

        Args:
            screen_width: Ширина экрана
            screen_height: Высота экрана
            paddle_width: Ширина платформы
            config: Конфигурация AI
            position_optimizer: Оптимизатор позиции
            learning_system: Система обучения
            zone_handler: Обработчик зон
            target_tracker: Трекер целей
            get_optimal_paddle_position_func: Функция для получения оптимальной позиции
            loop_prevention_system: Система предотвращения зацикливания
            smoothness_system: Система плавности движения
            separation_zone_tracker: Трекер зоны разделения
            logger: Логгер
            log_paddle_movement_func: Функция логирования движения
            should_log_debug_func: Функция проверки необходимости логирования
            current_game_state: Текущее состояние игры
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.paddle_width = paddle_width
        self.config = config
        self.position_optimizer = position_optimizer
        self.learning_system = learning_system
        self.zone_handler = zone_handler
        self.target_tracker = target_tracker
        self.get_optimal_paddle_position = get_optimal_paddle_position_func
        self.loop_prevention_system = loop_prevention_system
        self.smoothness_system = smoothness_system
        self.separation_zone_tracker = separation_zone_tracker
        self._logger = logger
        self._log_paddle_movement = log_paddle_movement_func
        self._should_log_debug = should_log_debug_func
        self.current_game_state = current_game_state

    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции с предотвращением зацикливания.

        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Базовая скорость движения платформы

        Returns:
            Смещение платформы (-1, 0, 1)
        """
        # Проверка состояния
        if not self._validate_state():
            return self._fallback_movement(current_x)

        try:
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )

            # Обработка зоны кубиков
            zones = self.zone_handler.calculate_zones()
            if ball_y < zones["separation_zone_start"]:
                bricks_count = len(self.current_game_state.remaining_bricks) if self.current_game_state else 50
                is_last_brick = bricks_count == 1
                if not is_last_brick:
                    return self.zone_handler.handle_bricks_zone(ball_y, self.current_game_state)

            # Обработка потерянного мяча
            lost_ball_result = self._handle_lost_ball(ball_y, current_x)
            if lost_ball_result is not None:
                return lost_ball_result

            # Обработка зоны разделения
            separation_result = self.zone_handler.handle_separation_zone(
                ball_y, ball_vel_y, zones, self.current_game_state
            )
            if separation_result is not None:
                return separation_result

            # Фиксация целевой позиции
            fixed_target_result = self._handle_fixed_target(
                current_x, paddle_speed, ball_y, ball_vel_y, zones
            )
            if fixed_target_result is not None:
                return fixed_target_result

            # Установка новой цели
            new_target_result = self._set_new_target(
                current_x, paddle_speed, ball_y, ball_vel_y, zones
            )
            if new_target_result is not None:
                return new_target_result

            # Обычная логика движения
            return self._handle_normal_movement(current_x, paddle_speed)

        except Exception as e:
            self._logger.error(f"Ошибка при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)

    def _validate_state(self) -> bool:
        """
        Проверяет валидность состояния для движения платформы.

        Returns:
            True, если состояние валидно
        """
        if not self.current_game_state:
            return False

        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if hasattr(self.current_game_state, "ball_velocity")
            else 0
        )

        if ball_vel_y == 0:
            self._log_paddle_movement(
                self.current_game_state.paddle_position.x,
                self.current_game_state.paddle_position.x,
                "ball_vel_y_zero_warning",
                0.5
            )

        return True

    def _handle_lost_ball(self, ball_y: float, current_x: int) -> Optional[int]:
        """
        Обрабатывает ситуацию, когда мяч потерян.

        Args:
            ball_y: Y-координата мяча
            current_x: Текущая X-координата платформы

        Returns:
            Смещение платформы или None, если мяч не потерян
        """
        if not self.current_game_state:
            return None

        paddle_y = self.current_game_state.paddle_position.y
        ball_lost = ball_y > paddle_y

        if ball_lost:
            if self._should_log_debug(interval_multiplier=2):
                self._logger.debug(
                    f"[PADDLE DEBUG] Мяч потерян (ball_y={ball_y:.1f} > paddle_y={paddle_y:.1f}), "
                    f"платформа не двигается"
                )
            self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle", 1.0)
            return 0

        return None

    def _handle_fixed_target(
        self,
        current_x: int,
        paddle_speed: int,
        ball_y: float,
        ball_vel_y: float,
        zones: Dict[str, float],
    ) -> Optional[int]:
        """
        Обрабатывает движение к зафиксированной целевой позиции.

        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Скорость движения платформы
            ball_y: Y-координата мяча
            ball_vel_y: Y-скорость мяча
            zones: Словарь с границами зон

        Returns:
            Смещение платформы или None, если позиция не зафиксирована
        """
        if not self.target_tracker.is_target_set():
            return None

        # КРИТИЧНО: Проверяем, не потерян ли мяч
        if not self.current_game_state:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        ball_lost = ball_y > paddle_y
        
        if ball_lost:
            # Мяч потерян - не двигаемся
            return None

        separation_zone_start = zones["separation_zone_start"]
        paddle_zone_start = zones["paddle_zone_start"]
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

        # КРИТИЧНО: Платформа должна двигаться к зафиксированной цели,
        # даже если мяч временно не в зоне разделения (например, близко к платформе)
        # НО только если мяч не потерян и не в зоне кубиков
        if not in_separation_zone:
            # Если мяч в зоне кубиков (выше зоны разделения) - не двигаемся
            if ball_y < separation_zone_start:
                return None
            # Если мяч близко к платформе (ниже зоны разделения, но не потерян) - продолжаем движение к цели
            # Это позволяет платформе завершить движение к зафиксированной позиции

        current_target = self.target_tracker.get_target_position()
        if current_target is None:
            return None

        # Проверяем отскоки от стены и кирпичей
        if self.current_game_state:
            current_vel_x = (
                self.current_game_state.ball_velocity.x
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )

            if self.target_tracker.check_wall_bounce(current_vel_x):
                # Отскок от стены - сбрасываем цель
                self.target_tracker.reset_target_position()
                self.target_tracker.update_saved_velocity(current_vel_x)
                return None

            self.target_tracker.update_saved_velocity(current_vel_x)

        # Двигаемся к зафиксированной позиции
        target_pos = int(current_target)
        distance_to_target = abs(current_x - target_pos)
        tolerance = 15  # Равен скорости движения платформы

        # КРИТИЧНО: Логируем для диагностики проблем с движением
        if self._should_log_debug(interval_multiplier=1):  # Каждый 100-й кадр
            self._logger.debug(
                f"[FIXED TARGET] current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
                f"distance={distance_to_target:.1f}, tolerance={tolerance}, "
                f"in_separation_zone={in_separation_zone}, ball_y={ball_y:.1f}"
            )

        if distance_to_target > tolerance:
            movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
            if movement != 0:
                self._update_loop_tracking(movement, int(current_x), int(target_pos))
                self._update_smoothness_tracking(movement, current_x)
                self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target", 1.0)
                return movement
        else:
            # КРИТИЧНО: Логируем, почему не двигаемся (достигли цели)
            if self._should_log_debug(interval_multiplier=1):
                self._logger.debug(
                    f"[FIXED TARGET] Достигли цели! distance={distance_to_target:.1f} <= tolerance={tolerance}"
                )
            return 0

    def _set_new_target(
        self,
        current_x: int,
        paddle_speed: int,
        ball_y: float,
        ball_vel_y: float,
        zones: Dict[str, float],
    ) -> Optional[int]:
        """
        Устанавливает новую целевую позицию.

        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Скорость движения платформы
            ball_y: Y-координата мяча
            ball_vel_y: Y-скорость мяча
            zones: Словарь с границами зон

        Returns:
            Смещение платформы или None, если цель не установлена
        """
        separation_zone_start = zones["separation_zone_start"]
        paddle_zone_start = zones["paddle_zone_start"]
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

        if not in_separation_zone or self.target_tracker.is_target_set():
            return None

        if not self.current_game_state:
            return None

        paddle_y = self.current_game_state.paddle_position.y
        ball_lost = ball_y > paddle_y

        if ball_lost:
            return None

        # Устанавливаем целевую позицию
        optimal_x = self.get_optimal_paddle_position()

        if optimal_x is None:
            return self._fallback_movement(current_x)

        # Проверяем достижимость цели
        distance_to_target = abs(current_x - optimal_x)
        distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
        time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')

        if time_to_paddle != float('inf') and time_to_paddle > 0 and distance_to_target > 0:
            frames_to_reach = distance_to_target / paddle_speed if paddle_speed > 0 else float('inf')
            if frames_to_reach > time_to_paddle * 1.1:
                max_distance = paddle_speed * time_to_paddle * 0.9
                if optimal_x > current_x:
                    optimal_x = min(optimal_x, current_x + max_distance)
                else:
                    optimal_x = max(optimal_x, current_x - max_distance)

        # Сохраняем целевую позицию
        if self.current_game_state:
            current_vel_x = (
                self.current_game_state.ball_velocity.x
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            self.target_tracker.set_target_position(int(optimal_x), "new_target", self._logger)
            self.target_tracker.update_saved_velocity(current_vel_x)

        target_pos = int(optimal_x)
        distance_to_target = abs(current_x - target_pos)

        if target_pos == current_x:
            return 0

        if distance_to_target <= 25:
            return 0

        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
        if movement == 0:
            return self._fallback_movement(current_x)

        self._update_loop_tracking(movement, int(current_x), int(target_pos))
        self._update_smoothness_tracking(movement, current_x)
        self._log_paddle_movement(current_x, target_pos, "moving_to_new_target", 0.9)
        return movement

    def _handle_normal_movement(self, current_x: int, paddle_speed: int) -> int:
        """
        Обрабатывает обычную логику движения платформы.

        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Скорость движения платформы

        Returns:
            Смещение платформы (-1, 0, 1)
        """
        optimal_x = self.get_optimal_paddle_position()

        if optimal_x is None:
            return self._fallback_movement(current_x)

        # Проверяем зацикливание
        if not self.target_tracker.is_target_set():
            self._change_strategy_if_looping()
            if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                optimal_x = self._apply_alternative_strategy(optimal_x)
                if optimal_x is None:
                    return self._fallback_movement(current_x)

        # Проверяем дрожание
        jitter_detected = self._detect_jitter()
        precision_tolerance = 2
        if jitter_detected:
            precision_tolerance = max(5, precision_tolerance + 2)
            self.smoothness_system["smoothness_penalty"] = min(
                1.0, self.smoothness_system["smoothness_penalty"] + 0.1
            )
        else:
            self.smoothness_system["smoothness_penalty"] = max(
                0.0, self.smoothness_system["smoothness_penalty"] - 0.05
            )

        distance_to_optimal = abs(optimal_x - current_x)
        min_movement_distance = self.smoothness_system["min_movement_distance"]

        if distance_to_optimal < min_movement_distance:
            if distance_to_optimal <= precision_tolerance:
                return 0
            else:
                return self._calculate_smooth_movement(current_x, optimal_x, distance_to_optimal)
        elif distance_to_optimal <= precision_tolerance:
            return 0
        else:
            # Адаптивная скорость
            adjusted_paddle_speed = paddle_speed
            if self.current_game_state:
                ball_speed = self.current_game_state.ball_speed
                speed_multiplier = self.learning_system.get_adaptive_paddle_speed(
                    ball_speed, distance_to_optimal
                )
                base_speed_multiplier = 10.0
                if distance_to_optimal > 150:
                    base_speed_multiplier = 15.0
                elif distance_to_optimal > 100:
                    base_speed_multiplier = 12.0

                adjusted_paddle_speed = int(paddle_speed * base_speed_multiplier)
                adjusted_paddle_speed = max(int(paddle_speed * 0.8), adjusted_paddle_speed)

            movement = self.position_optimizer.calculate_paddle_movement(
                current_x, optimal_x, adjusted_paddle_speed
            )

            if movement == 0 and optimal_x != current_x:
                movement = self._fallback_movement(current_x)

            self._update_loop_tracking(movement, current_x, optimal_x)
            self._update_smoothness_tracking(movement, current_x)

            return movement

    def _fallback_movement(self, current_x: int) -> int:
        """
        Резервное движение платформы.

        Args:
            current_x: Текущая X-координата платформы

        Returns:
            Смещение платформы (-1, 0, 1)
        """
        if not self.current_game_state:
            return 0

        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y

        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y != 0 else 0
            if time_to_paddle > 0:
                predicted_x = ball_x + vel_x * time_to_paddle

                ball_radius = self.config.ball.radius
                while (
                    predicted_x < ball_radius
                    or predicted_x > self.screen_width - ball_radius
                ):
                    if predicted_x < ball_radius:
                        predicted_x = 2 * ball_radius - predicted_x
                        vel_x = abs(vel_x)
                    elif predicted_x > self.screen_width - ball_radius:
                        predicted_x = 2 * (self.screen_width - ball_radius) - predicted_x
                        vel_x = -abs(vel_x)
                target_x = predicted_x
            else:
                target_x = ball_x
        else:
            prediction_factor = abs(vel_x) * 2
            if vel_x > 0:
                target_x = ball_x + prediction_factor
            elif vel_x < 0:
                target_x = ball_x - prediction_factor
            else:
                target_x = ball_x

        distance = target_x - current_x
        tolerance = 3

        if abs(distance) <= tolerance:
            return 0
        return 1 if distance > 0 else -1

    def _detect_loop_pattern(self) -> bool:
        """
        Обнаруживает зацикливание в движениях платформы.

        Returns:
            True, если обнаружено зацикливание
        """
        history = self.loop_prevention_system["movement_history"]
        threshold = self.loop_prevention_system["loop_detection_threshold"]

        if len(history) < threshold * 2:
            return False

        recent_movements = history[-threshold:]
        movement_counts: Dict[int, int] = {}
        for movement in recent_movements:
            movement_counts[movement] = movement_counts.get(movement, 0) + 1

        max_count = max(movement_counts.values())
        if max_count >= threshold * 0.8:
            return True

        position_history = self.loop_prevention_system["position_history"]
        if len(position_history) >= 10:
            recent_positions = position_history[-10:]
            if len(set(recent_positions[-8:])) <= 2:
                return True

        return False

    def _change_strategy_if_looping(self) -> None:
        """Меняет стратегию при обнаружении зацикливания."""
        if not self._detect_loop_pattern():
            return

        if self.loop_prevention_system["strategy_change_cooldown"] > 0:
            self.loop_prevention_system["strategy_change_cooldown"] -= 1
            return

        strategies = self.loop_prevention_system["alternative_strategies"]
        idx = self.loop_prevention_system["current_strategy_index"]
        self.loop_prevention_system["current_strategy_index"] = (idx + 1) % len(strategies)

        self.loop_prevention_system["strategy_change_cooldown"] = 10
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []

    def _apply_alternative_strategy(self, optimal_position: int) -> int:
        """
        Применяет альтернативную стратегию позиционирования.

        Args:
            optimal_position: Оптимальная позиция

        Returns:
            Скорректированная позиция
        """
        strategy_index = self.loop_prevention_system["current_strategy_index"]
        strategy = self.loop_prevention_system["alternative_strategies"][strategy_index]
        screen_center = self.screen_width // 2

        if strategy == "center_focus":
            return screen_center

        if strategy == "edge_focus":
            if self.current_game_state:
                current_pos = self.current_game_state.paddle_position
                if current_pos:
                    return self.screen_width - 70 if current_pos.x < screen_center else 70
            return 70

        return optimal_position

    def _detect_jitter(self) -> bool:
        """
        Обнаруживает дрожание платформы.

        Returns:
            True, если обнаружено дрожание
        """
        movements = self.smoothness_system["recent_movements"]
        if len(movements) < self.smoothness_system["jitter_threshold"]:
            return False

        direction_changes = 0
        for i in range(1, len(movements)):
            prev = movements[i - 1]
            curr = movements[i]
            if prev != 0 and curr != 0 and prev != curr:
                direction_changes += 1

        threshold = self.smoothness_system["jitter_threshold"]
        if direction_changes >= threshold:
            return True

        movement_changes = self.smoothness_system["movement_changes"]
        if len(movement_changes) >= threshold:
            return True

        positions = self.smoothness_system["recent_positions"]
        if len(positions) >= 5:
            recent_positions = positions[-5:]
            position_variance = max(recent_positions) - min(recent_positions)
            if (
                position_variance < 10
                and len([m for m in movements[-5:] if m != 0]) >= 3
            ):
                return True

        return False

    def _calculate_smooth_movement(
        self, current_x: int, optimal_x: int, distance: float
    ) -> int:
        """
        Вычисляет плавное движение с учетом штрафов за дрожание.

        Args:
            current_x: Текущая позиция платформы
            optimal_x: Оптимальная позиция платформы
            distance: Расстояние до оптимальной позиции

        Returns:
            Направление движения (-1, 0, 1)
        """
        if self.target_tracker.is_target_set():
            effective_min_distance = 30
        else:
            penalty = self.smoothness_system["smoothness_penalty"]
            effective_min_distance = self.smoothness_system["min_movement_distance"] * (1 + penalty)

        if distance < effective_min_distance:
            return 0

        if optimal_x > current_x:
            return 1
        elif optimal_x < current_x:
            return -1
        else:
            return 0

    def _update_loop_tracking(
        self, movement: int, current_x: int, optimal_x: int
    ) -> None:
        """
        Обновляет данные отслеживания зацикливания.

        Args:
            movement: Направление движения
            current_x: Текущая позиция
            optimal_x: Оптимальная позиция
        """
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 10:
            self.loop_prevention_system["movement_history"] = (
                self.loop_prevention_system["movement_history"][-10:]
            )

        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = (
                self.loop_prevention_system["position_history"][-10:]
            )

        if self.current_game_state:
            trajectory_info = {
                "ball_x": self.current_game_state.ball_position.x,
                "ball_y": self.current_game_state.ball_position.y,
                "optimal_x": optimal_x,
                "timestamp": time.time(),
            }
            self.loop_prevention_system["trajectory_history"].append(trajectory_info)
            if len(self.loop_prevention_system["trajectory_history"]) > 10:
                self.loop_prevention_system["trajectory_history"] = (
                    self.loop_prevention_system["trajectory_history"][-5:]
                )

    def _update_smoothness_tracking(self, movement: int, current_x: int) -> None:
        """
        Обновляет данные отслеживания плавности движения.

        Args:
            movement: Направление движения
            current_x: Текущая позиция
        """
        self.smoothness_system["recent_movements"].append(movement)
        if len(self.smoothness_system["recent_movements"]) > self.smoothness_system["jitter_window"]:
            self.smoothness_system["recent_movements"] = self.smoothness_system[
                "recent_movements"
            ][-self.smoothness_system["jitter_window"]:]

        self.smoothness_system["recent_positions"].append(current_x)
        if len(self.smoothness_system["recent_positions"]) > self.smoothness_system["jitter_window"]:
            self.smoothness_system["recent_positions"] = self.smoothness_system[
                "recent_positions"
            ][-self.smoothness_system["jitter_window"]:]

        if len(self.smoothness_system["recent_movements"]) >= 2:
            prev_movement = self.smoothness_system["recent_movements"][-2]
            if prev_movement != 0 and movement != 0 and prev_movement != movement:
                self.smoothness_system["movement_changes"].append(time.time())
                current_time = time.time()
                self.smoothness_system["movement_changes"] = [
                    t
                    for t in self.smoothness_system["movement_changes"]
                    if current_time - t < 1.0
                ]
