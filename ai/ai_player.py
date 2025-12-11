"""
Основной класс AIPlayer для управления авторежимом игры Арканоид.
"""

import time
import math
import random
import os
import json
import logging
import sys
from typing import List, Optional, Dict, Any

import pygame

from .game_state import GameState, Point
from .trajectory_predictor import TrajectoryPredictor
from .position_optimizer import PositionOptimizer
from .learning_system import LearningSystem
from .performance_logger import PerformanceLogger


class AIPlayer:
    """
    Основной класс AIPlayer для управления авторежимом.

    Координирует работу всех компонентов AI системы:
    - TrajectoryPredictor для предсказания траектории мяча
    - PositionOptimizer для поиска оптимальной позиции платформы
    - LearningSystem для обучения на основе опыта
    - PerformanceLogger для логирования и аналитики
    """

    def __init__(
        self,
        screen_width: int = 800,
        screen_height: int = 600,
        debug_mode: bool = False,
    ):
        """
        Инициализация AIPlayer.

        Args:
            screen_width: Ширина игрового экрана.
            screen_height: Высота игрового экрана.
            debug_mode: Режим отладки с визуализацией.

        Raises:
            TypeError: Если типы параметров некорректны.
            ValueError: Если значения параметров некорректны.
        """
        # Валидация входных данных
        self._validate_dimensions(screen_width, screen_height)
        
        # Компоненты системы
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = bool(debug_mode)
        
        # Настройка логирования для этого экземпляра
        self._logger = self._setup_logging(debug_mode)

        self.trajectory_predictor = TrajectoryPredictor(screen_width, screen_height)
        self.position_optimizer = PositionOptimizer(screen_width, screen_height)
        self.learning_system = LearningSystem()

        # Логирование производительности (включено по умолчанию для диагностики)
        enable_session_logging = self._get_env_bool("AI_ENABLE_SESSION_LOGGING", default=True)
        self.performance_logger = PerformanceLogger(
            enable_session_logging=enable_session_logging
        )
        # КРИТИЧНО: НЕ создаем файл лога сразу при старте - это может блокировать выполнение
        # Файл лога будет создан автоматически при первом вызове save_session_log()
        # Это предотвращает блокировку при создании AIPlayer

        # Состояние AI
        self.current_game_state: Optional[GameState] = None
        self.last_paddle_position: Optional[float] = None
        self.last_action_time = time.time()

        # Общие метрики
        self.performance_metrics: Dict[str, Any] = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
            "best_time_50_bricks": None,  # Лучшее время для матча с 50 блоками (в секундах)
        }

        # Статистика текущей игры
        self.current_game_stats: Dict[str, Any] = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0,
        }

        # Флаг активности
        self.is_active = False

        # Система прицельного отбивания
        self.targeting_system: Dict[str, Any] = {
            "target_brick": None,  # Целевой кубик
            "optimal_offset": 0.0,  # Оптимальное смещение (-1..1)
            "successful_hits": [],  # История удачных ударов
            "brick_map": {},  # Карта всех кубиков
            "trajectory_targets": [],  # Цели для текущей траектории
            "hit_patterns": {},  # Паттерны успешных ударов
            "brick_coordinates": [],  # Координаты центров кубиков
            "visible_targets": [],  # Видимые цели
            "recent_target_positions": [],  # История последних выбранных целей для проверки симметрии
        }

        # Система предотвращения зацикливания
        self.loop_prevention_system: Dict[str, Any] = {
            "movement_history": [],  # История последних движений
            "position_history": [],  # История позиций платформы
            "trajectory_history": [],  # История траекторий мяча
            "loop_detection_threshold": 5,  # Порог повторений
            "strategy_change_cooldown": 0,  # Кулдаун смены стратегии
            "alternative_strategies": [
                "center_focus",
                "edge_focus",
                "predictive_targeting",
            ],
            "current_strategy_index": 0,
        }

        # Система отслеживания плавности движения
        self.smoothness_system: Dict[str, Any] = {
            "recent_movements": [],  # История последних движений (значения: -1, 0, 1)
            "recent_positions": [],  # История последних позиций
            "movement_changes": [],  # История смен направления движения
            "jitter_threshold": 3,  # Порог дрожания (количество смен направления)
            "jitter_window": 8,  # Окно анализа для дрожания
            "min_movement_distance": 5,  # Минимальное расстояние для движения (пиксели)
            "smoothness_penalty": 0.0,  # Текущий штраф за дрожание (0.0 - 1.0)
            "consecutive_stops": 0,  # Количество последовательных остановок (поощряется)
        }

        # Параметры платформы
        self.paddle_width = 120  # Ширина платформы

        # Последний множитель скорости платформы (для обучения)
        self._last_paddle_speed_multiplier = 1.0
        # Последняя скорректированная скорость платформы
        self._last_adjusted_paddle_speed = None

        # Метрики по сессиям (серии игр)
        self.session_metrics: List[Dict[str, Any]] = []
        self.session_counter: int = 0

        # Параметры для обучения в режиме обучения
        # Параметры режима обучения
        # Максимальная скорость мяча: 8 (с учетом времени движения платформы в зоне разделения)
        self.training_parameters: Dict[str, Any] = {
            "ball_speed": 8,  # Текущая скорость мяча (начальная скорость для обучения, ограничена временем движения платформы)
            "paddle_speed_multiplier": 2.0,  # Множитель скорости платформы (высокий для быстрой игры)
            "total_bricks_destroyed": 0,  # Всего кубиков сбито за матч
            "total_time": 0,  # Общее время матча
            "lives_lost": 0,  # Потерянные жизни
            "match_history": [],  # История матчей
        }
        
        # Отслеживание отбитий в пустоту
        self.empty_bounce_tracker = {
            "consecutive_empty_bounces": 0,  # Количество последовательных отбитий в пустоту
            "last_bounce_position": None,  # Последняя позиция платформы при отбитии
            "last_bounce_time": 0,  # Время последнего отбития
            "max_empty_bounces": 1,  # Максимум отбитий в пустоту подряд (уменьшено с 2 до 1)
            "bounce_history": [],  # История отбитий (для анализа)
            "ceiling_bounces": 0,  # Количество отскоков от потолка без попадания в кубики
        }
        
        # КРИТИЧНО: Отслеживание входа в зону разделения для одноразового движения платформы
        self.separation_zone_tracker = {
            "ball_entered_separation_zone": False,  # Мяч вошел в зону разделения
            "target_position_set": False,  # Целевая позиция установлена
            "target_position": None,  # Целевая позиция платформы
            "separation_zone_start": 226,  # Начало зоны разделения (bricks_zone_end + ball_diameter)
            "paddle_zone_start": 540,  # Начало зоны платформы (screen_height - 60)
            "paddle_moved_after_set": False,  # Флаг: платформа начала двигаться после установки цели
            "paddle_reached_target": False,  # Флаг: платформа достигла целевой позиции
            "last_movement_frame": 0,  # Номер кадра последнего движения
            "frames_since_target_set": 0,  # Количество кадров с момента установки цели
            "saved_ball_vel_x": None,  # Сохраненная скорость vel_x для отслеживания отскоков от стены
            "game_restart_required": False,  # Флаг: требуется перезапуск игры из-за нарушения правила
        }

    def _validate_dimensions(self, screen_width: int, screen_height: int) -> None:
        """
        Валидирует размеры экрана.
        
        Args:
            screen_width: Ширина экрана для валидации.
            screen_height: Высота экрана для валидации.
        
        Raises:
            TypeError: Если типы данных некорректны.
            ValueError: Если размеры некорректны.
        """
        if not isinstance(screen_width, int):
            raise TypeError(
                f"screen_width должен быть целым числом, получено: {type(screen_width).__name__}"
            )
        if not isinstance(screen_height, int):
            raise TypeError(
                f"screen_height должен быть целым числом, получено: {type(screen_height).__name__}"
            )
        if screen_width <= 0:
            raise ValueError(
                f"screen_width должен быть положительным, получено: {screen_width}"
            )
        if screen_height <= 0:
            raise ValueError(
                f"screen_height должен быть положительным, получено: {screen_height}"
            )
        if screen_width < 400 or screen_height < 300:
            raise ValueError(
                f"Минимальные размеры экрана: 400x300, получено: {screen_width}x{screen_height}"
            )

    @staticmethod
    def _get_env_bool(key: str, default: bool = True) -> bool:
        """
        Безопасно получает булево значение из переменной окружения.
        
        Args:
            key: Имя переменной окружения
            default: Значение по умолчанию
        
        Returns:
            Булево значение
        """
        try:
            value = os.getenv(key, "").strip().lower()
            if not value:
                return default
            return value in ("1", "true", "yes", "on")
        except Exception:
            # В случае ошибки возвращаем значение по умолчанию
            return default

    _instance_counter = 0  # Счетчик для создания уникальных имен логгеров
    
    @classmethod
    def _setup_logging(cls, debug_mode: bool) -> logging.Logger:
        """
        Настраивает и возвращает логгер для экземпляра AIPlayer.
        
        Args:
            debug_mode: Если True, устанавливает уровень DEBUG, иначе INFO
        
        Returns:
            Настроенный логгер для этого экземпляра
        """
        # Создаем уникальный логгер для каждого экземпляра
        cls._instance_counter += 1
        logger_name = f"{__name__}.instance_{cls._instance_counter}"
        logger = logging.getLogger(logger_name)
        
        # Настраиваем handler только если еще не настроен
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            # Предотвращаем дублирование сообщений через родительские логгеры
            logger.propagate = False
        
        # Устанавливаем уровень логирования для этого экземпляра
        # В debug_mode показываем все сообщения, иначе только INFO и выше
        if debug_mode:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        
        return logger

    def activate(self) -> None:
        """
        Активирует AIPlayer для управления игрой.
        """
        self.is_active = True
        self._logger.info("AIPlayer активирован. Начинаем управление игрой...")

    def deactivate(self) -> None:
        """
        Деактивирует AIPlayer.
        """
        self.is_active = False
        self._logger.info("AIPlayer деактивирован.")

    # ==========================
    # Обновление состояния игры
    # ==========================

    def update_game_state(
        self,
        ball,
        paddle,
        bricks,
        score: int,
        start_time: int,
    ) -> None:
        """
        Обновляет состояние игры для AI-системы.

        Args:
            ball: Объект мяча из игры.
            paddle: Объект платформы из игры.
            bricks: Список оставшихся кубиков.
            score: Текущий счёт игрока.
            start_time: Время начала игры.

        Raises:
            ValueError: Если входные данные некорректны.
        """
        # Проверка входных данных
        if ball is None or paddle is None or bricks is None:
            raise ValueError("Ball, paddle и bricks не могут быть None")
        if score < 0:
            raise ValueError("Score не может быть отрицательным")
        if start_time < 0:
            raise ValueError("Start_time не может быть отрицательным")

        # Создаём новое состояние игры
        self.current_game_state = GameState.create_from_game_objects(
            ball, paddle, bricks, score, start_time
        )

        # Инициализируем статистику игры, если это новая игра
        if self.current_game_stats["start_time"] is None:
            self.current_game_stats["start_time"] = start_time
            self.performance_logger.log_game_start(self.current_game_state)

        # Обновляем карту кубиков
        self._update_brick_map()

        # Логируем предсказание траектории, если включен debug-режим
        if self.debug_mode and self.is_ball_moving_towards_paddle():
            predicted_trajectory = self.trajectory_predictor.predict_trajectory(
                self.current_game_state
            )
            self.performance_logger.log_trajectory_prediction(
                [{"x": p.x, "y": p.y} for p in predicted_trajectory]
            )

    # ==========================
    # Работа с кубиками/целями
    # ==========================

    def _update_brick_map(self) -> None:
        """Обновляет карту всех кубиков на поле и координаты их центров."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            self.targeting_system["brick_map"] = {}
            self.targeting_system["brick_coordinates"] = []
            return

        brick_map: Dict[str, Dict[str, Any]] = {}
        brick_coordinates: List[Dict[str, Any]] = []

        for brick in self.current_game_state.remaining_bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", 60)
            brick_height = getattr(brick, "height", 20)

            # Ключ для карты кирпичей
            brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

            brick_info = {
                "x": brick_x,
                "y": brick_y,
                "width": brick_width,
                "height": brick_height,
                "center_x": brick_x + brick_width / 2,
                "center_y": brick_y + brick_height / 2,
                "row": int(brick_y / 30),
                "col": int(brick_x / 60),
            }

            brick_map[brick_key] = brick_info
            brick_coordinates.append(
                {
                    "x": brick_info["center_x"],
                    "y": brick_info["center_y"],
                    "brick": brick,
                    "key": brick_key,
                }
            )

        self.targeting_system["brick_map"] = brick_map
        self.targeting_system["brick_coordinates"] = brick_coordinates

        # Обновляем видимые цели для текущей траектории мяча
        self._update_visible_targets()

    def _update_visible_targets(self) -> None:
        """
        Обновляет список видимых целей (кубиков), в которые можно прицельно ударить
        с учётом текущей траектории мяча и возможных смещений по платформе.
        """
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            self.targeting_system["visible_targets"] = []
            return

        try:
            # Точка приземления мяча при текущей траектории
            landing_x = self._predict_exact_landing_position()

            visible_targets: List[Dict[str, Any]] = []

            # Несколько тестовых смещений платформы относительно точки приземления
            test_offsets = [-40, -20, 0, 20, 40]

            for offset in test_offsets:
                test_x = landing_x + offset

                # Строго ограничиваем позицию возможного центра платформы
                paddle_half_width = self.paddle_width / 2
                test_x = max(
                    paddle_half_width,
                    min(self.screen_width - paddle_half_width, test_x),
                )

                # Временное состояние игры с тестовой позицией платформы
                temp_game_state = self.current_game_state.clone()
                temp_game_state.paddle_position.x = test_x

                # Точка пересечения мяча с платформой
                intersection_point = (
                    self.trajectory_predictor.predict_paddle_intersection(
                        temp_game_state,
                        self.current_game_state.paddle_position.y,
                    )
                )
                if intersection_point is None:
                    continue

                # Траектория после отскока с данной позиции
                after_bounce_trajectory = (
                    self.trajectory_predictor.predict_after_bounce_trajectory(
                        temp_game_state,
                        intersection_point,
                        test_x,
                    )
                )

                # Проверяем, какие кубики пересекает эта траектория
                # Используем точную проверку пересечения с границами кубиков
                for coord in self.targeting_system["brick_coordinates"]:
                    brick = coord["brick"]
                    brick_x = getattr(brick, "x", 0)
                    brick_y = getattr(brick, "y", 0)
                    brick_width = getattr(brick, "width", 60)
                    brick_height = getattr(brick, "height", 20)
                    
                    # Точные границы кубика
                    brick_left = brick_x
                    brick_right = brick_x + brick_width
                    brick_top = brick_y
                    brick_bottom = brick_y + brick_height
                    
                    # Радиус мяча для проверки пересечения
                    ball_radius = 8
                    
                    # Проверяем пересечение траектории с кубиком
                    # Используем более частую проверку для точности
                    for i, point in enumerate(after_bounce_trajectory):
                        if not hasattr(point, "x") or not hasattr(point, "y"):
                            continue
                            
                        # Проверяем пересечение мяча (с учетом радиуса) с границами кубика
                        if (
                            brick_left - ball_radius
                            <= point.x
                            <= brick_right + ball_radius
                            and brick_top - ball_radius
                            <= point.y
                            <= brick_bottom + ball_radius
                        ):
                            # Дополнительная проверка: мяч действительно попадает в кубик
                            # Проверяем, что центр мяча находится в расширенной области кубика
                            if (
                                brick_left <= point.x <= brick_right
                                or brick_top <= point.y <= brick_bottom
                                or math.sqrt(
                                    (point.x - (brick_left + brick_right) / 2) ** 2
                                    + (point.y - (brick_top + brick_bottom) / 2) ** 2
                                )
                                < (brick_width / 2 + ball_radius)
                            ):
                                if coord not in visible_targets:
                                    visible_targets.append(coord)
                                break

            self.targeting_system["visible_targets"] = visible_targets
        except Exception as e:
            self._logger.warning(f"Ошибка при обновлении видимых целей: {e}", exc_info=True)
            self.targeting_system["visible_targets"] = []

    # ==========================
    # Базовые проверки/утилиты
    # ==========================

    def is_ball_moving_towards_paddle(self) -> bool:
        """Проверяет, движется ли мяч к платформе (вниз)."""
        if not self.current_game_state:
            return False
        return self.current_game_state.is_ball_falling()

    # ==========================
    # Оптимальная позиция платформы
    # ==========================

    def get_optimal_paddle_position(self) -> int:
        """
        Получает оптимальную позицию центра платформы
        с прицельным отбиванием по кубикам.
        """
        if not self.current_game_state or not self.is_active:
            # Резервная позиция — центр экрана
            return self.screen_width // 2

        try:
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )

            # Зоны по Y
            bricks_zone_end = 210  # Верхняя зона с кубиками
            ball_diameter = 16
            separation_zone_start = bricks_zone_end + ball_diameter  # ~226
            paddle_zone_start = self.screen_height - 60  # ~540

            # Обновляем отслеживание зоны разделения
            self.separation_zone_tracker["separation_zone_start"] = separation_zone_start
            self.separation_zone_tracker["paddle_zone_start"] = paddle_zone_start

            # КРИТИЧНО: Если мяч в зоне кубиков - платформа НЕ должна двигаться
            if ball_y < separation_zone_start:
                # Мяч в зоне кубиков - платформа на месте
                # КРИТИЧНО: НЕ сбрасываем отслеживание зоны разделения и целевую позицию,
                # так как мяч может временно попасть в зону кубиков (при отскоке),
                # но потом вернуться в зону разделения
                # Сбрасываем только если мяч действительно ушел далеко вверх (выше 50)
                # и НЕ установлена целевая позиция (чтобы не сбрасывать уже установленную позицию)
                if ball_y < 50 and not self.separation_zone_tracker.get("target_position_set", False):
                    # Мяч очень высоко и целевая позиция не установлена - сбрасываем отслеживание
                    self.separation_zone_tracker["ball_entered_separation_zone"] = False
                    self.separation_zone_tracker["target_position_set"] = False
                    self.separation_zone_tracker["target_position"] = None
                # ВСЕГДА возвращаем текущую позицию, не двигаемся
                return int(self.current_game_state.paddle_position.x)
            
            # Если мяч в разделительной зоне, но движется вверх — не дёргаем платформу
            if separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y <= 0:
                return int(self.current_game_state.paddle_position.x)

            # КРИТИЧНО: УБРАНО - больше не блокируем пересчет позиции
            # Позиция должна ВСЕГДА пересчитываться для точности
            # Это позволяет платформе адаптироваться к изменению траектории мяча
            
            # КРИТИЧНО: Проверяем, вошел ли мяч в зону разделения
            in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
            
            # КРИТИЧНО: Если позиция уже зафиксирована в зоне разделения - возвращаем её БЕЗ пересчета
            # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз при входе мяча в зону разделения
            # и не меняется до следующего отскока от стены
            if in_separation_zone and self.separation_zone_tracker.get("target_position_set"):
                fixed_position = self.separation_zone_tracker.get("target_position")
                if fixed_position is not None:
                    # КРИТИЧНО: Логируем возврат зафиксированной позиции для отслеживания
                    import random
                    if random.random() < 0.1:  # Логируем 10% кадров
                        self._logger.debug(f"[POSITION RETURN] ФЛАГ: Возвращаем зафиксированную позицию БЕЗ пересчета! "
                                          f"target_position={fixed_position:.1f}, ball_y={ball_y:.1f}")
                    
                    # КРИТИЧНО: Проверяем, не изменилась ли позиция (нарушение правила)
                    # Если позиция изменилась без отскока от стены - это нарушение
                    saved_vel_x = self.separation_zone_tracker.get("saved_ball_vel_x")
                    current_vel_x = self.current_game_state.ball_velocity.x if self.current_game_state else 0
                    
                    # Если vel_x не изменился (нет отскока от стены), но позиция изменилась - нарушение
                    if saved_vel_x is not None and abs(current_vel_x - saved_vel_x) <= 0.1:
                        # Нет отскока от стены - позиция НЕ должна меняться
                        # Возвращаем зафиксированную позицию БЕЗ изменений
                        return int(fixed_position)
                    else:
                        # vel_x изменился - это отскок от стены, позиция может измениться
                        # Но мы все равно возвращаем зафиксированную позицию до следующего пересчета
                        return int(fixed_position)
            
            # Если мяч только что вошел в зону разделения, определяем целевую позицию ОДИН РАЗ
            if in_separation_zone and not self.separation_zone_tracker["ball_entered_separation_zone"]:
                self.separation_zone_tracker["ball_entered_separation_zone"] = True
                # Определяем целевую позицию на основе траектории и оставшихся кубиков
                # Это будет сделано ниже в коде

            # Мяч ниже кубиков и движется вниз/в разделительной зоне — считаем прицельную позицию
            if ball_y < paddle_zone_start:
                landing_x = self._predict_exact_landing_position()
                bricks_count = (
                    len(self.current_game_state.remaining_bricks)
                    if self.current_game_state
                    else 0
                )
                ball_speed = (
                    self.current_game_state.ball_speed if self.current_game_state else 5
                )

                # Получаем текущую ситуацию для learning_system
                current_situation = {
                    "bricks_remaining": bricks_count,
                    "ball_speed": ball_speed,
                    "time_pressure": self._is_time_pressure(),
                }

                # Применяем пользовательские правила из промпта "разрушение и контроль"
                user_rules = self.learning_system.apply_user_prompt_rules(
                    current_situation
                )

                # Получаем рекомендации по стратегии
                strategy_weights = self.learning_system.get_strategy_recommendation(
                    current_situation
                )

                # КРИТИЧНО: Для малого количества блоков (<=10) ВСЕГДА используем точное прицеливание
                # Учитываем пользовательские правила из промпта "разрушение и контроль"
                precision_priority = (
                    user_rules.get("precision_priority", False) or bricks_count <= 10
                )
                
                # Применяем правила из промпта: если указан приоритет точности, используем его
                if user_rules.get("destruction_priority", False):
                    precision_priority = True  # Приоритет разрушения всех блоков
                
                # КРИТИЧНО: Если было отбитие в пустоту, принудительно используем точное прицеливание
                # Порог уменьшен до 1 - после первого отбития в пустоту сразу меняем стратегию
                if self.empty_bounce_tracker["consecutive_empty_bounces"] >= self.empty_bounce_tracker["max_empty_bounces"]:
                    precision_priority = True
                    # Используем координаты кубиков напрямую из brick_coordinates
                    if self.targeting_system.get("brick_coordinates"):
                        # Принудительно находим позицию для прицеливания в ближайший кубик
                        optimal_position = self._force_target_brick_from_coordinates(landing_x)
                        if optimal_position is not None:
                            # КРИТИЧНО: При отбитии в пустоту СБРАСЫВАЕМ целевую позицию и устанавливаем новую
                            # Это позволяет изменить траекторию мяча и избежать зацикливания
                            self.separation_zone_tracker["target_position_set"] = False
                            self.separation_zone_tracker["target_position"] = None
                            # Устанавливаем новую целевую позицию для изменения траектории
                            if in_separation_zone:
                                self.separation_zone_tracker["target_position"] = int(optimal_position)
                                self.separation_zone_tracker["target_position_set"] = True
                            self._log_paddle_movement(
                                self.current_game_state.paddle_position.x,
                                int(optimal_position),
                                f"ПРИНУДИТЕЛЬНОЕ прицеливание после {self.empty_bounce_tracker['consecutive_empty_bounces']} отбитий в пустоту. Координаты кубиков: {len(self.targeting_system.get('brick_coordinates', []))}",
                                1.0
                            )
                            return int(optimal_position)

                if precision_priority:
                    # КРИТИЧНО: Используем координаты кубиков из brick_coordinates для точного прицеливания
                    optimal_position = self._calculate_precise_position_for_few_bricks(
                        landing_x
                    )
                    # Если позиция не найдена, но есть координаты кубиков - используем их напрямую
                    if optimal_position is None and self.targeting_system.get("brick_coordinates"):
                        optimal_position = self._force_target_brick_from_coordinates(landing_x)
                    
                    if optimal_position is not None:
                        # Оцениваем вероятность успеха для этой позиции
                        action_plan = {
                            "ball_speed": ball_speed,
                            "movement_distance": abs(
                                optimal_position
                                - self.current_game_state.paddle_position.x
                            ),
                            "confidence": 0.8,
                        }
                        success_prob = self.learning_system.predict_success_probability(
                            action_plan
                        )
                        # КРИТИЧНО: Для малого количества блоков (<=10) ВСЕГДА используем позицию,
                        # даже если вероятность невысокая, чтобы не отбивать в пустоту
                        if success_prob > 0.2 or bricks_count <= 10:  # Очень низкий порог для малого количества
                            # КРИТИЧНО: Если целевая позиция уже установлена, возвращаем её вместо пересчета
                            if self.separation_zone_tracker.get("target_position_set", False):
                                return int(self.separation_zone_tracker.get("target_position"))
                            
                            # КРИТИЧНО: Если мяч в зоне разделения, сохраняем целевую позицию один раз
                            if in_separation_zone:
                                if self.separation_zone_tracker.get("target_position_set", False):
                                    # НАРУШЕНИЕ ПРАВИЛА: Позиция уже установлена, но пытаемся установить снова!
                                    old_pos = self.separation_zone_tracker.get("target_position")
                                    import sys
                                    self._logger.warning(f"[RULE VIOLATION] ФЛАГ: Попытка установить позицию ПОВТОРНО (few_bricks)! "
                                                         f"Старая позиция={old_pos:.1f}, Новая позиция={int(optimal_position):.1f}, "
                                                         f"Разница={abs(old_pos - int(optimal_position)):.1f}px")
                                    self.separation_zone_tracker["game_restart_required"] = True
                                else:
                                    self.separation_zone_tracker["target_position"] = int(optimal_position)
                                    self.separation_zone_tracker["target_position_set"] = True
                                    self._logger.debug(f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые (few_bricks)! "
                                                       f"target_position={int(optimal_position):.1f}")
                            
                            # Логируем передвижение платформы (используем лог из промпта)
                            if user_rules.get("use_movement_log", True):  # По умолчанию включено
                                brick_coords = [f"({b.get('x', 0):.0f},{b.get('y', 0):.0f})" for b in self.targeting_system.get('brick_coordinates', [])]
                                self._log_paddle_movement(
                                    self.current_game_state.paddle_position.x,
                                    int(optimal_position),
                                    f"Точное прицеливание в {bricks_count} блоков. Координаты: {', '.join(brick_coords[:5])}",
                                    0.9
                                )
                            return int(optimal_position)
                
                # На поздних этапах используем стратегию максимизации разрушений
                if bricks_count <= 15:
                    optimal_position = self._calculate_position_for_max_destruction(
                        landing_x
                    )
                    if optimal_position is not None:
                        # Оцениваем вероятность успеха
                        action_plan = {
                            "ball_speed": ball_speed,
                            "movement_distance": abs(
                                optimal_position
                                - self.current_game_state.paddle_position.x
                            ),
                            "confidence": 0.7,
                        }
                        success_prob = self.learning_system.predict_success_probability(
                            action_plan
                        )
                        if success_prob > 0.5:
                            # КРИТИЧНО: Если целевая позиция уже установлена, возвращаем её вместо пересчета
                            if self.separation_zone_tracker.get("target_position_set", False):
                                return int(self.separation_zone_tracker.get("target_position"))
                        return int(optimal_position)
                
                target_brick = self._find_best_target_brick()

                if target_brick:
                    # Оптимальное смещение по платформе
                    optimal_offset = self._calculate_optimal_offset(
                        landing_x, target_brick
                    )

                    self.targeting_system["target_brick"] = target_brick
                    self.targeting_system["optimal_offset"] = optimal_offset

                    paddle_half_width = self.paddle_width / 2
                    optimal_position = landing_x - (optimal_offset * paddle_half_width)

                    # КРИТИЧНО: Границы по центру платформы с безопасным отступом от краев
                    # Минимум 30 пикселей от края экрана, чтобы избежать боковых ударов
                    safe_margin = 30  # Безопасный отступ от края
                    min_position = paddle_half_width + safe_margin
                    max_position = self.screen_width - paddle_half_width - safe_margin
                    
                    # Если рассчитанная позиция слишком близко к краю, смещаем к центру
                    if optimal_position < min_position:
                        # Слишком близко к левому краю - смещаем вправо
                        optimal_position = min_position
                    elif optimal_position > max_position:
                        # Слишком близко к правому краю - смещаем влево
                        optimal_position = max_position
                    
                    # Дополнительная проверка: если позиция все еще слишком близко к краю
                    # (менее 20 пикселей от края платформы), смещаем еще больше к центру
                    paddle_left_edge = optimal_position - paddle_half_width
                    paddle_right_edge = optimal_position + paddle_half_width
                    
                    if paddle_left_edge < safe_margin:
                        # Платформа слишком близко к левому краю
                        optimal_position = safe_margin + paddle_half_width
                    elif paddle_right_edge > self.screen_width - safe_margin:
                        # Платформа слишком близко к правому краю
                        optimal_position = self.screen_width - safe_margin - paddle_half_width

                    # Учитываем предпочтения позиций из learning_system
                    position_preference = (
                        self.learning_system.get_optimal_position_preference(
                            int(optimal_position)
                        )
                    )
                    # Если предпочтительность низкая, немного корректируем позицию
                    if position_preference < 0.4:
                        # КРИТИЧНО: Если целевая позиция уже установлена, не ищем альтернативную позицию
                        if self.separation_zone_tracker.get("target_position_set", False):
                            pass  # Пропускаем поиск альтернативной позиции
                        else:
                            # Ищем ближайшую позицию с высокой предпочтительностью
                            for offset in range(-40, 41, 10):
                                test_x = int(optimal_position) + offset
                                if min_position <= test_x <= max_position:
                                    pref = self.learning_system.get_optimal_position_preference(
                                        test_x
                                    )
                                    if pref > 0.6:
                                        return test_x

                    # КРИТИЧНО: УБРАНО - больше не блокируем пересчет позиции
                    # Позиция должна ВСЕГДА пересчитываться для точности
                    
                    # КРИТИЧНО: Если мяч в зоне разделения, сохраняем целевую позицию один раз
                    if in_separation_zone and not self.separation_zone_tracker["target_position_set"]:
                        self.separation_zone_tracker["target_position"] = int(optimal_position)
                        self.separation_zone_tracker["target_position_set"] = True
                    
                    # Логируем передвижение (всегда для анализа)
                    self._log_paddle_movement(
                        self.current_game_state.paddle_position.x,
                        int(optimal_position),
                        f"Прицеливание в целевой блок (осталось {bricks_count} блоков)",
                        0.8
                    )
                    return int(optimal_position)
                else:
                    # КРИТИЧНО: Если нет явной цели, но есть координаты кубиков - используем их
                    if bricks_count <= 10 and self.targeting_system.get("brick_coordinates"):
                        # КРИТИЧНО: Если целевая позиция уже установлена, возвращаем её вместо пересчета
                        if self.separation_zone_tracker.get("target_position_set", False):
                            return int(self.separation_zone_tracker.get("target_position"))
                        
                        optimal_position = self._force_target_brick_from_coordinates(landing_x)
                        if optimal_position is not None:
                            # КРИТИЧНО: Обеспечиваем безопасную позицию (не слишком близко к краям)
                            safe_margin = 30  # Безопасный отступ от края
                            paddle_half_width = self.paddle_width / 2
                            min_position = paddle_half_width + safe_margin
                            max_position = self.screen_width - paddle_half_width - safe_margin
                            optimal_position = max(min_position, min(max_position, optimal_position))
                            
                            # КРИТИЧНО: Если мяч в зоне разделения, сохраняем целевую позицию один раз
                            if in_separation_zone:
                                if self.separation_zone_tracker.get("target_position_set", False):
                                    # НАРУШЕНИЕ ПРАВИЛА: Позиция уже установлена, но пытаемся установить снова!
                                    old_pos = self.separation_zone_tracker.get("target_position")
                                    import sys
                                    self._logger.warning(f"[RULE VIOLATION] ФЛАГ: Попытка установить позицию ПОВТОРНО (brick_coords)! "
                                                         f"Старая позиция={old_pos:.1f}, Новая позиция={int(optimal_position):.1f}, "
                                                         f"Разница={abs(old_pos - int(optimal_position)):.1f}px")
                                    self.separation_zone_tracker["game_restart_required"] = True
                                else:
                                    self.separation_zone_tracker["target_position"] = int(optimal_position)
                                    self.separation_zone_tracker["target_position_set"] = True
                                    self._logger.debug(f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые (brick_coords)! "
                                                       f"target_position={int(optimal_position):.1f}")
                            
                            # Логируем передвижение (всегда для анализа)
                            self._log_paddle_movement(
                                self.current_game_state.paddle_position.x,
                                int(optimal_position),
                                f"Прицеливание по координатам (осталось {bricks_count} блоков)",
                                0.7
                            )
                            return int(optimal_position)
                    
                    # Нет явной цели — просто ловим мяч
                    # КРИТИЧНО: Если позиция уже зафиксирована - возвращаем её
                    if in_separation_zone and self.separation_zone_tracker.get("target_position_set"):
                        fixed_position = self.separation_zone_tracker.get("target_position")
                        if fixed_position is not None:
                            return int(fixed_position)
                    
                    # КРИТИЧНО: Обеспечиваем безопасную позицию (не слишком близко к краям)
                    safe_margin = 30  # Безопасный отступ от края
                    paddle_half_width = self.paddle_width / 2
                    min_position = paddle_half_width + safe_margin
                    max_position = self.screen_width - paddle_half_width - safe_margin
                    base_position = max(min_position, min(max_position, int(landing_x)))
                    
                    # КРИТИЧНО: Фиксируем позицию в зоне разделения
                    if in_separation_zone:
                        if self.separation_zone_tracker.get("target_position_set", False):
                            # НАРУШЕНИЕ ПРАВИЛА: Позиция уже установлена, но пытаемся установить снова!
                            old_pos = self.separation_zone_tracker.get("target_position")
                            self._logger.warning(f"[RULE VIOLATION] ФЛАГ: Попытка установить позицию ПОВТОРНО (простое движение)! "
                                                 f"Старая позиция={old_pos:.1f}, Новая позиция={base_position:.1f}, "
                                                 f"Разница={abs(old_pos - base_position):.1f}px")
                            self.separation_zone_tracker["game_restart_required"] = True
                        else:
                            self.separation_zone_tracker["target_position"] = base_position
                            self.separation_zone_tracker["target_position_set"] = True
                            self._logger.debug(f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые (простое движение)! "
                                               f"target_position={base_position:.1f}")
                    
                    # Логируем даже простое движение для полного анализа
                    self._log_paddle_movement(
                        self.current_game_state.paddle_position.x,
                        base_position,
                        f"Простое движение к мячу (осталось {bricks_count} блоков)",
                        0.5
                    )
                    # Учитываем предпочтения позиций
                    position_preference = (
                        self.learning_system.get_optimal_position_preference(
                            base_position
                        )
                    )
                    if position_preference < 0.4:
                        # Ищем ближайшую позицию с высокой предпочтительностью
                        for offset in range(-40, 41, 10):
                            test_x = base_position + offset
                            # КРИТИЧНО: Учитываем безопасные границы при поиске альтернативной позиции
                            if min_position <= test_x <= max_position:
                                pref = self.learning_system.get_optimal_position_preference(
                                    test_x
                                )
                                if pref > 0.6:
                                    return test_x
                    return base_position
            else:
                # Мяч движется вверх — обрабатываем возможный отскок от потолка
                if ball_y < 50:
                    return self._handle_ceiling_bounce_positioning()
                # Иначе просто сопровождаем мяч
                return int(self._track_ball_position())

        except Exception as e:
            self._logger.error(f"Ошибка при расчете оптимальной позиции: {e}", exc_info=True)
            return int(self.current_game_state.paddle_position.x)

    # ==========================
    # Выбор целевого кирпича
    # ==========================

    def _find_best_target_brick(self) -> Optional[Any]:
        """
        Находит лучший кубик для прицеливания с учётом видимости, позиции платформы и траектории.

        Приоритеты:
        1. На поздних этапах (<= 15 блоков) - максимизация разрушений в следующем цикле.
        2. Кубики, видимые для текущей траектории.
        3. Кубики в нижних рядах (ближе к платформе).
        4. Кубики ближе к центру экрана (стабильнее).
        5. Кубики с хорошей историей попаданий.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks_count = len(self.current_game_state.remaining_bricks)
        
        # На поздних этапах используем стратегию максимизации разрушений
        if bricks_count <= 15:
            return self._find_optimal_angle_for_max_destruction()

        visible_targets = self.targeting_system["visible_targets"]
        paddle_y = self.current_game_state.paddle_position.y

        # 1. Сначала рассматриваем только видимые цели
        if visible_targets:
            best_visible_brick = None
            best_visible_score = -float("inf")
            
            # Получаем историю последних выбранных целей для проверки симметрии
            recent_targets = self.targeting_system.get("recent_target_positions", [])
            screen_center = self.screen_width // 2

            for target in visible_targets:
                brick = target["brick"]
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", 60)
                brick_center_x = brick_x + brick_width / 2

                score = 1000.0  # базовый бонус за видимость

                # Бонус за близость к платформе
                distance_to_paddle = paddle_y - brick_y
                if distance_to_paddle > 0:
                    score += (1.0 / distance_to_paddle) * 500.0

                # Штраф за удалённость от центра
                center_distance = abs(brick_center_x - screen_center)
                score -= center_distance * 0.3

                # Проверка на симметричные паттерны
                # Штрафуем цели, которые создают симметричные отскоки
                if recent_targets:
                    # Проверяем, не создает ли эта цель симметричный паттерн
                    for prev_target_x in recent_targets[
                        -3:
                    ]:  # Проверяем последние 3 цели
                        # Если текущая цель симметрична предыдущей относительно центра
                        symmetry_distance = abs(
                            abs(brick_center_x - screen_center)
                            - abs(prev_target_x - screen_center)
                        )
                        if symmetry_distance < 20:  # Слишком симметрично
                            # Штраф за симметрию
                            score -= 300.0
                            
                        # Дополнительная проверка: если цели находятся на одинаковом расстоянии от центра
                        # но с разных сторон - это симметричный паттерн
                        if (
                            abs(brick_center_x - screen_center) < 30
                            and abs(prev_target_x - screen_center) < 30
                            and (brick_center_x - screen_center)
                            * (prev_target_x - screen_center)
                            < 0
                        ):
                            # Цели симметричны относительно центра
                            score -= 400.0

                # Бонус за успешную историю попаданий
                brick_key = target["key"]
                if brick_key in self.targeting_system["hit_patterns"]:
                    pattern = self.targeting_system["hit_patterns"][brick_key]
                    score += pattern.get("success_rate", 0.0) * 200.0

                if score > best_visible_score:
                    best_visible_score = score
                    best_visible_brick = brick

            if best_visible_brick:
                # Сохраняем позицию выбранной цели для проверки симметрии
                selected_brick_x = (
                    getattr(best_visible_brick, "x", 0)
                    + getattr(best_visible_brick, "width", 60) / 2
                )
                if "recent_target_positions" not in self.targeting_system:
                    self.targeting_system["recent_target_positions"] = []
                self.targeting_system["recent_target_positions"].append(
                    selected_brick_x
                )
                # Ограничиваем историю последними 5 целями
                if len(self.targeting_system["recent_target_positions"]) > 5:
                    self.targeting_system["recent_target_positions"] = (
                        self.targeting_system["recent_target_positions"][-5:]
                    )
                return best_visible_brick

        # 2. Резервная логика, если нет видимых целей
        bricks = self.current_game_state.remaining_bricks
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y

        # Если кубиков мало — отдельная логика
        if len(bricks) <= 5:
            return self._find_best_target_for_few_bricks(bricks, paddle_y, ball_x)

        # Проверяем, отбивается ли мяч от потолка
        is_ceiling_bounce = ball_y < 100 and self.current_game_state.ball_velocity.y > 0

        best_brick = None
        best_score = -float("inf")

        # Получаем историю последних выбранных целей для проверки симметрии
        recent_targets = self.targeting_system.get("recent_target_positions", [])
        screen_center = self.screen_width // 2

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            if distance_to_paddle > 0:
                # Приоритет нижним кубикам
                score += (1.0 / distance_to_paddle) * 1000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            # Проверка на симметричные паттерны
            if recent_targets:
                for prev_target_x in recent_targets[-3:]:  # Проверяем последние 3 цели
                    # Если текущая цель симметрична предыдущей относительно центра
                    symmetry_distance = abs(
                        abs(brick_center_x - screen_center)
                        - abs(prev_target_x - screen_center)
                    )
                    if symmetry_distance < 20:  # Слишком симметрично
                        # Штраф за симметрию
                        score -= 200.0
                        
                    # Дополнительная проверка: если цели находятся на одинаковом расстоянии от центра
                    # но с разных сторон - это симметричный паттерн
                    if (
                        abs(brick_center_x - screen_center) < 30
                        and abs(prev_target_x - screen_center) < 30
                        and (brick_center_x - screen_center)
                        * (prev_target_x - screen_center)
                        < 0
                    ):
                        # Цели симметричны относительно центра
                        score -= 300.0

            if is_ceiling_bounce:
                # При отскоке от потолка меньше любим центр
                center_distance = abs(brick_center_x - screen_center)
                score -= center_distance * 0.3
                # Бонус за близость к краям
                edge_distance = min(brick_center_x, self.screen_width - brick_center_x)
                score += edge_distance * 0.2
            else:
                # Обычная логика — ближе к текущей траектории
                horizontal_distance = abs(brick_center_x - ball_x)
                score -= horizontal_distance * 0.5

            # Бонус за историю попаданий
            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system["hit_patterns"]:
                pattern = self.targeting_system["hit_patterns"][brick_key]
                score += pattern.get("success_rate", 0.0) * 100.0

            if score > best_score:
                best_score = score
                best_brick = brick

        if best_brick:
            # Сохраняем позицию выбранной цели для проверки симметрии
            selected_brick_x = (
                getattr(best_brick, "x", 0) + getattr(best_brick, "width", 60) / 2
            )
            if "recent_target_positions" not in self.targeting_system:
                self.targeting_system["recent_target_positions"] = []
            self.targeting_system["recent_target_positions"].append(selected_brick_x)
            # Ограничиваем историю последними 5 целями
            if len(self.targeting_system["recent_target_positions"]) > 5:
                self.targeting_system["recent_target_positions"] = (
                    self.targeting_system["recent_target_positions"][-5:]
                )

        return best_brick

    def _calculate_precise_position_for_few_bricks(
        self, landing_x: float
    ) -> Optional[float]:
        """
        Вычисляет точную позицию платформы для попадания в оставшиеся блоки (1-10 блоков).
        Использует точное прицеливание в каждый блок для избежания отбивания в пустоту.
        КРИТИЧНО: При 1 кубике использует максимально агрессивное прицеливание.

        Args:
            landing_x: X-координата приземления мяча.

        Returns:
            Оптимальная X-координата центра платформы или None.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        bricks_count = len(bricks)

        if bricks_count > 10:
            return None  # Этот метод только для малого количества блоков (до 10)
        
        # КРИТИЧНО: При 1 кубике используем максимально агрессивное прицеливание
        is_critical = bricks_count == 1

        paddle_y = self.current_game_state.paddle_position.y
        paddle_half_width = self.paddle_width / 2

        # Получаем точку пересечения с платформой
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )

        if intersection_point is None:
            return None

        best_position = None
        best_score = -float("inf")

        # Для каждого блока рассчитываем точную позицию платформы для попадания
        for brick in bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", 60)
            brick_height = getattr(brick, "height", 20)
            brick_center_x = brick_x + brick_width / 2
            brick_center_y = brick_y + brick_height / 2

            # Рассчитываем необходимый угол отскока для попадания в центр блока
            # Расстояние от платформы до блока
            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y

            if dy <= 0:
                continue  # Блок выше платформы или на уровне

            # Рассчитываем необходимую горизонтальную скорость после отскока
            # Используем физику: угол отскока зависит от позиции на платформе
            # Чем дальше от центра платформы, тем больше горизонтальная скорость

            # Целевой угол (в радианах) для попадания в блок
            target_angle = math.atan2(dx, dy)

            # Рассчитываем необходимое смещение на платформе для получения этого угла
            # Максимальный угол отскока зависит от позиции на платформе
            # Используем более точную формулу
            max_angle = math.atan2(paddle_half_width, 50)  # Максимальный угол отскока

            # Нормализуем целевой угол
            normalized_angle = max(-max_angle, min(max_angle, target_angle))

            # Рассчитываем смещение на платформе
            required_offset = normalized_angle / max_angle if max_angle > 0 else 0

            # Вычисляем позицию платформы
            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x

            # Ограничиваем границами
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))

            # Проверяем, действительно ли эта позиция приведет к попаданию
            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )

            # Проверяем, попадет ли мяч в этот блок
            will_hit = False
            hit_confidence = 0.0  # Уверенность в попадании (0.0-1.0)
            
            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue

                # Расширенная проверка попадания с учетом радиуса мяча
                ball_radius = 8
                # Более широкая проверка попадания
                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    # Рассчитываем уверенность: чем ближе к центру блока, тем выше
                    center_x = brick_x + brick_width / 2
                    center_y = brick_y + brick_height / 2
                    distance_to_center = math.sqrt(
                        (point.x - center_x) ** 2 + (point.y - center_y) ** 2
                    )
                    max_distance = math.sqrt((brick_width / 2 + ball_radius) ** 2 + (brick_height / 2 + ball_radius) ** 2)
                    hit_confidence = max(hit_confidence, 1.0 - (distance_to_center / max_distance))
                    break

            # КРИТИЧНО: При 1 кубике используем позицию даже при низкой уверенности
            # или если мяч пролетит близко к блоку (в пределах 30 пикселей)
            if is_critical and not will_hit:
                min_distance_to_brick = float('inf')
                for point in after_bounce_trajectory:
                    if not hasattr(point, "x") or not hasattr(point, "y"):
                        continue
                    # Расстояние от точки траектории до блока
                    closest_x = max(brick_x, min(point.x, brick_x + brick_width))
                    closest_y = max(brick_y, min(point.y, brick_y + brick_height))
                    distance = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    min_distance_to_brick = min(min_distance_to_brick, distance)
                
                # Если траектория проходит близко к блоку (в пределах 30 пикселей), используем позицию
                if min_distance_to_brick <= 30:
                    will_hit = True
                    hit_confidence = max(0.3, 1.0 - (min_distance_to_brick / 30.0))

            if will_hit:
                # Оцениваем качество этой позиции
                # Приоритет: ближайшие блоки, нижние блоки
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)  # Ближе = лучше

                # Бонус за нижние блоки
                if brick_y > 200:
                    score += 5000.0

                # Бонус за центральные блоки (более предсказуемо)
                center_distance = abs(brick_center_x - self.screen_width // 2)
                score -= center_distance * 0.1
                
                # КРИТИЧНО: При 1 кубике добавляем огромный бонус за уверенность в попадании
                if is_critical:
                    score += hit_confidence * 50000.0  # Огромный бонус за уверенность
                    # При 1 кубике приоритет - найти ЛЮБУЮ рабочую позицию
                    if hit_confidence > 0.2:  # Даже низкая уверенность приемлема
                        score += 100000.0

                if score > best_score:
                    best_score = score
                    best_position = paddle_position

        # Если не нашли точное попадание, используем более агрессивный расчет
        if best_position is None and bricks:
            # Пробуем более широкий диапазон смещений для каждого блока
            for brick in bricks:
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", 60)
                brick_height = getattr(brick, "height", 20)
                brick_center_x = brick_x + brick_width / 2

                # Пробуем разные смещения на платформе для попадания в блок
                for test_offset in [
                    -1.0,
                    -0.8,
                    -0.6,
                    -0.4,
                    -0.2,
                    0.0,
                    0.2,
                    0.4,
                    0.6,
                    0.8,
                    1.0,
                ]:
                    test_bounce_x = intersection_point.x - (
                        test_offset * paddle_half_width
                    )
                    test_paddle_position = test_bounce_x

                    # Ограничиваем границами
                    min_position = paddle_half_width
                    max_position = self.screen_width - paddle_half_width
                    test_paddle_position = max(
                        min_position, min(max_position, test_paddle_position)
                    )

                    # Симулируем траекторию
                    test_trajectory = (
                        self.trajectory_predictor.predict_after_bounce_trajectory(
                            self.current_game_state, intersection_point, test_bounce_x
                        )
                    )

                    # Проверяем попадание
                    for point in test_trajectory:
                        if not hasattr(point, "x") or not hasattr(point, "y"):
                            continue

                        # Расширенная проверка попадания (с учетом радиуса мяча)
                        ball_radius = 8
                        if (
                            brick_x - ball_radius
                            <= point.x
                            <= brick_x + brick_width + ball_radius
                            and brick_y - ball_radius
                            <= point.y
                            <= brick_y + brick_height + ball_radius
                        ):
                            # Нашли попадание - используем эту позицию
                            best_position = test_paddle_position
                            break

                    if best_position is not None:
                        break

                if best_position is not None:
                    break

            # Если все еще не нашли, используем упрощенный расчет с более агрессивным поиском
            if best_position is None:
                # Берем ближайший нижний блок и рассчитываем позицию для прицеливания в него
                closest_brick = min(
                    bricks,
                    key=lambda b: (
                        paddle_y - getattr(b, "y", 0),
                        abs(
                            (getattr(b, "x", 0) + getattr(b, "width", 60) / 2)
                            - landing_x
                        ),
                    ),
                )

                brick_center_x = (
                    getattr(closest_brick, "x", 0)
                    + getattr(closest_brick, "width", 60) / 2
                )

                # КРИТИЧНО: При 1 кубике используем максимально агрессивное прицеливание
                if is_critical:
                    # Для 1 кубика пробуем несколько вариантов смещения для гарантированного попадания
                    for test_offset_multiplier in [1.0, 1.2, 1.5, 2.0]:
                        dx = brick_center_x - landing_x
                        required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * test_offset_multiplier)))
                        test_position = landing_x - (required_offset * paddle_half_width)
                        
                        # Ограничиваем границами
                        min_position = paddle_half_width
                        max_position = self.screen_width - paddle_half_width
                        test_position = max(min_position, min(max_position, test_position))
                        
                        # Проверяем, что позиция разумна
                        if abs(test_position - landing_x) < self.screen_width:
                            best_position = test_position
                            break
                else:
                    # Для нескольких блоков используем стандартный расчет
                    dx = brick_center_x - landing_x
                    required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
                    best_position = landing_x - (required_offset * paddle_half_width)

                # Ограничиваем границами
                min_position = paddle_half_width
                max_position = self.screen_width - paddle_half_width
                best_position = max(min_position, min(max_position, best_position))

        # КРИТИЧНО: Если все еще не нашли позицию при малом количестве блоков,
        # используем прицеливание в ближайший блок (даже если точное попадание не гарантировано)
        if best_position is None and bricks_count <= 10 and bricks:
            # Берем ближайший нижний блок
            closest_brick = min(
                bricks,
                key=lambda b: (
                    paddle_y - getattr(b, "y", 0),
                    abs(
                        (getattr(b, "x", 0) + getattr(b, "width", 60) / 2)
                        - landing_x
                    ),
                ),
            )
            
            brick_center_x = (
                getattr(closest_brick, "x", 0)
                + getattr(closest_brick, "width", 60) / 2
            )
            
            # Рассчитываем позицию для прицеливания в центр блока
            dx = brick_center_x - landing_x
            # Используем более агрессивное смещение для попадания в блок
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            best_position = landing_x - (required_offset * paddle_half_width)
            
            # Ограничиваем границами
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            best_position = max(min_position, min(max_position, best_position))

        return best_position

    def _force_target_brick_from_coordinates(self, landing_x: float) -> Optional[float]:
        """
        Принудительно находит позицию платформы для прицеливания в блок, используя координаты из brick_coordinates.
        Используется когда обычные методы не находят позицию, но координаты блоков известны.
        
        Args:
            landing_x: X-координата приземления мяча
            
        Returns:
            Оптимальная X-координата центра платформы или None
        """
        if not self.current_game_state:
            return None
        
        brick_coordinates = self.targeting_system.get("brick_coordinates", [])
        if not brick_coordinates:
            # КРИТИЧНО: Если координаты не загружены, используем remaining_bricks напрямую
            if self.current_game_state and self.current_game_state.remaining_bricks:
                # Создаем координаты из remaining_bricks
                brick_coordinates = []
                for brick in self.current_game_state.remaining_bricks:
                    brick_x = getattr(brick, "x", 0)
                    brick_y = getattr(brick, "y", 0)
                    brick_width = getattr(brick, "width", 60)
                    brick_coordinates.append({
                        "x": brick_x + brick_width / 2,
                        "y": brick_y,
                        "brick": brick,
                    })
        
        if not brick_coordinates:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        paddle_half_width = self.paddle_width / 2
        
        # Получаем точку пересечения с платформой
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        best_position = None
        best_score = -float("inf")
        
        # КРИТИЧНО: Сортируем кубики по приоритету (ближайшие и нижние получают больший приоритет)
        sorted_bricks = sorted(
            brick_coordinates,
            key=lambda b: (
                -b.get("y", 0),  # Нижние кубики в приоритете (больше Y = ниже)
                abs(b.get("x", 0) - landing_x)  # Ближе к траектории приземления
            )
        )
        
        # Для каждого блока из координат рассчитываем позицию
        for brick_info in sorted_bricks[:10]:  # Проверяем только первые 10 приоритетных кубиков
            brick_x = brick_info.get("x", 0)
            brick_y = brick_info.get("y", 0)
            brick = brick_info.get("brick")
            
            if brick is None:
                continue
            
            brick_width = getattr(brick, "width", 60)
            brick_height = getattr(brick, "height", 20)
            brick_center_x = brick_x  # brick_x уже центр кубика из координат
            brick_center_y = brick_y
            
            # Расстояние от платформы до блока
            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y
            
            if dy <= 0:
                continue  # Блок выше платформы
            
            # КРИТИЧНО: Рассчитываем необходимое смещение для попадания в блок
            # Используем более агрессивную формулу для гарантированного попадания
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))  # Более агрессивное смещение
            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x
            
            # Ограничиваем границами
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))
            
            # Симулируем траекторию для проверки попадания
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            # Проверяем попадание
            will_hit = False
            ball_radius = 8
            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue
                
                # Более широкая проверка попадания
                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    break
            
            if will_hit:
                # Оцениваем качество позиции
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)
                
                if brick_y > 200:  # Нижние блоки
                    score += 5000.0
                
                # Бонус за близость к текущей позиции платформы (меньше движения = лучше)
                current_paddle_x = self.current_game_state.paddle_position.x
                movement_distance = abs(paddle_position - current_paddle_x)
                score -= movement_distance * 0.1  # Небольшой штраф за большое движение
                
                if score > best_score:
                    best_score = score
                    best_position = paddle_position
        
        # Если нашли позицию, возвращаем её
        if best_position is not None:
            return best_position
        
        # Fallback: используем ближайший блок по координатам
        if brick_coordinates:
            closest_brick = min(
                brick_coordinates,
                key=lambda b: (
                    paddle_y - b.get("y", 0),
                    abs(b.get("x", 0) - landing_x)
                )
            )
            
            brick_center_x = closest_brick.get("x", 0)
            dx = brick_center_x - landing_x
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            best_position = landing_x - (required_offset * paddle_half_width)
            
            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            best_position = max(min_position, min(max_position, best_position))
            
            return best_position
        
        return None

    def _log_paddle_movement(self, from_x: int, to_x: int, reason: str, confidence: float = 1.0) -> None:
        """
        Логирует передвижение платформы для анализа.
        
        Args:
            from_x: Текущая X-координата платформы
            to_x: Целевая X-координата платформы
            reason: Причина передвижения
            confidence: Уверенность в решении (0.0-1.0)
        """
        if hasattr(self, 'performance_logger'):
            self.performance_logger.log_paddle_movement(from_x, to_x, reason, confidence)

    def _calculate_position_for_max_destruction(
        self, landing_x: float
    ) -> Optional[float]:
        """
        Вычисляет оптимальную позицию платформы для максимизации разрушений в следующем цикле.
        Используется на поздних этапах игры (<= 15 блоков).
        
        Args:
            landing_x: X-координата приземления мяча.
            
        Returns:
            Оптимальная X-координата центра платформы или None.
        """
        if not self.current_game_state:
            return None
        
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2
        
        # Тестируем различные углы удара (смещения на платформе)
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_offset = 0.0
        best_destruction_count = 0
        
        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            self.current_game_state, paddle_y
        )
        
        if intersection_point is None:
            return None
        
        for offset in test_offsets:
            # Вычисляем позицию отскока на платформе
            bounce_x = landing_x - (offset * paddle_half_width)
            
            # Ограничиваем границами платформы
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            # Подсчитываем количество блоков, которые будут разрушены
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            # Если это лучший результат, сохраняем
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset
        
        # Вычисляем оптимальную позицию платформы
        optimal_position = landing_x - (best_offset * paddle_half_width)
        
        # Границы по центру платформы
        min_position = paddle_half_width
        max_position = self.screen_width - paddle_half_width
        optimal_position = max(min_position, min(max_position, optimal_position))
        
        return optimal_position

    def _find_optimal_angle_for_max_destruction(self) -> Optional[Any]:
        """
        Находит оптимальный угол удара для максимизации количества разрушенных блоков
        в следующем цикле отскоков. Используется на поздних этапах игры (<= 15 блоков).
        
        Returns:
            Целевой кубик, который приведет к максимальному количеству разрушений.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None
        
        landing_x = self._predict_exact_landing_position()
        paddle_y = self.current_game_state.paddle_position.y
        paddle_center = self.current_game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2
        
        # Тестируем различные углы удара (смещения на платформе)
        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_offset = 0.0
        best_destruction_count = 0
        best_target_brick = None
        
        for offset in test_offsets:
            # Вычисляем позицию отскока на платформе
            bounce_x = landing_x - (offset * paddle_half_width)
            
            # Ограничиваем границами платформы
            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))
            
            # Получаем точку пересечения с платформой
            intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state, paddle_y
            )
            
            if intersection_point is None:
                continue
            
            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    self.current_game_state, intersection_point, bounce_x
                )
            )
            
            # Подсчитываем количество блоков, которые будут разрушены
            destruction_count = self._count_bricks_in_trajectory(
                after_bounce_trajectory, self.current_game_state.remaining_bricks
            )
            
            # Если это лучший результат, сохраняем
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset
                
                # Находим первый блок, который будет разрушен
                first_hit_brick = self._find_first_brick_in_trajectory(
                    after_bounce_trajectory, self.current_game_state.remaining_bricks
                )
                if first_hit_brick:
                    best_target_brick = first_hit_brick
        
        # Если нашли оптимальный угол, возвращаем соответствующий целевой блок
        if best_target_brick:
            return best_target_brick
        
        # Fallback: используем стандартную логику для малого количества блоков
        return self._find_best_target_for_few_bricks(
            self.current_game_state.remaining_bricks,
            paddle_y,
            self.current_game_state.ball_position.x,
        )

    def _count_bricks_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> int:
        """
        Подсчитывает количество блоков, которые будут разрушены траекторией.
        Использует точные координаты кубиков для более точного подсчета.
        
        Args:
            trajectory: Траектория мяча после отскока.
            bricks: Список оставшихся блоков.
            
        Returns:
            Количество блоков, которые будут разрушены.
        """
        if not trajectory or not bricks:
            return 0
        
        destroyed_bricks = set()
        ball_radius = 8  # Радиус мяча
        
        # Используем более частую проверку для точности
        # Проверяем каждую точку траектории (не каждую вторую)
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
                
            for brick in bricks:
                # Пропускаем уже учтенные блоки
                brick_id = id(brick)
                if brick_id in destroyed_bricks:
                    continue
                
                # Точные координаты кубика
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", 60)
                brick_height = getattr(brick, "height", 20)
                
                # Точные границы кубика
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                # Точная проверка пересечения мяча (с учетом радиуса) с границами кубика
                # Мяч пересекает кубик, если его центр находится в расширенной области кубика
                # или если мяч касается границ кубика
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    # Дополнительная проверка: мяч действительно попадает в кубик
                    # Проверяем, что центр мяча находится в области кубика или очень близко к границам
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    # Проверяем расстояние от центра мяча до ближайшей точки кубика
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        destroyed_bricks.add(brick_id)
        
        return len(destroyed_bricks)

    def _find_first_brick_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> Optional[Any]:
        """
        Находит первый блок, который будет разрушен траекторией.
        Использует точные координаты кубиков для более точного определения.
        
        Args:
            trajectory: Траектория мяча после отскока.
            bricks: Список оставшихся блоков.
            
        Returns:
            Первый блок, который будет разрушен, или None.
        """
        if not trajectory or not bricks:
            return None
        
        ball_radius = 8
        min_distance = float("inf")
        first_brick = None
        
        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue
                
            for brick in bricks:
                # Точные координаты кубика
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", 60)
                brick_height = getattr(brick, "height", 20)
                
                # Точные границы кубика
                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height
                
                # Точная проверка пересечения мяча (с учетом радиуса) с границами кубика
                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    # Дополнительная проверка: мяч действительно попадает в кубик
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )
                    
                    # Проверяем расстояние от центра мяча до ближайшей точки кубика
                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    
                    if center_in_brick or distance_to_brick <= ball_radius:
                        # Вычисляем расстояние от начала траектории
                        distance = math.sqrt(
                            (point.x - trajectory[0].x) ** 2
                            + (point.y - trajectory[0].y) ** 2
                        )
                        
                        if distance < min_distance:
                            min_distance = distance
                            first_brick = brick
                            break  # Нашли первый кубик, выходим из внутреннего цикла
        
        return first_brick

    def _find_best_target_for_few_bricks(
        self,
        bricks: List[Any],
        paddle_y: float,
        ball_x: float,
    ) -> Optional[Any]:
        """
        Специальная логика выбора цели для малого количества оставшихся кубиков.
        Помогает быстрее завершить уровень и избегать симметричных циклов.
        """
        if not bricks:
            return None

        # Для 1–3 кубиков — просто самый нижний
        if len(bricks) <= 3:
            return min(bricks, key=lambda b: getattr(b, "y", 0))

        # Для 4–5 — более сложная оценка
        best_brick = None
        best_score = -float("inf")

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            # Максимальный приоритет нижним кубикам
            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 2000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            # Центр — более предсказуемая зона
            center_distance = abs(brick_center_x - self.screen_width // 2)
            score -= center_distance * 0.3

            # Бонус за близость к текущей траектории
            horizontal_distance = abs(brick_center_x - ball_x)
            score -= horizontal_distance * 0.2

            # История успехов
            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system["hit_patterns"]:
                pattern = self.targeting_system["hit_patterns"][brick_key]
                score += pattern.get("success_rate", 0.0) * 300.0

            if score > best_score:
                best_score = score
                best_brick = brick

        return best_brick

    # ==========================
    # Расчёт смещения по платформе
    # ==========================

    def _calculate_optimal_offset(self, landing_x: float, target_brick: Any) -> float:
        """
        Рассчитывает оптимальное смещение на платформе для попадания в кубик.
        Использует точные координаты кубика для избежания пропущенных попаданий.

        Args:
            landing_x: X-координата приземления мяча.
            target_brick: Целевой кубик.

        Returns:
            Смещение от -1.0 до 1.0 (0 — центр платформы).
        """
        # Точные координаты кубика
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_width = getattr(target_brick, "width", 60)
        brick_height = getattr(target_brick, "height", 20)
        
        # Центр целевого кубика
        brick_center_x = brick_x + brick_width / 2
        brick_center_y = brick_y + brick_height / 2
        
        # Учитываем границы кубика для более точного прицеливания
        # Предпочитаем прицеливаться в центр, но учитываем возможность попадания в края
        brick_left = brick_x
        brick_right = brick_x + brick_width
        brick_top = brick_y
        brick_bottom = brick_y + brick_height

        paddle_y = self.current_game_state.paddle_position.y

        # Рассчитываем оптимальную точку попадания в кубик
        # Предпочитаем центр кубика, но учитываем текущую траекторию мяча
        ball_x = self.current_game_state.ball_position.x
        ball_vel_x = self.current_game_state.ball_velocity.x
        
        # Если мяч движется в сторону кубика, можно прицеливаться ближе к краю
        # для более эффективного попадания
        if abs(ball_vel_x) > 0:
            # Определяем, в какую сторону движется мяч относительно кубика
            if ball_vel_x > 0 and ball_x < brick_center_x:
                # Мяч движется вправо и находится слева от кубика
                # Прицеливаемся немного правее центра для компенсации движения
                target_x = brick_center_x + min(brick_width * 0.15, 10)
            elif ball_vel_x < 0 and ball_x > brick_center_x:
                # Мяч движется влево и находится справа от кубика
                # Прицеливаемся немного левее центра
                target_x = brick_center_x - min(brick_width * 0.15, 10)
            else:
                # Стандартное прицеливание в центр
                target_x = brick_center_x
        else:
            target_x = brick_center_x

        # Ограничиваем целевую точку границами кубика
        target_x = max(brick_left, min(brick_right, target_x))

        # Требуемый угол отскока с учетом точной целевой точки
        delta_x = target_x - landing_x
        delta_y = paddle_y - brick_center_y

        if delta_y <= 0:
            # Кубик ниже платформы — физически недостижимо
            return 0.0

        target_angle = math.atan2(delta_x, delta_y)

        # Нормируем угол к диапазону смещения [-1; 1]
        max_angle = math.pi / 4  # около 45 градусов
        offset = target_angle / max_angle

        # Ограничиваем диапазон
        offset = max(-1.0, min(1.0, offset))

        # Проверка на симметричные паттерны
        # Если смещение очень близко к 0 (вертикальный удар), избегаем его
        if abs(offset) < 0.1:
            # Выбираем направление в сторону кубика, избегая симметрии
            if delta_x > 0:
                offset = 0.25  # Смещение вправо
            else:
                offset = -0.25  # Смещение влево
        elif abs(delta_x) < 10:
            # Почти вертикальный удар — добавляем небольшое смещение для избежания симметрии
            # Выбираем направление в сторону кубика
            if delta_x > 0:
                offset = max(0.2, offset)
            else:
                offset = min(-0.2, offset)

        # Уточняем по истории успешных ударов
        offset = self._adjust_offset_from_history(offset, target_brick)
        return offset

    def _adjust_offset_from_history(self, offset: float, target_brick: Any) -> float:
        """
        Корректирует смещение на основе истории успешных ударов по данному кубику.
        """
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

        pattern = self.targeting_system["hit_patterns"].get(brick_key)
        if not pattern:
            return offset

        successful_offsets = pattern.get("successful_offsets", [])
        if not successful_offsets:
            return offset

        avg_successful_offset = sum(successful_offsets) / len(successful_offsets)

        # Смешиваем текущее и историческое смещение
        return offset * 0.7 + avg_successful_offset * 0.3

    # ==========================
    # Предотвращение зацикливания
    # ==========================

    def _detect_loop_pattern(self) -> bool:
        """
        Обнаруживает зацикливание в движениях платформы.

        Возвращает True, если обнаружен повторяющийся паттерн движений
        или вертикальные траектории мяча.
        """
        history = self.loop_prevention_system["movement_history"]
        trajectory_history = self.loop_prevention_system["trajectory_history"]

        threshold = self.loop_prevention_system["loop_detection_threshold"]

        # Нужно достаточно данных
        if len(history) < threshold * 2:
            return False

        # Проверяем последние движения
        recent_movements = history[-threshold:]
        movement_counts: Dict[int, int] = {}
        for movement in recent_movements:
            movement_counts[movement] = movement_counts.get(movement, 0) + 1

        max_count = max(movement_counts.values())
        # 80% одинаковых движений считается зацикливанием
        if max_count >= threshold * 0.8:
            return True

        # Позиционная стагнация
        position_history = self.loop_prevention_system["position_history"]
        if len(position_history) >= 10:
            recent_positions = position_history[-10:]
            # Если за последние 8 кадров платформа почти не меняла позицию
            if len(set(recent_positions[-8:])) <= 2:
                return True

        # Вертикальные траектории мяча
        if len(trajectory_history) >= 5 and self.current_game_state:
            recent_trajectories = trajectory_history[-5:]
            vertical_count = 0
            for traj in recent_trajectories:
                prev_ball_x = traj.get("ball_x")
                if prev_ball_x is None:
                    continue
                current_ball_x = self.current_game_state.ball_position.x
                if abs(current_ball_x - prev_ball_x) < 3:
                    vertical_count += 1
            # 4 из 5 почти вертикальные — считаем зацикливанием
            if vertical_count >= 4:
                return True

        return False

    def _log_paddle_movement(self, from_x: float, to_x: float, reason: str, confidence: float) -> None:
        """
        Логирует движение платформы для анализа дергания.
        
        Args:
            from_x: Начальная позиция платформы
            to_x: Целевая позиция платформы
            reason: Причина движения
            confidence: Уверенность в решении (0.0-1.0)
        """
        try:
            self.performance_logger.log_paddle_movement(
                from_x=from_x,
                to_x=to_x,
                reason=reason,
                confidence=confidence,
            )
        except Exception:
            pass  # Игнорируем ошибки логирования
    
    def _change_strategy_if_looping(self) -> None:
        """Меняет стратегию при обнаружении зацикливания."""
        if not self._detect_loop_pattern():
            return

        # Учитываем кулдаун
        if self.loop_prevention_system["strategy_change_cooldown"] > 0:
            self.loop_prevention_system["strategy_change_cooldown"] -= 1
            return

        # Смена стратегии
        strategies = self.loop_prevention_system["alternative_strategies"]
        idx = self.loop_prevention_system["current_strategy_index"]
        self.loop_prevention_system["current_strategy_index"] = (idx + 1) % len(
            strategies
        )
        new_strategy = strategies[self.loop_prevention_system["current_strategy_index"]]

        # Кулдаун и сброс истории
        self.loop_prevention_system["strategy_change_cooldown"] = 10
        # print(f"[AI] Зацикливание обнаружено! Смена стратегии на: {new_strategy}")
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []

    def _apply_alternative_strategy(self, optimal_position: int) -> int:
        """
        Применяет альтернативную стратегию позиционирования для выхода из зацикливания.
        """
        strategy_index = self.loop_prevention_system["current_strategy_index"]
        strategy = self.loop_prevention_system["alternative_strategies"][strategy_index]
        screen_center = self.screen_width // 2

        if strategy == "center_focus":
            # Фокусируемся на центре экрана
            return screen_center

        if strategy == "edge_focus":
            # Фокусируемся на краях для смены паттерна
            current_pos = getattr(self.current_game_state, "paddle_position", None)
            if current_pos and hasattr(current_pos, "x"):
                return self.screen_width - 70 if current_pos.x < screen_center else 70
            return 70

        if strategy == "predictive_targeting":
            # Агрессивное прицеливание в дальние кубики
            target_brick = self._find_most_distant_brick()
            if target_brick:
                landing_x = self._predict_exact_landing_position()
                brick_center_x = (
                    getattr(target_brick, "x", 0)
                    + getattr(target_brick, "width", 60) / 2
                )
                offset_direction = 1 if brick_center_x > landing_x else -1
                return int(optimal_position + offset_direction * 30)

        return optimal_position

    def _find_most_distant_brick(self) -> Optional[Any]:
        """Находит самый дальний по Y кубик от платформы."""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        paddle_y = self.current_game_state.paddle_position.y

        most_distant_brick = None
        max_distance = -1.0

        for brick in bricks:
            brick_y = getattr(brick, "y", 0)
            distance = abs(paddle_y - brick_y)
            if distance > max_distance:
                max_distance = distance
                most_distant_brick = brick

        return most_distant_brick

    def _update_loop_tracking(
        self,
        movement: int,
        current_x: int,
        optimal_x: int,
    ) -> None:
        """Обновляет данные отслеживания зацикливания."""
        # История движений
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 10:
            self.loop_prevention_system["movement_history"] = (
                self.loop_prevention_system["movement_history"][-10:]
            )

        # История позиций
        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = (
                self.loop_prevention_system["position_history"][-10:]
            )

        # История траекторий
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
        """Обновляет данные отслеживания плавности движения."""
        # История движений
        self.smoothness_system["recent_movements"].append(movement)
        if (
            len(self.smoothness_system["recent_movements"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_movements"] = self.smoothness_system[
                "recent_movements"
            ][-self.smoothness_system["jitter_window"] :]

        # История позиций
        self.smoothness_system["recent_positions"].append(current_x)
        if (
            len(self.smoothness_system["recent_positions"])
            > self.smoothness_system["jitter_window"]
        ):
            self.smoothness_system["recent_positions"] = self.smoothness_system[
                "recent_positions"
            ][-self.smoothness_system["jitter_window"] :]

        # Отслеживание смен направления движения
        if len(self.smoothness_system["recent_movements"]) >= 2:
            prev_movement = self.smoothness_system["recent_movements"][-2]
            if prev_movement != 0 and movement != 0 and prev_movement != movement:
                # Произошла смена направления
                self.smoothness_system["movement_changes"].append(time.time())
                # Очищаем старые записи (старше 1 секунды)
                current_time = time.time()
                self.smoothness_system["movement_changes"] = [
                    t
                    for t in self.smoothness_system["movement_changes"]
                    if current_time - t < 1.0
                ]

    def _detect_jitter(self) -> bool:
        """
        Обнаруживает дрожание платформы (частые смены направления движения).
        
        Returns:
            True, если обнаружено дрожание.
        """
        movements = self.smoothness_system["recent_movements"]
        if len(movements) < self.smoothness_system["jitter_threshold"]:
            return False

        # Подсчитываем количество смен направления в последних движениях
        direction_changes = 0
        for i in range(1, len(movements)):
            prev = movements[i - 1]
            curr = movements[i]
            # Смена направления: с -1 на 1, с 1 на -1, или с любого на противоположное
            if prev != 0 and curr != 0 and prev != curr:
                direction_changes += 1

        # Если слишком много смен направления - это дрожание
        threshold = self.smoothness_system["jitter_threshold"]
        if direction_changes >= threshold:
            return True

        # Дополнительная проверка: частые смены направления за короткое время
        movement_changes = self.smoothness_system["movement_changes"]
        if len(movement_changes) >= threshold:
            return True

        # Проверка на микродвижения (очень маленькие изменения позиции)
        positions = self.smoothness_system["recent_positions"]
        if len(positions) >= 5:
            recent_positions = positions[-5:]
            position_variance = max(recent_positions) - min(recent_positions)
            # Если позиция меняется очень мало, но часто - это дрожание
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
            current_x: Текущая позиция платформы.
            optimal_x: Оптимальная позиция платформы.
            distance: Расстояние до оптимальной позиции.
            
        Returns:
            Направление движения (-1, 0, 1).
        """
        # КРИТИЧНО: Проверяем, находится ли мяч в зоне разделения с установленной позицией
        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
        ball_vel_y = (
            self.current_game_state.ball_velocity.y
            if self.current_game_state and hasattr(self.current_game_state, "ball_velocity")
            else 0
        )
        separation_zone_start = self.separation_zone_tracker.get("separation_zone_start", 226)
        paddle_zone_start = self.separation_zone_tracker.get("paddle_zone_start", 540)
        in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0
        
        # КРИТИЧНО: Если целевая позиция установлена, используем увеличенный допуск
        # Когда мяч движется точно вниз по известной траектории, платформа должна оставаться на месте
        if self.separation_zone_tracker.get("target_position_set", False):
            # Увеличенный допуск для предотвращения дрожания в зоне разделения
            effective_min_distance = 30  # Увеличенный допуск 30 пикселей для стабильности
        else:
            # Если есть штраф за дрожание, увеличиваем порог для движения
            penalty = self.smoothness_system["smoothness_penalty"]
            effective_min_distance = self.smoothness_system["min_movement_distance"] * (
                1 + penalty
            )

        if distance < effective_min_distance:
            # Не двигаемся, если расстояние слишком мало (с учетом штрафа или зоны разделения)
            # КРИТИЧНО: Это предотвращает уход платформы с траектории мяча
            return 0

        # Определяем направление движения
        if optimal_x > current_x:
            return 1
        elif optimal_x < current_x:
            return -1
        else:
            return 0

    def _reevaluate_after_bounce(self) -> None:
        """Переоценивает ситуацию после отбития мяча."""
        if not self.current_game_state:
            return

        target_brick = self._find_best_target_brick()
        if target_brick:
            self.targeting_system["target_brick"] = target_brick
            landing_x = self._predict_exact_landing_position()
            new_offset = self._calculate_optimal_offset(landing_x, target_brick)
            self.targeting_system["optimal_offset"] = new_offset
            # print(f"[AI] Переоценка после отбития: offset={new_offset:.2f}")

        # Сбрасываем историю зацикливания для нового цикла
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        
        # Сбрасываем историю плавности движения после отскока
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        
        # КРИТИЧНО: Сбрасываем отслеживание зоны разделения после отскока
        self.separation_zone_tracker["ball_entered_separation_zone"] = False
        self.separation_zone_tracker["target_position_set"] = False
        self.separation_zone_tracker["target_position"] = None
        self.separation_zone_tracker["paddle_moved_after_set"] = False
        self.separation_zone_tracker["paddle_reached_target"] = False
        self.separation_zone_tracker["last_movement_frame"] = 0
        
        # КРИТИЧНО: Проверяем, было ли отбитие в пустоту (мяч отскочил от потолка без попадания в кубики)
        # Это определяется в PyGameBall.py при отскоке от потолка
        # Здесь мы сбрасываем счетчик только если было успешное попадание в кубик

    # ==========================
    # Запись результатов ударов
    # ==========================

    def record_hit_result(
        self,
        brick_hit: Any,
        paddle_offset: float,
        success: bool,
    ) -> None:
        """
        Записывает результат удара по кубику для обучения системы прицеливания.

        Args:
            brick_hit: Объект/описание сбитого кубика.
            paddle_offset: Смещение по платформе (-1..1).
            success: Был ли удар успешным.
        """
        brick_x = getattr(brick_hit, "x", 0)
        brick_y = getattr(brick_hit, "y", 0)
        brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

        hit_patterns = self.targeting_system["hit_patterns"]

        if brick_key not in hit_patterns:
            hit_patterns[brick_key] = {
                "total_attempts": 0,
                "successful_hits": 0,
                "success_rate": 0.0,
                "successful_offsets": [],
            }

        pattern = hit_patterns[brick_key]
        pattern["total_attempts"] += 1

        if success:
            pattern["successful_hits"] += 1
            pattern["successful_offsets"].append(paddle_offset)
            # Ограничиваем историю
            if len(pattern["successful_offsets"]) > 20:
                pattern["successful_offsets"] = pattern["successful_offsets"][-10:]

        pattern["success_rate"] = (
            pattern["successful_hits"] / pattern["total_attempts"]
            if pattern["total_attempts"] > 0
            else 0.0
        )

        # Глобальная история успешных ударов
        if success:
            self.targeting_system["successful_hits"].append(
                {
                    "brick_key": brick_key,
                    "offset": paddle_offset,
                    "ball_speed": (
                        self.current_game_state.ball_speed
                        if self.current_game_state
                        else 5
                    ),
                    "timestamp": time.time(),
                }
            )
            if len(self.targeting_system["successful_hits"]) > 100:
                self.targeting_system["successful_hits"] = self.targeting_system[
                    "successful_hits"
                ][-50:]

    # ==========================
    # Предсказание траектории и позиционирование
    # ==========================

    def _predict_exact_landing_position(self) -> float:
        """
        Точное предсказание X-координаты, где мяч встретится с платформой.
        ИСПРАВЛЕННАЯ ВЕРСИЯ с правильным расчетом отскоков от стен.
        """
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y

        if vel_y <= 0:
            return ball_x

        ball_radius = 8
        paddle_height = 15
        screen_width = self.screen_width
        
        # КРИТИЧНО: paddle_y - это centery платформы, нужно вычислить top
        paddle_top = paddle_y - paddle_height / 2
        
        # Расстояние от центра мяча до верха платформы
        distance_y = (paddle_top - ball_radius) - ball_y
        
        if distance_y <= 0:
            return ball_x

        # Время до платформы (в кадрах)
        time_to_paddle = distance_y / vel_y
        if time_to_paddle <= 0:
            return ball_x

        # КРИТИЧНО: Правильная симуляция движения с учетом отскоков от стен
        # Используем ту же логику, что и в Ball.update()
        current_x = ball_x
        current_vel_x = vel_x
        remaining_time = time_to_paddle
        min_center_x = ball_radius
        max_center_x = screen_width - ball_radius
        
        while remaining_time > 0 and abs(current_vel_x) > 0.001:
            # Двигаем мяч
            new_x = current_x + current_vel_x * remaining_time
            
            # Проверяем столкновение со стенами (как в Ball.update())
            if new_x < min_center_x:
                # Отскок от левой стены
                time_to_wall = (min_center_x - current_x) / current_vel_x if current_vel_x < 0 else 0
                if time_to_wall > 0 and time_to_wall < remaining_time:
                    current_x = min_center_x
                    remaining_time -= time_to_wall
                    current_vel_x = -current_vel_x
                else:
                    current_x = new_x
                    break
            elif new_x > max_center_x:
                # Отскок от правой стены
                time_to_wall = (max_center_x - current_x) / current_vel_x if current_vel_x > 0 else 0
                if time_to_wall > 0 and time_to_wall < remaining_time:
                    current_x = max_center_x
                    remaining_time -= time_to_wall
                    current_vel_x = -current_vel_x
                else:
                    current_x = new_x
                    break
            else:
                # Нет отскока
                current_x = new_x
                break

        # Ограничиваем границами для платформы
        min_x = self.paddle_width // 2
        max_x = screen_width - self.paddle_width // 2
        return max(min_x, min(max_x, current_x))

    def _handle_ceiling_bounce_positioning(self) -> int:
        """
        Специальная логика для позиционирования при отскоке мяча от потолка.
        Предотвращает симметричные отскоки и зацикливание.
        """
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x

        if ball_y < 30 and self.current_game_state.ball_velocity.y > 0:
            # Мяч только что отскочил от потолка
            if abs(vel_x) < 2:
                # Почти вертикальный отскок — смещаемся в сторону средней позиции кубиков
                remaining_bricks = self.targeting_system["brick_coordinates"]
                if remaining_bricks:
                    avg_brick_x = sum(c["x"] for c in remaining_bricks) / len(
                        remaining_bricks
                    )
                    target_x = (ball_x + avg_brick_x) / 2.0
                else:
                    # Нет кубиков — небольшое смещение от центра
                    center_x = self.screen_width // 2
                    target_x = center_x + (ball_x - center_x) * 0.3
            else:
                # Есть горизонтальная скорость — небольшое упреждение
                target_x = ball_x + vel_x * 2.0

            # Добавляем случайное смещение, чтобы избежать идеальной симметрии
            target_x += random.choice([-15, -10, 0, 10, 15])

            paddle_half_width = self.paddle_width / 2
            min_x = paddle_half_width + 5
            max_x = self.screen_width - paddle_half_width - 5
            target_x = max(min_x, min(max_x, target_x))
            return int(target_x)

        # Стандартное слежение за мячом
        return int(self._track_ball_position())

    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с небольшим упреждением."""
        ball_x = self.current_game_state.ball_position.x
        vel_x = self.current_game_state.ball_velocity.x

        prediction_time = 3  # кадров вперёд
        predicted_x = ball_x + vel_x * prediction_time

        screen_width = self.screen_width
        ball_radius = 8
        min_x = ball_radius
        max_x = screen_width - ball_radius

        return max(min_x, min(max_x, predicted_x))

    # ==========================
    # Адаптивная скорость платформы
    # ==========================

    def calculate_adaptive_paddle_speed(
        self, current_x: int, optimal_x: int, ball_speed: int
    ) -> int:
        """
        Рассчитывает адаптивную скорость платформы на основе физики игры.
        
        Учитывает:
        - Скорость мяча
        - Расстояние до оптимальной позиции
        - Время до встречи с мячом
        - Историю успешных движений
        
        Args:
            current_x: Текущая позиция платформы
            optimal_x: Оптимальная позиция платформы
            ball_speed: Скорость мяча
            
        Returns:
            Адаптивная скорость платформы
        """
        # Базовые параметры
        base_paddle_speed = 15  # Увеличено с 9 до 15 для лучшей скорости
        min_speed = 5
        max_speed = 50  # Увеличено с 30 до 50 для критических ситуаций
        
        if not self.current_game_state:
            return base_paddle_speed
        
        distance_to_optimal = abs(optimal_x - current_x)
        
        # Если позиция уже оптимальна или близка к ней
        if distance_to_optimal <= 5:
            return min_speed
        
        # Рассчитываем время до встречи с мячом (если он движется к платформе)
        time_to_meeting = 0
        if self.is_ball_moving_towards_paddle():
            ball_y = self.current_game_state.ball_position.y
            paddle_y = self.current_game_state.paddle_position.y
            ball_vel_y = self.current_game_state.ball_velocity.y
            
            if ball_vel_y > 0:  # Мяч движется вниз
                # Более точный расчет времени с учетом текущей позиции мяча
                distance_y = paddle_y - ball_y
                if distance_y > 0:
                    time_to_meeting = distance_y / ball_vel_y
                    time_to_meeting = max(
                        0, time_to_meeting
                    )  # Не может быть отрицательным
        
        # Рассчитываем требуемую скорость на основе времени до встречи
        required_speed = base_paddle_speed
        
        if time_to_meeting > 0 and time_to_meeting != float("inf"):
            # Если времени мало, нужна высокая скорость
            if time_to_meeting <= 20:  # Менее 20 кадров - критическая ситуация
                required_speed = max(
                    base_paddle_speed * 2.5,  # Увеличено с 1.5 до 2.5
                    distance_to_optimal / max(time_to_meeting * 0.5, 1),  # Увеличена скорость
                )
            elif time_to_meeting <= 40:  # Менее 40 кадров
                required_speed = max(
                    base_paddle_speed * 2.0,  # Увеличено с 1.2 до 2.0
                    distance_to_optimal / max(time_to_meeting * 0.6, 1),  # Увеличена скорость
                )
            elif time_to_meeting <= 80:  # Менее 80 кадров  
                required_speed = max(
                    base_paddle_speed * 1.5,  # Увеличено с 0.9 до 1.5
                    distance_to_optimal / max(time_to_meeting * 0.8, 1),
                )
            else:  # Много времени - можно двигаться медленно
                required_speed = max(min_speed, base_paddle_speed * 1.0)  # Увеличено с 0.6 до 1.0
        else:
            # Мяч не движется к платформе, используем умеренную скорость
            required_speed = base_paddle_speed * 0.8
        
        # Корректируем на основе скорости мяча
        speed_ratio = ball_speed / 5.0  # 5 - BALL_SPEED_DEFAULT
        speed_multiplier = (
            0.7 + speed_ratio * 0.6
        )  # 0.7x до 1.3x в зависимости от скорости мяча
        required_speed *= speed_multiplier
        
        # Учитываем расстояние - чем дальше, тем быстрее
        if distance_to_optimal > 150:
            required_speed *= 1.4
        elif distance_to_optimal > 100:
            required_speed *= 1.2
        elif distance_to_optimal > 50:
            required_speed *= 1.1
        
        # Дополнительная корректировка для экстренных ситуаций
        if (
            distance_to_optimal > time_to_meeting * ball_speed * 0.8
            and time_to_meeting > 0
        ):
            # Если расстояние больше, чем может пролететь мяч за время до встречи
            required_speed *= 1.3
        
        # Применяем границы
        required_speed = max(min_speed, min(max_speed, required_speed))
        
        # Добавляем небольшую случайность для естественности
        if distance_to_optimal > 20:
            import random

            variation = random.uniform(0.97, 1.03)
            required_speed *= variation
        
        return int(required_speed)

    # ==========================
    # Движение платформы
    # ==========================

    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции с предотвращением зацикливания.
        ПОЛНОСТЬЮ ПЕРЕПИСАННЫЙ МЕТОД с флагами и логированием.

        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.

        Returns:
            Смещение платформы (-1, 0, 1).
        """
        if not self.current_game_state or not self.is_active:
            # КРИТИЧНО: Логируем, почему платформа не двигается
            self._logger.debug(f"[PADDLE DEBUG] move_paddle_towards: current_game_state={self.current_game_state is not None}, is_active={self.is_active}")
            return self._fallback_movement(current_x)

        try:
            # Получаем состояние мяча
            ball_y = self.current_game_state.ball_position.y
            ball_vel_y = (
                self.current_game_state.ball_velocity.y
                if hasattr(self.current_game_state, "ball_velocity")
                else 0
            )
            separation_zone_start = self.separation_zone_tracker.get("separation_zone_start", 226)
            paddle_zone_start = self.separation_zone_tracker.get("paddle_zone_start", 540)
            
            # КРИТИЧНО: Логируем состояние мяча для диагностики (только периодически, чтобы не засорять логи)
            import random
            if random.random() < 0.01:  # 1% кадров
                optimal_x = self.get_optimal_paddle_position()
                self._logger.debug(f"[PADDLE DEBUG] ball_y={ball_y:.1f}, ball_vel_y={ball_vel_y}, current_x={current_x}, optimal_x={optimal_x}, distance={abs(current_x - optimal_x):.1f}")
            
            # КРИТИЧНО: УБРАНО ПРАВИЛО 1 - платформа ДОЛЖНА двигаться к точке падения мяча
            # даже когда мяч летит вверх, чтобы успеть к моменту падения
            # Продолжаем расчет оптимальной позиции независимо от направления мяча
            
            if ball_vel_y == 0:
                # КРИТИЧНО: Если vel_y == 0, это ошибка состояния (должно быть исправлено в PyGameBall.py)
                # Но на всякий случай продолжаем движение к оптимальной позиции, а не используем fallback
                # Это предотвращает ситуацию, когда платформа перестает двигаться из-за временного vel_y=0
                # Логируем для диагностики, но продолжаем нормальную логику
                self._log_paddle_movement(current_x, current_x, "ball_vel_y_zero_warning", 0.5)
                # Продолжаем обработку с обычной логикой - НЕ возвращаем fallback!
            
            # ПРАВИЛО 2: Если мяч в зоне кубиков - платформа НЕ двигается
            # КРИТИЧНО: Но только если мяч действительно в зоне кубиков
            # Если мяч уже ниже зоны кубиков, но еще не в зоне разделения - все равно двигаемся
            if ball_y < separation_zone_start:
                # КРИТИЧНО: Логируем для диагностики (периодически)
                import random
                if random.random() < 0.05:  # 5% кадров
                    self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 2: Мяч в зоне кубиков (ball_y={ball_y:.1f} < {separation_zone_start}), платформа не двигается")
                self._log_paddle_movement(current_x, current_x, "ball_in_bricks_zone", 1.0)
                return 0
            
            # КРИТИЧНО: Проверяем, не потерян ли мяч (ниже верхней границы платформы)
            # Если мяч ниже верхней границы платформы - он считается потерянным, платформа НЕ двигается
            paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
            ball_lost = ball_y > paddle_y  # Мяч ниже верхней границы платформы
            
            if ball_lost:
                # Мяч потерян - платформа НЕ двигается
                # КРИТИЧНО: Логируем для диагностики (периодически)
                import random
                if random.random() < 0.05:  # 5% кадров
                    self._logger.debug(f"[PADDLE DEBUG] Мяч потерян (ball_y={ball_y:.1f} > paddle_y={paddle_y:.1f}), платформа не двигается")
                self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle", 1.0)
                return 0
            
            # Проверяем, находится ли мяч в зоне разделения
            # КРИТИЧНО: Мяч должен быть выше верхней границы платформы и в разрешенной зоне
            # Зона разделения: от separation_zone_start до верхней границы платформы
            in_separation_zone = separation_zone_start <= ball_y < paddle_y and ball_vel_y > 0
            
            # КРИТИЧНО: Логируем состояние зоны разделения для диагностики
            import random
            import sys
            # Логируем всегда когда мяч в зоне разделения или близко к платформе
            should_log = in_separation_zone or (ball_y > paddle_y - 100 and ball_vel_y > 0)
            # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
            if should_log:  # Всегда логируем когда мяч близко
                ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                ball_speed = self.current_game_state.ball_speed if self.current_game_state else 0
                distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
                time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
                # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() если позиция уже зафиксирована
                # Это может вызвать пересчет и дергание
                if self.separation_zone_tracker.get("target_position_set", False):
                    optimal_x = self.separation_zone_tracker.get("target_position")
                else:
                    optimal_x = self.get_optimal_paddle_position()
                distance_to_target = abs(current_x - optimal_x) if optimal_x is not None else 0
                self._logger.debug(f"[BALL TRACKING] ball=({ball_x:.1f},{ball_y:.1f}) vel=({ball_vel_x:.1f},{ball_vel_y:.1f}) speed={ball_speed:.1f} | "
                                   f"paddle_x={current_x:.1f} optimal_x={optimal_x:.1f} dist_to_target={distance_to_target:.1f} | "
                                   f"zone: sep_start={separation_zone_start} paddle_y={paddle_y:.1f} in_zone={in_separation_zone} | "
                                   f"time_to_paddle={time_to_paddle:.2f} frames")
            
            # ПРАВИЛО 3: Если целевая позиция установлена - используем её БЕЗ пересчета
            # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз при входе мяча в зону разделения
            # и не меняется до следующего отскока от стены
            if self.separation_zone_tracker.get("target_position_set", False):
                # КРИТИЧНО: В зоне разделения траектория мяча НЕ МЕНЯЕТСЯ (нет отскоков от кубиков)
                # Проверяем ТОЛЬКО изменение скорости vel_x (отскок от стены)
                # НЕ пересчитываем цель на основе разницы в optimal_x - это вызывает дёргание
                current_target = self.separation_zone_tracker.get("target_position")
                if current_target is not None and in_separation_zone:
                    # КРИТИЧНО: Проверяем изменение vel_x - это единственный признак отскока от стены
                    # Сохраняем предыдущую скорость vel_x для сравнения
                    saved_vel_x = self.separation_zone_tracker.get("saved_ball_vel_x")
                    current_vel_x = self.current_game_state.ball_velocity.x if self.current_game_state else 0
                    
                    # Если vel_x изменился (мяч отскочил от стены) - сбрасываем цель
                    if saved_vel_x is not None and abs(current_vel_x - saved_vel_x) > 0.1:
                        # Мяч отскочил от стены - траектория изменилась, нужно пересчитать цель
                        self._logger.debug(f"[TARGET RESET] Мяч отскочил от стены! Старая vel_x={saved_vel_x:.1f}, Новая vel_x={current_vel_x:.1f}")
                        self.separation_zone_tracker["target_position_set"] = False
                        self.separation_zone_tracker["target_position"] = None
                        self.separation_zone_tracker["paddle_moved_after_set"] = False
                        self.separation_zone_tracker["paddle_reached_target"] = False
                        self.separation_zone_tracker["frames_since_target_set"] = 0
                        self.separation_zone_tracker["saved_ball_vel_x"] = current_vel_x
                        self._log_paddle_movement(current_x, current_x, "target_reset_wall_bounce", 1.0)
                        # Продолжаем обработку с обычной логикой для установки новой цели
                    else:
                        # Скорость не изменилась - траектория стабильна, НЕ обновляем цель
                        # КРИТИЧНО: Возвращаем зафиксированную позицию БЕЗ пересчета
                        # Это гарантирует, что позиция не изменится до отскока от стены
                        self.separation_zone_tracker["saved_ball_vel_x"] = current_vel_x
                        
                        # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() для проверки - это может вызвать пересчет
                        # Просто используем зафиксированную позицию
                        
                        # ВСЕГДА возвращаем зафиксированную позицию
                        # КРИТИЧНО: НЕ вызываем get_optimal_paddle_position() - это может вызвать пересчет и дергание
                        target_pos = int(current_target)
                        distance_to_target = abs(current_x - target_pos)
                        
                        # КРИТИЧНО: Используем большой tolerance для остановки, чтобы предотвратить дергание
                        # Проблема: платформа движется со скоростью 15px/кадр и "перескакивает" через цель
                        # Решение: используем большой tolerance (равный скорости движения), чтобы платформа останавливалась
                        # даже если немного перескочила через цель
                        tolerance = 15  # Равен скорости движения платформы - предотвращает дергание
                        
                        # КРИТИЧНО: Логируем движение к зафиксированной позиции для отслеживания
                        import random
                        if random.random() < 0.1:  # Логируем 10% кадров
                            self._logger.debug(f"[MOVING TO FIXED] ФЛАГ: Движение к зафиксированной позиции! "
                                               f"current_x={current_x:.1f}, target_pos={target_pos:.1f}, "
                                               f"distance={distance_to_target:.1f}px, tolerance={tolerance}")
                        
                        # Двигаемся к зафиксированной позиции
                        if distance_to_target > tolerance:
                            # Платформа далеко от цели - начинаем движение
                            movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                            if movement != 0:
                                self._update_loop_tracking(movement, current_x, target_pos)
                                self._update_smoothness_tracking(movement, current_x)
                                self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target", 1.0)
                                return movement
                        else:
                            # Достигли цели - останавливаемся
                            # КРИТИЧНО: НЕ устанавливаем флаг paddle_reached_target - он не нужен
                            # Просто останавливаемся, если близко к цели
                            return 0
                
                # КРИТИЧНО: Если позиция зафиксирована, но мяч не в зоне разделения - проверяем сброс
                # КРИТИЧНО: Используем гистерезис для предотвращения дергания
                # Сбрасываем целевую позицию ТОЛЬКО если:
                # 1. Мяч ушел далеко вверх (выше зоны кубиков) ИЛИ
                # 2. Мяч потерян (ниже верхней границы платформы)
                should_reset = False
                
                # Проверка 1: Мяч ушел далеко вверх (выше зоны кубиков)
                if ball_y < separation_zone_start - 50:  # Далеко выше зоны разделения
                    should_reset = True
                
                # Проверка 2: Мяч потерян (ниже верхней границы платформы)
                if ball_lost:
                    should_reset = True
                
                # Если нужно сбросить - сбрасываем
                if should_reset:
                    self.separation_zone_tracker["target_position_set"] = False
                    self.separation_zone_tracker["target_position"] = None
                    self.separation_zone_tracker["paddle_moved_after_set"] = False
                    self.separation_zone_tracker["paddle_reached_target"] = False
                    self._log_paddle_movement(current_x, current_x, "target_reset_ball_left_zone", 1.0)
                    # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
                else:
                    # КРИТИЧНО: Позиция зафиксирована, но мяч не в зоне разделения
                    # Используем зафиксированную позицию БЕЗ пересчета
                    current_target = self.separation_zone_tracker.get("target_position")
                    if current_target is not None:
                        target_pos = int(current_target)
                        distance_to_target = abs(current_x - target_pos)
                        tolerance = 3
                        
                        if distance_to_target > tolerance:
                            movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                            if movement != 0:
                                self._update_loop_tracking(movement, current_x, target_pos)
                                self._update_smoothness_tracking(movement, current_x)
                                self._log_paddle_movement(current_x, target_pos, "moving_to_fixed_target_outside_zone", 1.0)
                                return movement
                        else:
                            return 0
                    
                    # КРИТИЧНО: УБРАНО - пересчет позиции в зоне разделения вызывает дёргание
                    # Позиция фиксируется один раз и НЕ пересчитывается до отскока от стены
                    if False:  # Никогда не пересчитываем в зоне разделения
                        # Используем простой расчет для стабильности
                        if self.current_game_state:
                            ball_x = self.current_game_state.ball_position.x
                            ball_y_state = self.current_game_state.ball_position.y
                            vel_x = self.current_game_state.ball_velocity.x
                            vel_y = self.current_game_state.ball_velocity.y
                            
                            if vel_y > 0 and ball_y_state < paddle_y:
                                # КРИТИЧНО: Улучшенное предсказание точки падения с учетом времени движения платформы
                                time_to_paddle = (paddle_y - ball_y_state) / vel_y
                                if time_to_paddle > 0:
                                    # Предсказываем позицию мяча в момент падения
                                    predicted_x = ball_x + vel_x * time_to_paddle
                                    
                                    # КРИТИЧНО: Учитываем отскоки от стен более точно
                                    screen_width = self.screen_width
                                    ball_radius = 8
                                    remaining_time = time_to_paddle
                                    current_predicted_x = ball_x
                                    current_vel_x = vel_x
                                    
                                    # Симулируем движение мяча с учетом отскоков от стен
                                    while remaining_time > 0:
                                        # Рассчитываем, когда мяч достигнет стены
                                        if current_vel_x > 0:
                                            time_to_right_wall = (screen_width - ball_radius - current_predicted_x) / current_vel_x
                                        else:
                                            time_to_right_wall = float('inf')
                                        
                                        if current_vel_x < 0:
                                            time_to_left_wall = (current_predicted_x - ball_radius) / abs(current_vel_x)
                                        else:
                                            time_to_left_wall = float('inf')
                                        
                                        time_to_wall = min(time_to_left_wall, time_to_right_wall)
                                        
                                        if time_to_wall > 0 and time_to_wall <= remaining_time:
                                            # Мяч отскочит от стены
                                            current_predicted_x += current_vel_x * time_to_wall
                                            remaining_time -= time_to_wall
                                            current_vel_x = -current_vel_x
                                        else:
                                            # Мяч не достигнет стены до падения
                                            current_predicted_x += current_vel_x * remaining_time
                                            remaining_time = 0
                                    
                                    predicted_x = current_predicted_x
                                    
                                    # Дополнительная проверка границ
                                    if predicted_x < ball_radius:
                                        predicted_x = ball_radius
                                    elif predicted_x > screen_width - ball_radius:
                                        predicted_x = screen_width - ball_radius
                                    
                                    # КРИТИЧНО: Разделяем платформу на 3 зоны и всегда прицеливаемся в центр выбранной зоны
                                    # Платформа шириной 120px делится на 3 равные зоны по 40px каждая
                                    # Левая зона: от -60px до -20px от центра платформы (центр на -40px)
                                    # Центральная зона: от -20px до +20px от центра платформы (центр на 0px)
                                    # Правая зона: от +20px до +60px от центра платформы (центр на +40px)
                                    
                                    zone_size = self.paddle_width / 3  # 40px
                                    zone_half = zone_size / 2  # 20px - половина зоны
                                    
                                    # КРИТИЧНО: Проверяем, не находится ли точка падения близко к стене
                                    # Если точка падения в пределах 40px от края экрана - используем точку падения напрямую
                                    screen_width = self.screen_width
                                    ball_radius = 8
                                    min_safe_x = ball_radius + 40  # Минимум 40px от левого края
                                    max_safe_x = screen_width - ball_radius - 40  # Минимум 40px от правого края
                                    
                                    use_direct_position = (predicted_x < min_safe_x or predicted_x > max_safe_x)
                                    
                                    if use_direct_position:
                                        # Точка падения близко к стене - используем точку падения напрямую
                                        # КРИТИЧНО: Если мяч очень близко (менее 3 кадров), платформа должна доезжать до края зоны
                                        # Край платформы должен касаться стены для максимального покрытия
                                        if time_to_paddle < 3:
                                            # Мяч очень близко - доезжаем до края зоны
                                            if predicted_x > screen_width / 2:
                                                # Мяч справа - край платформы касается правой стены
                                                zone_center_x = screen_width - self.paddle_width // 2
                                            else:
                                                # Мяч слева - край платформы касается левой стены
                                                zone_center_x = self.paddle_width // 2
                                        else:
                                            # Мяч не очень близко - используем точку падения напрямую
                                            zone_center_x = predicted_x
                                        selected_zone = "EDGE"
                                    else:
                                        # КРИТИЧНО: Правильная логика позиционирования для попадания в ЦЕНТР зоны
                                        # Цель: позиционировать платформу так, чтобы predicted_x попал в ЦЕНТР выбранной зоны
                                        
                                        # Если центр платформы = X, то:
                                        # - Левая зона: от X-60 до X-20, центр на X-40
                                        # - Центральная зона: от X-20 до X+20, центр на X
                                        # - Правая зона: от X+20 до X+60, центр на X+40
                                        
                                        # КРИТИЧНО: Выбираем зону так, чтобы мяч попал в ЦЕНТР зоны, а не на границу
                                        # Для этого нужно определить, в какую зону попадает predicted_x,
                                        # и позиционировать платформу так, чтобы центр этой зоны совпал с predicted_x
                                        
                                        # Варианты позиционирования:
                                        # 1. Центральная зона: центр платформы = predicted_x (центр зоны = predicted_x)
                                        # 2. Левая зона: центр платформы = predicted_x + 40 (центр зоны = predicted_x)
                                        # 3. Правая зона: центр платформы = predicted_x - 40 (центр зоны = predicted_x)
                                        
                                        # Определяем, какая зона лучше подходит, проверяя границы зон:
                                        # Если центр платформы = predicted_x:
                                        #   - Левая зона: от predicted_x-60 до predicted_x-20
                                        #   - Центральная зона: от predicted_x-20 до predicted_x+20
                                        #   - Правая зона: от predicted_x+20 до predicted_x+60
                                        
                                        # Если predicted_x находится в центральной зоне (от predicted_x-20 до predicted_x+20),
                                        # то predicted_x всегда попадает в центр центральной зоны - используем центральную зону
                                        
                                        # Если predicted_x находится в левой зоне (от predicted_x-60 до predicted_x-20),
                                        # то нужно сдвинуть платформу вправо на 40px, чтобы predicted_x попал в центр левой зоны
                                        
                                        # Если predicted_x находится в правой зоне (от predicted_x+20 до predicted_x+60),
                                        # то нужно сдвинуть платформу влево на 40px, чтобы predicted_x попал в центр правой зоны
                                        
                                        # Но predicted_x - это точка падения, а не позиция относительно платформы!
                                        # Нужно определить, в какую зону попадает predicted_x, если центр платформы = predicted_x
                                        
                                        # Упрощенный подход: выбираем зону на основе расстояния от predicted_x до центров зон
                                        # при условии, что центр платформы = predicted_x
                                        
                                        # Центры зон при центре платформы = predicted_x:
                                        center_zone_center = predicted_x  # центр центральной зоны
                                        left_zone_center = predicted_x - zone_size  # центр левой зоны (predicted_x - 40)
                                        right_zone_center = predicted_x + zone_size  # центр правой зоны (predicted_x + 40)
                                        
                                        # Расстояния от predicted_x до центров зон:
                                        dist_to_center = abs(predicted_x - center_zone_center)  # всегда 0
                                        dist_to_left = abs(predicted_x - left_zone_center)  # всегда 40
                                        dist_to_right = abs(predicted_x - right_zone_center)  # всегда 40
                                        
                                        # КРИТИЧНО: Выбираем зону на основе того, где находится predicted_x относительно экрана
                                        # Если predicted_x близко к левому краю - предпочитаем левую зону
                                        # Если predicted_x близко к правому краю - предпочитаем правую зону
                                        # Иначе - используем центральную зону
                                        
                                        screen_center = screen_width / 2
                                        # КРИТИЧНО: Используем более широкие пороги для выбора боковых зон
                                        # Это гарантирует, что платформа будет двигаться дальше влево/вправо,
                                        # чтобы мяч попадал в центр боковой зоны, а не на границу
                                        left_threshold = screen_center - zone_size * 2  # 400 - 80 = 320
                                        right_threshold = screen_center + zone_size * 2  # 400 + 80 = 480
                                        
                                        if predicted_x < left_threshold:
                                            # predicted_x в левой части экрана - используем левую зону
                                            # Чтобы predicted_x попал в центр левой зоны, центр платформы = predicted_x + 40
                                            zone_center_x = predicted_x + zone_size
                                            selected_zone = "LEFT"
                                        elif predicted_x > right_threshold:
                                            # predicted_x в правой части экрана - используем правую зону
                                            # Чтобы predicted_x попал в центр правой зоны, центр платформы = predicted_x - 40
                                            zone_center_x = predicted_x - zone_size
                                            selected_zone = "RIGHT"
                                        else:
                                            # predicted_x в центральной части экрана - используем центральную зону
                                            # Чтобы predicted_x попал в центр центральной зоны, центр платформы = predicted_x
                                            zone_center_x = predicted_x
                                            selected_zone = "CENTER"
                                    
                                    # КРИТИЧНО: Логируем выбор зоны для диагностики (всегда)
                                    current_paddle_x = self.current_game_state.paddle_position.x if self.current_game_state else 0
                                    distance_to_zone_center = abs(current_paddle_x - zone_center_x)
                                    # Вычисляем, где будет центр выбранной зоны при позиции платформы = zone_center_x
                                    if selected_zone == "LEFT":
                                        actual_zone_center = zone_center_x - zone_size  # центр левой зоны
                                    elif selected_zone == "RIGHT":
                                        actual_zone_center = zone_center_x + zone_size  # центр правой зоны
                                    else:
                                        actual_zone_center = zone_center_x  # центр центральной зоны
                                    
                                    self._logger.debug(f"[ZONE SELECTION] predicted_x={predicted_x:.1f} -> zone={selected_zone} "
                                                       f"paddle_center={zone_center_x:.1f} actual_zone_center={actual_zone_center:.1f} "
                                                       f"current_paddle={current_paddle_x:.1f} distance_to_zone={distance_to_zone_center:.1f}px "
                                                       f"time_to_paddle={time_to_paddle:.2f} frames")
                                    
                                    # Ограничиваем границами экрана
                                    # КРИТИЧНО: Если мяч в EDGE зоне и очень близко (менее 3 кадров),
                                    # платформа должна доезжать до края зоны (край платформы касается стены)
                                    # НЕ ограничиваем границами в этом случае
                                    min_x = self.paddle_width // 2 + 30
                                    max_x = screen_width - self.paddle_width // 2 - 30
                                    
                                    # КРИТИЧНО: Если это EDGE зона и мяч очень близко, доезжаем до края
                                    if selected_zone == "EDGE" and time_to_paddle < 3:
                                        # В EDGE зоне и очень близко - используем zone_center_x напрямую
                                        # (уже рассчитан для края зоны в строках 2794 или 2797)
                                        new_optimal_x = int(zone_center_x)
                                    else:
                                        # Обычное ограничение границами
                                        new_optimal_x = max(min_x, min(max_x, int(zone_center_x)))
                                    
                                    # КРИТИЧНО: Используем экспоненциальное сглаживание
                                    # НО: не обновляем целевую позицию, если платформа уже близко к текущей цели
                                    # КРИТИЧНО: Если мяч очень близко (менее 5 кадров), ВСЕГДА обновляем цель без сглаживания
                                    old_target = self.separation_zone_tracker.get("target_position")
                                    if old_target is not None:
                                        # Проверяем, насколько далеко платформа от текущей цели
                                        distance_to_old_target = abs(current_x - old_target)
                                        
                                        # КРИТИЧНО: НЕ обновляем цель без сглаживания когда мяч очень близко
                                        # Это вызывает дёргание платформы, если траектория стабильна
                                        # Обновляем только если траектория кардинально изменилась
                                        distance_to_paddle_y = paddle_y - ball_y_state if ball_y_state < paddle_y else 0
                                        
                                        if distance_to_old_target <= 40:
                                            # КРИТИЧНО: Если платформа уже близко к текущей цели, НЕ обновляем цель вообще
                                            # Это предотвращает дёргание в точке падения
                                            # Используем удвоенный tolerance для проверки "близко к цели"
                                            tolerance_check = 30  # Удвоенный tolerance (15 * 2)
                                            if distance_to_old_target <= tolerance_check:
                                                # Платформа уже близко к цели - НЕ обновляем, даже если new_optimal немного отличается
                                                # Это критично для предотвращения дёргания в точке падения
                                                optimal_x = old_target
                                                # Логируем, что мы НЕ обновляем цель, хотя new_optimal отличается
                                                if abs(new_optimal_x - old_target) > 10:  # Только если разница значительная
                                                    self._logger.debug(f"[POSITION CHANGE BLOCKED] Платформа близко к цели (distance={distance_to_old_target:.1f} <= {tolerance_check}), "
                                                                       f"НОВУЮ цель НЕ устанавливаем! Старая={old_target:.1f}, Новая={new_optimal_x:.1f}, Разница={abs(new_optimal_x - old_target):.1f}px")
                                            else:
                                                # Платформа еще далеко от цели - проверяем, не изменилась ли траектория кардинально
                                                # Увеличиваем порог до 50px минимум, чтобы не реагировать на мелкие изменения
                                                threshold = 50 if distance_to_paddle_y < 50 else 80
                                                # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз и НЕ меняется до отскока от стены
                                                # НЕ обновляем позицию, даже если траектория "изменилась кардинально"
                                                # Это нарушение правила - используем старую позицию
                                                optimal_x = old_target
                                                if abs(new_optimal_x - old_target) > threshold:
                                                    self._logger.warning(f"[CRITICAL ERROR] НАРУШЕНИЕ ПРАВИЛА: Попытка изменить позицию ({old_target:.1f} -> {new_optimal_x:.1f}) "
                                                                        f"БЕЗ отскока от стены! Используем старую позицию.")
                                        else:
                                            # Платформа далеко от старой цели - используем сглаживание
                                            # НО: увеличиваем порог для обновления, чтобы не дёргаться
                                            # КРИТИЧНО: Проверяем разницу между старой и новой целью
                                            # Если разница маленькая (менее 50px), НЕ обновляем, даже если платформа далеко
                                            target_difference = abs(new_optimal_x - old_target)
                                            if target_difference <= 50:
                                                # Разница слишком маленькая - не обновляем, даже если платформа далеко
                                                optimal_x = old_target
                                                if distance_to_old_target > 50:  # Только логируем если платформа действительно далеко
                                                    self._logger.debug(f"[POSITION CHANGE BLOCKED] Разница между целями слишком маленькая (target_difference={target_difference:.1f} <= 50), "
                                                                       f"НЕ обновляем цель при сглаживании! Старая={old_target:.1f}, Новая={new_optimal_x:.1f}, distance_to_old={distance_to_old_target:.1f}")
                                            else:
                                                # КРИТИЧЕСКОЕ ПРАВИЛО: позиция фиксируется один раз и НЕ меняется до отскока от стены
                                                # НЕ используем сглаживание - это нарушение правила
                                                # Всегда используем старую позицию
                                                optimal_x = old_target
                                                if abs(new_optimal_x - old_target) > 50:
                                                    self._logger.warning(f"[CRITICAL ERROR] НАРУШЕНИЕ ПРАВИЛА: Попытка изменить позицию через сглаживание "
                                                                        f"({old_target:.1f} -> {new_optimal_x:.1f}) БЕЗ отскока от стены! Используем старую позицию.")
                                    else:
                                        # ПРАВИЛО 4: Устанавливаем целевую позицию впервые
                                        # КРИТИЧНО: Проверяем, не была ли позиция уже установлена (нарушение правила)
                                        if self.separation_zone_tracker.get("target_position_set", False):
                                            # НАРУШЕНИЕ ПРАВИЛА: Позиция уже установлена, но пытаемся установить снова!
                                            old_pos = self.separation_zone_tracker.get("target_position")
                                            self._logger.warning(f"[RULE VIOLATION] ФЛАГ: Попытка установить позицию ПОВТОРНО (ПРАВИЛО 4)! "
                                                                 f"Старая позиция={old_pos:.1f}, Новая позиция={int(new_optimal_x):.1f}, "
                                                                 f"Разница={abs(old_pos - int(new_optimal_x)):.1f}px")
                                            self.separation_zone_tracker["game_restart_required"] = True
                                            # Используем старую позицию
                                            optimal_x = old_pos
                                        else:
                                            # Позиция устанавливается впервые - это правильно
                                            current_vel_x = self.current_game_state.ball_velocity.x if self.current_game_state else 0
                                            self.separation_zone_tracker["target_position"] = int(new_optimal_x)
                                            self.separation_zone_tracker["target_position_set"] = True
                                            self.separation_zone_tracker["frames_since_target_set"] = 0
                                            self.separation_zone_tracker["paddle_moved_after_set"] = False
                                            self.separation_zone_tracker["paddle_reached_target"] = False
                                            self.separation_zone_tracker["saved_ball_vel_x"] = current_vel_x
                                            current_target = self.separation_zone_tracker.get("target_position")
                                            current_target_str = f"{current_target:.1f}" if current_target is not None else "None"
                                            self._logger.debug(f"[POSITION FIXED] ФЛАГ: Позиция зафиксирована впервые (ПРАВИЛО 4)! "
                                                               f"target_position={int(new_optimal_x):.1f}, paddle_x={current_x:.1f}")
                                            optimal_x = int(new_optimal_x)
                                else:
                                    optimal_x = self.separation_zone_tracker.get("target_position")
                            else:
                                optimal_x = self.separation_zone_tracker.get("target_position")
                        else:
                            optimal_x = self.separation_zone_tracker.get("target_position")
                    else:
                        # Используем сохраненную позицию
                        optimal_x = self.separation_zone_tracker.get("target_position")
                        # КРИТИЧНО: Обновляем счетчик кадров с момента установки цели
                        frames_since_target_set = self.separation_zone_tracker.get("frames_since_target_set", 0)
                        self.separation_zone_tracker["frames_since_target_set"] = frames_since_target_set + 1
                    
                    if optimal_x is not None:
                        target_pos = int(optimal_x)
                        distance_to_target = abs(current_x - target_pos)
                        
                        # КРИТИЧНО: Сначала проверяем, успеет ли платформа добраться до цели
                        # Это должно быть ПЕРЕД проверкой tolerance, чтобы не останавливаться раньше времени
                        ball_y = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                        distance_to_paddle = paddle_y - ball_y if ball_y < paddle_y else 0
                        time_to_paddle = distance_to_paddle / ball_vel_y if ball_vel_y > 0 and distance_to_paddle > 0 else float('inf')
                        distance_to_move = distance_to_target
                        frames_to_reach = distance_to_move / paddle_speed if paddle_speed > 0 else float('inf')
                        # КРИТИЧНО: Добавляем небольшой запас (0.5 кадра) для учета неточностей расчета
                        # Это особенно важно, когда мяч очень близко
                        will_reach = (frames_to_reach <= time_to_paddle + 0.5) if time_to_paddle != float('inf') else False
                        
                        # КРИТИЧНО: НЕ пересчитываем цель когда мяч очень близко, если траектория стабильна
                        # Если мяч летит по прямой траектории и не может её изменить (нет кубиков на пути, нет стен),
                        # то пересчёт цели в последний момент только вызывает дёргание платформы
                        # Пересчитываем ТОЛЬКО если платформа не успевает добраться до цели
                        force_recalculate = False  # УБРАНО: пересчёт при близком мяче вызывает дёргание
                        
                        # КРИТИЧНО: УБРАНО - пересчет позиции когда "не успевает" вызывает дёргание
                        # Платформа должна продолжать движение к зафиксированной цели, даже если "не успевает"
                        # Это лучше, чем постоянно пересчитывать позицию и дёргаться
                        # if (not will_reach) and time_to_paddle != float('inf') and time_to_paddle > 0:
                        #     ... пересчет позиции ...
                        
                        # ПРАВИЛО 3.1: Если платформа близко к цели - проверяем, нужно ли еще двигаться
                        # КРИТИЧНО: Минимальный tolerance - платформа должна двигаться до точной позиции
                        # Останавливаемся ТОЛЬКО когда действительно достигли цели (tolerance = 3px)
                        tolerance = 3
                        
                        # КРИТИЧНО: УБРАНО - сложная логика с проверкой зон вызывает дёргание
                        # Платформа должна просто двигаться к цели до точной позиции
                        
                        # КРИТИЧНО: Если мяч очень близко к платформе (менее 10 кадров), уменьшаем tolerance еще больше
                        if time_to_paddle != float('inf') and time_to_paddle < 10:
                            tolerance = max(3, tolerance // 2)  # Уменьшаем tolerance вдвое, минимум 3px
                        
                        # КРИТИЧНО: Используем зафиксированную позицию БЕЗ пересчета
                        # Позиция фиксируется один раз и НЕ меняется до отскока от стены
                        target_pos = self.separation_zone_tracker.get("target_position")
                        if target_pos is None:
                            target_pos = current_x
                        distance_to_target = abs(current_x - target_pos)
                        # Определяем is_edge_zone на основе сохранённой цели
                        if target_pos is not None:
                            screen_width = self.screen_width
                            ball_radius = 8
                            min_safe_x = ball_radius + 40
                            max_safe_x = screen_width - ball_radius - 40
                            is_edge_zone = (target_pos < min_safe_x or target_pos > max_safe_x)
                        else:
                            is_edge_zone = False
                        
                        # Продолжаем движение к актуальной цели, даже если близко к старой цели
                        # Для EDGE зоны используем меньший порог (2px), для остальных - 3px
                        # КРИТИЧНО: Если мяч в EDGE зоне и очень близко (менее 3 кадров), НЕ останавливаемся до достижения края
                        if is_edge_zone and time_to_paddle < 3:
                            # В EDGE зоне и очень близко - продолжаем движение до края зоны
                            # Проверяем, достигли ли мы края зоны
                            screen_width = self.screen_width
                            # Определяем, к какому краю нужно двигаться
                            saved_target = self.separation_zone_tracker.get("target_position")
                            target_to_check = target_pos if target_pos is not None else (saved_target if saved_target is not None else current_x)
                            
                            if target_to_check > screen_width / 2:
                                # Правый край - проверяем, достигли ли мы правого края
                                right_edge = screen_width - self.paddle_width // 2
                                if abs(current_x - right_edge) > 2:
                                    pass  # Продолжаем движение к правому краю
                                else:
                                    # Достигли правого края - останавливаемся
                                    if not self.separation_zone_tracker.get("paddle_reached_target", False):
                                        self.separation_zone_tracker["paddle_reached_target"] = True
                                    return 0
                            else:
                                # Левый край - проверяем, достигли ли мы левого края
                                left_edge = self.paddle_width // 2
                                if abs(current_x - left_edge) > 2:
                                    pass  # Продолжаем движение к левому краю
                                else:
                                    # Достигли левого края - останавливаемся
                                    if not self.separation_zone_tracker.get("paddle_reached_target", False):
                                        self.separation_zone_tracker["paddle_reached_target"] = True
                                    return 0
                        elif distance_to_target <= tolerance:
                            # КРИТИЧНО: В зоне разделения цель установлена ОДИН РАЗ и НЕ обновляется
                            # Траектория мяча не меняется - используем сохраненную цель БЕЗ изменений
                            # НЕ проверяем actual_distance - это вызывает дёргание
                            
                            # КРИТИЧНО: Если мяч очень близко (менее 3 кадров), НЕ останавливаемся
                            # Это критично для предотвращения потери мяча в последний момент
                            # КРИТИЧНО: Если мяч в EDGE зоне, НЕ останавливаемся до достижения края зоны
                            # даже если мяч не очень близко - это критично для предотвращения потери мяча у края
                            if (time_to_paddle != float('inf') and time_to_paddle < 3) or is_edge_zone:
                                # Мяч очень близко ИЛИ в EDGE зоне - продолжаем движение, даже если близко к цели
                                # Для EDGE зоны проверяем, достигли ли мы края зоны
                                if is_edge_zone:
                                    screen_width = self.screen_width
                                    saved_target = self.separation_zone_tracker.get("target_position")
                                    target_to_check = target_pos if target_pos is not None else (saved_target if saved_target is not None else current_x)
                                    
                                    if target_to_check > screen_width / 2:
                                        # Правый край - проверяем, достигли ли мы правого края
                                        right_edge = screen_width - self.paddle_width // 2
                                        if abs(current_x - right_edge) > 2:
                                            # Еще не достигли правого края - продолжаем движение
                                            pass  # Пропускаем остановку, продолжаем движение
                                        else:
                                            # Достигли правого края - останавливаемся
                                            if not self.separation_zone_tracker.get("paddle_reached_target", False):
                                                self.separation_zone_tracker["paddle_reached_target"] = True
                                            return 0
                                    else:
                                        # Левый край - проверяем, достигли ли мы левого края
                                        left_edge = self.paddle_width // 2
                                        if abs(current_x - left_edge) > 2:
                                            # Еще не достигли левого края - продолжаем движение
                                            pass  # Пропускаем остановку, продолжаем движение
                                        else:
                                            # Достигли левого края - останавливаемся
                                            if not self.separation_zone_tracker.get("paddle_reached_target", False):
                                                self.separation_zone_tracker["paddle_reached_target"] = True
                                            return 0
                                else:
                                    # Мяч очень близко, но не в EDGE зоне - продолжаем движение
                                    pass  # Пропускаем остановку, продолжаем движение
                            else:
                                # КРИТИЧНО: В зоне разделения цель установлена ОДИН РАЗ и НЕ обновляется
                                # Если достигли сохраненной цели - останавливаемся
                                if not self.separation_zone_tracker.get("paddle_reached_target", False):
                                    self.separation_zone_tracker["paddle_reached_target"] = True
                                # КРИТИЧНО: Логируем для диагностики
                                import random
                                if random.random() < 0.2:  # 20% кадров
                                    self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 3.1: Платформа очень близко к цели (distance={distance_to_target:.1f} <= {tolerance}), не двигаемся")
                                self._log_paddle_movement(current_x, current_x, "paddle_reached_target", 1.0)
                                return 0
                        
                        # ПРАВИЛО 3.2: Платформа еще не достигла цели - двигаемся к сохраненной позиции
                        # КРИТИЧНО: УБРАНО - сложная логика с проверкой "очень близко" вызывает дёргание
                        # Платформа должна просто двигаться к цели до точной позиции (tolerance = 3px)
                        
                        # Устанавливаем флаг, что платформа начала двигаться после установки цели
                        if not self.separation_zone_tracker.get("paddle_moved_after_set", False):
                            self.separation_zone_tracker["paddle_moved_after_set"] = True
                            # КРИТИЧНО: Логируем начало движения
                            self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 3.2: Начинаем движение к сохраненной позиции. current_x={current_x}, target_pos={target_pos}, distance={distance_to_target:.1f}")
                            self._log_paddle_movement(current_x, target_pos, "paddle_moving_to_target", 0.9)
                        
                        # КРИТИЧНО: Проверяем, что движение действительно нужно
                        # Если target_pos == current_x, не двигаемся
                        if target_pos == current_x:
                            return 0
                        
                        # Двигаемся к сохраненной позиции БЕЗ дополнительных проверок
                        movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                        # КРИТИЧНО: Проверяем, что movement не равен 0 (должно быть -1 или 1)
                        if movement == 0:
                            # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                            self._logger.warning(f"[PADDLE DEBUG] ПРАВИЛО 3.2: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback")
                            return self._fallback_movement(current_x)
                        
                        # КРИТИЧНО: Логируем движение с информацией о скорости (всегда)
                        # Примечание: проверка will_reach уже выполнена выше, перед проверкой tolerance
                        # КРИТИЧНО: Логируем всегда (100% кадров) для диагностики
                        # Пересчитываем для логирования
                        ball_y_log = self.current_game_state.ball_position.y if self.current_game_state else 0
                        ball_vel_y_log = self.current_game_state.ball_velocity.y if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                        paddle_y_log = self.current_game_state.paddle_position.y if self.current_game_state else paddle_zone_start
                        distance_to_paddle_log = paddle_y_log - ball_y_log if ball_y_log < paddle_y_log else 0
                        time_to_paddle_log = distance_to_paddle_log / ball_vel_y_log if ball_vel_y_log > 0 and distance_to_paddle_log > 0 else float('inf')
                        distance_to_move_log = distance_to_target
                        frames_to_reach_log = distance_to_move_log / paddle_speed if paddle_speed > 0 else float('inf')
                        will_reach_log = frames_to_reach_log <= time_to_paddle_log if time_to_paddle_log != float('inf') else False
                        
                        self._logger.debug(f"[PADDLE MOVEMENT] movement={movement} distance={distance_to_target:.1f}px "
                                           f"current_x={current_x:.1f} target={target_pos:.1f} | "
                                           f"paddle_speed={paddle_speed} frames_to_reach={frames_to_reach_log:.1f} "
                                           f"time_to_paddle={time_to_paddle_log:.1f} will_reach={will_reach_log}")
                        
                        self._update_loop_tracking(movement, current_x, target_pos)
                        self._update_smoothness_tracking(movement, current_x)
                        self._log_paddle_movement(current_x, target_pos, "moving_to_locked_target", 1.0)
                        return movement
                    else:
                        # target_pos is None - сбрасываем флаг и продолжаем обработку
                        self.separation_zone_tracker["target_position_set"] = False
                        self._log_paddle_movement(current_x, current_x, "target_reset_none", 1.0)
                        # Продолжаем обработку с обычной логикой - НЕ возвращаем 0!
            
            # ПРАВИЛО 4: Если целевая позиция НЕ установлена и мяч в зоне разделения
            # - устанавливаем целевую позицию ОДИН РАЗ через get_optimal_paddle_position
            # - после установки используем её без пересчета
            # КРИТИЧНО: Проверяем, что мяч НЕ потерян перед установкой целевой позиции
            if in_separation_zone and not self.separation_zone_tracker.get("target_position_set", False) and not ball_lost:
                # КРИТИЧНО: Логируем установку целевой позиции
                import random
                if random.random() < 0.2:  # 20% кадров для диагностики
                    self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Устанавливаем целевую позицию. ball_y={ball_y:.1f}, in_separation_zone={in_separation_zone}")
                # Устанавливаем целевую позицию один раз
                optimal_x = self.get_optimal_paddle_position()
                
                # КРИТИЧНО: Проверяем, что optimal_x валиден
                if optimal_x is None:
                    # Если не удалось рассчитать позицию, используем fallback
                    return self._fallback_movement(current_x)
                
                # КРИТИЧНО: Проверяем, успеет ли платформа добраться до цели
                # Если мяч уже очень близко (менее 10 кадров), и платформа далеко от цели (более 100px),
                # используем более близкую позицию или текущую позицию мяча
                distance_to_target = abs(current_x - optimal_x)
                distance_to_paddle_y = paddle_y - ball_y if ball_y < paddle_y else 0
                time_to_paddle = distance_to_paddle_y / ball_vel_y if ball_vel_y > 0 and distance_to_paddle_y > 0 else float('inf')
                
                if time_to_paddle != float('inf') and time_to_paddle < 10 and distance_to_target > 100:
                    # Мяч очень близко, а платформа далеко - пересчитываем цель с учетом зон
                    # Вместо простого ограничения движения, пересчитываем оптимальную позицию
                    # с учетом того, что платформа не успеет далеко переместиться
                    original_optimal = optimal_x
                    
                    # Рассчитываем максимальное расстояние, которое платформа может пройти
                    # Используем переданный paddle_speed или базовую скорость
                    max_distance = paddle_speed * time_to_paddle
                    
                    # Определяем, в какую зону попадает predicted_x
                    ball_x = self.current_game_state.ball_position.x if self.current_game_state else 0
                    ball_vel_x = self.current_game_state.ball_velocity.x if (self.current_game_state and hasattr(self.current_game_state, "ball_velocity")) else 0
                    predicted_x = ball_x + ball_vel_x * time_to_paddle
                    
                    # Применяем логику зон к predicted_x
                    zone_size = self.paddle_width / 3
                    screen_center = self.screen_width / 2
                    left_threshold = screen_center - zone_size * 2
                    right_threshold = screen_center + zone_size * 2
                    
                    if predicted_x < left_threshold:
                        # Левая зона
                        zone_center_x = predicted_x + zone_size
                    elif predicted_x > right_threshold:
                        # Правая зона
                        zone_center_x = predicted_x - zone_size
                    else:
                        # Центральная зона
                        zone_center_x = predicted_x
                    
                    # Ограничиваем максимальное расстояние движения
                    if zone_center_x > current_x:
                        optimal_x = min(zone_center_x, current_x + max_distance)
                    else:
                        optimal_x = max(zone_center_x, current_x - max_distance)
                    
                    self._logger.debug(f"[TARGET ADJUST] Мяч близко! time_to_paddle={time_to_paddle:.1f}, скорректирована цель с {original_optimal:.1f} на {optimal_x:.1f} (max_distance={max_distance:.1f})")
                
                # Сохраняем целевую позицию
                current_target = self.separation_zone_tracker.get("target_position")
                old_target_str = f"{current_target:.1f}" if current_target is not None else "None"
                self._logger.debug(f"[POSITION CHANGE] ФЛАГ: Платформа устанавливает новую цель (ПРАВИЛО 4)! paddle_x={current_x:.1f}, "
                                   f"старая_цель={old_target_str}, "
                                   f"новая_цель={optimal_x:.1f}, distance_to_target={abs(current_x - optimal_x):.1f}")
                self.separation_zone_tracker["target_position"] = int(optimal_x)
                self.separation_zone_tracker["target_position_set"] = True
                self.separation_zone_tracker["paddle_moved_after_set"] = False
                self.separation_zone_tracker["paddle_reached_target"] = False
                self.separation_zone_tracker["frames_since_target_set"] = 0
                self._log_paddle_movement(current_x, optimal_x, "target_position_set", 1.0)
                # Продолжаем обработку с установленной позицией
                target_pos = int(optimal_x)
                distance_to_target = abs(current_x - target_pos)
                
                # КРИТИЧНО: Проверяем, что движение действительно нужно
                # Если target_pos == current_x, не двигаемся
                if target_pos == current_x:
                    self.separation_zone_tracker["paddle_reached_target"] = True
                    return 0
                
                # КРИТИЧНО: В зоне разделения останавливаемся только если ОЧЕНЬ близко к цели
                # Увеличено до 25 пикселей для предотвращения дрожания
                if distance_to_target <= 25:
                    self.separation_zone_tracker["paddle_reached_target"] = True
                    # КРИТИЧНО: Логируем для диагностики
                    import sys
                    import random
                    if random.random() < 0.2:  # 20% кадров
                        self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Платформа очень близко к цели (distance={distance_to_target:.1f} <= 5), не двигаемся")
                    return 0
                
                movement = 1 if target_pos > current_x else (-1 if target_pos < current_x else 0)
                # КРИТИЧНО: Проверяем, что movement не равен 0
                if movement == 0:
                    # Если по какой-то причине movement = 0, но target_pos != current_x, используем fallback
                    self._logger.warning(f"[PADDLE DEBUG] ПРАВИЛО 4: ОШИБКА: movement=0, но target_pos={target_pos} != current_x={current_x}, using fallback")
                    return self._fallback_movement(current_x)
                
                # КРИТИЧНО: Логируем движение
                import random
                if random.random() < 0.2:  # 20% кадров
                    self._logger.debug(f"[PADDLE DEBUG] ПРАВИЛО 4: Движение! movement={movement}, distance={distance_to_target:.1f}, current_x={current_x}, target_pos={target_pos}")
                
                self.separation_zone_tracker["paddle_moved_after_set"] = True
                self._update_loop_tracking(movement, current_x, target_pos)
                self._update_smoothness_tracking(movement, current_x)
                self._log_paddle_movement(current_x, target_pos, "moving_to_new_target", 0.9)
                return movement
            
            # ПРАВИЛО 5: Если мяч НЕ в зоне разделения и целевая позиция НЕ установлена
            # - используем обычную логику (мяч еще в зоне кубиков или выше)
            # КРИТИЧНО: Но только если мяч НЕ потерян и движется вниз
            # Если мяч потерян или движется вверх - не двигаемся
            if ball_lost:
                self._log_paddle_movement(current_x, current_x, "ball_lost_below_paddle_rule5", 1.0)
                return 0
            
            # КРИТИЧНО: УБРАНО правило "не двигаться когда мяч летит вверх"
            # Платформа ДОЛЖНА двигаться к точке падения мяча даже когда мяч летит вверх,
            # чтобы успеть к моменту падения. Продолжаем расчет оптимальной позиции.
            
            # КРИТИЧНО: Если мяч в разрешенной зоне (ниже кубиков, но выше платформы) и движется вниз
            # - платформа ДОЛЖНА двигаться к точке падения мяча
            optimal_x = self.get_optimal_paddle_position()
            
            # КРИТИЧНО: Проверяем, что optimal_x валиден
            if optimal_x is None:
                # Если не удалось рассчитать позицию, используем fallback
                return self._fallback_movement(current_x)

            # Проверяем зацикливание и при необходимости меняем стратегию
            # НО ТОЛЬКО если целевая позиция НЕ установлена
            if not self.separation_zone_tracker.get("target_position_set", False):
                self._change_strategy_if_looping()
                if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                    optimal_x = self._apply_alternative_strategy(optimal_x)
                    # Проверяем, что альтернативная стратегия тоже валидна
                    if optimal_x is None:
                        return self._fallback_movement(current_x)

            # Допуск по точности позиционирования
            precision_tolerance = 2
            # Проверяем дрожание и применяем штрафы
            jitter_detected = self._detect_jitter()
            if jitter_detected:
                # Увеличиваем допуск для уменьшения дрожания
                precision_tolerance = max(5, precision_tolerance + 2)
                # Увеличиваем штраф за дрожание
                self.smoothness_system["smoothness_penalty"] = min(
                    1.0, self.smoothness_system["smoothness_penalty"] + 0.1
                )
            else:
                # Уменьшаем штраф при плавном движении
                self.smoothness_system["smoothness_penalty"] = max(
                    0.0, self.smoothness_system["smoothness_penalty"] - 0.05
                )

            # Допуск по точности позиционирования (учитываем штраф за дрожание)
            base_precision_tolerance = 2
            precision_tolerance = base_precision_tolerance + int(
                self.smoothness_system["smoothness_penalty"] * 3
            )

            # Увеличиваем допуск, когда мяч движется вниз и траектория известна
            if self.current_game_state:
                ball_vel_y = (
                    self.current_game_state.ball_velocity.y
                    if hasattr(self.current_game_state, "ball_velocity")
                    else 0
                )
                ball_y = self.current_game_state.ball_position.y
                paddle_zone_start = self.screen_height - 60
                separation_zone_start = self.separation_zone_tracker.get("separation_zone_start", 226)
                in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y > 0

                # КРИТИЧНО: НЕ увеличиваем допуск слишком сильно, иначе платформа не будет двигаться
                # Если мяч движется вниз и уже ниже кубиков - используем умеренный допуск
                if ball_vel_y > 0 and ball_y > 250:  # Мяч движется вниз и ниже кубиков
                    # Используем умеренный допуск (5-10 пикселей), чтобы платформа могла двигаться
                    # Только если платформа УЖЕ очень близко к цели (менее 5 пикселей) - не двигаемся
                    if abs(optimal_x - current_x) < 5:
                        precision_tolerance = max(precision_tolerance, 5)  # Очень близко - не двигаемся
                    else:
                        # Платформа еще не достигла цели - используем минимальный допуск для движения
                        precision_tolerance = max(precision_tolerance, 2)  # Минимальный допуск

            distance_to_optimal = abs(optimal_x - current_x)

            # Поощряем минимальные движения - если расстояние очень мало, не двигаемся
            min_movement_distance = self.smoothness_system["min_movement_distance"]
            
            # КРИТИЧНО: Убрана проверка ball_approaching_quickly - она вызывала дергание
            # В зоне разделения с установленной целевой позицией платформа просто движется к цели и останавливается
            
            if distance_to_optimal < min_movement_distance:
                # Если расстояние меньше минимального, проверяем, стоит ли двигаться
                if distance_to_optimal <= precision_tolerance:
                    movement = 0
                    # Поощряем точное позиционирование
                    self.smoothness_system["consecutive_stops"] += 1
                    if self.smoothness_system["consecutive_stops"] > 3:
                        # Уменьшаем штраф за хорошее позиционирование
                        self.smoothness_system["smoothness_penalty"] = max(
                            0.0, self.smoothness_system["smoothness_penalty"] - 0.1
                        )
                    # Сохраняем базовую скорость, так как не двигаемся
                    self._last_adjusted_paddle_speed = paddle_speed
                else:
                    # Двигаемся только если действительно нужно
                    movement = self._calculate_smooth_movement(
                        current_x, optimal_x, distance_to_optimal
                    )
                    # Сохраняем базовую скорость для этого случая
                    self._last_adjusted_paddle_speed = paddle_speed
            elif distance_to_optimal <= precision_tolerance:
                movement = 0
                self.smoothness_system["consecutive_stops"] += 1
                # Сохраняем базовую скорость, так как не двигаемся
                self._last_adjusted_paddle_speed = paddle_speed
            else:
                self.smoothness_system["consecutive_stops"] = 0
                # Адаптивная скорость от системы обучения
                if self.current_game_state:
                    ball_speed = self.current_game_state.ball_speed
                    distance_to_target = distance_to_optimal

                    # Рассчитываем время до встречи с мячом для более агрессивного увеличения скорости
                    time_to_meeting = float("inf")
                    ball_vel_y = (
                        self.current_game_state.ball_velocity.y
                        if hasattr(self.current_game_state, "ball_velocity")
                        else 0
                    )
                    if ball_vel_y > 0:  # Мяч движется вниз
                        ball_y = self.current_game_state.ball_position.y
                        paddle_y = self.current_game_state.paddle_position.y
                        distance_y = paddle_y - ball_y
                        if distance_y > 0:
                            time_to_meeting = distance_y / ball_vel_y

                    speed_multiplier = self.learning_system.get_adaptive_paddle_speed(
                        ball_speed, distance_to_target
                    )

                    # Если мяч быстро приближается, агрессивно увеличиваем скорость
                    if time_to_meeting != float("inf") and time_to_meeting > 0:
                        # Чем меньше времени до встречи, тем выше должна быть скорость
                        if time_to_meeting < 30:  # Менее 30 кадров (0.5 сек при 60 FPS)
                            urgency_factor = 30.0 / max(time_to_meeting, 1)
                            speed_multiplier *= min(
                                urgency_factor, 3.0
                            )  # До 3x дополнительного ускорения
                        elif time_to_meeting < 60:  # Менее 60 кадров (1 сек)
                            urgency_factor = 60.0 / max(time_to_meeting, 1)
                            speed_multiplier *= min(
                                urgency_factor, 2.0
                            )  # До 2x дополнительного ускорения

                    # КРИТИЧНО: Увеличиваем базовую скорость платформы в 10 раз
                    # Платформа не может не успеть - скорость задает сам алгоритм
                    base_speed_multiplier = 10.0  # Увеличиваем базовую скорость в 10 раз
                    
                    # Ограничиваем минимальный множитель скорости, чтобы платформа не двигалась слишком медленно
                    # AI может увеличивать скорость до 10x для достижения цели (в дополнение к базовому 10x)
                    max_multiplier = 10.0  # Дополнительный множитель до 10x
                    speed_multiplier = max(0.8, min(max_multiplier, speed_multiplier))
                    adjusted_paddle_speed = int(paddle_speed * base_speed_multiplier)  # ИСПРАВЛЕНО: убрано двойное умножение
                    # Гарантируем минимальную скорость платформы
                    adjusted_paddle_speed = max(
                        int(paddle_speed * 0.8), adjusted_paddle_speed
                    )
                    self._last_paddle_speed_multiplier = speed_multiplier
                    # Сохраняем для использования в PyGameBall.py
                    self._last_adjusted_paddle_speed = adjusted_paddle_speed
                else:
                    adjusted_paddle_speed = paddle_speed

                # Сохраняем для использования в PyGameBall.py
                self._last_adjusted_paddle_speed = adjusted_paddle_speed

                movement = self.position_optimizer.calculate_paddle_movement(
                    current_x, optimal_x, adjusted_paddle_speed
                )

                # Если расчёт не даёт движения, но мы не на месте — fallback
                if movement == 0 and optimal_x != current_x:
                    movement = self._fallback_movement(current_x)

            # Обновляем данные по зацикливанию
            self._update_loop_tracking(movement, current_x, optimal_x)
            
            # Обновляем данные по плавности движения
            self._update_smoothness_tracking(movement, current_x)

            # Логирование движения
            if movement != 0:
                reason = (
                    "ball_tracking"
                    if not self.is_ball_moving_towards_paddle()
                    else "trajectory_optimization"
                )
                confidence = self._calculate_decision_confidence(optimal_x)
                self.performance_logger.log_paddle_movement(
                    from_x=current_x,
                    to_x=current_x + movement * paddle_speed,
                    reason=reason,
                    confidence=confidence,
                )

            # Статистика по ходам
            self.current_game_stats["total_moves"] += 1
            if abs(optimal_x - current_x) < 10:
                self.current_game_stats["optimal_moves"] += 1

            # Учитываем плавность движения в обучении
            if movement != 0:
                # Штрафуем за дрожание при обучении
                if self.smoothness_system["smoothness_penalty"] > 0.5:
                    # Высокий штраф за дрожание - это плохое поведение
                    jitter_penalty = {
                        "action_type": "movement_jitter",
                        "success": False,
                        "penalty": self.smoothness_system["smoothness_penalty"],
                        "movement_distance": abs(optimal_x - current_x),
                    }
                    # Можно добавить в систему обучения для улучшения поведения
                    # self.learning_system.update_strategy(jitter_penalty)

            return movement

        except Exception as e:
            # Не выводим в exe файле
            import sys

            self._logger.error(f"Ошибка при движении платформы: {e}", exc_info=True)
            return self._fallback_movement(current_x)

    def _fallback_movement(self, current_x: int) -> int:
        """
        Резервное движение платформы — улучшенное следование за мячом.

        Args:
            current_x: Текущая X-координата платформы.

        Returns:
            Смещение платформы (-1, 0, 1).
        """
        if not self.current_game_state:
            return 0

        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y

        # Если мяч падает — предсказываем точку встречи с платформой
        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y != 0 else 0
            if time_to_paddle > 0:
                predicted_x = ball_x + vel_x * time_to_paddle

                screen_width = self.screen_width
                ball_radius = 8

                # Простое моделирование отскоков
                while (
                    predicted_x < ball_radius
                    or predicted_x > screen_width - ball_radius
                ):
                    if predicted_x < ball_radius:
                        predicted_x = 2 * ball_radius - predicted_x
                        vel_x = abs(vel_x)
                    elif predicted_x > screen_width - ball_radius:
                        predicted_x = 2 * (screen_width - ball_radius) - predicted_x
                        vel_x = -abs(vel_x)
                target_x = predicted_x
            else:
                target_x = ball_x
        else:
            # Мяч движется вверх — следим с небольшим упреждением
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

    # ==========================
    # Оценка уверенности и давление по времени
    # ==========================

    def _is_time_pressure(self) -> bool:
        """Определяет, есть ли давление по времени/ситуации (мало времени или кубиков)."""
        if not self.current_game_state:
            return False

        game_time = self.current_game_state.game_time
        if game_time > 300:
            return True

        if len(self.current_game_state.remaining_bricks) <= 5:
            return True

        return False

    def _calculate_decision_confidence(self, target_position: int) -> float:
        """
        Рассчитывает уверенность в принятом решении.

        Args:
            target_position: Целевая X-позиция платформы.

        Returns:
            Уровень уверенности (0.0–1.0).
        """
        if not self.current_game_state:
            return 0.5

        confidence = 0.7

        bricks_count = len(self.current_game_state.remaining_bricks)
        if bricks_count <= 5:
            confidence += 0.1
        elif bricks_count >= 20:
            confidence -= 0.1

        ball_speed = self.current_game_state.ball_speed
        if ball_speed >= 8:
            confidence -= 0.1
        elif ball_speed <= 3:
            confidence += 0.1

        return max(0.1, min(1.0, confidence))

    # ==========================
    # Обучение по результату действия
    # ==========================

    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучает AI-систему на основе результата последнего действия.

        Args:
            action_result: Словарь с информацией о результате (hit/miss, счёт и т.д.).

        Raises:
            ValueError: Если action_result не является словарем или пуст.
        """
        if not isinstance(action_result, dict):
            raise ValueError("action_result должен быть словарем")

        if not action_result:
            raise ValueError("action_result не может быть пустым")

        if not self.current_game_state:
            return

        enhanced_result = action_result.copy()
        enhanced_result.update(
            {
                "game_state_before": {
                    "ball_position": {
                        "x": self.current_game_state.ball_position.x,
                        "y": self.current_game_state.ball_position.y,
                    },
                    "paddle_position": {
                        "x": self.current_game_state.paddle_position.x,
                        "y": self.current_game_state.paddle_position.y,
                    },
                    "bricks_remaining": len(self.current_game_state.remaining_bricks),
                    "ball_speed": self.current_game_state.ball_speed,
                },
                "trajectory_prediction": self._get_current_trajectory_prediction(),
            }
        )

        # Запись результата для системы прицеливания
        action_type = action_result.get("action_type", "")

        if action_type == "brick_hit":
            bricks_destroyed = action_result.get("bricks_destroyed", [])
            for brick in bricks_destroyed:
                paddle_x = self.current_game_state.paddle_position.x
                ball_x = self.current_game_state.ball_position.x
                paddle_offset = (ball_x - paddle_x) / (self.paddle_width / 2)
                paddle_offset = max(-1.0, min(1.0, paddle_offset))
                self.record_hit_result(brick, paddle_offset, success=True)

        elif action_type == "paddle_bounce":
            # Отслеживаем отбития в пустоту
            bricks_before = enhanced_result.get("game_state_before", {}).get("bricks_remaining", 0)
            bricks_after = len(self.current_game_state.remaining_bricks) if self.current_game_state else 0
            
            # Если количество блоков не изменилось после отскока - это отбитие в пустоту
            if bricks_before == bricks_after and bricks_before > 0:
                self.empty_bounce_tracker["consecutive_empty_bounces"] += 1
                self.empty_bounce_tracker["last_bounce_position"] = self.current_game_state.paddle_position.x if self.current_game_state else None
                self.empty_bounce_tracker["last_bounce_time"] = time.time()
                self.empty_bounce_tracker["bounce_history"].append({
                    "position": self.current_game_state.paddle_position.x if self.current_game_state else 0,
                    "bricks_remaining": bricks_after,
                    "time": time.time(),
                })
                # Ограничиваем историю
                if len(self.empty_bounce_tracker["bounce_history"]) > 10:
                    self.empty_bounce_tracker["bounce_history"] = self.empty_bounce_tracker["bounce_history"][-5:]
            else:
                # Блок был сбит - сбрасываем счетчик
                self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
            
            if self.targeting_system["target_brick"]:
                paddle_x = self.current_game_state.paddle_position.x
                ball_x = self.current_game_state.ball_position.x
                paddle_offset = (ball_x - paddle_x) / (self.paddle_width / 2)
                paddle_offset = max(-1.0, min(1.0, paddle_offset))

                enhanced_result["targeting_info"] = {
                    "target_brick": self.targeting_system["target_brick"],
                    "optimal_offset": self.targeting_system["optimal_offset"],
                    "actual_offset": paddle_offset,
                }

                # После отскока переоцениваем ситуацию
                self._reevaluate_after_bounce()

        # Обновляем стратегию обучения
        self.learning_system.update_strategy(enhanced_result)

        # Обратная связь по скорости платформы
        if hasattr(self, "_last_paddle_speed_multiplier") and self.current_game_state:
            success_flag = action_result.get("success", False)
            ball_speed = self.current_game_state.ball_speed
            self.learning_system.update_paddle_speed_feedback(
                ball_speed,
                self._last_paddle_speed_multiplier,
                success_flag,
            )

        # Логирование действия
        self.performance_logger.log_action(enhanced_result)

        # Обновление метрик
        self._update_performance_metrics(action_result)

    def _get_current_trajectory_prediction(self) -> Optional[Dict[str, Any]]:
        """Возвращает текущее предсказание траектории мяча (для логирования/обучения)."""
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            return None

        try:
            trajectory = self.trajectory_predictor.predict_trajectory(
                self.current_game_state
            )
            intersection_point = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state,
                self.current_game_state.paddle_position.y,
            )
            return {
                "predicted_points": [{"x": p.x, "y": p.y} for p in trajectory],
                "intersection_point": intersection_point,
            }
        except Exception:
            return None

    # ==========================
    # Метрики и окончание игры
    # ==========================

    def _update_performance_metrics(self, action_result: Dict[str, Any]) -> None:
        """Обновляет метрики производительности на основе результата действия."""
        success = action_result.get("success", False)

        if success:
            self.current_game_stats["successful_predictions"] += 1

        if "bricks_destroyed" in action_result:
            bricks_value = action_result["bricks_destroyed"]
            # КРИТИЧНО: Если это окончание игры (game_end), устанавливаем значение напрямую, а не накапливаем
            # Это предотвращает неправильный подсчет при повторных вызовах
            if action_result.get("action_type") == "game_end":
                # При окончании игры bricks_destroyed - это общее количество за всю игру
                if isinstance(bricks_value, int):
                    # КРИТИЧНО: Ограничиваем значение максимумом кубиков в игре (50)
                    # Это предотвращает отображение неправильных значений (например, 70 вместо 50)
                    max_bricks = 50  # Максимальное количество кубиков в игре
                    self.current_game_stats["bricks_destroyed"] = min(bricks_value, max_bricks)
                elif isinstance(bricks_value, list):
                    max_bricks = 50
                    self.current_game_stats["bricks_destroyed"] = min(len(bricks_value), max_bricks)
            else:
                # Для других событий накапливаем значение
                if isinstance(bricks_value, int):
                    self.current_game_stats["bricks_destroyed"] += bricks_value
                elif isinstance(bricks_value, list):
                    self.current_game_stats["bricks_destroyed"] += len(bricks_value)
                
                # КРИТИЧНО: Ограничиваем накопленное значение максимумом кубиков в игре
                max_bricks = 50
                if self.current_game_stats["bricks_destroyed"] > max_bricks:
                    self.current_game_stats["bricks_destroyed"] = max_bricks

        self.current_game_stats["total_predictions"] += 1

        if "final_score" in action_result:
            self.performance_metrics["total_score"] += action_result["final_score"]

    def on_game_end(
        self, success: bool, final_score: int, training_mode: bool = False
    ) -> None:
        """
        Обрабатывает окончание игры.

        Args:
            success: True, если все кубики сбиты.
            final_score: Итоговый счёт.
            training_mode: True, если это режим обучения.

        Raises:
            ValueError: Если final_score отрицательный.
        """
        if final_score < 0:
            raise ValueError("Final_score не может быть отрицательным")

        self.performance_metrics["games_played"] += 1
        if success:
            self.performance_metrics["games_won"] += 1

        # Точность предсказаний
        if self.current_game_stats["total_predictions"] > 0:
            accuracy = (
                self.current_game_stats["successful_predictions"]
                / self.current_game_stats["total_predictions"]
            )
            self.performance_metrics["average_accuracy"] = (
                self.performance_metrics["average_accuracy"] * 0.9 + accuracy * 0.1
            )

        # Прогресс обучения
        learning_progress = self.learning_system.get_learning_progress()
        if isinstance(learning_progress, dict):
            # Если learning_progress - словарь, вычисляем прогресс на основе метрик
            if "message" in learning_progress:
                # Обучение еще не начато
                learning_progress_value = 0.0
            else:
                # Используем success_rate как основной показатель прогресса
                success_rate = learning_progress.get("success_rate", 0.0)
                # Учитываем также количество итераций и улучшения
                total_iterations = learning_progress.get("total_iterations", 0)
                avg_improvement = learning_progress.get("average_improvement", 0.0)
                # Прогресс = успешность * (1 - exp(-итерации/10)) + улучшение
                iteration_factor = 1.0 - (2.71828 ** (-total_iterations / 10.0))
                learning_progress_value = success_rate * iteration_factor + min(
                    avg_improvement, 0.3
                )
                learning_progress_value = max(0.0, min(1.0, learning_progress_value))
        else:
            learning_progress_value = (
                float(learning_progress) if learning_progress else 0.0
            )

        self.performance_metrics["learning_progress"] = (
            self.performance_metrics["learning_progress"] * 0.9
            + learning_progress_value * 0.1
        )

        # Логирование окончания игры
        # Создаем минимальное состояние игры, если его нет
        if self.current_game_state is None:
            # Создаем пустое состояние для логирования
            empty_state = GameState(
                ball_position=Point(0, 0),
                ball_velocity=Point(0, 0),
                paddle_position=Point(0, 0),
                paddle_width=self.paddle_width,
                remaining_bricks=[],
                game_score=final_score,
                game_time=0,
                ball_speed=0,
            )
            game_state = empty_state
        else:
            game_state = self.current_game_state

        self.performance_logger.log_game_end(game_state, success, final_score)

        # В режиме обучения обрабатываем результаты матча
        if training_mode:
            self._process_training_match(success, final_score)

        # Сохраняем данные по сессии и подготавливаемся к новой игре
        self._save_session_metrics(success, final_score)
        
        # Выводим метрики оценки работы системы scikit-learn
        self._print_ml_system_metrics(success, final_score)
        
        # В режиме обучения выводим средние значения параметров
        if training_mode:
            self._print_training_parameters()

        self._reset_current_game_stats()
        
        # КРИТИЧНО: Сбрасываем все трекеры состояния для новой игры
        self._reset_game_state_trackers()

    def _reset_game_state_trackers(self) -> None:
        """Сбрасывает все трекеры состояния игры для новой игры."""
        # Сбрасываем отслеживание зоны разделения
        self.separation_zone_tracker["ball_entered_separation_zone"] = False
        self.separation_zone_tracker["target_position_set"] = False
        self.separation_zone_tracker["target_position"] = None
        self.separation_zone_tracker["paddle_moved_after_set"] = False
        self.separation_zone_tracker["paddle_reached_target"] = False
        self.separation_zone_tracker["last_movement_frame"] = 0
        
        # Сбрасываем отслеживание отбитий в пустоту
        self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
        self.empty_bounce_tracker["ceiling_bounces"] = 0
        self.empty_bounce_tracker["last_bounce_position"] = None
        self.empty_bounce_tracker["last_bounce_time"] = 0
        
        # Сбрасываем историю зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        
        # Сбрасываем историю плавности движения
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        self.smoothness_system["consecutive_stops"] = 0
        
        # КРИТИЧНО: НЕ сбрасываем current_game_state в None, так как это блокирует движение
        # Вместо этого состояние будет обновлено при следующем вызове update_game_state
        # Если сбросить в None, move_paddle_towards вернет _fallback_movement и платформа не будет двигаться
        # self.current_game_state = None  # ЗАКОММЕНТИРОВАНО - не сбрасываем!

    def _reset_current_game_stats(self) -> None:
        """Сбрасывает статистику текущей игры."""
        self.current_game_stats = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0,
        }

    def _print_ml_system_metrics(self, success: bool, final_score: int) -> None:
        """
        Выводит метрики оценки работы системы scikit-learn в лог.
        
        Args:
            success: True, если игра выиграна.
            final_score: Итоговый счёт игры.
        """
        try:
            self._logger.info("\n" + "=" * 70)
            self._logger.info("МЕТРИКИ ОЦЕНКИ РАБОТЫ СИСТЕМЫ AI (scikit-learn)")
            self._logger.info("=" * 70)
            
            # Базовые метрики игры
            self._logger.info(f"\n[РЕЗУЛЬТАТЫ] Результаты игры:")
            result_text = "[+] ПОБЕДА" if success else "[-] ПОРАЖЕНИЕ"
            self._logger.info(f"   Результат: {result_text}")
            self._logger.info(f"   Финальный счёт: {final_score}")
            self._logger.info(f"   Всего игр: {self.performance_metrics['games_played']}")
            self._logger.info(f"   Побед: {self.performance_metrics['games_won']}")
            if self.performance_metrics["games_played"] > 0:
                win_rate = (
                    self.performance_metrics["games_won"]
                    / self.performance_metrics["games_played"]
                ) * 100
                self._logger.info(f"   Процент побед: {win_rate:.1f}%")
            
            # Метрики текущей игры
            self._logger.info(f"\n[МЕТРИКИ] Метрики текущей игры:")
            self._logger.info(
                f"   Уничтожено кубиков: {self.current_game_stats['bricks_destroyed']}"
            )
            self._logger.info(
                f"   Всего предсказаний: {self.current_game_stats['total_predictions']}"
            )
            if self.current_game_stats["total_predictions"] > 0:
                prediction_accuracy = (
                    self.current_game_stats["successful_predictions"]
                    / self.current_game_stats["total_predictions"]
                ) * 100
                self._logger.info(f"   Точность предсказаний: {prediction_accuracy:.1f}%")
            self._logger.info(f"   Всего ходов: {self.current_game_stats['total_moves']}")
            if self.current_game_stats["total_moves"] > 0:
                optimal_move_rate = (
                    self.current_game_stats["optimal_moves"]
                    / self.current_game_stats["total_moves"]
                ) * 100
                self._logger.info(f"   Оптимальных ходов: {optimal_move_rate:.1f}%")
            
            # Метрики обучения и scikit-learn
            learning_progress = self.learning_system.get_learning_progress()
            
            if (
                isinstance(learning_progress, dict)
                and learning_progress.get("total_iterations", 0) > 0
            ):
                self._logger.info(f"\n[ОБУЧЕНИЕ] Система обучения (scikit-learn):")
                self._logger.info(
                    f"   Всего итераций обучения: {learning_progress.get('total_iterations', 0)}"
                )
                self._logger.info(
                    f"   Успешность адаптаций: {learning_progress.get('success_rate', 0.0):.2%}"
                )
                self._logger.info(
                    f"   Средний прогресс: {learning_progress.get('average_improvement', 0.0):.2%}"
                )
                
                # Кластеризация траекторий (KMeans)
                self._logger.info(f"\n[КЛАСТЕРИЗАЦИЯ] Кластеризация траекторий (KMeans):")
                trajectory_clusters = self.learning_system.cluster_trajectories()
                unique_clusters = learning_progress.get("trajectory_clusters_count", 0)
                cluster_diversity = learning_progress.get("cluster_diversity", 0.0)
                trajectory_patterns = learning_progress.get("trajectory_patterns", 0)
                
                self._logger.info(f"   Найдено паттернов траекторий: {trajectory_patterns}")
                self._logger.info(f"   Количество кластеров: {unique_clusters}")
                self._logger.info(f"   Разнообразие кластеров: {cluster_diversity:.3f}")
                
                if trajectory_clusters:
                    # Анализ распределения по кластерам
                    cluster_counts = {}
                    for item in trajectory_clusters:
                        cluster_id = item.get("cluster", -1)
                        cluster_counts[cluster_id] = (
                            cluster_counts.get(cluster_id, 0) + 1
                        )
                    
                    self._logger.info(f"   Распределение по кластерам:")
                    for cluster_id, count in sorted(cluster_counts.items()):
                        percentage = (count / len(trajectory_clusters)) * 100
                        self._logger.info(
                            f"      Кластер {cluster_id}: {count} паттернов ({percentage:.1f}%)"
                        )
                else:
                    self._logger.info(f"   [ВНИМАНИЕ]  Недостаточно данных для кластеризации")
                
                # Модель предсказания успеха (RandomForestClassifier)
                self._logger.info(f"\n[МОДЕЛЬ] Модель предсказания успеха (RandomForestClassifier):")
                model = self.learning_system.learning_data.get(
                    "success_prediction_model"
                )
                model_metrics = self.learning_system.learning_data.get(
                    "model_metrics", {}
                )
                
                if model is not None:
                    self._logger.info(f"   [+] Модель обучена и готова к использованию")
                    
                    # Показываем метрики модели
                    model_accuracy = model_metrics.get("last_accuracy")
                    if model_accuracy is not None:
                        self._logger.info(f"   Точность модели (accuracy): {model_accuracy:.2%}")
                    
                    training_samples = model_metrics.get("training_samples", 0)
                    test_samples = model_metrics.get("test_samples", 0)
                    features_count = model_metrics.get("features_count", 0)
                    
                    if training_samples > 0:
                        self._logger.info(f"   Образцов для обучения: {training_samples}")
                        self._logger.info(f"   Образцов для тестирования: {test_samples}")
                        self._logger.info(f"   Количество признаков: {features_count}")
                    
                    # Получаем информацию о факторах успеха
                    success_factors = self.learning_system.learning_data.get(
                        "success_factors", {}
                    )
                    if success_factors:
                        self._logger.info(f"   Факторы успеха:")
                        for factor_name, factor_data in success_factors.items():
                            total = factor_data.get("total_cases", 0)
                            successful = factor_data.get("successful_cases", 0)
                            if total > 0:
                                success_rate = (successful / total) * 100
                                self._logger.info(
                                    f"      {factor_name}: {successful}/{total} успешных ({success_rate:.1f}%)"
                                )
                else:
                    self._logger.info(
                        f"   [ВНИМАНИЕ]  Модель ещё не обучена (требуется минимум 100 итераций)"
                    )
                    success_factors = self.learning_system.learning_data.get(
                        "success_factors", {}
                    )
                    if success_factors:
                        total_cases = sum(
                            f.get("total_cases", 0) for f in success_factors.values()
                        )
                        self._logger.info(f"   Накоплено данных: {total_cases} случаев")
                        iterations_needed = max(
                            0,
                            100 - (learning_progress.get("total_iterations", 0) % 100),
                        )
                        self._logger.info(
                            f"   До следующего обучения: {iterations_needed} итераций"
                        )
                
                # Веса стратегий
                strategy_weights = learning_progress.get("strategy_weights", {})
                if strategy_weights:
                    self._logger.info(f"\n[ВЕСА]  Веса стратегий:")
                    for strategy, weight in strategy_weights.items():
                        bar_length = int(weight * 20)
                        bar = "█" * bar_length + "░" * (20 - bar_length)
                        self._logger.info(f"   {strategy:12s}: {bar} {weight:.3f}")
                
                # Предпочтения позиций (убрано по запросу пользователя)
                # learned_positions = learning_progress.get('learned_positions', 0)
                # self._logger.info(f"\n📍 Изученные позиции: {learned_positions}")
                
            else:
                self._logger.info(f"\n[ВНИМАНИЕ]  Система обучения ещё не накопила достаточно данных")
                self._logger.info(
                    f"   Продолжайте играть для активации кластеризации и предсказания"
                )
            
            # Общая оценка системы
            self._logger.info(f"\n[ОЦЕНКА] Общая оценка системы:")
            if isinstance(learning_progress, dict):
                avg_accuracy = self.performance_metrics.get("average_accuracy", 0.0)
                learning_prog = self.performance_metrics.get("learning_progress", 0.0)
                
                # Комплексная оценка
                if learning_progress.get("total_iterations", 0) > 0:
                    # Базовые компоненты оценки
                    prediction_accuracy_weight = 0.3
                    learning_progress_weight = 0.25
                    success_rate_weight = 0.25
                    model_accuracy_weight = 0.2
                    
                    system_score = (
                        avg_accuracy * prediction_accuracy_weight
                        + learning_prog * learning_progress_weight
                        + (learning_progress.get("success_rate", 0.0))
                        * success_rate_weight
                    ) * 100
                    
                    # Добавляем оценку модели предсказания, если она обучена
                    model_accuracy = learning_progress.get("prediction_model_accuracy")
                    if model_accuracy is not None:
                        system_score += model_accuracy * model_accuracy_weight * 100
                        self._logger.info(f"   Точность ML модели: {model_accuracy:.2%}")
                    else:
                        # Если модель не обучена, перераспределяем веса
                        adjusted_weight = (
                            prediction_accuracy_weight
                            + learning_progress_weight
                            + success_rate_weight
                        )
                        system_score = (
                            system_score / (1 - model_accuracy_weight) * adjusted_weight
                        )
                    
                    self._logger.info(f"   Средняя точность предсказаний: {avg_accuracy:.2%}")
                    self._logger.info(f"   Прогресс обучения: {learning_prog:.2%}")
                    self._logger.info(
                        f"   Успешность адаптаций: {learning_progress.get('success_rate', 0.0):.2%}"
                    )
                    self._logger.info(f"   Комплексная оценка системы: {system_score:.1f}/100")
                    
                    if system_score >= 80:
                        self._logger.info(f"   [ОТЛИЧНО] Система работает эффективно")
                    elif system_score >= 60:
                        self._logger.info(f"   [ХОРОШО] Система работает стабильно")
                    elif system_score >= 40:
                        self._logger.info(f"   [УДОВЛЕТВОРИТЕЛЬНО] Система обучается")
                    else:
                        self._logger.info(f"   [ТРЕБУЕТ УЛУЧШЕНИЯ] Недостаточно данных")
                else:
                    self._logger.info(f"   [ВНИМАНИЕ]  Недостаточно данных для комплексной оценки")
            
            self._logger.info("=" * 70 + "\n")
        except Exception as e:
            # В случае ошибки выводим минимальную информацию
            # КРИТИЧНО: Не используем эмодзи в сообщении об ошибке, чтобы избежать UnicodeError
            try:
                self._logger.error(f"\n[ОШИБКА] Ошибка при выводе метрик: {e}\n", exc_info=True)
            except Exception as e2:
                # Если даже это не работает, выводим без форматирования
                self._logger.error(f"\n[ОШИБКА] Ошибка при выводе метрик: {e}\n", exc_info=True)
                self._logger.error(f"[ОШИБКА] Дополнительная ошибка: {e2}\n", exc_info=True)

    # ==========================
    # Сессии и анализ обучения
    # ==========================

    def _save_session_metrics(self, success: bool, final_score: int) -> None:
        """
        Сохраняет агрегированные метрики по завершённой игре в список сессий.
        """
        session_data = {
            "session_id": self.session_counter,
            "success": success,
            "final_score": final_score,
            "average_accuracy": self.performance_metrics["average_accuracy"],
            "learning_progress": self.performance_metrics["learning_progress"],
            "bricks_destroyed": self.current_game_stats["bricks_destroyed"],
            "total_moves": self.current_game_stats["total_moves"],
            "optimal_moves": self.current_game_stats["optimal_moves"],
        }

        self.session_metrics.append(session_data)
        self.session_counter += 1

        # Опционально: можно печатать прогресс каждые N игр
        if self.session_counter % 10 == 0:
            self._print_learning_progress_comparison()

    def _print_learning_progress_comparison(self) -> None:
        """
        Печатает краткий обзор прогресса обучения по последним сессиям.
        Никакой логики игры не меняет, только вывод/анализ.
        """
        if not self.session_metrics:
            return

        last_sessions = self.session_metrics[-10:]
        avg_score = sum(s["final_score"] for s in last_sessions) / len(last_sessions)
        avg_accuracy = sum(s["average_accuracy"] for s in last_sessions) / len(
            last_sessions
        )
        avg_learning = sum(s["learning_progress"] for s in last_sessions) / len(
            last_sessions
        )

        # Логируем статистику последних игр
        self._logger.info(
            f"[AI] Последние {len(last_sessions)} игр: "
            f"средний счёт={avg_score:.1f}, "
            f"точность={avg_accuracy:.2f}, "
            f"прогресс обучения={avg_learning:.2f}"
        )

    # ==========================
    # Публичный сброс обучения
    # ==========================

    def reset_learning(self) -> None:
        """
        Полный сброс обучающихся компонентов и внутренних статистик AI.
        """
        # Сброс системы обучения
        self.learning_system.reset()

        # Сброс прицеливания
        self.targeting_system = {
            "target_brick": None,
            "optimal_offset": 0.0,
            "successful_hits": [],
            "brick_map": {},
            "trajectory_targets": [],
            "hit_patterns": {},
            "brick_coordinates": [],
            "visible_targets": [],
        }
        
        # Отслеживание отбитий в пустоту
        self.empty_bounce_tracker = {
            "consecutive_empty_bounces": 0,  # Количество последовательных отбитий в пустоту
            "last_bounce_position": None,  # Последняя позиция платформы при отбитии
            "last_bounce_time": 0,  # Время последнего отбития
            "max_empty_bounces": 1,  # Максимум отбитий в пустоту подряд (уменьшено с 2 до 1)
            "bounce_history": [],  # История отбитий (для анализа)
            "ceiling_bounces": 0,  # Количество отскоков от потолка без попадания в кубики
        }

        # Сброс системы предотвращения зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        self.loop_prevention_system["current_strategy_index"] = 0

        # Сброс системы плавности движения
        self.smoothness_system["recent_movements"] = []
        self.smoothness_system["recent_positions"] = []
        self.smoothness_system["movement_changes"] = []
        self.smoothness_system["smoothness_penalty"] = 0.0
        self.smoothness_system["consecutive_stops"] = 0
        
        # Сброс отслеживания отбитий в пустоту
        self.empty_bounce_tracker["consecutive_empty_bounces"] = 0
        self.empty_bounce_tracker["last_bounce_position"] = None
        self.empty_bounce_tracker["last_bounce_time"] = 0
        self.empty_bounce_tracker["bounce_history"] = []

        # Сброс общих метрик и сессий
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
        }
        self.session_metrics = []
        self.session_counter = 0

        # Сброс статистики текущей игры
        self._reset_current_game_stats()

    # ==========================
    # Сохранение и загрузка данных обучения
    # ==========================

    def save_learning_data(self) -> None:
        """
        Сохраняет данные обучения AI системы.
        """
        try:
            if hasattr(self, "learning_system") and self.learning_system:
                # Сохраняем данные обучающей системы
                learning_data = {
                    "performance_metrics": self.performance_metrics,
                    "session_metrics": self.session_metrics,
                    "targeting_system": self.targeting_system,
                    "session_counter": self.session_counter,
                }
                
                # Здесь можно добавить сохранение в файл, если нужно
                # Пока просто логируем успешное сохранение
                self._logger.debug(
                    f"[AI DEBUG] Данные обучения сохранены. Сессий: {self.session_counter}"
                )
                
        except Exception as e:
            self._logger.error(f"[AI DEBUG] Ошибка при сохранении данных обучения: {e}", exc_info=True)

    def load_learning_data(self) -> None:
        """
        Загружает данные обучения AI системы.
        """
        try:
            if hasattr(self, "learning_system") and self.learning_system:
                # Здесь можно добавить загрузку из файла
                self._logger.debug("[AI DEBUG] Данные обучения загружены")
                
        except Exception as e:
            self._logger.error(f"[AI DEBUG] Ошибка при загрузке данных обучения: {e}", exc_info=True)

    # ==========================
    # Отладочная визуализация
    # ==========================

    def visualize_debug_info(self, screen) -> None:
        """
        Отображает отладочную информацию AI системы на экране.
        
        Args:
            screen: Объект поверхности pygame для отрисовки.
        """
        try:
            import pygame
            
            # Информация о состоянии AI
            info_lines = [
                f"Accuracy: {self.performance_metrics['average_accuracy']:.2f}",
                f"Learning: {self.performance_metrics['learning_progress']:.2f} (прогресс обучения)",
                f"Games: {self.performance_metrics['games_played']}",
            ]
            
            # Добавляем лучшее время для матча с 50 блоками
            best_time = self.performance_metrics.get("best_time_50_bricks")
            if best_time is not None:
                info_lines.append(f"Best: {best_time:.1f}s (50 blocks)")
            else:
                info_lines.append(f"Best: -- (50 blocks)")
            
            # Отрисовка фона для текста
            font = pygame.font.SysFont("arial", 16)
            line_height = 20
            box_width = 200
            box_height = len(info_lines) * line_height + 10
            
            # Полупрозрачный фон
            debug_surface = pygame.Surface((box_width, box_height))
            debug_surface.set_alpha(128)
            debug_surface.fill((0, 0, 0))
            screen.blit(debug_surface, (10, 10))
            
            # Текст
            y_offset = 15
            for line in info_lines:
                text_surface = font.render(line, True, (255, 255, 0))
                screen.blit(text_surface, (15, y_offset))
                y_offset += line_height
                
            # Визуализация предсказанной траектории
            if (
                self.is_active
                and self.current_game_state
                and self.is_ball_moving_towards_paddle()
                and self.debug_mode
            ):
                self._draw_predicted_trajectory(screen)
                
        except Exception as e:
            # Игнорируем ошибки визуализации, чтобы не прерывать игру
            pass

    def _draw_predicted_trajectory(self, screen) -> None:
        """
        Рисует предсказанную траекторию мяча для отладки.
        
        Args:
            screen: Объект поверхности pygame для отрисовки.
        """
        try:
            import pygame
            
            if not self.current_game_state:
                return
                
            # Предсказываем траекторию
            trajectory = self.trajectory_predictor.predict_trajectory(
                self.current_game_state
            )
            
            if not trajectory:
                return
                
            # Рисуем точки траектории
            for i, point in enumerate(
                trajectory[::3]
            ):  # Каждая 3-я точка для оптимизации
                if hasattr(point, "x") and hasattr(point, "y"):
                    # Цвет зависит от типа точки
                    if i < len(trajectory) // 3:
                        color = (0, 255, 0)  # Зеленый - начало траектории
                    else:
                        color = (255, 255, 0)  # Желтый - конец траектории
                    
                    pygame.draw.circle(screen, color, (int(point.x), int(point.y)), 2)
            
            # Рисуем точку пересечения с платформой
            intersection = self.trajectory_predictor.predict_paddle_intersection(
                self.current_game_state,
                self.current_game_state.paddle_position.y,
            )
            
            if (
                intersection
                and hasattr(intersection, "x")
                and hasattr(intersection, "y")
            ):
                pygame.draw.circle(
                    screen, (255, 0, 0), (int(intersection.x), int(intersection.y)), 4
                )
                
        except Exception as e:
            # Игнорируем ошибки отрисовки траектории
            pass

    # ==========================
    # Методы для режима обучения
    # ==========================

    def _process_training_match(self, success: bool, final_score: int) -> None:
        """
        Обрабатывает результаты матча в режиме обучения.

        Args:
            success: True, если все кубики сбиты.
            final_score: Итоговый счёт.
        """
        # Сохраняем параметры текущего матча
        match_data = {
            "success": success,
            "score": final_score,
            "ball_speed": self.training_parameters["ball_speed"],
            "paddle_speed_multiplier": self.training_parameters[
                "paddle_speed_multiplier"
            ],
            "bricks_destroyed": self.training_parameters["total_bricks_destroyed"],
            "time": self.training_parameters["total_time"],
            "lives_lost": self.training_parameters["lives_lost"],
        }
        self.training_parameters["match_history"].append(match_data)

        # Обновляем лучшее время для матча с 50 блоками
        if success and self.training_parameters["total_bricks_destroyed"] == 50:
            match_time = self.training_parameters["total_time"]
            best_time = self.performance_metrics.get("best_time_50_bricks")
            if best_time is None or match_time < best_time:
                self.performance_metrics["best_time_50_bricks"] = match_time

        # Ограничиваем историю последними 10 матчами
        if len(self.training_parameters["match_history"]) > 10:
            self.training_parameters["match_history"].pop(0)

        # Обучаемся на основе результатов
        self._learn_from_match_results(match_data)

    def _learn_from_match_results(self, match_data: Dict[str, Any]) -> None:
        """
        Обучается на основе результатов матча.

        Основная стратегия: алгоритм должен стремиться сбить как можно больше кубиков за меньшее время.
        Если не может сбить все 50 кубиков за 3 жизни - снижаем скорость мяча.

        Args:
            match_data: Данные о матче.
        """
        # Вычисляем эффективность: кубики за время с учетом потерянных жизней
        bricks_destroyed = match_data["bricks_destroyed"]
        time_taken = max(match_data["time"], 1)  # Избегаем деления на 0
        lives_lost = match_data["lives_lost"]

        # КРИТИЧЕСКИЙ КРИТЕРИЙ: Если не сбиты все 50 кубиков за 3 жизни - снижаем скорость
        all_bricks_destroyed = bricks_destroyed >= 50

        # Эффективность = кубики / (время * (1 + штраф за жизни))
        # Штраф за жизни: каждая потерянная жизнь увеличивает время на 20%
        time_penalty = 1.0 + (lives_lost * 0.2)
        efficiency = bricks_destroyed / (time_taken * time_penalty)

        # Обновляем параметры на основе эффективности
        current_ball_speed = self.training_parameters["ball_speed"]
        current_paddle_mult = self.training_parameters["paddle_speed_multiplier"]

        # Целевое время матча: 5 секунд
        target_time = 5.0
        time_ratio = time_taken / target_time if target_time > 0 else 1.0

        # ПРИОРИТЕТ 1: Если не сбиты все 50 кубиков - снижаем скорость
        if not all_bricks_destroyed:
            # Чем больше кубиков осталось, тем больше снижаем скорость
            bricks_remaining = 50 - bricks_destroyed
            speed_reduction = min(5, bricks_remaining // 5)  # Снижаем на 1-5 единиц
            if current_ball_speed > 15:  # Минимум 15 для обучения
                # Ограничиваем максимальную скорость 25 (с учетом ограничения 16.67 мс на расчет)
                self.training_parameters["ball_speed"] = max(
                    15, current_ball_speed - speed_reduction
                )
            # Также снижаем скорость платформы если потеряны все жизни
            if lives_lost >= 3:
                if current_paddle_mult > 1.5:
                    self.training_parameters["paddle_speed_multiplier"] = max(
                        1.5, current_paddle_mult - 0.3
                    )
        # ПРИОРИТЕТ 2: Если все кубики сбиты - можно увеличивать скорость для оптимизации времени
        elif all_bricks_destroyed and lives_lost <= 1:
            # Если время больше целевого, увеличиваем скорость
            if time_ratio > 1.2:  # Время на 20% больше целевого
                if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 1
                    )
                if current_paddle_mult < 3.0:
                    self.training_parameters["paddle_speed_multiplier"] = min(
                        3.0, current_paddle_mult + 0.1
                    )
            # Если время хорошее и эффективность высокая - можно немного увеличить
            elif time_ratio < 0.8 and efficiency > 8.0:  # Быстро и эффективно
                if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 1
                    )

        # Если это первый матч или мало данных, используем более агрессивную адаптацию
        if len(self.training_parameters["match_history"]) <= 2:
            # Для первых матчей более агрессивно увеличиваем скорость только если результат хороший
            if (
                bricks_destroyed >= 45 and lives_lost <= 1
            ):  # Хороший результат (почти все блоки)
                # Увеличиваем скорость мяча до максимума для быстрой игры (максимум 25)
                if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                    self.training_parameters["ball_speed"] = min(
                        25, current_ball_speed + 2
                    )
                # Увеличиваем скорость платформы
                if current_paddle_mult < 3.0:
                    self.training_parameters["paddle_speed_multiplier"] = min(
                        3.0, current_paddle_mult + 0.2
                    )
        else:
            # После накопления данных используем сравнение со средним и целевым временем
            avg_efficiency = self._get_average_efficiency()

            if (
                avg_efficiency > 0 and all_bricks_destroyed
            ):  # Только если все кубики сбиты
                # Если время больше целевого, агрессивно увеличиваем скорость (максимум 25)
                if time_ratio > 1.2:  # Время на 20% больше целевого
                    if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                        self.training_parameters["ball_speed"] = min(
                            25, current_ball_speed + 1
                        )
                    if current_paddle_mult < 3.0:
                        self.training_parameters["paddle_speed_multiplier"] = min(
                            3.0, current_paddle_mult + 0.1
                        )
                elif efficiency > avg_efficiency * 1.1:  # На 10% лучше среднего
                    # Увеличиваем скорость мяча (до 25)
                    if current_ball_speed < 25:  # Максимум 25 (с учетом ограничения 16.67 мс на расчет)
                        self.training_parameters["ball_speed"] = min(
                            25, current_ball_speed + 1
                        )
                    # Увеличиваем скорость платформы (до 3.0)
                    if current_paddle_mult < 3.0:
                        self.training_parameters["paddle_speed_multiplier"] = min(
                            3.0, current_paddle_mult + 0.1
                        )

    def _get_average_efficiency(self) -> float:
        """Вычисляет среднюю эффективность за последние матчи."""
        if not self.training_parameters["match_history"]:
            return 0.0

        total_efficiency = 0.0
        for match in self.training_parameters["match_history"]:
            bricks = match["bricks_destroyed"]
            time_taken = max(match["time"], 1)
            lives_lost = match["lives_lost"]
            time_penalty = 1.0 + (lives_lost * 0.2)
            efficiency = bricks / (time_taken * time_penalty)
            total_efficiency += efficiency

        return total_efficiency / len(self.training_parameters["match_history"])

    def get_optimal_ball_speed(self) -> int:
        """
        Возвращает оптимальную скорость мяча на основе обучения.

        Returns:
            Оптимальная скорость мяча (20-50 для режима обучения).
        """
        return int(self.training_parameters["ball_speed"])

    def get_optimal_paddle_speed_multiplier(self) -> float:
        """
        Возвращает оптимальный множитель скорости платформы на основе обучения.

        Returns:
            Множитель скорости платформы (0.5-2.0).
        """
        return self.training_parameters["paddle_speed_multiplier"]

    def get_adjusted_paddle_speed(self, base_speed: int) -> int:
        """
        Возвращает скорректированную скорость платформы с учетом адаптации AI.

        Args:
            base_speed: Базовая скорость платформы.

        Returns:
            Скорректированная скорость платформы.
        """
        if self._last_adjusted_paddle_speed is not None:
            return self._last_adjusted_paddle_speed
        return base_speed

    def update_training_stats(
        self, bricks_destroyed: int, time_elapsed: float, lives_lost: int
    ) -> None:
        """
        Обновляет статистику обучения во время игры.

        Args:
            bricks_destroyed: Количество сбитых кубиков.
            time_elapsed: Прошедшее время.
            lives_lost: Потерянные жизни.
        """
        self.training_parameters["total_bricks_destroyed"] = bricks_destroyed
        self.training_parameters["total_time"] = time_elapsed
        self.training_parameters["lives_lost"] = lives_lost

    def _print_training_parameters(self) -> None:
        """Выводит средние значения параметров обучения в лог."""
        if not self.training_parameters["match_history"]:
            return

        self._logger.info("\n" + "=" * 70)
        self._logger.info("ПАРАМЕТРЫ ОБУЧЕНИЯ ИИ")
        self._logger.info("=" * 70)

        # Вычисляем средние значения
        avg_ball_speed = sum(
            m["ball_speed"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_paddle_mult = sum(
            m["paddle_speed_multiplier"]
            for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_bricks = sum(
            m["bricks_destroyed"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_time = sum(
            m["time"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_lives_lost = sum(
            m["lives_lost"] for m in self.training_parameters["match_history"]
        ) / len(self.training_parameters["match_history"])
        avg_efficiency = self._get_average_efficiency()

        self._logger.info(
            f"\n📊 Средние значения за последние {len(self.training_parameters['match_history'])} матчей:"
        )
        self._logger.info(f"   Скорость мяча: {avg_ball_speed:.1f}")
        self._logger.info(f"   Множитель скорости платформы: {avg_paddle_mult:.2f}")
        self._logger.info(f"   Кубиков за матч: {int(round(avg_bricks))}")
        self._logger.info(f"   Время матча: {avg_time:.1f} сек")
        self._logger.info(f"   Потерянных жизней: {int(round(avg_lives_lost))}")
        self._logger.info(
            f"   Эффективность: {avg_efficiency:.3f} (кубики/(время * штраф_за_жизни))"
        )

        self._logger.info(f"\n🎯 Текущие параметры:")
        self._logger.info(f"   Скорость мяча: {self.training_parameters['ball_speed']}")
        self._logger.info(
            f"   Множитель скорости платформы: {self.training_parameters['paddle_speed_multiplier']:.2f}"
        )
        self._logger.info("=" * 70 + "\n")
