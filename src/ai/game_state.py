"""
Модуль для хранения состояния игры для AI системы
"""

import pygame
from dataclasses import dataclass
from typing import List, Tuple, Optional
import time


@dataclass
class Point:
    """Простая структура для координат точки"""

    x: float
    y: float

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)

    def distance_to(self, other) -> float:
        """Вычисляет расстояние до другой точки"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class GameState:
    """Класс для хранения состояния игры"""

    # Позиции объектов
    ball_position: Point
    ball_velocity: Point
    paddle_position: Point
    paddle_width: int

    # Игровое состояние
    remaining_bricks: List[pygame.Rect]
    game_score: int
    game_time: int

    # Дополнительная информация
    ball_speed: int
    last_action_result: Optional[dict] = None
    predicted_trajectory: Optional[List[Point]] = None
    optimal_paddle_position: Optional[int] = None

    @classmethod
    def create_from_game_objects(
        cls, ball, paddle, bricks, score: int, start_time: int
    ) -> "GameState":
        """Создает состояние игры на основе объектов pygame"""
        ball_point = Point(ball.rect.centerx, ball.rect.centery)
        ball_vel = Point(ball.vel_x, ball.vel_y)
        paddle_point = Point(paddle.rect.centerx, paddle.rect.centery)

        return cls(
            ball_position=ball_point,
            ball_velocity=ball_vel,
            paddle_position=paddle_point,
            paddle_width=paddle.rect.width,
            remaining_bricks=bricks.copy(),
            game_score=score,
            game_time=int(time.time()) - start_time,
            ball_speed=ball.get_speed(),
        )

    def is_ball_falling(self) -> bool:
        """Проверяет, падает ли мяч вниз"""
        return self.ball_velocity.y > 0

    def get_ball_trajectory_direction(self) -> str:
        """Определяет направление траектории мяча"""
        if abs(self.ball_velocity.x) < 1:
            return "vertical"
        elif self.ball_velocity.x > 0:
            return "right"
        else:
            return "left"

    def get_nearest_bricks(self, count: int = 5) -> List[Tuple[pygame.Rect, float]]:
        """Возвращает ближайшие к мячу кубики с расстояниями"""
        distances = []
        for brick in self.remaining_bricks:
            brick_center = Point(brick.centerx, brick.centery)
            distance = self.ball_position.distance_to(brick_center)
            distances.append((brick, distance))

        # Сортируем по расстоянию и возвращаем нужное количество
        distances.sort(key=lambda x: x[1])
        return distances[:count]

    def get_bricks_in_trajectory(self) -> List[pygame.Rect]:
        """Возвращает кубики, которые находятся на траектории мяча"""
        bricks_in_path = []

        # Простое определение траектории - проверяем пересечение с прямоугольниками
        for brick in self.remaining_bricks:
            if self._will_ball_hit_brick(brick):
                bricks_in_path.append(brick)

        return bricks_in_path

    def _will_ball_hit_brick(self, brick: pygame.Rect) -> bool:
        """Простое определение того, попадет ли мяч в кубик"""
        # Упрощенная проверка - если кубик находится в направлении движения мяча
        ball_dir_x = 1 if self.ball_velocity.x > 0 else -1
        ball_dir_y = 1 if self.ball_velocity.y > 0 else -1

        # Проверяем, находится ли кубик в направлении движения
        brick_center = Point(brick.centerx, brick.centery)

        # Если мяч движется вправо, кубик должен быть правее мяча
        if ball_dir_x > 0 and brick_center.x <= self.ball_position.x:
            return False
        # Если мяч движется влево, кубик должен быть левее мяча
        if ball_dir_x < 0 and brick_center.x >= self.ball_position.x:
            return False

        # Если мяч движется вниз, кубик должен быть ниже мяча
        if ball_dir_y > 0 and brick_center.y <= self.ball_position.y:
            return False
        # Если мяч движется вверх, кубик должен быть выше мяча
        if ball_dir_y < 0 and brick_center.y >= self.ball_position.y:
            return False

        return True

    def get_paddle_intersection_point(self, paddle_y: float) -> Optional[Point]:
        """Вычисляет точку пересечения траектории мяча с платформой"""
        if self.ball_velocity.y <= 0:  # Мяч не падает
            return None

        # Рассчитываем время до достижения платформы
        time_to_paddle = (paddle_y - self.ball_position.y) / self.ball_velocity.y

        if time_to_paddle <= 0:
            return None

        # Рассчитываем x-координату в точке пересечения
        x_intersection = self.ball_position.x + self.ball_velocity.x * time_to_paddle

        return Point(x_intersection, paddle_y)

    def update_from_result(self, action_result: dict):
        """Обновляет состояние на основе результата действия"""
        self.last_action_result = action_result

        if action_result.get("success", False):
            # Увеличиваем счет при успехе
            self.game_score += 1

        # Удаляем сбитые кубики
        if "hit_bricks" in action_result:
            hit_bricks = action_result["hit_bricks"]
            self.remaining_bricks = [
                b for b in self.remaining_bricks if b not in hit_bricks
            ]

    def clone(self) -> "GameState":
        """Создает копию состояния"""
        return GameState(
            ball_position=Point(self.ball_position.x, self.ball_position.y),
            ball_velocity=Point(self.ball_velocity.x, self.ball_velocity.y),
            paddle_position=Point(self.paddle_position.x, self.paddle_position.y),
            paddle_width=self.paddle_width,
            remaining_bricks=[pygame.Rect(b) for b in self.remaining_bricks],
            game_score=self.game_score,
            game_time=self.game_time,
            ball_speed=self.ball_speed,
            last_action_result=self.last_action_result,
            predicted_trajectory=(
                self.predicted_trajectory.copy() if self.predicted_trajectory else None
            ),
            optimal_paddle_position=self.optimal_paddle_position,
        )
