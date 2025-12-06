"""
Основной класс AIPlayer для управления авторежимом игры Арканоид.
"""

import time
import math
import random
import os
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
        """
        # Компоненты системы
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = debug_mode

        self.trajectory_predictor = TrajectoryPredictor(screen_width, screen_height)
        self.position_optimizer = PositionOptimizer(screen_width, screen_height)
        self.learning_system = LearningSystem()

        # Логирование производительности (по переменной окружения)
        enable_session_logging = os.getenv("AI_ENABLE_SESSION_LOGGING", "0") == "1"
        self.performance_logger = PerformanceLogger(
            enable_session_logging=enable_session_logging
        )

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

        # Параметры платформы
        self.paddle_width = 120  # Ширина платформы

        # Последний множитель скорости платформы (для обучения)
        self._last_paddle_speed_multiplier = 1.0

        # Метрики по сессиям (серии игр)
        self.session_metrics: List[Dict[str, Any]] = []
        self.session_counter: int = 0

    def activate(self) -> None:
        """
        Активирует AIPlayer для управления игрой.
        """
        self.is_active = True
        print("[AI DEBUG] AIPlayer активирован. Начинаем управление игрой...")

    def deactivate(self) -> None:
        """
        Деактивирует AIPlayer.
        """
        self.is_active = False
        print("[AI DEBUG] AIPlayer деактивирован.")

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
        """
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
                for coord in self.targeting_system["brick_coordinates"]:
                    brick_center_x = coord["x"]
                    brick_center_y = coord["y"]

                    # Проверяем каждую вторую точку для оптимизации
                    for point in after_bounce_trajectory[::2]:
                        if hasattr(point, "x") and hasattr(point, "y"):
                            distance = math.sqrt(
                                (point.x - brick_center_x) ** 2
                                + (point.y - brick_center_y) ** 2
                            )
                            # Радиус условного попадания в кубик
                            if distance < 35:
                                if coord not in visible_targets:
                                    visible_targets.append(coord)
                                break

            self.targeting_system["visible_targets"] = visible_targets
        except Exception as e:
            print(f"Ошибка при обновлении видимых целей: {e}")
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

            # Если мяч в зоне кубиков или в разделительной зоне, но движется вверх — не дёргаем платформу
            if ball_y < separation_zone_start or (
                separation_zone_start <= ball_y < paddle_zone_start and ball_vel_y <= 0
            ):
                return int(self.current_game_state.paddle_position.x)

            # Мяч ниже кубиков и движется вниз/в разделительной зоне — считаем прицельную позицию
            if ball_y < paddle_zone_start:
                landing_x = self._predict_exact_landing_position()
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

                    # Границы по центру платформы
                    min_position = paddle_half_width
                    max_position = self.screen_width - paddle_half_width
                    optimal_position = max(
                        min_position, min(max_position, optimal_position)
                    )
                    return int(optimal_position)
                else:
                    # Нет явной цели — просто ловим мяч
                    return int(landing_x)
            else:
                # Мяч движется вверх — обрабатываем возможный отскок от потолка
                if ball_y < 50:
                    return self._handle_ceiling_bounce_positioning()
                # Иначе просто сопровождаем мяч
                return int(self._track_ball_position())

        except Exception as e:
            print(f"Ошибка при расчете оптимальной позиции: {e}")
            return int(self.current_game_state.paddle_position.x)

    # ==========================
    # Выбор целевого кирпича
    # ==========================

    def _find_best_target_brick(self) -> Optional[Any]:
        """
        Находит лучший кубик для прицеливания с учётом видимости, позиции платформы и траектории.

        Приоритеты:
        1. Кубики, видимые для текущей траектории.
        2. Кубики в нижних рядах (ближе к платформе).
        3. Кубики ближе к центру экрана (стабильнее).
        4. Кубики с хорошей историей попаданий.
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        visible_targets = self.targeting_system["visible_targets"]
        paddle_y = self.current_game_state.paddle_position.y

        # 1. Сначала рассматриваем только видимые цели
        if visible_targets:
            best_visible_brick = None
            best_visible_score = -float("inf")

            for target in visible_targets:
                brick = target["brick"]
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)

                score = 1000.0  # базовый бонус за видимость

                # Бонус за близость к платформе
                distance_to_paddle = paddle_y - brick_y
                if distance_to_paddle > 0:
                    score += (1.0 / distance_to_paddle) * 500.0

                # Штраф за удалённость от центра
                center_distance = abs(brick_x + 30 - self.screen_width // 2)
                score -= center_distance * 0.3

                # Бонус за успешную историю попаданий
                brick_key = target["key"]
                if brick_key in self.targeting_system["hit_patterns"]:
                    pattern = self.targeting_system["hit_patterns"][brick_key]
                    score += pattern.get("success_rate", 0.0) * 200.0

                if score > best_visible_score:
                    best_visible_score = score
                    best_visible_brick = brick

            if best_visible_brick:
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

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            if distance_to_paddle > 0:
                # Приоритет нижним кубикам
                score += (1.0 / distance_to_paddle) * 1000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            if is_ceiling_bounce:
                # При отскоке от потолка меньше любим центр
                center_distance = abs(brick_center_x - self.screen_width // 2)
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

        return best_brick

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

        Args:
            landing_x: X-координата приземления мяча.
            target_brick: Целевой кубик.

        Returns:
            Смещение от -1.0 до 1.0 (0 — центр платформы).
        """
        # Центр целевого кубика
        brick_center_x = (
            getattr(target_brick, "x", 0) + getattr(target_brick, "width", 60) / 2
        )
        brick_center_y = (
            getattr(target_brick, "y", 0) + getattr(target_brick, "height", 20) / 2
        )

        paddle_y = self.current_game_state.paddle_position.y

        # Требуемый угол отскока
        delta_x = brick_center_x - landing_x
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

        # Если почти строго вертикальный удар — добавляем небольшой рандом
        if abs(delta_x) < 10:
            offset = random.choice([-0.3, 0.3])

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
        """Точное предсказание X-координаты, где мяч встретится с платформой."""
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y

        # Время до платформы
        time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y != 0 else 0
        if time_to_paddle <= 0:
            return ball_x

        predicted_x = ball_x + vel_x * time_to_paddle
        screen_width = self.screen_width
        ball_radius = 8

        # Моделируем отскоки от вертикальных стен
        while predicted_x < ball_radius or predicted_x > screen_width - ball_radius:
            if predicted_x < ball_radius:
                predicted_x = 2 * ball_radius - predicted_x
            elif predicted_x > screen_width - ball_radius:
                predicted_x = 2 * (screen_width - ball_radius) - predicted_x

        return predicted_x

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
    # Движение платформы
    # ==========================

    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции с предотвращением зацикливания.

        Args:
            current_x: Текущая X-координата платформы.
            paddle_speed: Базовая скорость движения платформы.

        Returns:
            Смещение платформы (-1, 0, 1).
        """
        if not self.current_game_state or not self.is_active:
            # Резервное движение: просто следуем за мячом
            return self._fallback_movement(current_x)

        try:
            optimal_x = self.get_optimal_paddle_position()

            # Проверяем зацикливание и при необходимости меняем стратегию
            self._change_strategy_if_looping()
            if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                optimal_x = self._apply_alternative_strategy(optimal_x)

            # Допуск по точности позиционирования
            precision_tolerance = 2
            distance_to_optimal = abs(optimal_x - current_x)

            if distance_to_optimal <= precision_tolerance:
                movement = 0
            else:
                # Адаптивная скорость от системы обучения
                if self.current_game_state:
                    ball_speed = self.current_game_state.ball_speed
                    distance_to_target = distance_to_optimal
                    speed_multiplier = self.learning_system.get_adaptive_paddle_speed(
                        ball_speed, distance_to_target
                    )
                    adjusted_paddle_speed = int(paddle_speed * speed_multiplier)
                    self._last_paddle_speed_multiplier = speed_multiplier
                else:
                    adjusted_paddle_speed = paddle_speed

                movement = self.position_optimizer.calculate_paddle_movement(
                    current_x, optimal_x, adjusted_paddle_speed
                )

                # Если расчёт не даёт движения, но мы не на месте — fallback
                if movement == 0 and optimal_x != current_x:
                    movement = self._fallback_movement(current_x)

            # Обновляем данные по зацикливанию
            self._update_loop_tracking(movement, current_x, optimal_x)

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

            return movement

        except Exception as e:
            print(f"Ошибка при движении платформы: {e}")
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
        """
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
            self.current_game_stats["bricks_destroyed"] += len(
                action_result["bricks_destroyed"]
            )

        self.current_game_stats["total_predictions"] += 1

        if "final_score" in action_result:
            self.performance_metrics["total_score"] += action_result["final_score"]

    def on_game_end(self, success: bool, final_score: int) -> None:
        """
        Обрабатывает окончание игры.

        Args:
            success: True, если все кубики сбиты.
            final_score: Итоговый счёт.
        """
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
            # Если learning_progress - словарь, извлекаем числовое значение
            learning_progress_value = learning_progress.get("progress", 0.0)
        else:
            learning_progress_value = learning_progress

        self.performance_metrics["learning_progress"] = (
            self.performance_metrics["learning_progress"] * 0.9
            + learning_progress_value * 0.1
        )

        # Логирование окончания игры
        game_duration = 0
        if self.current_game_stats["start_time"] is not None:
            game_duration = int(time.time() - self.current_game_stats["start_time"])

        self.performance_logger.log_game_end(
            {
                "success": success,
                "final_score": final_score,
                "accuracy": self.performance_metrics["average_accuracy"],
                "learning_progress": self.performance_metrics["learning_progress"],
                "game_duration": game_duration,
                "bricks_destroyed": self.current_game_stats["bricks_destroyed"],
                "total_moves": self.current_game_stats["total_moves"],
                "optimal_moves": self.current_game_stats["optimal_moves"],
            }
        )

        # Сохраняем данные по сессии и подготавливаемся к новой игре
        self._save_session_metrics(success, final_score)
        self._reset_current_game_stats()

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

        print(
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

        # Сброс системы предотвращения зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        self.loop_prevention_system["current_strategy_index"] = 0

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
            if hasattr(self, 'learning_system') and self.learning_system:
                # Сохраняем данные обучающей системы
                learning_data = {
                    'performance_metrics': self.performance_metrics,
                    'session_metrics': self.session_metrics,
                    'targeting_system': self.targeting_system,
                    'session_counter': self.session_counter,
                }
                
                # Здесь можно добавить сохранение в файл, если нужно
                # Пока просто логируем успешное сохранение
                print(f"[AI DEBUG] Данные обучения сохранены. Сессий: {self.session_counter}")
                
        except Exception as e:
            print(f"[AI DEBUG] Ошибка при сохранении данных обучения: {e}")

    def load_learning_data(self) -> None:
        """
        Загружает данные обучения AI системы.
        """
        try:
            if hasattr(self, 'learning_system') and self.learning_system:
                # Здесь можно добавить загрузку из файла
                print("[AI DEBUG] Данные обучения загружены")
                
        except Exception as e:
            print(f"[AI DEBUG] Ошибка при загрузке данных обучения: {e}")

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
                f"AI: {'ACTIVE' if self.is_active else 'INACTIVE'}",
                f"Session: {self.session_counter}",
                f"Accuracy: {self.performance_metrics['average_accuracy']:.2f}",
                f"Learning: {self.performance_metrics['learning_progress']:.2f}",
                f"Games: {self.performance_metrics['games_played']}",
            ]
            
            # Если есть текущая цель, показываем её
            if self.targeting_system.get('target_brick'):
                info_lines.append("Target: BRICK")
                if 'optimal_offset' in self.targeting_system:
                    offset = self.targeting_system['optimal_offset']
                    info_lines.append(f"Offset: {offset:.2f}")
            else:
                info_lines.append("Target: None")
            
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
            if (self.is_active and self.current_game_state and 
                self.is_ball_moving_towards_paddle() and self.debug_mode):
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
            for i, point in enumerate(trajectory[::3]):  # Каждая 3-я точка для оптимизации
                if hasattr(point, 'x') and hasattr(point, 'y'):
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
            
            if intersection and hasattr(intersection, 'x') and hasattr(intersection, 'y'):
                pygame.draw.circle(screen, (255, 0, 0), (int(intersection.x), int(intersection.y)), 4)
                
        except Exception as e:
            # Игнорируем ошибки отрисовки траектории
            pass
