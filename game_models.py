"""
Модели данных для игры Арканоид.

Содержит классы Ball, Paddle и GameState, которые представляют
игровые объекты и состояние игры.
"""

import random
from dataclasses import dataclass, field
from typing import List, Optional

import pygame

from game_config import (
    BALL_SIZE,
    BALL_SPEED_DEFAULT,
    PADDLE_HEIGHT,
    PADDLE_SPEED,
    PADDLE_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from settings import SettingsManager


@dataclass
class Paddle:
    """Модель платформы (ракетки) игрока."""

    rect: pygame.Rect = field(
        default_factory=lambda: pygame.Rect(
            (SCREEN_WIDTH - PADDLE_WIDTH) // 2,
            SCREEN_HEIGHT - 60,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        )
    )

    def move(self, direction: int) -> None:
        """
        Перемещает платформу в указанном направлении.
        
        Args:
            direction: -1 (влево) или 1 (вправо)
        """
        self.rect.x += direction * PADDLE_SPEED
        paddle_half_width: int = PADDLE_WIDTH // 2
        min_center_x: int = paddle_half_width
        max_center_x: int = SCREEN_WIDTH - paddle_half_width
        self.rect.centerx = max(min_center_x, min(max_center_x, self.rect.centerx))


@dataclass
class Ball:
    """Модель мяча с интегрированным управлением скоростью."""

    rect: pygame.Rect = field(
        default_factory=lambda: pygame.Rect(
            (SCREEN_WIDTH - BALL_SIZE) // 2,
            SCREEN_HEIGHT // 2,
            BALL_SIZE,
            BALL_SIZE,
        )
    )
    vel_x: int = field(
        default_factory=lambda: random.choice([-BALL_SPEED_DEFAULT, BALL_SPEED_DEFAULT])
    )
    vel_y: int = field(default_factory=lambda: -BALL_SPEED_DEFAULT)
    current_speed: int = field(default_factory=lambda: BALL_SPEED_DEFAULT)
    _last_vel_x: int = field(default=0)
    _just_bounced: bool = field(default=False)
    _bounce_frame: int = field(default=0)
    _wall_bounce_count: int = field(default=0)

    def update(self) -> None:
        """Обновляет позицию мяча и обрабатывает столкновения со стенами."""
        ball_radius: int = BALL_SIZE // 2
        min_center_x: int = ball_radius
        max_center_x: int = SCREEN_WIDTH - ball_radius
        min_center_y: int = ball_radius

        new_center_x: int = self.rect.centerx + self.vel_x
        new_center_y: int = self.rect.centery + self.vel_y

        # Проверяем столкновение со стенами по горизонтали
        if new_center_x < min_center_x:
            new_center_x = min_center_x
            self.vel_x *= -1
        elif new_center_x > max_center_x:
            new_center_x = max_center_x
            self.vel_x *= -1

        self.rect.centerx = new_center_x

        # Проверяем столкновение с потолком
        if new_center_y < min_center_y:
            new_center_y = min_center_y
            self.vel_y *= -1
            self._wall_bounce_count = 0
        else:
            self.rect.centery = new_center_y

        # Защита от зацикливания у стен
        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self._wall_bounce_count += 1

            if self._wall_bounce_count > 10:
                self.vel_y += random.choice([-1, 0, 1])
                self._wall_bounce_count = 0

    def bounce_vertical(self) -> None:
        """Отражает мяч по вертикали."""
        if self.vel_y == 0:
            self.vel_y = -self.current_speed
        else:
            self.vel_y *= -1

    def reset(self, paddle_rect: pygame.Rect) -> None:
        """Сбрасывает мяч на платформу с текущей скоростью."""
        ball_radius: int = BALL_SIZE // 2
        self.rect.centerx = paddle_rect.centerx
        self.rect.centery = paddle_rect.top - ball_radius - 5
        self.vel_x = random.choice([-self.current_speed, self.current_speed])
        self.vel_y = -self.current_speed

    def set_speed(
        self,
        speed: int,
        settings_manager: Optional[SettingsManager] = None,
        auto_mode: bool = False,
    ) -> None:
        """Устанавливает скорость мяча и обновляет настройки."""
        max_speed: int = 8 if auto_mode else 10
        if 1 <= speed <= max_speed:
            old_speed: int = self.current_speed
            self.current_speed = speed
            self.vel_x = (
                int(self.vel_x * speed / old_speed) if old_speed != 0 else speed
            )
            self.vel_y = (
                int(self.vel_y * speed / old_speed) if old_speed != 0 else -speed
            )

            if settings_manager:
                settings_manager.set_ball_speed(speed, auto_mode)

    def increase_speed(
        self, settings_manager: Optional[SettingsManager] = None, auto_mode: bool = False
    ) -> None:
        """Увеличивает скорость на 1 (максимум зависит от режима)."""
        max_speed: int = 25 if auto_mode else 10
        if self.current_speed < max_speed:
            self.set_speed(self.current_speed + 1, settings_manager, auto_mode)

    def decrease_speed(
        self, settings_manager: Optional[SettingsManager] = None, auto_mode: bool = False
    ) -> None:
        """Уменьшает скорость на 1 (минимум 1)."""
        if self.current_speed > 1:
            self.set_speed(self.current_speed - 1, settings_manager, auto_mode)

    def get_speed(self) -> int:
        """Возвращает текущую скорость мяча."""
        return self.current_speed


@dataclass
class GameState:
    """Состояние игры, содержащее все игровые данные."""

    score: int = 0
    lives_left: int = 3
    game_started: bool = False
    game_over: bool = False
    bricks: List[pygame.Rect] = field(default_factory=list)
    game_start_time: float = 0.0

    def reset(self) -> None:
        """Сбрасывает состояние игры к начальным значениям."""
        self.score = 0
        self.lives_left = 3
        self.game_started = False
        self.game_over = False
        self.bricks = []
        self.game_start_time = 0.0
