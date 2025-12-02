"""
Основной класс AIPlayer для управления авторежимом игры Арканоид
"""

import pygame
import time
import math
from typing import List, Tuple, Optional, Dict, Any
from .game_state import GameState, Point
from .trajectory_predictor import TrajectoryPredictor
from .position_optimizer import PositionOptimizer
from .learning_system import LearningSystem
from .performance_logger import PerformanceLogger


class AIPlayer:
    """
    Основной класс AIPlayer для управления авторежимом

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
        Инициализация AIPlayer

        Args:
            screen_width: Ширина игрового экрана
            screen_height: Высота игрового экрана
            debug_mode: Режим отладки с визуализацией
        """
        # Инициализируем компоненты системы
        self.trajectory_predictor = TrajectoryPredictor(screen_width, screen_height)
        self.position_optimizer = PositionOptimizer(screen_width, screen_height)
        self.learning_system = LearningSystem()
        self.performance_logger = PerformanceLogger()

        # Параметры системы
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = debug_mode

        # Состояние AI
        self.current_game_state: Optional[GameState] = None
        self.last_paddle_position = None
        self.last_action_time = time.time()
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
        }

        # Статистика текущей игры
        self.current_game_stats = {
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
        self.targeting_system = {
            "target_brick": None,  # Целевой кубик
            "optimal_offset": 0.0,  # Оптимальное смещение на платформе (-1 до 1)
            "successful_hits": [],  # История удачных ударов
            "hit_patterns": {},  # Паттерны успешных ударов
        }

        # Система предотвращения зацикливания
        self.loop_prevention_system = {
            "movement_history": [],  # История последних движений
            "position_history": [],  # История позиций платформы
            "trajectory_history": [],  # История траекторий мяча
            "loop_detection_threshold": 5,  # Количество повторений для детекции зацикливания
            "strategy_change_cooldown": 0,  # Кулдаун смены стратегии
            "alternative_strategies": [
                "center_focus",
                "edge_focus",
                "predictive_targeting",
            ],  # Альтернативные стратегии
            "current_strategy_index": 0,  # Текущая альтернативная стратегия
        }

        # Параметры платформы для расчёта угла отскока
        self.paddle_width = 120  # Ширина платформы

    def update_game_state(
        self, ball, paddle, bricks, score: int, start_time: int
    ) -> None:
        """
        Обновляет состояние игры для AI системы

        Args:
            ball: Объект мяча из игры
            paddle: Объект платформы из игры
            bricks: Список оставшихся кубиков
            score: Текущий счет игрока
            start_time: Время начала игры (для расчета продолжительности)
        """
        # Создаем новое состояние игры
        self.current_game_state = GameState.create_from_game_objects(
            ball, paddle, bricks, score, start_time
        )

        # Инициализируем статистику игры если это новая игра
        if self.current_game_stats["start_time"] is None:
            self.current_game_stats["start_time"] = start_time
            self.performance_logger.log_game_start(self.current_game_state)

        # Логируем предсказание траектории если включен режим отладки
        if self.debug_mode and self.is_ball_moving_towards_paddle():
            predicted_trajectory = self.trajectory_predictor.predict_trajectory(
                self.current_game_state
            )
            self.performance_logger.log_trajectory_prediction(
                [{"x": p.x, "y": p.y} for p in predicted_trajectory]
            )

    def is_ball_moving_towards_paddle(self) -> bool:
        """Проверяет, движется ли мяч к платформе"""
        if not self.current_game_state:
            return False
        return self.current_game_state.is_ball_falling()

    def get_optimal_paddle_position(self) -> int:
        """
        Получает оптимальную позицию для платформы с прицельным отбиванием в кубики

        Returns:
            X-координата центра платформы
        """
        if not self.current_game_state or not self.is_active:
            return self.screen_width // 2  # Резервная позиция

        try:
            # Если мяч падает - рассчитываем прицельную позицию
            if self.is_ball_moving_towards_paddle():
                # Получаем точку приземления мяча
                landing_x = self._predict_exact_landing_position()

                # Находим лучший кубик для прицеливания
                target_brick = self._find_best_target_brick()

                if target_brick:
                    # Рассчитываем оптимальное смещение для попадания в кубик
                    optimal_offset = self._calculate_optimal_offset(
                        landing_x, target_brick
                    )

                    # Сохраняем информацию о прицеливании
                    self.targeting_system["target_brick"] = target_brick
                    self.targeting_system["optimal_offset"] = optimal_offset

                    # Рассчитываем позицию платформы с учётом смещения
                    # offset от -1 до 1, где 0 = центр платформы
                    paddle_half_width = self.paddle_width / 2
                    optimal_position = landing_x - (optimal_offset * paddle_half_width)

                    # Ограничиваем позицию границами экрана
                    optimal_position = max(
                        paddle_half_width,
                        min(self.screen_width - paddle_half_width, optimal_position),
                    )

                    return int(optimal_position)
                else:
                    # Нет кубиков - просто ловим мяч
                    return int(landing_x)
            else:
                # Мяч движется вверх - следим за ним
                return int(self._track_ball_position())

        except Exception as e:
            print(f"Ошибка при расчете оптимальной позиции: {e}")
            return int(self.current_game_state.ball_position.x)

    def _find_best_target_brick(self) -> Optional[Dict]:
        """
        Находит лучший кубик для прицеливания

        Приоритеты:
        1. Кубики в нижних рядах (ближе к платформе)
        2. Кубики ближе к текущей траектории мяча
        3. Кубики с успешной историей попаданий

        Returns:
            Словарь с информацией о кубике или None
        """
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        ball_x = self.current_game_state.ball_position.x
        paddle_y = self.current_game_state.paddle_position.y

        best_brick = None
        best_score = -float("inf")

        for brick in bricks:
            # Оценка кубика
            score = 0

            # Приоритет нижним кубикам (ближе к платформе = выше оценка)
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y
            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 1000  # Ближе = лучше

            # Приоритет кубикам ближе к траектории мяча
            brick_x = (
                getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
            )  # Центр кубика
            horizontal_distance = abs(brick_x - ball_x)
            score -= horizontal_distance * 0.5  # Ближе по горизонтали = лучше

            # Бонус за успешные попадания в этот кубик (из истории)
            brick_key = f"{int(brick_x/60)}_{int(brick_y/30)}"
            if brick_key in self.targeting_system["hit_patterns"]:
                pattern = self.targeting_system["hit_patterns"][brick_key]
                score += pattern.get("success_rate", 0) * 100

            if score > best_score:
                best_score = score
                best_brick = brick

        return best_brick

    def _calculate_optimal_offset(self, landing_x: float, target_brick: Dict) -> float:
        """
        Рассчитывает оптимальное смещение на платформе для попадания в кубик

        Args:
            landing_x: X-координата приземления мяча
            target_brick: Целевой кубик

        Returns:
            Смещение от -1 до 1 (где 0 = центр платформы)
        """
        # Центр целевого кубика
        brick_center_x = (
            getattr(target_brick, "x", 0) + getattr(target_brick, "width", 60) / 2
        )
        brick_center_y = (
            getattr(target_brick, "y", 0) + getattr(target_brick, "height", 20) / 2
        )

        # Позиция платформы
        paddle_y = self.current_game_state.paddle_position.y

        # Рассчитываем нужный угол отскока
        # Угол = arctan((brick_x - landing_x) / (paddle_y - brick_y))
        delta_x = brick_center_x - landing_x
        delta_y = paddle_y - brick_center_y

        if delta_y <= 0:
            return 0.0  # Кубик ниже платформы - невозможно

        # Нужный угол отскока (в радианах)
        target_angle = math.atan2(delta_x, delta_y)

        # Преобразуем угол в смещение на платформе
        # Угол отскока пропорционален смещению от центра
        # Максимальный угол ~45 градусов при смещении 1.0
        max_angle = math.pi / 4  # 45 градусов

        offset = target_angle / max_angle

        # Ограничиваем смещение
        offset = max(-1.0, min(1.0, offset))

        # Проверяем историю успешных ударов для корректировки
        offset = self._adjust_offset_from_history(offset, target_brick)

        return offset

    def _adjust_offset_from_history(self, offset: float, target_brick: Dict) -> float:
        """
        Корректирует смещение на основе истории успешных ударов

        Args:
            offset: Рассчитанное смещение
            target_brick: Целевой кубик

        Returns:
            Скорректированное смещение
        """
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_key = f"{int(brick_x/60)}_{int(brick_y/30)}"

        if brick_key in self.targeting_system["hit_patterns"]:
            pattern = self.targeting_system["hit_patterns"][brick_key]
            if pattern.get("successful_offsets"):
                # Усредняем с успешными смещениями
                avg_successful_offset = sum(pattern["successful_offsets"]) / len(
                    pattern["successful_offsets"]
                )
                # Смешиваем расчётное и историческое смещение
                offset = offset * 0.7 + avg_successful_offset * 0.3

        return offset

    def _detect_loop_pattern(self) -> bool:
        """
        Обнаруживает зацикливание в движениях платформы

        Returns:
            True если обнаружено зацикливание
        """
        history = self.loop_prevention_system["movement_history"]
        if len(history) < self.loop_prevention_system["loop_detection_threshold"]:
            return False

        # Проверяем последние движения на повторяющиеся паттерны
        recent_movements = history[
            -self.loop_prevention_system["loop_detection_threshold"] :
        ]

        # Считаем количество повторяющихся движений
        movement_counts = {}
        for movement in recent_movements:
            movement_counts[movement] = movement_counts.get(movement, 0) + 1

        # Если какое-то движение повторяется слишком часто - это зацикливание
        max_count = max(movement_counts.values())
        threshold = (
            self.loop_prevention_system["loop_detection_threshold"] * 0.6
        )  # 60% повторений

        if max_count >= threshold:
            return True

        return False

    def _change_strategy_if_looping(self) -> None:
        """Меняет стратегию при обнаружении зацикливания"""
        if not self._detect_loop_pattern():
            return

        # Уменьшаем кулдаун
        if self.loop_prevention_system["strategy_change_cooldown"] > 0:
            self.loop_prevention_system["strategy_change_cooldown"] -= 1
            return

        # Сменяем стратегию
        self.loop_prevention_system["current_strategy_index"] = (
            self.loop_prevention_system["current_strategy_index"] + 1
        ) % len(self.loop_prevention_system["alternative_strategies"])

        new_strategy = self.loop_prevention_system["alternative_strategies"][
            self.loop_prevention_system["current_strategy_index"]
        ]

        # Устанавливаем кулдаум на 10 кадров
        self.loop_prevention_system["strategy_change_cooldown"] = 10

        print(f"[AI] Зацикливание обнаружено! Смена стратегии на: {new_strategy}")

        # Очищаем историю для нового старта
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []

    def _apply_alternative_strategy(self, optimal_position: int) -> int:
        """
        Применяет альтернативную стратегию для предотвращения зацикливания

        Args:
            optimal_position: Базовая оптимальная позиция

        Returns:
            Скорректированная позиция
        """
        strategy_index = self.loop_prevention_system["current_strategy_index"]
        strategy = self.loop_prevention_system["alternative_strategies"][strategy_index]

        screen_center = self.screen_width // 2

        if strategy == "center_focus":
            # Фокусируемся на центре экрана
            return screen_center

        elif strategy == "edge_focus":
            # Фокусируемся на краях для смены паттерна
            current_pos = getattr(self.current_game_state, "paddle_position", None)
            if current_pos:
                # Если мы были слева, идем вправо и наоборот
                return self.screen_width - 50 if current_pos.x < screen_center else 50
            else:
                return 50  # По умолчанию левая сторона

        elif strategy == "predictive_targeting":
            # Более агрессивное прицеливание в дальние кубики
            target_brick = self._find_most_distant_brick()
            if target_brick:
                landing_x = self._predict_exact_landing_position()
                brick_center_x = (
                    getattr(target_brick, "x", 0)
                    + getattr(target_brick, "width", 60) / 2
                )
                # Смещаемся в сторону дальнего кубика
                offset_direction = 1 if brick_center_x > landing_x else -1
                return int(optimal_position + offset_direction * 30)

        return optimal_position

    def _find_most_distant_brick(self) -> Optional[Dict]:
        """Находит самый дальний кубик от платформы для смены паттерна"""
        if not self.current_game_state or not self.current_game_state.remaining_bricks:
            return None

        bricks = self.current_game_state.remaining_bricks
        paddle_y = self.current_game_state.paddle_position.y

        most_distant_brick = None
        max_distance = -1

        for brick in bricks:
            brick_y = getattr(brick, "y", 0)
            distance = abs(paddle_y - brick_y)
            if distance > max_distance:
                max_distance = distance
                most_distant_brick = brick

        return most_distant_brick

    def _update_loop_tracking(
        self, movement: int, current_x: int, optimal_x: int
    ) -> None:
        """Обновляет данные отслеживания зацикливания"""
        # Добавляем движение в историю
        self.loop_prevention_system["movement_history"].append(movement)
        if len(self.loop_prevention_system["movement_history"]) > 10:
            self.loop_prevention_system["movement_history"] = [-1]

        # Добавляем позицию в историю
        self.loop_prevention_system["position_history"].append(current_x)
        if len(self.loop_prevention_system["position_history"]) > 20:
            self.loop_prevention_system["position_history"] = (
                self.loop_prevention_system["position_history"][-10:]
            )

        # Добавляем информацию о траектории
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
        """Переоценивает ситуацию после отбития мяча"""
        if not self.current_game_state:
            return

        # Анализируем текущую ситуацию для поиска новых возможностей
        target_brick = self._find_best_target_brick()
        if target_brick:
            # Обновляем цель прицеливания
            self.targeting_system["target_brick"] = target_brick

            # Рассчитываем новые параметры отскока
            landing_x = self._predict_exact_landing_position()
            new_offset = self._calculate_optimal_offset(landing_x, target_brick)
            self.targeting_system["optimal_offset"] = new_offset

            print(
                f"[AI] Переоценка после отбития: новая цель и смещение {new_offset:.2f}"
            )

        # Очищаем историю зацикливания для нового цикла
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []

    def record_hit_result(
        self, brick_hit: Dict, paddle_offset: float, success: bool
    ) -> None:
        """
        Записывает результат удара для обучения

        Args:
            brick_hit: Информация о сбитом кубике
            paddle_offset: Смещение на платформе при ударе
            success: Был ли удар успешным
        """
        brick_x = getattr(brick_hit, "x", 0)
        brick_y = getattr(brick_hit, "y", 0)
        brick_key = f"{int(brick_x/60)}_{int(brick_y/30)}"

        if brick_key not in self.targeting_system["hit_patterns"]:
            self.targeting_system["hit_patterns"][brick_key] = {
                "total_attempts": 0,
                "successful_hits": 0,
                "success_rate": 0.0,
                "successful_offsets": [],
            }

        pattern = self.targeting_system["hit_patterns"][brick_key]
        pattern["total_attempts"] += 1

        if success:
            pattern["successful_hits"] += 1
            pattern["successful_offsets"].append(paddle_offset)

            # Ограничиваем размер списка
            if len(pattern["successful_offsets"]) > 20:
                pattern["successful_offsets"] = pattern["successful_offsets"][-10:]

        # Обновляем success_rate
        pattern["success_rate"] = pattern["successful_hits"] / pattern["total_attempts"]

        # Сохраняем в историю успешных ударов
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

            # Ограничиваем размер истории
            if len(self.targeting_system["successful_hits"]) > 100:
                self.targeting_system["successful_hits"] = self.targeting_system[
                    "successful_hits"
                ][-50:]

    def _predict_exact_landing_position(self) -> float:
        """Точное предсказание позиции приземления мяча на платформу"""
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y

        # Рассчитываем время до достижения платформы
        time_to_paddle = (paddle_y - ball_y) / vel_y

        if time_to_paddle <= 0:
            return ball_x

        # Предсказываем траекторию с учетом отскоков от стен
        predicted_x = ball_x + vel_x * time_to_paddle
        screen_width = self.screen_width
        ball_radius = 8

        # Моделируем отскоки от стен
        while predicted_x < ball_radius or predicted_x > screen_width - ball_radius:
            if predicted_x < ball_radius:
                predicted_x = 2 * ball_radius - predicted_x
            elif predicted_x > screen_width - ball_radius:
                predicted_x = 2 * (screen_width - ball_radius) - predicted_x

        return predicted_x

    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с упреждающим движением"""
        ball_x = self.current_game_state.ball_position.x
        vel_x = self.current_game_state.ball_velocity.x

        # Добавляем упреждающее движение
        prediction_time = 3  # Упреждение на 3 кадра
        predicted_x = ball_x + vel_x * prediction_time

        # Ограничиваем предсказание границами экрана
        screen_width = self.screen_width
        ball_radius = 8
        min_x = ball_radius
        max_x = screen_width - ball_radius

        return max(min_x, min(max_x, predicted_x))

    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции с предотвращением зацикливания

        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Скорость движения платформы

        Returns:
            Смещение платформы (-1, 0, 1)
        """
        if not self.current_game_state or not self.is_active:
            # Резервное движение: просто следует за мячом если AI не инициализирован
            return self._fallback_movement(current_x)

        try:
            optimal_x = self.get_optimal_paddle_position()

            # Проверяем зацикливание и применяем альтернативную стратегию если нужно
            self._change_strategy_if_looping()
            if self.loop_prevention_system["strategy_change_cooldown"] == 0:
                optimal_x = self._apply_alternative_strategy(optimal_x)

            # Улучшенная точность позиционирования
            precision_tolerance = (
                2  # Уменьшаем допуск для более точного позиционирования
            )
            distance_to_optimal = abs(optimal_x - current_x)

            if distance_to_optimal <= precision_tolerance:
                # Мы достаточно близко к оптимальной позиции
                movement = 0
            else:
                # Рассчитываем движение
                movement = self.position_optimizer.calculate_paddle_movement(
                    current_x, optimal_x, paddle_speed
                )

                # Если нет движения, но AI активен, попробуем резервное движение
                if movement == 0 and optimal_x != current_x:
                    movement = self._fallback_movement(current_x)

            # Обновляем отслеживание зацикливания
            self._update_loop_tracking(movement, current_x, optimal_x)

            # Логируем движение платформы
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

                # Обновляем статистику текущей игры
                self.current_game_stats["total_moves"] += 1
                if abs(optimal_x - current_x) < 10:  # Точное попадание
                    self.current_game_stats["optimal_moves"] += 1

            return movement

        except Exception as e:
            print(f"Ошибка при движении платформы: {e}")
            # Резервное движение при ошибках
            return self._fallback_movement(current_x)

    def _fallback_movement(self, current_x: int) -> int:
        """
        Резервное движение платформы - улучшенное следование за мячом

        Args:
            current_x: Текущая X-координата платформы

        Returns:
            Смещение платформы (-1, 0, 1)
        """
        if not self.current_game_state:
            return 0

        # Получаем данные о мяче
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y

        # Если мяч падает, предсказываем траекторию до платформы
        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y

            if time_to_paddle > 0:
                # Предсказываем точную позицию попадания
                predicted_x = ball_x + vel_x * time_to_paddle

                # Учитываем отскоки от стен
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
            # Мяч движется вверх, следим за ним напрямую
            # Добавляем упреждение на основе скорости
            prediction_factor = abs(vel_x) * 2

            if vel_x > 0:
                target_x = ball_x + prediction_factor
            elif vel_x < 0:
                target_x = ball_x - prediction_factor
            else:
                target_x = ball_x

        # Рассчитываем движение с высокой чувствительностью
        distance = target_x - current_x
        tolerance = 3  # Очень точный контроль

        if abs(distance) <= tolerance:
            return 0
        elif distance > 0:
            return 1
        else:
            return -1

    def _is_time_pressure(self) -> bool:
        """Определяет, есть ли временное давление (мало времени/жизней)"""
        if not self.current_game_state:
            return False

        # Проверяем время игры (больше 5 минут = давление)
        game_time = self.current_game_state.game_time
        if game_time > 300:  # 5 минут
            return True

        # Проверяем количество оставшихся кубиков (меньше 5 = давление)
        if len(self.current_game_state.remaining_bricks) <= 5:
            return True

        return False

    def _calculate_decision_confidence(self, target_position: int) -> float:
        """
        Рассчитывает уверенность в принятом решении

        Args:
            target_position: Целевая позиция

        Returns:
            Уровень уверенности (0.0 - 1.0)
        """
        if not self.current_game_state:
            return 0.5

        # Базовая уверенность
        confidence = 0.7

        # Корректируем на основе количества кубиков
        bricks_count = len(self.current_game_state.remaining_bricks)
        if bricks_count <= 5:  # Мало кубиков = больше важность
            confidence += 0.1
        elif bricks_count >= 20:  # Много кубиков = больше вариантов
            confidence -= 0.1

        # Корректируем на основе скорости мяча
        ball_speed = self.current_game_state.ball_speed
        if ball_speed >= 8:  # Высокая скорость = сложнее
            confidence -= 0.1
        elif ball_speed <= 3:  # Низкая скорость = проще
            confidence += 0.1

        return max(0.1, min(1.0, confidence))

    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучает AI систему на основе результата действия

        Args:
            action_result: Результат последнего действия
        """
        if not self.current_game_state:
            return

        # Добавляем контекст к результату
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

        # Записываем результат удара для системы прицеливания
        action_type = action_result.get("action_type", "")
        if action_type == "brick_hit":
            bricks_destroyed = action_result.get("bricks_destroyed", [])
            for brick in bricks_destroyed:
                # Рассчитываем смещение на платформе при ударе
                paddle_x = self.current_game_state.paddle_position.x
                ball_x = self.current_game_state.ball_position.x
                paddle_offset = (ball_x - paddle_x) / (self.paddle_width / 2)
                paddle_offset = max(-1.0, min(1.0, paddle_offset))

                # Записываем успешный удар
                self.record_hit_result(brick, paddle_offset, success=True)

        elif action_type == "paddle_bounce":
            # Записываем информацию об отскоке для анализа
            if self.targeting_system["target_brick"]:
                paddle_x = self.current_game_state.paddle_position.x
                ball_x = self.current_game_state.ball_position.x
                paddle_offset = (ball_x - paddle_x) / (self.paddle_width / 2)
                paddle_offset = max(-1.0, min(1.0, paddle_offset))

                # Сохраняем информацию о прицеливании для последующего анализа
                enhanced_result["targeting_info"] = {
                    "target_brick": self.targeting_system["target_brick"],
                    "optimal_offset": self.targeting_system["optimal_offset"],
                    "actual_offset": paddle_offset,
                }

                # Переоцениваем ситуацию после отбития
                self._reevaluate_after_bounce()

        # Обновляем систему обучения
        self.learning_system.update_strategy(enhanced_result)

        # Логируем результат
        self.performance_logger.log_action(enhanced_result)

        # Обновляем метрики производительности
        self._update_performance_metrics(action_result)

    def _get_current_trajectory_prediction(self) -> Optional[Dict]:
        """Получает текущее предсказание траектории"""
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            return None

        try:
            trajectory = self.trajectory_predictor.predict_trajectory(
                self.current_game_state
            )
            return {
                "predicted_points": [{"x": p.x, "y": p.y} for p in trajectory],
                "intersection_point": self.trajectory_predictor.predict_paddle_intersection(
                    self.current_game_state, self.current_game_state.paddle_position.y
                ),
            }
        except:
            return None

    def _update_performance_metrics(self, action_result: Dict[str, Any]) -> None:
        """Обновляет метрики производительности"""
        success = action_result.get("success", False)

        if success:
            self.current_game_stats["successful_predictions"] += 1
            if "bricks_destroyed" in action_result:
                self.current_game_stats["bricks_destroyed"] += len(
                    action_result["bricks_destroyed"]
                )

        self.current_game_stats["total_predictions"] += 1

        # Обновляем общую статистику
        if "final_score" in action_result:
            self.performance_metrics["total_score"] += action_result["final_score"]

    def on_game_end(self, success: bool, final_score: int) -> None:
        """
        Обрабатывает окончание игры

        Args:
            success: Успешное завершение игры (все кубики сбиты)
            final_score: Итоговый счет
        """
        self.performance_metrics["games_played"] += 1

        if success:
            self.performance_metrics["games_won"] += 1

        # Обновляем среднюю точность
        if self.current_game_stats["total_predictions"] > 0:
            accuracy = (
                self.current_game_stats["successful_predictions"]
                / self.current_game_stats["total_predictions"]
            )
            self.performance_metrics["average_accuracy"] = (
                self.performance_metrics["average_accuracy"] * 0.9
            ) + (accuracy * 0.1)

        # Получаем прогресс обучения
        learning_progress = self.learning_system.get_learning_progress()
        self.performance_metrics["learning_progress"] = learning_progress.get(
            "success_rate", 0.0
        )

        # Логируем окончание игры
        self.performance_logger.log_game_end(
            self.current_game_state, success, final_score
        )

        # Сохраняем метрики
        self.performance_logger.log_performance_metrics(self.performance_metrics)

        # Сбрасываем статистику текущей игры
        self.current_game_stats = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0,
        }

        # Сбрасываем систему предотвращения зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        self.loop_prevention_system["current_strategy_index"] = 0

    def activate(self) -> None:
        """Активирует AI систему"""
        self.is_active = True
        self.performance_logger.log_action(
            {"type": "ai_activated", "timestamp": time.time()}
        )

    def deactivate(self) -> None:
        """Деактивирует AI систему"""
        self.is_active = False
        self.performance_logger.log_action(
            {"type": "ai_deactivated", "timestamp": time.time()}
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """Возвращает отчет о производительности AI"""
        return {
            "performance_metrics": self.performance_metrics,
            "learning_progress": self.learning_system.get_learning_progress(),
            "session_report": self.performance_logger.generate_performance_report(),
            "recent_trends": self.performance_logger.analyze_trends(),
        }

    def visualize_debug_info(self, screen: pygame.Surface) -> None:
        """
        Отображает отладочную информацию на экране

        Args:
            screen: Surface для отрисовки
        """
        if not self.debug_mode or not self.current_game_state:
            return

        try:
            # Рисуем предсказанную траекторию
            if self.is_ball_moving_towards_paddle():
                trajectory = self.trajectory_predictor.predict_trajectory(
                    self.current_game_state
                )
                self.trajectory_predictor.visualize_trajectory(
                    screen, trajectory, (255, 255, 0)
                )

            # Отображаем оптимальную позицию
            optimal_x = self.get_optimal_paddle_position()
            pygame.draw.line(
                screen, (0, 255, 0), (optimal_x, 0), (optimal_x, self.screen_height), 2
            )

            # Показываем информацию об AI
            font = pygame.font.SysFont("arial", 16)
            info_text = f"AI: {len(self.current_game_state.remaining_bricks)} кубиков"
            text_surface = font.render(info_text, True, (255, 255, 0))
            screen.blit(text_surface, (10, 10))

            # Показываем статус системы предотвращения зацикливания
            loop_status = (
                f"Loop: {len(self.loop_prevention_system['movement_history'])}/5"
            )
            status_surface = font.render(loop_status, True, (255, 100, 100))
            screen.blit(status_surface, (10, 30))

            # Показываем текущую стратегию
            strategy = self.loop_prevention_system["alternative_strategies"][
                self.loop_prevention_system["current_strategy_index"]
            ]
            strategy_text = f"Strat: {strategy}"
            strategy_surface = font.render(strategy_text, True, (100, 255, 100))
            screen.blit(strategy_surface, (10, 50))

        except Exception as e:
            print(f"Ошибка при визуализации: {e}")

    def save_learning_data(self) -> None:
        """Сохраняет данные обучения"""
        self.learning_system.save_model()
        self.performance_logger.save_session_log()

    def reset_learning(self) -> None:
        """Сбрасывает данные обучения"""
        self.learning_system.reset_learning_data()
        self.performance_logger.clear_session_data()

        # Сбрасываем метрики
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0,
        }

        # Сбрасываем систему предотвращения зацикливания
        self.loop_prevention_system["movement_history"] = []
        self.loop_prevention_system["position_history"] = []
        self.loop_prevention_system["trajectory_history"] = []
        self.loop_prevention_system["strategy_change_cooldown"] = 0
        self.loop_prevention_system["current_strategy_index"] = 0

        # Сбрасываем систему прицеливания
        self.targeting_system = {
            "target_brick": None,
            "optimal_offset": 0.0,
            "successful_hits": [],
            "hit_patterns": {},
        }
