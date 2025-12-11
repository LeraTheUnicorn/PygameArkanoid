"""
Модуль для выбора целевых кирпичей.

Содержит класс TargetSelector для выбора оптимальных целей для прицеливания.
"""

import math
from typing import List, Optional, Any

from ..game_state import GameState, Point
from ..trajectory_predictor import TrajectoryPredictor
from ..config import AIConfig


class TargetSelector:
    """Класс для выбора целевых кирпичей для прицеливания."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        config: AIConfig,
        trajectory_predictor: TrajectoryPredictor,
        targeting_system: Any,  # TargetingSystem dataclass
    ):
        """
        Инициализация TargetSelector.

        Args:
            screen_width: Ширина экрана
            screen_height: Высота экрана
            config: Конфигурация AI
            trajectory_predictor: Предиктор траектории
            targeting_system: Система прицеливания (dataclass)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.config = config
        self.trajectory_predictor = trajectory_predictor
        self.targeting_system = targeting_system

    def find_best_target_brick(
        self, game_state: GameState, paddle_y: float, ball_x: float
    ) -> Optional[Any]:
        """
        Находит лучший кубик для прицеливания с учётом видимости, позиции платформы и траектории.

        Приоритеты:
        1. На поздних этапах (<= 15 блоков) - максимизация разрушений в следующем цикле.
        2. Кубики, видимые для текущей траектории.
        3. Кубики в нижних рядах (ближе к платформе).
        4. Кубики ближе к центру экрана (стабильнее).
        5. Кубики с хорошей историей попаданий.

        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы
            ball_x: X-координата мяча

        Returns:
            Лучший целевой кирпич или None
        """
        if not game_state or not game_state.remaining_bricks:
            return None

        bricks_count = len(game_state.remaining_bricks)

        # На поздних этапах используем стратегию максимизации разрушений
        if bricks_count <= 15:
            return self.find_optimal_angle_for_max_destruction(game_state, paddle_y, ball_x)

        visible_targets = self.targeting_system.visible_targets

        # 1. Сначала рассматриваем только видимые цели
        if visible_targets:
            best_visible_brick = None
            best_visible_score = -float("inf")

            # Получаем историю последних выбранных целей для проверки симметрии
            recent_targets = self.targeting_system.recent_target_positions
            screen_center = self.screen_width // 2

            for target in visible_targets:
                brick = target["brick"]
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
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
                if recent_targets:
                    for prev_target_x in recent_targets[-3:]:
                        symmetry_distance = abs(
                            abs(brick_center_x - screen_center)
                            - abs(prev_target_x - screen_center)
                        )
                        if symmetry_distance < 20:
                            score -= 300.0

                        if (
                            abs(brick_center_x - screen_center) < 30
                            and abs(prev_target_x - screen_center) < 30
                            and (brick_center_x - screen_center)
                            * (prev_target_x - screen_center)
                            < 0
                        ):
                            score -= 400.0

                # Бонус за успешную историю попаданий
                brick_key = target["key"]
                if brick_key in self.targeting_system.hit_patterns:
                    pattern = self.targeting_system.hit_patterns[brick_key]
                    score += pattern.get("success_rate", 0.0) * 200.0

                if score > best_visible_score:
                    best_visible_score = score
                    best_visible_brick = brick

            if best_visible_brick:
                # Сохраняем позицию выбранной цели
                selected_brick_x = (
                    getattr(best_visible_brick, "x", 0)
                    + getattr(best_visible_brick, "width", self.config.brick.default_width) / 2
                )
                if not self.targeting_system.recent_target_positions:
                    self.targeting_system.recent_target_positions = []
                self.targeting_system.recent_target_positions.append(selected_brick_x)
                if len(self.targeting_system.recent_target_positions) > self.config.recent_targets_max:
                    self.targeting_system.recent_target_positions = (
                        self.targeting_system.recent_target_positions[-self.config.recent_targets_max:]
                    )
                return best_visible_brick

        # 2. Резервная логика, если нет видимых целей
        bricks = game_state.remaining_bricks
        ball_y = game_state.ball_position.y

        # Если кубиков мало — отдельная логика
        if len(bricks) <= 5:
            return self.find_best_target_for_few_bricks(bricks, paddle_y, ball_x, game_state)

        # Проверяем, отбивается ли мяч от потолка
        is_ceiling_bounce = ball_y < 100 and game_state.ball_velocity.y > 0

        best_brick = None
        best_score = -float("inf")

        recent_targets = self.targeting_system.recent_target_positions
        screen_center = self.screen_width // 2

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 1000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            # Проверка на симметричные паттерны
            if recent_targets:
                for prev_target_x in recent_targets[-3:]:
                    symmetry_distance = abs(
                        abs(brick_center_x - screen_center)
                        - abs(prev_target_x - screen_center)
                    )
                    if symmetry_distance < 20:
                        score -= 200.0

                    if (
                        abs(brick_center_x - screen_center) < 30
                        and abs(prev_target_x - screen_center) < 30
                        and (brick_center_x - screen_center)
                        * (prev_target_x - screen_center)
                        < 0
                    ):
                        score -= 300.0

            if is_ceiling_bounce:
                center_distance = abs(brick_center_x - screen_center)
                score -= center_distance * 0.3
                edge_distance = min(brick_center_x, self.screen_width - brick_center_x)
                score += edge_distance * 0.2
            else:
                horizontal_distance = abs(brick_center_x - ball_x)
                score -= horizontal_distance * 0.5

            # Бонус за историю попаданий
            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system.hit_patterns:
                pattern = self.targeting_system.hit_patterns[brick_key]
                score += pattern.get("success_rate", 0.0) * 100.0

            if score > best_score:
                best_score = score
                best_brick = brick

        if best_brick:
            # Сохраняем позицию выбранной цели
            selected_brick_x = (
                getattr(best_brick, "x", 0) + getattr(best_brick, "width", 60) / 2
            )
            if not self.targeting_system.recent_target_positions:
                self.targeting_system.recent_target_positions = []
            self.targeting_system.recent_target_positions.append(selected_brick_x)
            if len(self.targeting_system.recent_target_positions) > self.config.recent_targets_max:
                self.targeting_system.recent_target_positions = (
                    self.targeting_system.recent_target_positions[-self.config.recent_targets_max:]
                )

        return best_brick

    def find_optimal_angle_for_max_destruction(
        self, game_state: GameState, paddle_y: float, ball_x: float
    ) -> Optional[Any]:
        """
        Находит оптимальный угол удара для максимизации количества разрушенных блоков
        в следующем цикле отскоков. Используется на поздних этапах игры (<= 15 блоков).

        Args:
            game_state: Текущее состояние игры
            paddle_y: Y-координата платформы
            ball_x: X-координата мяча

        Returns:
            Целевой кубик, который приведет к максимальному количеству разрушений.
        """
        if not game_state or not game_state.remaining_bricks:
            return None

        # Предсказываем точку приземления
        landing_x = self._predict_exact_landing_position(game_state)
        paddle_center = game_state.paddle_position.x
        paddle_half_width = self.config.paddle.width / 2

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
                game_state, paddle_y
            )

            if intersection_point is None:
                continue

            # Симулируем траекторию после отскока
            after_bounce_trajectory = (
                self.trajectory_predictor.predict_after_bounce_trajectory(
                    game_state, intersection_point, bounce_x
                )
            )

            # Подсчитываем количество блоков, которые будут разрушены
            destruction_count = self.count_bricks_in_trajectory(
                after_bounce_trajectory, game_state.remaining_bricks
            )

            # Если это лучший результат, сохраняем
            if destruction_count > best_destruction_count:
                best_destruction_count = destruction_count
                best_offset = offset

                # Находим первый блок, который будет разрушен
                first_hit_brick = self.find_first_brick_in_trajectory(
                    after_bounce_trajectory, game_state.remaining_bricks
                )
                if first_hit_brick:
                    best_target_brick = first_hit_brick

        # Если нашли оптимальный угол, возвращаем соответствующий целевой блок
        if best_target_brick:
            return best_target_brick

        # Fallback: используем стандартную логику для малого количества блоков
        return self.find_best_target_for_few_bricks(
            game_state.remaining_bricks,
            paddle_y,
            ball_x,
            game_state,
        )

    def count_bricks_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> int:
        """
        Подсчитывает количество блоков, которые будут разрушены траекторией.

        Args:
            trajectory: Траектория мяча после отскока
            bricks: Список оставшихся блоков

        Returns:
            Количество блоков, которые будут разрушены
        """
        if not trajectory or not bricks:
            return 0

        destroyed_bricks = set()
        ball_radius = self.config.ball.radius

        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue

            for brick in bricks:
                brick_id = id(brick)
                if brick_id in destroyed_bricks:
                    continue

                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)

                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height

                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )

                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )

                    if center_in_brick or distance_to_brick <= ball_radius:
                        destroyed_bricks.add(brick_id)

        return len(destroyed_bricks)

    def find_first_brick_in_trajectory(
        self, trajectory: List[Point], bricks: List[Any]
    ) -> Optional[Any]:
        """
        Находит первый блок, который будет разрушен траекторией.

        Args:
            trajectory: Траектория мяча после отскока
            bricks: Список оставшихся блоков

        Returns:
            Первый блок, который будет разрушен, или None
        """
        if not trajectory or not bricks:
            return None

        ball_radius = self.config.ball.radius
        min_distance = float("inf")
        first_brick = None

        for point in trajectory:
            if not hasattr(point, "x") or not hasattr(point, "y"):
                continue

            for brick in bricks:
                brick_x = getattr(brick, "x", 0)
                brick_y = getattr(brick, "y", 0)
                brick_width = getattr(brick, "width", self.config.brick.default_width)
                brick_height = getattr(brick, "height", 20)

                brick_left = brick_x
                brick_right = brick_x + brick_width
                brick_top = brick_y
                brick_bottom = brick_y + brick_height

                if (
                    brick_left - ball_radius <= point.x <= brick_right + ball_radius
                    and brick_top - ball_radius <= point.y <= brick_bottom + ball_radius
                ):
                    center_in_brick = (
                        brick_left <= point.x <= brick_right
                        and brick_top <= point.y <= brick_bottom
                    )

                    closest_x = max(brick_left, min(point.x, brick_right))
                    closest_y = max(brick_top, min(point.y, brick_bottom))
                    distance_to_brick = math.sqrt(
                        (point.x - closest_x) ** 2 + (point.y - closest_y) ** 2
                    )

                    if center_in_brick or distance_to_brick <= ball_radius:
                        distance = math.sqrt(
                            (point.x - trajectory[0].x) ** 2
                            + (point.y - trajectory[0].y) ** 2
                        )

                        if distance < min_distance:
                            min_distance = distance
                            first_brick = brick
                            break

        return first_brick

    def find_best_target_for_few_bricks(
        self,
        bricks: List[Any],
        paddle_y: float,
        ball_x: float,
        game_state: GameState,
    ) -> Optional[Any]:
        """
        Специальная логика выбора цели для малого количества оставшихся кубиков.

        Args:
            bricks: Список оставшихся кирпичей
            paddle_y: Y-координата платформы
            ball_x: X-координата мяча
            game_state: Текущее состояние игры

        Returns:
            Лучший целевой кирпич или None
        """
        if not bricks:
            return None

        # КРИТИЧНО: Для 1 кирпича - используем улучшенную логику
        if len(bricks) == 1:
            brick = bricks[0]
            return brick

        # Для 2-3 кубиков — самый нижний, но с учетом траектории
        if len(bricks) <= 3:
            bottom_brick = min(bricks, key=lambda b: getattr(b, "y", 0))

            ball_y = game_state.ball_position.y if game_state else 0
            vel_x = (
                game_state.ball_velocity.x
                if (game_state and hasattr(game_state, "ball_velocity"))
                else 0
            )

            for brick in bricks:
                brick_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2
                brick_y = getattr(brick, "y", 0)

                if abs(brick_x - ball_x) < 150 and brick_y <= getattr(bottom_brick, "y", 0) + 30:
                    if (vel_x > 0 and brick_x > ball_x) or (vel_x < 0 and brick_x < ball_x):
                        return brick

            return bottom_brick

        # Для 4–5 — более сложная оценка
        best_brick = None
        best_score = -float("inf")

        for brick in bricks:
            score = 0.0
            brick_y = getattr(brick, "y", 0)
            distance_to_paddle = paddle_y - brick_y

            if distance_to_paddle > 0:
                score += (1.0 / distance_to_paddle) * 2000.0

            brick_center_x = getattr(brick, "x", 0) + getattr(brick, "width", 60) / 2

            center_distance = abs(brick_center_x - self.screen_width // 2)
            score -= center_distance * 0.3

            horizontal_distance = abs(brick_center_x - ball_x)
            score -= horizontal_distance * 0.2

            brick_key = f"{int(brick_center_x / 60)}_{int(brick_y / 30)}"
            if brick_key in self.targeting_system.hit_patterns:
                pattern = self.targeting_system.hit_patterns[brick_key]
                score += pattern.get("success_rate", 0.0) * 300.0

            if score > best_score:
                best_score = score
                best_brick = brick

        return best_brick

    def _predict_exact_landing_position(self, game_state: GameState) -> float:
        """
        Предсказывает точную X-координату приземления мяча.

        Args:
            game_state: Текущее состояние игры

        Returns:
            X-координата приземления
        """
        if not game_state:
            return self.screen_width // 2

        ball_x = game_state.ball_position.x
        ball_y = game_state.ball_position.y
        vel_x = game_state.ball_velocity.x
        vel_y = game_state.ball_velocity.y
        paddle_y = game_state.paddle_position.y

        if vel_y <= 0:
            return ball_x

        time_to_paddle = (paddle_y - ball_y) / vel_y if vel_y > 0 else 0
        if time_to_paddle <= 0:
            return ball_x

        predicted_x = ball_x + vel_x * time_to_paddle

        # Учитываем отскоки от стен
        ball_radius = self.config.ball.radius
        while predicted_x < ball_radius or predicted_x > self.screen_width - ball_radius:
            if predicted_x < ball_radius:
                predicted_x = 2 * ball_radius - predicted_x
                vel_x = abs(vel_x)
            elif predicted_x > self.screen_width - ball_radius:
                predicted_x = 2 * (self.screen_width - ball_radius) - predicted_x
                vel_x = -abs(vel_x)

        return predicted_x
