"""
Модуль для стратегии движения платформы.

Содержит класс PaddleMovementStrategy с разделенной логикой движения платформы.
"""

import time
from typing import Optional, Dict, Any

from ..game_state import GameState, Point
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
        
        # КРИТИЧНО: Отслеживание предыдущей позиции и скорости мяча для обнаружения отскоков от блоков
        self._last_ball_position = None
        self._last_ball_velocity = None

    def _detect_brick_bounce(self) -> bool:
        """
        ✅ НОВАЯ ФУНКЦИЯ: Обнаруживает отскок от блока с высокой чувствительностью.
        Возвращает True если обнаружен отскок (вниз->вверх или резкое изменение).
        """
        if (not self.current_game_state or 
            not self._last_ball_position or 
            not self._last_ball_velocity):
            return False
        
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        ball_vel_y = self.current_game_state.ball_velocity.y
        current_vel_x = (
            self.current_game_state.ball_velocity.x
            if hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        
        last_ball_x = self._last_ball_position.x
        last_ball_y = self._last_ball_position.y
        last_vel_y = self._last_ball_velocity.y
        
        # Не анализируем, если мяч слишком близко к верхней границе
        if ball_y < 30:
            return False
        
        # ✅ УСЛОВИЕ 1: Изменение направления velocity (вниз -> вверх)
        # Это самый надежный признак отскока от блока/стены
        if last_vel_y > 0.5 and ball_vel_y < -1:
            self._logger.debug(
                f"[BOUNCE DETECT] Условие 1: direction change "
                f"({last_vel_y:.1f} -> {ball_vel_y:.1f})"
            )
            return True
        
        # ✅ УСЛОВИЕ 2: Резкое изменение Y скорости (больше, чем гравитация ~0.5)
        vel_y_change = abs(ball_vel_y - last_vel_y)
        if vel_y_change > 6:  # Пороговое значение выше гравитации
            self._logger.debug(
                f"[BOUNCE DETECT] Условие 2: vel_y change {vel_y_change:.1f} > 6"
            )
            return True
        
        # ✅ УСЛОВИЕ 3: Резкое изменение позиции X при движении вниз
        x_change = abs(ball_x - last_ball_x)
        y_change = ball_y - last_ball_y
        if (x_change > 15 and y_change < -3 and last_vel_y > 0 and ball_vel_y < 0):
            self._logger.debug(
                f"[BOUNCE DETECT] Условие 3: x_change={x_change:.1f}, "
                f"y_change={y_change:.1f}, direction reverse"
            )
            return True
        
        # ✅ УСЛОВИЕ 4: Сочетание резких X и Y изменений (мяч отскочил от блока в углу)
        if (x_change > 12 and abs(y_change) > 8 and 
            last_vel_y > 1 and ball_vel_y < -1):
            self._logger.debug(
                f"[BOUNCE DETECT] Условие 4: combined x_change={x_change:.1f}, "
                f"y_change={y_change:.1f}"
            )
            return True
        
        return False

    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции с предотвращением зацикливания.

        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Базовая скорость движения платформы

        Returns:
            Смещение платформы (-1, 0, 1)
        """
        # КРИТИЧНО: Валидация входных параметров
        current_x = self._clamp_paddle_position(current_x)
        
        # ТЕСТ: Логируем каждый вызов для диагностики
        self._logger.debug(f"[MOVE_PADDLE_CALL] move_paddle_towards вызван: current_x={current_x}, paddle_speed={paddle_speed}")
        
        # Проверка состояния
        if not self._validate_state():
            self._logger.debug("[MOVE_PADDLE_CALL] _validate_state вернул False, используем fallback")
            return self._validate_movement(self._fallback_movement(current_x))

        try:
            self._logger.debug("[MOVE_PADDLE_CALL] Начинаем обработку движения платформы")
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            self._logger.debug(f"[MOVE_PADDLE_CALL] ball_y={ball_y:.1f}, ball_vel_y={ball_vel_y:.1f}")
            
            # ✅ ДОБАВЛЕНО: Инициализируем отслеживание в первый раз
            if self._last_ball_position is None and self.current_game_state:
                ball_x = self.current_game_state.ball_position.x
                current_vel_x = (
                    self.current_game_state.ball_velocity.x
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                self._last_ball_position = Point(ball_x, ball_y)
                self._last_ball_velocity = Point(current_vel_x, ball_vel_y)
                self._logger.debug("[MOVE_PADDLE_CALL] Инициализировано отслеживание позиции/скорости")
            
            # ✅ ДОБАВЛЕНО: НЕМЕДЛЕННАЯ проверка отскоков ДО всего остального
            brick_bounce_detected = self._detect_brick_bounce()
            if brick_bounce_detected:
                self._logger.debug(
                    "[IMMEDIATE BOUNCE] Отскок обнаружен НЕМЕДЛЕННО в начале! "
                    "Сбрасываем целевую позицию и переходим к установке новой"
                )
                self.target_tracker.reset_target_position()
                # Не выходим - продолжаем обработку для установки новой цели
            
            # Обновляем отслеживание для СЛЕДУЮЩЕГО кадра (ВСЕГДА, даже при отскоке)
            if self.current_game_state:
                ball_x = self.current_game_state.ball_position.x
                current_vel_x = (
                    self.current_game_state.ball_velocity.x
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                self._last_ball_position = Point(ball_x, ball_y)
                self._last_ball_velocity = Point(current_vel_x, ball_vel_y)
            
            # КРИТИЧНО: Проверяем отскоки от верхней границы ДО обработки зон
            # Это обеспечивает немедленную реакцию на отскоки
            last_vel_y = self.separation_zone_tracker.last_ball_vel_y
            if (last_vel_y is not None and 
                last_vel_y > 0 and  # мяч двигался вниз на предыдущем кадре
                ball_vel_y < 0):  # мяч теперь двигается вверх (отскок от верхней границы)
                # Мяч отскочил от верхней границы - сбрасываем цель и НЕМЕДЛЕННО пересчитываем
                self._logger.debug(
                    f"[EARLY BOUNCE DETECTION] Мяч отскочил от верхней границы! "
                    f"vel_y изменился с {last_vel_y:.1f} (вниз) на {ball_vel_y:.1f} (вверх), "
                    f"сбрасываем целевую позицию и немедленно пересчитываем"
                )
                self.target_tracker.reset_target_position()
                self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
                self.separation_zone_tracker.ball_moving_downward_last_frame = False
                
                # КРИТИЧНО: НЕМЕДЛЕННО пересчитываем новую цель после отскока
                # Это позволяет платформе быстро адаптироваться к изменению траектории
                zones = self.zone_handler.calculate_zones()
                emergency_result = self._set_new_target(
                    current_x, paddle_speed, ball_y, ball_vel_y, zones
                )
                if emergency_result is not None:
                    self._logger.debug(
                        f"[BOUNCE RECOVERY] Новая цель установлена после отскока, "
                        f"движение: {emergency_result}"
                    )
                    return self._validate_movement(emergency_result)
                
                # Если не удалось установить цель (мяч движется вверх) - 
                # упреждающее движение к центру для подготовки к следующей атаке
                center_movement = self._proactive_center_movement(current_x, ball_y)
                if center_movement != 0:
                    self._logger.debug(
                        f"[BOUNCE RECOVERY] Мяч движется вверх, двигаемся к центру: {center_movement}"
                    )
                    return self._validate_movement(center_movement)
                
                # Если ничего не подошло - останавливаемся
                return self._validate_movement(0)
            
            # КРИТИЧНО: Проверяем отскоки от блоков ДО обработки зон
            # Это обеспечивает немедленную реакцию на отскоки от блоков
            if brick_bounce_detected:
                # Мяч отскочил от блока - сбрасываем цель и НЕМЕДЛЕННО пересчитываем
                self._logger.debug(
                    f"[BRICK BOUNCE RECOVERY] Мяч отскочил от блока! "
                    f"Сбрасываем целевую позицию и немедленно пересчитываем"
                )
                self.target_tracker.reset_target_position()
                self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
                self.separation_zone_tracker.ball_moving_downward_last_frame = (ball_vel_y > 0)
                
                # КРИТИЧНО: НЕМЕДЛЕННО пересчитываем новую цель после отскока от блока
                # Это позволяет платформе быстро адаптироваться к изменению траектории
                zones = self.zone_handler.calculate_zones()
                emergency_result = self._set_new_target(
                    current_x, paddle_speed, ball_y, ball_vel_y, zones
                )
                if emergency_result is not None:
                    self._logger.debug(
                        f"[BRICK BOUNCE RECOVERY] Новая цель установлена после отскока от блока, "
                        f"движение: {emergency_result}"
                    )
                    return self._validate_movement(emergency_result)
                
                # Если не удалось установить цель (мяч движется вверх) - 
                # упреждающее движение к центру для подготовки к следующей атаке
                center_movement = self._proactive_center_movement(current_x, ball_y)
                if center_movement != 0:
                    self._logger.debug(
                        f"[BRICK BOUNCE RECOVERY] Мяч движется вверх, двигаемся к центру: {center_movement}"
                    )
                    return self._validate_movement(center_movement)
                
                # Если ничего не подошло - останавливаемся
                return self._validate_movement(0)

            # Обработка зоны кубиков
            zones = self.zone_handler.calculate_zones()
            if ball_y < zones["separation_zone_start"]:
                bricks_count = len(self.current_game_state.remaining_bricks) if self.current_game_state else 50
                is_last_brick = bricks_count == 1
                if not is_last_brick:
                    result = self.zone_handler.handle_bricks_zone(ball_y, self.current_game_state)
                    return self._validate_movement(result)

            # Обработка потерянного мяча
            lost_ball_result = self._handle_lost_ball(ball_y, current_x)
            if lost_ball_result is not None:
                return self._validate_movement(lost_ball_result)

            # Обработка зоны разделения
            separation_result = self.zone_handler.handle_separation_zone(
                ball_y, ball_vel_y, zones, self.current_game_state
            )
            if separation_result is not None:
                return self._validate_movement(separation_result)

            # Фиксация целевой позиции
            fixed_target_result = self._handle_fixed_target(
                current_x, paddle_speed, ball_y, ball_vel_y, zones
            )
            if fixed_target_result is not None:
                return self._validate_movement(fixed_target_result)

            # Установка новой цели
            new_target_result = self._set_new_target(
                current_x, paddle_speed, ball_y, ball_vel_y, zones
            )
            if new_target_result is not None:
                return self._validate_movement(new_target_result)

            # Обычная логика движения
            return self._validate_movement(self._handle_normal_movement(current_x, paddle_speed))

        except Exception as e:
            self._logger.error(f"Ошибка при движении платформы: {e}", exc_info=True)
            return self._validate_movement(self._fallback_movement(current_x))

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
            # Фильтрация по уровню выполняется автоматически системой логирования Python
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

        # ✅ ИСПРАВЛЕНО: ПРИОРИТЕТНАЯ проверка отскоков в НАЧАЛЕ функции для немедленной реакции
        # Проверяем отскоки от блоков ДО всех других проверок при наличии установленной цели
        if self.target_tracker.is_target_set():
            brick_bounce_detected_immediate = self._detect_brick_bounce()
            
            if brick_bounce_detected_immediate:
                self._logger.debug(
                    "[FIXED TARGET] [IMMEDIATE BOUNCE CHECK] "
                    "Обнаружен отскок от блока при наличии зафиксированной цели! "
                    "Немедленно сбрасываем целевую позицию и возвращаемся для пересчета"
                )
                self.target_tracker.reset_target_position()
                self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
                return None  # Выходим НЕМЕДЛЕННО для пересчета целевой позиции

        # КРИТИЧНО: Проверяем отскок от верхней границы (вниз -> вверх)
        # Если мяч отскочил от верхней границы, нужно сбросить целевую позицию немедленно
        last_vel_y = self.separation_zone_tracker.last_ball_vel_y
        if (last_vel_y is not None and 
            last_vel_y > 0 and  # мяч двигался вниз на предыдущем кадре
            ball_vel_y < 0):  # мяч теперь двигается вверх (отскок от верхней границы)
            # Мяч отскочил от верхней границы - сбрасываем цель немедленно
            self._logger.debug(
                f"[FIXED TARGET] [EARLY BOUNCE DETECTION] Мяч отскочил от верхней границы! "
                f"vel_y изменился с {last_vel_y:.1f} (вниз) на {ball_vel_y:.1f} (вверх), "
                f"сбрасываем целевую позицию и немедленно пересчитываем"
            )
            self.target_tracker.reset_target_position()
            self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
            self.separation_zone_tracker.ball_moving_downward_last_frame = False
            return None  # Возвращаем None, чтобы не двигаться к старой цели

        # КРИТИЧНО: Проверяем смену направления мяча (вверх -> вниз)
        # Если мяч только что начал двигаться вниз после движения вверх,
        # нужно сбросить целевую позицию и пересчитать её
        if (last_vel_y is not None and 
            last_vel_y <= 0 and  # мяч двигался вверх на предыдущем кадре
            ball_vel_y > 0 and  # мяч теперь двигается вниз
            in_separation_zone):  # мяч в зоне разделения
            # Мяч сменил направление на движение вниз - сбрасываем цель для пересчета
            self._logger.debug(
                f"[DIRECTION CHANGE] Мяч сменил направление с вверх (vel_y={last_vel_y:.1f}) "
                f"на вниз (vel_y={ball_vel_y:.1f}), сбрасываем целевую позицию"
            )
            self.target_tracker.reset_target_position()
            self.separation_zone_tracker.ball_moving_downward_last_frame = True
            # Обновляем отслеживание направления
            self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
            return None  # Возвращаем None, чтобы установить новую цель
        
        # Обновляем отслеживание направления
        self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
        if ball_vel_y > 0:
            self.separation_zone_tracker.ball_moving_downward_last_frame = True
        elif ball_vel_y <= 0:
            self.separation_zone_tracker.ball_moving_downward_last_frame = False

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
            
            # КРИТИЧНО: Проверяем отскоки от блоков по изменению позиции/скорости
            brick_bounce_detected_here = False
            if self._last_ball_position is not None and self._last_ball_velocity is not None:
                ball_x = self.current_game_state.ball_position.x
                last_vel_y = self._last_ball_velocity.y
                vel_y_direction_change = (last_vel_y > 0 and ball_vel_y < 0)
                position_change = abs(ball_x - self._last_ball_position.x)
                y_change = ball_y - self._last_ball_position.y
                vel_y_change = abs(ball_vel_y - last_vel_y)
                
                if ball_y > 30:  # Мяч не у верхней границы
                    if (vel_y_direction_change or 
                        (position_change > 15 and y_change < -3) or
                        (vel_y_change > 5 and y_change < -3)):
                        vel_x_change = abs(current_vel_x - self._last_ball_velocity.x)
                        if vel_x_change < 15 or vel_y_direction_change:
                            brick_bounce_detected_here = True
                            self._logger.debug(
                                f"[FIXED TARGET] Обнаружен отскок от блока! Сбрасываем зафиксированную цель"
                            )

            if self.target_tracker.check_wall_bounce(current_vel_x):
                # Отскок от стены - сбрасываем цель
                self.target_tracker.reset_target_position()
                self.target_tracker.update_saved_velocity(current_vel_x)
                return None
            elif brick_bounce_detected_here:
                # Отскок от блока - сбрасываем цель
                self.target_tracker.reset_target_position()
                self.target_tracker.update_saved_velocity(current_vel_x)
                return None

            # КРИТИЧНО: Проверяем, летит ли мяч к стене и должен отскочить
            # Если да, сбрасываем цель для пересчета с учетом максимальной позиции у стены
            ball_x = self.current_game_state.ball_position.x
            ball_radius = getattr(self.config, 'ball', None)
            ball_radius = ball_radius.radius if ball_radius and hasattr(ball_radius, 'radius') else 8
            distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
            time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
            
            if time_to_paddle != float('inf') and time_to_paddle > 0:
                # Проверяем, летит ли мяч к правой стене
                if current_vel_x > 0:  # Мяч движется вправо
                    distance_to_right_wall = self.screen_width - ball_radius - ball_x
                    if distance_to_right_wall > 0:
                        time_to_right_wall = distance_to_right_wall / current_vel_x if current_vel_x > 0 else float('inf')
                        # Если мяч достигнет правой стены до платформы, сбрасываем цель для пересчета
                        if time_to_right_wall < time_to_paddle and time_to_right_wall > 0:
                            self._logger.debug(
                                f"[FIXED TARGET WALL CHECK] Мяч летит к правой стене! "
                                f"time_to_wall={time_to_right_wall:.1f} < time_to_paddle={time_to_paddle:.1f}, "
                                f"сбрасываем цель для пересчета с максимальной правой позицией"
                            )
                            self.target_tracker.reset_target_position()
                            self.target_tracker.update_saved_velocity(current_vel_x)
                            return None
                
                # Проверяем, летит ли мяч к левой стене
                elif current_vel_x < 0:  # Мяч движется влево
                    distance_to_left_wall = ball_x - ball_radius
                    if distance_to_left_wall > 0:
                        time_to_left_wall = distance_to_left_wall / abs(current_vel_x) if current_vel_x < 0 else float('inf')
                        # Если мяч достигнет левой стены до платформы, сбрасываем цель для пересчета
                        if time_to_left_wall < time_to_paddle and time_to_left_wall > 0:
                            self._logger.debug(
                                f"[FIXED TARGET WALL CHECK] Мяч летит к левой стене! "
                                f"time_to_wall={time_to_left_wall:.1f} < time_to_paddle={time_to_paddle:.1f}, "
                                f"сбрасываем цель для пересчета с максимальной левой позицией"
                            )
                            self.target_tracker.reset_target_position()
                            self.target_tracker.update_saved_velocity(current_vel_x)
                            return None

            self.target_tracker.update_saved_velocity(current_vel_x)

        # Двигаемся к зафиксированной позиции
        target_pos = int(current_target)
        
        # КРИТИЧНО: Ограничиваем целевую позицию границами экрана
        target_pos = self._clamp_paddle_position(target_pos)
        
        distance_to_target = abs(current_x - target_pos)
        # КРИТИЧНО: Адаптивный tolerance на основе скорости мяча, расстояния и критичности
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else 0
        distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
        is_critical = distance_to_paddle < 50 or target_pos < 100 or target_pos > self.screen_width - 100
        
        # Используем адаптивный tolerance, который учитывает скорость мяча
        tolerance = self._get_adaptive_tolerance(
            ball_vel_y, distance_to_target, paddle_speed, is_critical
        )
        
        # КРИТИЧНО: Буферная зона для ранней остановки платформы
        # УМЕНЬШЕНО для критических случаев в углах - платформа должна доезжать до цели
        # Отключаем буферную зону, если мяч близко к платформе или в углу
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else 0
        distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
        
        # Если мяч очень близко к платформе (< 50px) или цель в углу - отключаем буферную зону
        is_critical = distance_to_paddle < 50 or target_pos < 100 or target_pos > self.screen_width - 100
        buffer_zone = 0 if is_critical else paddle_speed * 0.15  # Минимальная буферная зона только для некритических случаев

        # КРИТИЧНО: Логируем для диагностики проблем с движением
        # Фильтрация по уровню выполняется автоматически системой логирования Python
        self._logger.debug(
            f"[FIXED TARGET] current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
            f"distance={distance_to_target:.1f}px, tolerance={tolerance}, buffer_zone={buffer_zone:.1f}, "
            f"in_separation_zone={in_separation_zone}, ball_y={ball_y:.1f}, "
            f"paddle_speed={paddle_speed}"
        )

        # КРИТИЧНО: Используем буферную зону для более плавной остановки
        if distance_to_target > tolerance + buffer_zone:
            # Достаточно далеко - двигаемся к цели
            movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
            if movement != 0:
                self._update_loop_tracking(movement, int(current_x), int(target_pos))
                self._update_smoothness_tracking(movement, current_x)
                self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target", 1.0)
                self._logger.debug(
                    f"[FIXED TARGET] Движение: {movement} (влево=-1, вправо=1, стоп=0), "
                    f"distance={distance_to_target:.1f}px > tolerance+buffer={tolerance+buffer_zone:.1f}"
                )
                return movement
        elif distance_to_target <= tolerance:
            # Достигли цели - останавливаемся
            self._logger.debug(
                f"[FIXED TARGET] Достигли цели! distance={distance_to_target:.1f}px <= tolerance={tolerance}, "
                f"возвращаем 0 (стоп)"
            )
            return 0
        else:
            # В буферной зоне - останавливаемся раньше, чтобы избежать перелета
            self._logger.debug(
                f"[FIXED TARGET] В буферной зоне! distance={distance_to_target:.1f}px "
                f"(tolerance={tolerance:.1f} < distance <= tolerance+buffer={tolerance+buffer_zone:.1f}), "
                f"останавливаемся раньше для предотвращения перелета"
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

        # КРИТИЧНО: Устанавливаем цель раньше, когда мяч еще далеко
        # Это дает больше времени на движение к цели
        # УВЕЛИЧЕНО с 100px до 200px для более ранней реакции
        early_zone_start = separation_zone_start - 200  # На 200px раньше зоны разделения
        in_early_zone = early_zone_start <= ball_y < separation_zone_start and ball_vel_y > 0
        in_target_zone = in_separation_zone or in_early_zone

        # КРИТИЧНО: Устанавливаем новую цель если:
        # 1. Мяч в зоне разделения ИЛИ в ранней зоне И движется вниз (ball_vel_y > 0)
        # 2. Мяч действительно летит к AI (проверяется через ball_vel_y > 0)
        # 3. Цель еще не установлена ИЛИ мяч только что сменил направление на вниз
        if not in_target_zone:
            return None
        
        # КРИТИЧНО: Дополнительная проверка - мяч должен двигаться вниз (к AI)
        # Это критично, так как AI находится внизу экрана
        if ball_vel_y <= 0:
            # Мяч движется вверх или стоит на месте - не устанавливаем цель
            return None
        
        # КРИТИЧНО: Проверяем, что мяч действительно приближается к AI
        # AI находится внизу экрана, поэтому мяч должен двигаться вниз
        if not self.current_game_state:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        # Мяч должен быть выше платформы и двигаться вниз
        if ball_y >= paddle_y:
            # Мяч уже на уровне или ниже платформы - слишком поздно
            return None
        
        # КРИТИЧНО: В зоне разделения всегда пересчитываем цель для учета изменений траектории
        # Это особенно важно для мячей, которые отскакивают от боковых стен ИЛИ от кирпичей
        if self.target_tracker.is_target_set():
            # Получаем текущие координаты и скорость мяча для проверки отскоков
            if not self.current_game_state:
                return None
            ball_x = self.current_game_state.ball_position.x
            current_vel_x = (
                self.current_game_state.ball_velocity.x
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            
            # КРИТИЧНО: Проверяем отскоки от блоков по изменению позиции/скорости
            # Это более надежный способ, чем только проверка vel_y
            brick_bounce_detected_here = False
            if self._last_ball_position is not None and self._last_ball_velocity is not None:
                last_vel_y = self._last_ball_velocity.y
                vel_y_direction_change = (last_vel_y > 0 and ball_vel_y < 0)
                position_change = abs(ball_x - self._last_ball_position.x)
                y_change = ball_y - self._last_ball_position.y
                vel_y_change = abs(ball_vel_y - last_vel_y)
                
                if ball_y > 30:  # Мяч не у верхней границы
                    if (vel_y_direction_change or 
                        (position_change > 15 and y_change < -3) or
                        (vel_y_change > 5 and y_change < -3)):
                        vel_x_change = abs(current_vel_x - self._last_ball_velocity.x)
                        if vel_x_change < 15 or vel_y_direction_change:
                            brick_bounce_detected_here = True
            
            # Проверяем, не сменил ли мяч направление (отскок от верхней границы или кирпича)
            last_vel_y = self.separation_zone_tracker.last_ball_vel_y
            if (last_vel_y is not None and 
                last_vel_y <= 0 and  # мяч двигался вверх
                ball_vel_y > 0):  # мяч теперь двигается вниз
                # Мяч сменил направление - сбрасываем старую цель и устанавливаем новую
                self._logger.debug(
                    f"[NEW TARGET] Мяч сменил направление, сбрасываем старую цель и устанавливаем новую"
                )
                self.target_tracker.reset_target_position()
            elif (last_vel_y is not None and 
                  last_vel_y > 0 and  # мяч двигался вниз
                  ball_vel_y < 0):  # мяч теперь двигается вверх (отскок от кирпича!)
                # КРИТИЧНО: Мяч отскочил от кирпича вверх - траектория изменилась!
                self._logger.debug(
                    f"[NEW TARGET] Мяч отскочил от кирпича! vel_y изменился с {last_vel_y:.1f} (вниз) на {ball_vel_y:.1f} (вверх), "
                    f"сбрасываем цель и пересчитываем"
                )
                self.target_tracker.reset_target_position()
            elif brick_bounce_detected_here:
                # КРИТИЧНО: Обнаружен отскок от блока по изменению позиции/скорости
                self._logger.debug(
                    f"[NEW TARGET] Обнаружен отскок от блока в зоне разделения! "
                    f"Сбрасываем цель и пересчитываем"
                )
                self.target_tracker.reset_target_position()
            else:
                # КРИТИЧНО: В зоне разделения пересчитываем цель каждый шаг для учета отскоков от стен
                # Это позволяет платформе реагировать на изменения траектории
                if in_separation_zone:
                    # Проверяем, изменилась ли траектория мяча (например, после отскока от стены)
                    if self.current_game_state:
                        current_vel_x = (
                            self.current_game_state.ball_velocity.x
                            if hasattr(self.current_game_state, "ball_velocity")
                            else 0
                        )
                        saved_vel_x = self.target_tracker.get_saved_velocity()
                        # Если горизонтальная скорость изменилась - пересчитываем цель
                        # УМЕНЬШЕНО порог с 1 до 0.5 для более чувствительного обнаружения
                        if saved_vel_x is not None and abs(current_vel_x - saved_vel_x) > 0.5:
                            self._logger.debug(
                                f"[NEW TARGET] Траектория изменилась (vel_x: {saved_vel_x:.1f} -> {current_vel_x:.1f}), "
                                f"пересчитываем цель"
                            )
                            self.target_tracker.reset_target_position()
                        else:
                            # Траектория не изменилась - не пересчитываем
                            return None
                else:
                    # Вне зоны разделения - не пересчитываем
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

        # КРИТИЧНО: Вычисляем time_to_paddle для проверки отскока от стен
        distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
        time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')

        # КРИТИЧНО: Специальная обработка для мяча, летящего к стенам
        # Если мяч летит к правой/левой стене и должен отскочить, 
        # платформа должна быть максимально справа/слева, чтобы поймать мяч после отскока
        if self.current_game_state and time_to_paddle != float('inf') and time_to_paddle > 0:
            ball_x = self.current_game_state.ball_position.x
            ball_vel_x = (
                self.current_game_state.ball_velocity.x
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            ball_radius = getattr(self.config, 'ball', None)
            ball_radius = ball_radius.radius if ball_radius and hasattr(ball_radius, 'radius') else 8
            
            # Проверяем, летит ли мяч к правой стене
            if ball_vel_x > 0:  # Мяч движется вправо
                distance_to_right_wall = self.screen_width - ball_radius - ball_x
                # Если мяч близко к правой стене и должен отскочить до достижения платформы
                if distance_to_right_wall > 0:
                    time_to_right_wall = distance_to_right_wall / ball_vel_x if ball_vel_x > 0 else float('inf')
                    # Если мяч достигнет правой стены до платформы, устанавливаем максимальную правую позицию
                    if time_to_right_wall < time_to_paddle and time_to_right_wall > 0:
                        max_right_x = self.screen_width - self.paddle_width // 2
                        self._logger.debug(
                            f"[WALL BOUNCE DETECTION] Мяч летит к правой стене! "
                            f"time_to_wall={time_to_right_wall:.1f} < time_to_paddle={time_to_paddle:.1f}, "
                            f"устанавливаем максимальную правую позицию: {max_right_x:.1f}"
                        )
                        optimal_x = max_right_x
            
            # Проверяем, летит ли мяч к левой стене
            elif ball_vel_x < 0:  # Мяч движется влево
                distance_to_left_wall = ball_x - ball_radius
                # Если мяч близко к левой стене и должен отскочить до достижения платформы
                if distance_to_left_wall > 0:
                    time_to_left_wall = distance_to_left_wall / abs(ball_vel_x) if ball_vel_x < 0 else float('inf')
                    # Если мяч достигнет левой стены до платформы, устанавливаем максимальную левую позицию
                    if time_to_left_wall < time_to_paddle and time_to_left_wall > 0:
                        min_left_x = self.paddle_width // 2
                        self._logger.debug(
                            f"[WALL BOUNCE DETECTION] Мяч летит к левой стене! "
                            f"time_to_wall={time_to_left_wall:.1f} < time_to_paddle={time_to_paddle:.1f}, "
                            f"устанавливаем максимальную левую позицию: {min_left_x:.1f}"
                        )
                        optimal_x = min_left_x

        # КРИТИЧНО: Улучшенная проверка достижимости цели
        # Учитываем запас на ошибки, отскоки и инерцию
        distance_to_target = abs(current_x - optimal_x)

        if time_to_paddle != float('inf') and time_to_paddle > 0 and distance_to_target > 0:
            frames_to_reach = distance_to_target / paddle_speed if paddle_speed > 0 else float('inf')
            
            # КРИТИЧНО: Адаптивный запас на ошибки в зависимости от расстояния до платформы
            # Для критических случаев (мяч близко) используем меньший запас и более агрессивное движение
            if distance_to_paddle_y < 50:  # Мяч очень близко к платформе - экстремальный случай
                safety_margin = 1.0  # Минимальный запас для экстремальных случаев
                max_distance_factor = 1.0  # Максимально агрессивное ограничение (100%)
            elif distance_to_paddle_y < 100:  # Мяч близко к платформе - критический случай
                safety_margin = 1.1  # Меньший запас для критических случаев
                max_distance_factor = 0.95  # Более агрессивное ограничение (95%)
            else:
                safety_margin = 1.5  # Обычный запас (50%)
                max_distance_factor = 0.7  # Консервативное ограничение (70%)
            
            if frames_to_reach > time_to_paddle * safety_margin:
                # Цель недостижима - ограничиваем её до достижимого расстояния
                max_distance = paddle_speed * time_to_paddle * max_distance_factor
                self._logger.debug(
                    f"[NEW TARGET] Цель недостижима! distance={distance_to_target:.1f}px, "
                    f"frames_to_reach={frames_to_reach:.1f}, time_to_paddle={time_to_paddle:.1f}, "
                    f"max_distance={max_distance:.1f}px, distance_to_paddle_y={distance_to_paddle_y:.1f}, "
                    f"ограничиваем цель (safety_margin={safety_margin}, factor={max_distance_factor})"
                )
                if optimal_x > current_x:
                    optimal_x = min(optimal_x, current_x + max_distance)
                else:
                    optimal_x = max(optimal_x, current_x - max_distance)
            else:
                # КРИТИЧНО: Для критических случаев (мяч очень близко) устанавливаем цель даже если она немного недостижима
                # Это позволяет платформе попытаться добраться как можно ближе
                if distance_to_paddle_y < 50:
                    self._logger.debug(
                        f"[NEW TARGET] Критический случай! Мяч очень близко ({distance_to_paddle_y:.1f}px), "
                        f"устанавливаем цель даже если она немного недостижима для максимального приближения"
                    )
                    # Продолжаем установку цели - платформа попытается добраться как можно ближе

        # ✅ ИСПРАВЛЕНО: Жесткое ограничение максимального расстояния до цели (250px)
        # Это предотвращает установку нереалистично далеких целей
        distance_to_target = abs(current_x - optimal_x)
        MAX_TARGET_DISTANCE = 250  # ✅ Уменьшено с 300 до 250px для гарантии достижимости
        # ✅ ДОБАВЛЕНО: Проверяем достижимость целевой позиции перед ограничением
        # Это критично для обеспечения успешного перехвата мяча
        if time_to_paddle != float('inf') and time_to_paddle > 0 and distance_to_target > 0:
            # Минимальная скорость платформы во время движения
            frames_available = int(time_to_paddle)
            max_reachable_distance = paddle_speed * frames_available * 0.9  # 90% для буфера
            
            if distance_to_target > max_reachable_distance:
                self._logger.warning(
                    f"[NEW TARGET] Цель недостижима! "
                    f"distance={distance_to_target:.1f}px, "
                    f"reachable={max_reachable_distance:.1f}px, "
                    f"time_to_paddle={time_to_paddle:.1f}, "
                    f"paddle_speed={paddle_speed}, frames={frames_available}"
                )
                # Ограничиваем до максимально достижимого
                if optimal_x > current_x:
                    optimal_x = min(optimal_x, current_x + max_reachable_distance)
                else:
                    optimal_x = max(optimal_x, current_x - max_reachable_distance)
        
        if distance_to_target > MAX_TARGET_DISTANCE:
            self._logger.debug(
                f"[NEW TARGET] Расстояние до цели слишком большое ({distance_to_target:.1f}px > {MAX_TARGET_DISTANCE}px), "
                f"ограничиваем до {MAX_TARGET_DISTANCE}px"
            )
            if optimal_x > current_x:
                optimal_x = current_x + MAX_TARGET_DISTANCE
            else:
                optimal_x = current_x - MAX_TARGET_DISTANCE

        # КРИТИЧНО: Ограничиваем целевую позицию границами экрана
        optimal_x = self._clamp_paddle_position(int(optimal_x))

        # Сохраняем целевую позицию
        if self.current_game_state:
            current_vel_x = (
                self.current_game_state.ball_velocity.x
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            self.target_tracker.set_target_position(int(optimal_x), "new_target", self._logger)
            self.target_tracker.update_saved_velocity(current_vel_x)
            # КРИТИЧНО: Обновляем отслеживание направления мяча
            self.separation_zone_tracker.last_ball_vel_y = ball_vel_y
            self.separation_zone_tracker.ball_moving_downward_last_frame = True

        target_pos = int(optimal_x)
        distance_to_target = abs(current_x - target_pos)

        # КРИТИЧНО: Логируем установку новой цели для диагностики
        self._logger.debug(
            f"[NEW TARGET] Установлена новая цель: current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
            f"distance={distance_to_target:.1f}px, ball_y={ball_y:.1f}, ball_vel_y={ball_vel_y:.1f}, paddle_speed={paddle_speed}"
        )

        if target_pos == current_x:
            self._logger.debug(f"[NEW TARGET] Цель совпадает с текущей позицией, возвращаем 0")
            return 0

        if distance_to_target <= 25:
            self._logger.debug(
                f"[NEW TARGET] Расстояние до цели слишком мало ({distance_to_target:.1f}px <= 25), "
                f"возвращаем 0"
            )
            return 0

        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
        if movement == 0:
            self._logger.debug(f"[NEW TARGET] Не удалось определить направление, используем fallback")
            return self._fallback_movement(current_x)

        self._update_loop_tracking(movement, int(current_x), int(target_pos))
        self._update_smoothness_tracking(movement, current_x)
        self._log_paddle_movement(current_x, target_pos, "moving_to_new_target", 0.9)
        self._logger.debug(
            f"[NEW TARGET] Движение: {movement} (влево=-1, вправо=1, стоп=0), "
            f"distance={distance_to_target:.1f}px"
        )
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

        # КРИТИЧНО: Ограничиваем оптимальную позицию границами экрана
        optimal_x = self._clamp_paddle_position(int(optimal_x))

        # Проверяем зацикливание
        if not self.target_tracker.is_target_set():
            self._change_strategy_if_looping()
            if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                optimal_x = self._apply_alternative_strategy(optimal_x)
                if optimal_x is None:
                    return self._fallback_movement(current_x)
                # КРИТИЧНО: Ограничиваем альтернативную стратегию тоже
                optimal_x = self._clamp_paddle_position(int(optimal_x))

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

        # КРИТИЧНО: Логируем обычное движение для диагностики
        self._logger.debug(
            f"[NORMAL MOVEMENT] current_x={current_x:.1f}, optimal_x={optimal_x:.1f}, "
            f"distance={distance_to_optimal:.1f}px, min_movement_distance={min_movement_distance:.1f}, "
            f"precision_tolerance={precision_tolerance}, paddle_speed={paddle_speed}"
        )

        if distance_to_optimal < min_movement_distance:
            if distance_to_optimal <= precision_tolerance:
                self._logger.debug(
                    f"[NORMAL MOVEMENT] Расстояние слишком мало ({distance_to_optimal:.1f}px <= {precision_tolerance}), "
                    f"возвращаем 0"
                )
                return 0
            else:
                smooth_movement = self._calculate_smooth_movement(current_x, optimal_x, distance_to_optimal)
                self._logger.debug(
                    f"[NORMAL MOVEMENT] Плавное движение: {smooth_movement} "
                    f"(distance={distance_to_optimal:.1f}px < min_movement={min_movement_distance:.1f}px)"
                )
                return smooth_movement
        elif distance_to_optimal <= precision_tolerance:
            self._logger.debug(
                f"[NORMAL MOVEMENT] В пределах точности ({distance_to_optimal:.1f}px <= {precision_tolerance}), "
                f"возвращаем 0"
            )
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
                self._logger.debug(
                    f"[NORMAL MOVEMENT] position_optimizer вернул 0, но optimal_x != current_x, "
                    f"используем fallback"
                )
                movement = self._fallback_movement(current_x)

            self._update_loop_tracking(movement, current_x, optimal_x)
            self._update_smoothness_tracking(movement, current_x)

            self._logger.debug(
                f"[NORMAL MOVEMENT] Движение: {movement} (влево=-1, вправо=1, стоп=0), "
                f"distance={distance_to_optimal:.1f}px, adjusted_speed={adjusted_paddle_speed}"
            )

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
            self._logger.debug("[FALLBACK] Нет game_state, возвращаем 0")
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

        # КРИТИЧНО: Ограничиваем целевую позицию границами экрана
        target_x = self._clamp_paddle_position(int(target_x))

        distance = target_x - current_x
        tolerance = 3

        # КРИТИЧНО: Логируем fallback движение для диагностики
        self._logger.debug(
            f"[FALLBACK] current_x={current_x:.1f}, target_x={target_x:.1f}, "
            f"distance={abs(distance):.1f}px, tolerance={tolerance}, "
            f"ball=({ball_x:.1f},{ball_y:.1f}), vel=({vel_x:.1f},{vel_y:.1f})"
        )

        if abs(distance) <= tolerance:
            self._logger.debug(f"[FALLBACK] В пределах tolerance, возвращаем 0")
            return 0
        
        movement = 1 if distance > 0 else -1
        self._logger.debug(f"[FALLBACK] Движение: {movement} (влево=-1, вправо=1)")
        return movement

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

    def _validate_movement(self, movement: int) -> int:
        """
        Валидирует возвращаемое значение движения.

        Args:
            movement: Возвращаемое значение движения

        Returns:
            Валидное направление движения (-1, 0, 1)
        """
        # КРИТИЧНО: Проверяем, что возвращается направление, а не позиция
        if movement not in (-1, 0, 1):
            # Если возвращена позиция (больше 1 или меньше -1), конвертируем в направление
            if isinstance(movement, (int, float)) and abs(movement) > 1:
                # Это позиция, а не направление - логируем ошибку
                self._logger.error(
                    f"[CRITICAL ERROR] move_paddle_towards вернул позицию ({movement}) вместо направления! "
                    f"Исправляем на fallback движение."
                )
                # Используем fallback движение
                if self.current_game_state:
                    current_x = int(self.current_game_state.paddle_position.x)
                    return self._fallback_movement(current_x)
                return 0
            # Если это не число или невалидное значение - возвращаем 0
            self._logger.error(
                f"[CRITICAL ERROR] move_paddle_towards вернул невалидное значение: {movement} (тип: {type(movement)}). "
                f"Исправляем на 0."
            )
            return 0
        
        return movement

    def _get_adaptive_tolerance(
        self, ball_vel_y: float, distance_to_target: float, paddle_speed: int, is_critical: bool
    ) -> int:
        """
        Вычисляет адаптивный допуск на основе скорости мяча, расстояния и критичности.
        
        Args:
            ball_vel_y: Вертикальная скорость мяча
            distance_to_target: Расстояние до целевой позиции
            paddle_speed: Скорость платформы
            is_critical: Критическая ситуация (мяч близко или в углу)
        
        Returns:
            Адаптивный tolerance в пикселях
        """
        base_tolerance = 6  # минимальный допуск
        
        # Увеличиваем допуск при высокой скорости мяча
        # Чем быстрее мяч, тем больше допуск (но не более 3x)
        speed_factor = min(abs(ball_vel_y) / 10.0, 3.0) if ball_vel_y != 0 else 1.0
        
        # Уменьшаем допуск при приближении к цели
        # Чем ближе к цели, тем меньше допуск (но не менее 0.5x)
        distance_factor = max(1.0 - (distance_to_target / 300.0), 0.5)
        
        # Базовый tolerance от скорости платформы
        # ✅ ИСПРАВЛЕНО: Используем формулу paddle_speed // 3 вместо paddle_speed * 0.25
        # для соответствия ожидаемому поведению из анализа
        if is_critical:
            paddle_tolerance = max(3, paddle_speed // 6)  # ✅ ИСПРАВЛЕНО: Для критических случаев
        else:
            paddle_tolerance = max(4, paddle_speed // 3)  # ✅ ИСПРАВЛЕНО: 1/3 скорости движения (как ожидается в анализе)
        
        # Комбинируем все факторы
        adaptive_tolerance = int(paddle_tolerance * speed_factor * distance_factor)
        
        # Ограничиваем разумными пределами
        final_tolerance = max(base_tolerance, min(adaptive_tolerance, 20))
        
        self._logger.debug(
            f"[ADAPTIVE TOLERANCE] ball_vel_y={ball_vel_y:.1f}, distance={distance_to_target:.1f}, "
            f"speed_factor={speed_factor:.2f}, distance_factor={distance_factor:.2f}, "
            f"paddle_tolerance={paddle_tolerance}, final={final_tolerance}, is_critical={is_critical}"
        )
        
        return final_tolerance

    def _proactive_center_movement(self, current_x: int, ball_y: float) -> int:
        """
        Упреждающее движение к центру при неопределенности.
        
        Если мяч далеко и движется от платформы, возвращаемся к центру,
        готовясь к новой атаке.
        
        Args:
            current_x: Текущая X-координата платформы
            ball_y: Y-координата мяча
        
        Returns:
            Направление движения (-1, 0, 1) или 0 если движение не требуется
        """
        if not self.current_game_state:
            return 0
        
        paddle_y = self.current_game_state.paddle_position.y
        field_height = self.screen_height
        
        # Если мяч далеко (в верхней трети поля) и выше платформы
        if ball_y < field_height * 0.3 and ball_y < paddle_y:
            center = self.screen_width // 2
            distance_to_center = abs(current_x - center)
            
            # Если достаточно далеко от центра - двигаемся к нему
            if distance_to_center > 50:
                movement = 1 if center > current_x else (-1 if center < current_x else 0)
                self._logger.debug(
                    f"[PROACTIVE CENTER] Мяч далеко ({ball_y:.1f}px), "
                    f"двигаемся к центру: current_x={current_x}, center={center}, "
                    f"movement={movement}"
                )
                return movement
        
        return 0

    def _clamp_paddle_position(self, position: int) -> int:
        """
        Ограничивает позицию платформы границами экрана.

        Args:
            position: Позиция платформы

        Returns:
            Ограниченная позиция платформы
        """
        paddle_half_width = self.paddle_width // 2
        min_x = paddle_half_width
        max_x = self.screen_width - paddle_half_width
        
        clamped = max(min_x, min(max_x, position))
        
        if clamped != position:
            self._logger.debug(
                f"[POSITION CLAMP] Позиция {position} ограничена до {clamped} "
                f"(границы: {min_x} - {max_x})"
            )
        
        return clamped
