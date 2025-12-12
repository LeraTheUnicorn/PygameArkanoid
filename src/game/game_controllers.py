"""
Контроллеры для игры Арканоид.

Содержит классы, которые обрабатывают игровую логику,
разделяя её от представления и моделей данных.
"""

from typing import Dict, List, Optional, Tuple

import pygame

from .game_config import (
    BRICK_COLS,
    BRICK_HEIGHT,
    BRICK_OFFSET_TOP,
    BRICK_PADDING,
    BRICK_ROWS,
    BRICK_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEPARATION_ZONE_BOTTOM,
    SEPARATION_ZONE_TOP,
)
from .game_models import Ball, GameState, Paddle
from .settings import SettingsManager


class GameController:
    """Контроллер для основной игровой логики."""

    def __init__(
        self,
        game_state: GameState,
        ball: Ball,
        paddle: Paddle,
        settings_manager: SettingsManager,
    ) -> None:
        """
        Инициализирует игровой контроллер.
        
        Args:
            game_state: Состояние игры
            ball: Объект мяча
            paddle: Объект платформы
            settings_manager: Менеджер настроек
        """
        self.game_state: GameState = game_state
        self.ball: Ball = ball
        self.paddle: Paddle = paddle
        self.settings_manager: SettingsManager = settings_manager

    def build_bricks(self) -> List[pygame.Rect]:
        """
        Создает сетку кирпичей для игры.
        
        Returns:
            Список прямоугольников кирпичей
        """
        bricks: List[pygame.Rect] = []
        start_x: int = (
            SCREEN_WIDTH
            - (BRICK_COLS * BRICK_WIDTH + (BRICK_COLS - 1) * BRICK_PADDING)
        ) // 2
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                x: int = start_x + col * (BRICK_WIDTH + BRICK_PADDING)
                y: int = BRICK_OFFSET_TOP + row * (BRICK_HEIGHT + BRICK_PADDING)
                bricks.append(pygame.Rect(x, y, BRICK_WIDTH, BRICK_HEIGHT))
        return bricks

    def check_ball_paddle_collision(self) -> bool:
        """
        Проверяет столкновение мяча с платформой.
        
        Returns:
            True если произошло столкновение
        """
        if not self.ball.rect.colliderect(self.paddle.rect):
            return False

        if self.ball.vel_y <= 0:
            return False

        # Проверяем, что мяч попадает в верхнюю часть платформы
        paddle_top: int = self.paddle.rect.top
        ball_bottom: int = self.ball.rect.bottom

        if (
            ball_bottom >= paddle_top
            and ball_bottom <= paddle_top + 15
            and self.ball.rect.top < paddle_top + 10
        ):
            # Проверяем, что мяч находится в пределах платформы по горизонтали
            if (
                self.paddle.rect.left - 5
                <= self.ball.rect.centerx
                <= self.paddle.rect.right + 5
            ):
                return True

        return False

    def handle_ball_paddle_collision(self) -> None:
        """Обрабатывает столкновение мяча с платформой."""
        if not self.check_ball_paddle_collision():
            return

        # Вычисляем относительную позицию мяча на платформе
        relative_x: float = (
            self.ball.rect.centerx - self.paddle.rect.centerx
        ) / (self.paddle.rect.width / 2)

        # Ограничиваем значение от -1 до 1
        relative_x = max(-1, min(1, relative_x))

        # Изменяем горизонтальную скорость в зависимости от позиции
        self.ball.vel_x = int(relative_x * self.ball.current_speed)

        # Отскок по вертикали
        self.ball.bounce_vertical()

        # Устанавливаем флаг отскока
        self.ball._just_bounced = True

    def check_ball_brick_collision(self) -> Optional[int]:
        """
        Проверяет столкновение мяча с кирпичами.
        
        Returns:
            Индекс столкнувшегося кирпича или None
        """
        if not self.game_state.bricks:
            return None

        # Оптимизация: проверяем только если мяч в области кирпичей
        if self.ball.rect.bottom > SEPARATION_ZONE_TOP + 50:
            return None

        try:
            hit_index: int = self.ball.rect.collidelist(self.game_state.bricks)
            return hit_index if hit_index != -1 else None
        except Exception:
            return None

    def handle_ball_brick_collision(self) -> Optional[pygame.Rect]:
        """
        Обрабатывает столкновение мяча с кирпичом.
        
        Returns:
            Уничтоженный кирпич или None
        """
        hit_index: Optional[int] = self.check_ball_brick_collision()
        if hit_index is None:
            return None

        self.ball.bounce_vertical()
        destroyed_brick: pygame.Rect = self.game_state.bricks.pop(hit_index)
        self.game_state.score += 1
        return destroyed_brick

    def check_ball_out_of_bounds(self) -> bool:
        """
        Проверяет, вышел ли мяч за нижнюю границу экрана.
        
        Returns:
            True если мяч вышел за границы
        """
        return self.ball.rect.top > SCREEN_HEIGHT

    def handle_ball_out_of_bounds(self) -> None:
        """Обрабатывает выход мяча за границы экрана."""
        if not self.check_ball_out_of_bounds():
            return

        self.game_state.lives_left -= 1
        if self.game_state.lives_left <= 0:
            self.game_state.game_over = True
        else:
            # Сбрасываем мяч на платформу
            self.ball.reset(self.paddle.rect)
            self.ball.vel_y = 0
            self.game_state.game_started = False

    def update_ball(self) -> None:
        """Обновляет позицию мяча."""
        self.ball.update()

    def move_paddle(self, direction: int) -> None:
        """
        Перемещает платформу.
        
        Args:
            direction: -1 (влево) или 1 (вправо)
        """
        self.paddle.move(direction)

    def reset_game(self) -> None:
        """Сбрасывает игру к начальному состоянию."""
        self.game_state.reset()
        self.game_state.bricks = self.build_bricks()
        self.ball.reset(self.paddle.rect)
        self.ball.vel_y = 0
        ball_speed: int = self.settings_manager.get_ball_speed()
        self.ball.set_speed(ball_speed)


