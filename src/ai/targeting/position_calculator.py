"""
Модуль для расчета позиций платформы для прицеливания.

Содержит класс PositionCalculator для расчета оптимальных позиций платформы.
"""

import math
from typing import List, Optional, Any

from ..game_state import GameState, Point
from ..trajectory_predictor import TrajectoryPredictor
from ..config import AIConfig


class PositionCalculator:
    """Класс для расчета позиций платформы для прицеливания."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        paddle_width: int,
        config: AIConfig,
        trajectory_predictor: TrajectoryPredictor,
        targeting_system: Any,  # TargetingSystem dataclass
    ):
        """
        Инициализация PositionCalculator.

        Args:
            screen_width: Ширина экрана
            screen_height: Высота экрана
            paddle_width: Ширина платформы
            config: Конфигурация AI
            trajectory_predictor: Предиктор траектории
            targeting_system: Система прицеливания (dataclass)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.paddle_width = paddle_width
        self.config = config
        self.trajectory_predictor = trajectory_predictor
        self.targeting_system = targeting_system

    def _ensure_safe_paddle_position(
        self, paddle_center_x: float, landing_x: float, paddle_half_width: float
    ) -> float:
        """
        Обеспечивает безопасную позицию платформы, предотвращая попадание мяча в углы.
        
        Если предсказанная точка приземления (landing_x) слишком близко к краю платформы,
        смещает позицию платформы так, чтобы мяч попадал в безопасную зону (минимум 25px от края).
        
        Args:
            paddle_center_x: Текущая позиция центра платформы
            landing_x: Предсказанная X-координата приземления мяча
            paddle_half_width: Половина ширины платформы
            
        Returns:
            Скорректированная позиция центра платформы
        """
        ball_radius = 8  # Радиус мяча
        safe_edge_distance = 25  # Минимальное расстояние от края платформы до точки попадания мяча
        
        # Вычисляем края платформы при текущей позиции
        paddle_left_edge = paddle_center_x - paddle_half_width
        paddle_right_edge = paddle_center_x + paddle_half_width
        
        # Вычисляем расстояние от точки приземления до краев платформы
        distance_to_left_edge = landing_x - paddle_left_edge
        distance_to_right_edge = paddle_right_edge - landing_x
        
        # Если мяч попадает слишком близко к левому краю
        if distance_to_left_edge < safe_edge_distance:
            # Смещаем платформу вправо, чтобы мяч попадал в безопасную зону
            adjustment = safe_edge_distance - distance_to_left_edge
            paddle_center_x += adjustment
        
        # Если мяч попадает слишком близко к правому краю
        elif distance_to_right_edge < safe_edge_distance:
            # Смещаем платформу влево, чтобы мяч попадал в безопасную зону
            adjustment = safe_edge_distance - distance_to_right_edge
            paddle_center_x -= adjustment
        
        # Ограничиваем границами экрана
        safe_margin = 30
        min_position = paddle_half_width + safe_margin
        max_position = self.screen_width - paddle_half_width - safe_margin
        paddle_center_x = max(min_position, min(max_position, paddle_center_x))
        
        return paddle_center_x

    def calculate_optimal_offset(
        self, landing_x: float, target_brick: Any, game_state: GameState
    ) -> float:
        """
        Рассчитывает оптимальное смещение на платформе для попадания в кубик.

        Args:
            landing_x: X-координата приземления мяча
            target_brick: Целевой кубик
            game_state: Текущее состояние игры

        Returns:
            Смещение от -1.0 до 1.0 (0 — центр платформы)
        """
        if not target_brick or not game_state:
            return 0.0

        bricks_count = len(game_state.remaining_bricks)

        # КРИТИЧНО: При 1 кирпиче - используем максимально агрессивные углы
        if bricks_count == 1:
            brick_center_x = getattr(target_brick, "x", 0) + getattr(target_brick, "width", 60) / 2
            brick_y = getattr(target_brick, "y", 0)

            ball_y = game_state.ball_position.y
            paddle_y = game_state.paddle_position.y

            distance_to_brick = brick_y - paddle_y
            horizontal_offset_needed = brick_center_x - landing_x

            paddle_half_width = self.paddle_width / 2
            max_offset = 1.5

            if abs(horizontal_offset_needed) > paddle_half_width * max_offset:
                offset = max_offset if horizontal_offset_needed > 0 else -max_offset
            else:
                offset = horizontal_offset_needed / (paddle_half_width * max_offset) * max_offset

            vel_x = game_state.ball_velocity.x if hasattr(game_state, "ball_velocity") else 0
            if abs(vel_x) > 0.1:
                prediction_adjustment = (vel_x / abs(vel_x)) * 0.2
                offset += prediction_adjustment

            offset = max(-max_offset, min(max_offset, offset))
            return offset

        # Точные координаты кубика
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_width = getattr(target_brick, "width", 60)
        brick_height = getattr(target_brick, "height", 20)

        brick_center_x = brick_x + brick_width / 2
        brick_center_y = brick_y + brick_height / 2

        brick_left = brick_x
        brick_right = brick_x + brick_width
        brick_top = brick_y
        brick_bottom = brick_y + brick_height

        paddle_y = game_state.paddle_position.y
        ball_x = game_state.ball_position.x
        ball_vel_x = game_state.ball_velocity.x

        # Рассчитываем оптимальную точку попадания в кубик
        if abs(ball_vel_x) > 0:
            if ball_vel_x > 0 and ball_x < brick_center_x:
                target_x = brick_center_x + min(brick_width * 0.15, 10)
            elif ball_vel_x < 0 and ball_x > brick_center_x:
                target_x = brick_center_x - min(brick_width * 0.15, 10)
            else:
                target_x = brick_center_x
        else:
            target_x = brick_center_x

        target_x = max(brick_left, min(brick_right, target_x))

        delta_x = target_x - landing_x
        delta_y = paddle_y - brick_center_y

        if delta_y <= 0:
            return 0.0

        target_angle = math.atan2(delta_x, delta_y)
        max_angle = math.pi / 4
        offset = target_angle / max_angle
        offset = max(-1.0, min(1.0, offset))

        # Проверка на симметричные паттерны
        if abs(offset) < 0.1:
            if delta_x > 0:
                offset = 0.25
            else:
                offset = -0.25
        elif abs(delta_x) < 10:
            if delta_x > 0:
                offset = max(0.2, offset)
            else:
                offset = min(-0.2, offset)

        # Уточняем по истории успешных ударов
        offset = self.adjust_offset_from_history(offset, target_brick)
        return offset

    def adjust_offset_from_history(self, offset: float, target_brick: Any) -> float:
        """
        Корректирует смещение на основе истории успешных ударов по данному кубику.

        Args:
            offset: Текущее смещение
            target_brick: Целевой кубик

        Returns:
            Скорректированное смещение
        """
        brick_x = getattr(target_brick, "x", 0)
        brick_y = getattr(target_brick, "y", 0)
        brick_key = f"{int(brick_x / 60)}_{int(brick_y / 30)}"

        pattern = self.targeting_system.hit_patterns.get(brick_key)
        if not pattern:
            return offset

        successful_offsets = pattern.get("successful_offsets", [])
        if not successful_offsets:
            return offset

        avg_successful_offset = sum(successful_offsets) / len(successful_offsets)
        return offset * 0.7 + avg_successful_offset * 0.3

    def calculate_precise_position_for_few_bricks(
        self, landing_x: float, game_state: GameState
    ) -> Optional[float]:
        """
        Вычисляет точную позицию платформы для попадания в оставшиеся блоки (1-10 блоков).

        Args:
            landing_x: X-координата приземления мяча
            game_state: Текущее состояние игры

        Returns:
            Оптимальная X-координата центра платформы или None
        """
        if not game_state or not game_state.remaining_bricks:
            return None

        bricks = game_state.remaining_bricks
        bricks_count = len(bricks)

        if bricks_count > 10:
            return None

        is_critical = bricks_count == 1
        paddle_y = game_state.paddle_position.y
        paddle_half_width = self.paddle_width / 2

        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            game_state, paddle_y
        )

        if intersection_point is None:
            return None

        best_position = None
        best_score = -float("inf")

        # Для каждого блока рассчитываем точную позицию платформы для попадания
        for brick in bricks:
            brick_x = getattr(brick, "x", 0)
            brick_y = getattr(brick, "y", 0)
            brick_width = getattr(brick, "width", self.config.brick.default_width)
            brick_height = getattr(brick, "height", 20)
            brick_center_x = brick_x + brick_width / 2
            brick_center_y = brick_y + brick_height / 2

            dx = brick_center_x - intersection_point.x
            dy = brick_center_y - paddle_y

            if dy <= 0:
                continue

            target_angle = math.atan2(dx, dy)
            max_angle = math.atan2(paddle_half_width, 50)
            normalized_angle = max(-max_angle, min(max_angle, target_angle))
            required_offset = normalized_angle / max_angle if max_angle > 0 else 0

            bounce_x = intersection_point.x - (required_offset * paddle_half_width)
            paddle_position = bounce_x

            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            paddle_position = max(min_position, min(max_position, paddle_position))

            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    game_state, intersection_point, bounce_x
                )
            )

            will_hit = False
            hit_confidence = 0.0

            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue

                ball_radius = self.config.ball.radius
                if (
                    brick_x - brick_width/2 - ball_radius <= point.x <= brick_x + brick_width/2 + ball_radius
                    and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                ):
                    will_hit = True
                    center_x = brick_x + brick_width / 2
                    center_y = brick_y + brick_height / 2
                    distance_to_center = math.sqrt(
                        (point.x - center_x) ** 2 + (point.y - center_y) ** 2
                    )
                    max_distance = math.sqrt((brick_width / 2 + ball_radius) ** 2 + (brick_height / 2 + ball_radius) ** 2)
                    hit_confidence = max(hit_confidence, 1.0 - (distance_to_center / max_distance))
                    break

            if is_critical and not will_hit:
                min_distance_to_brick = float('inf')
                for point in after_bounce_trajectory:
                    if not hasattr(point, "x") or not hasattr(point, "y"):
                        continue
                    closest_x = max(brick_x, min(point.x, brick_x + brick_width))
                    closest_y = max(brick_y, min(point.y, brick_y + brick_height))
                    distance = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )
                    min_distance_to_brick = min(min_distance_to_brick, distance)

                if min_distance_to_brick <= 30:
                    will_hit = True
                    hit_confidence = max(0.3, 1.0 - (min_distance_to_brick / 30.0))

            if will_hit:
                distance_to_paddle = paddle_y - brick_y
                score = 10000.0 / max(distance_to_paddle, 1)

                if brick_y > 200:
                    score += 5000.0

                center_distance = abs(brick_center_x - self.screen_width // 2)
                score -= center_distance * 0.1

                if is_critical:
                    score += hit_confidence * 50000.0
                    if hit_confidence > 0.2:
                        score += 100000.0

                if score > best_score:
                    best_score = score
                    best_position = paddle_position

        # Если не нашли точное попадание, используем более агрессивный расчет
        if best_position is None and bricks:
            for brick in bricks:
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)
                brick_center_x = brick_x + brick_width / 2

                for test_offset in [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
                    test_bounce_x = intersection_point.x - (test_offset * paddle_half_width)
                    test_paddle_position = test_bounce_x

                    min_position = paddle_half_width
                    max_position = self.screen_width - paddle_half_width
                    test_paddle_position = max(
                        min_position, min(max_position, test_paddle_position)
                    )

                    test_trajectory = (
                        self.trajectory_predictor.predict_after_bounce_trajectory(
                            game_state, intersection_point, test_bounce_x
                        )
                    )

                    for point in test_trajectory:
                        if not hasattr(point, "x") or not hasattr(point, "y"):
                            continue

                        ball_radius = self.config.ball.radius
                        if (
                            brick_x - ball_radius
                            <= point.x
                            <= brick_x + brick_width + ball_radius
                            and brick_y - ball_radius
                            <= point.y
                            <= brick_y + brick_height + ball_radius
                        ):
                            best_position = test_paddle_position
                            break

                    if best_position is not None:
                        break

                if best_position is not None:
                    break

            # Если все еще не нашли, используем упрощенный расчет
            if best_position is None:
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

                if is_critical:
                    for test_offset_multiplier in [1.0, 1.2, 1.5, 2.0]:
                        dx = brick_center_x - landing_x
                        required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * test_offset_multiplier)))
                        test_position = landing_x - (required_offset * paddle_half_width)

                        min_position = paddle_half_width
                        max_position = self.screen_width - paddle_half_width
                        test_position = max(min_position, min(max_position, test_position))

                        if abs(test_position - landing_x) < self.screen_width:
                            best_position = test_position
                            break
                else:
                    dx = brick_center_x - landing_x
                    required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
                    best_position = landing_x - (required_offset * paddle_half_width)

                min_position = paddle_half_width
                max_position = self.screen_width - paddle_half_width
                if best_position is not None:
                    best_position = max(min_position, min(max_position, best_position))

        # Если все еще не нашли позицию при малом количестве блоков
        if best_position is None and bricks_count <= 10 and bricks:
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

            dx = brick_center_x - landing_x
            required_offset = max(-1.0, min(1.0, dx / (paddle_half_width * 1.5)))
            best_position = landing_x - (required_offset * paddle_half_width)

            min_position = paddle_half_width
            max_position = self.screen_width - paddle_half_width
            best_position = max(min_position, min(max_position, best_position))
            # КРИТИЧНО: Применяем защиту от попадания в углы платформы
            best_position = self._ensure_safe_paddle_position(best_position, landing_x, paddle_half_width)

        # КРИТИЧНО: Применяем защиту от попадания в углы платформы перед возвратом
        if best_position is not None:
            best_position = self._ensure_safe_paddle_position(best_position, landing_x, paddle_half_width)
        
        return best_position

    def calculate_position_with_target_brick(
        self,
        landing_x: float,
        target_brick: Any,
        game_state: GameState,
        zones: dict,
    ) -> Optional[float]:
        """
        Рассчитывает позицию с учетом целевого кирпича.

        Args:
            landing_x: X-координата приземления мяча
            target_brick: Целевой кирпич
            game_state: Текущее состояние игры
            zones: Словарь с границами зон

        Returns:
            Оптимальная позиция платформы или None
        """
        if not target_brick:
            return None

        optimal_offset = self.calculate_optimal_offset(landing_x, target_brick, game_state)
        self.targeting_system.target_brick = target_brick
        self.targeting_system.optimal_offset = optimal_offset

        paddle_half_width = self.paddle_width / 2
        optimal_position = landing_x - (optimal_offset * paddle_half_width)

        safe_margin = 30
        min_position = paddle_half_width + safe_margin
        max_position = self.screen_width - paddle_half_width - safe_margin
        optimal_position = max(min_position, min(max_position, optimal_position))

        paddle_left_edge = optimal_position - paddle_half_width
        paddle_right_edge = optimal_position + paddle_half_width
        if paddle_left_edge < safe_margin:
            optimal_position = safe_margin + paddle_half_width
        elif paddle_right_edge > self.screen_width - safe_margin:
            optimal_position = self.screen_width - safe_margin - paddle_half_width

        # КРИТИЧНО: Применяем защиту от попадания в углы платформы
        optimal_position = self._ensure_safe_paddle_position(optimal_position, landing_x, paddle_half_width)
        
        return optimal_position

    def calculate_position_for_max_destruction(
        self, landing_x: float, game_state: GameState
    ) -> Optional[float]:
        """
        Вычисляет оптимальную позицию платформы для максимизации разрушений в следующем цикле.

        Args:
            landing_x: X-координата приземления мяча
            game_state: Текущее состояние игры

        Returns:
            Оптимальная X-координата центра платформы или None
        """
        if not game_state:
            return None

        paddle_y = game_state.paddle_position.y
        paddle_center = game_state.paddle_position.x
        paddle_half_width = self.paddle_width / 2

        test_offsets = [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0]
        best_offset = 0.0
        best_destruction_count = 0

        intersection_point = self.trajectory_predictor.predict_paddle_intersection(
            game_state, paddle_y
        )

        if intersection_point is None:
            return None

        for offset in test_offsets:
            bounce_x = landing_x - (offset * paddle_half_width)

            min_bounce_x = paddle_center - paddle_half_width
            max_bounce_x = paddle_center + paddle_half_width
            bounce_x = max(min_bounce_x, min(max_bounce_x, bounce_x))

            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    game_state, intersection_point, bounce_x
                )
            )

            # Подсчитываем количество блоков, которые будут разрушены
            # Используем упрощенный подсчет для производительности
            destruction_count = 0
            ball_radius = self.config.ball.radius
            hit_bricks = set()

            for point in after_bounce_trajectory:
                if not hasattr(point, "x") or not hasattr(point, "y"):
                    continue

                for brick in game_state.remaining_bricks:
                    brick_id = id(brick)
                    if brick_id in hit_bricks:
                        continue

                    brick_x = getattr(brick, "x", 0)
                    brick_y = getattr(brick, "y", 0)
                    brick_width = getattr(brick, "width", self.config.brick.default_width)
                    brick_height = getattr(brick, "height", 20)

                    if (
                        brick_x - ball_radius <= point.x <= brick_x + brick_width + ball_radius
                        and brick_y - ball_radius <= point.y <= brick_y + brick_height + ball_radius
                    ):
                        hit_bricks.add(brick_id)
                        destruction_count += 1

            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset

        optimal_position = landing_x - (best_offset * paddle_half_width)

        min_position = paddle_half_width
        max_position = self.screen_width - paddle_half_width
        optimal_position = max(min_position, min(max_position, optimal_position))
        
        # КРИТИЧНО: Применяем защиту от попадания в углы платформы
        optimal_position = self._ensure_safe_paddle_position(optimal_position, landing_x, paddle_half_width)

        return optimal_position