class InputController:
    """Контроллер для обработки пользовательского ввода."""

    def __init__(self, game_controller: GameController) -> None:
        """
        Инициализирует контроллер ввода.
        
        Args:
            game_controller: Игровой контроллер
        """
        self.game_controller: GameController = game_controller

    def handle_keyboard_input(
        self, keys: pygame.key.ScancodeWrapper, auto_mode: bool = False
    ) -> Dict[str, bool]:
        """
        Обрабатывает нажатия клавиш.
        
        Args:
            keys: Состояние клавиш pygame
            auto_mode: Флаг авторежима
            
        Returns:
            Словарь с информацией о действиях
        """
        actions: Dict[str, bool] = {
            "paddle_left": False,
            "paddle_right": False,
            "start_game": False,
            "restart_game": False,
        }

        if not auto_mode:
            if keys[pygame.K_LEFT]:
                actions["paddle_left"] = True
                self.game_controller.move_paddle(-1)
            elif keys[pygame.K_RIGHT]:
                actions["paddle_right"] = True
                self.game_controller.move_paddle(1)

            if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
                if not self.game_controller.game_state.game_started:
                    actions["start_game"] = True
                    self.game_controller.game_state.game_started = True
                    if keys[pygame.K_LEFT]:
                        self.game_controller.ball.vel_x = -self.game_controller.ball.get_speed()
                    else:
                        self.game_controller.ball.vel_x = self.game_controller.ball.get_speed()
                    self.game_controller.ball.vel_y = -self.game_controller.ball.get_speed()

            if keys[pygame.K_r] and self.game_controller.game_state.game_over:
                actions["restart_game"] = True
                self.game_controller.reset_game()

        return actions
