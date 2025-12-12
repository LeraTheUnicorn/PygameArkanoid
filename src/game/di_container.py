"""
Контейнер для Dependency Injection.

Управляет созданием и внедрением зависимостей,
улучшая тестируемость и поддерживаемость кода.
"""

from typing import Optional

import pygame

from .dirty_rects import DirtyRectManager
from .game_config import SCREEN_HEIGHT, SCREEN_WIDTH
from .game_controllers import GameController, InputController
from .game_models import Ball, GameState, Paddle
from .game_views import (
    BallView,
    BricksView,
    HUDView,
    PaddleView,
)
from .highscores import HighScoreManager
from .settings import SettingsManager


class DIContainer:
    """Контейнер для управления зависимостями."""

    def __init__(self) -> None:
        """Инициализирует контейнер зависимостей."""
        self._screen: Optional[pygame.Surface] = None
        self._font: Optional[pygame.font.Font] = None
        self._big_font: Optional[pygame.font.Font] = None
        self._clock: Optional[pygame.time.Clock] = None
        self._highscore_manager: Optional[HighScoreManager] = None
        self._settings_manager: Optional[SettingsManager] = None
        self._dirty_rect_manager: Optional[DirtyRectManager] = None

        # Игровые объекты
        self._game_state: Optional[GameState] = None
        self._ball: Optional[Ball] = None
        self._paddle: Optional[Paddle] = None

        # Контроллеры
        self._game_controller: Optional[GameController] = None
        self._input_controller: Optional[InputController] = None

        # Представления
        self._bricks_view: Optional[BricksView] = None
        self._paddle_view: Optional[PaddleView] = None
        self._ball_view: Optional[BallView] = None
        self._hud_view: Optional[HUDView] = None

    # Геттеры для основных объектов pygame
    def get_screen(self) -> pygame.Surface:
        """Возвращает поверхность экрана."""
        if self._screen is None:
            raise RuntimeError("Screen not initialized. Call init_pygame() first.")
        return self._screen

    def get_font(self) -> pygame.font.Font:
        """Возвращает обычный шрифт."""
        if self._font is None:
            raise RuntimeError("Font not initialized. Call init_pygame() first.")
        return self._font

    def get_big_font(self) -> pygame.font.Font:
        """Возвращает большой шрифт."""
        if self._big_font is None:
            raise RuntimeError("Big font not initialized. Call init_pygame() first.")
        return self._big_font

    def get_clock(self) -> pygame.time.Clock:
        """Возвращает часы pygame."""
        if self._clock is None:
            raise RuntimeError("Clock not initialized. Call init_pygame() first.")
        return self._clock

    # Инициализация pygame объектов
    def init_pygame(self) -> None:
        """Инициализирует основные объекты pygame."""
        pygame.init()
        pygame.mixer.init()
        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Арканоид")
        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont("arial", 20)
        self._big_font = pygame.font.SysFont("arial", 42, bold=True)

    # Менеджеры
    def get_highscore_manager(self) -> HighScoreManager:
        """Возвращает менеджер рекордов."""
        if self._highscore_manager is None:
            self._highscore_manager = HighScoreManager()
        return self._highscore_manager

    def get_settings_manager(self) -> SettingsManager:
        """Возвращает менеджер настроек."""
        if self._settings_manager is None:
            self._settings_manager = SettingsManager()
        return self._settings_manager

    def get_dirty_rect_manager(self) -> DirtyRectManager:
        """Возвращает менеджер грязных прямоугольников."""
        if self._dirty_rect_manager is None:
            self._dirty_rect_manager = DirtyRectManager(SCREEN_WIDTH, SCREEN_HEIGHT)
        return self._dirty_rect_manager

    # Игровые объекты
    def get_game_state(self) -> GameState:
        """Возвращает состояние игры."""
        if self._game_state is None:
            self._game_state = GameState()
        return self._game_state

    def get_ball(self) -> Ball:
        """Возвращает объект мяча."""
        if self._ball is None:
            self._ball = Ball()
        return self._ball

    def get_paddle(self) -> Paddle:
        """Возвращает объект платформы."""
        if self._paddle is None:
            self._paddle = Paddle()
        return self._paddle

    # Контроллеры
    def get_game_controller(self) -> GameController:
        """Возвращает игровой контроллер."""
        if self._game_controller is None:
            self._game_controller = GameController(
                self.get_game_state(),
                self.get_ball(),
                self.get_paddle(),
                self.get_settings_manager(),
            )
        return self._game_controller

    def get_input_controller(self) -> InputController:
        """Возвращает контроллер ввода."""
        if self._input_controller is None:
            self._input_controller = InputController(self.get_game_controller())
        return self._input_controller

    # Представления
    def get_bricks_view(self) -> BricksView:
        """Возвращает представление кирпичей."""
        if self._bricks_view is None:
            self._bricks_view = BricksView(
                self.get_screen(), self.get_dirty_rect_manager()
            )
        return self._bricks_view

    def get_paddle_view(self) -> PaddleView:
        """Возвращает представление платформы."""
        if self._paddle_view is None:
            self._paddle_view = PaddleView(
                self.get_screen(), self.get_dirty_rect_manager()
            )
        return self._paddle_view

    def get_ball_view(self) -> BallView:
        """Возвращает представление мяча."""
        if self._ball_view is None:
            self._ball_view = BallView(
                self.get_screen(), self.get_dirty_rect_manager()
            )
        return self._ball_view

    def get_hud_view(self) -> HUDView:
        """Возвращает представление HUD."""
        if self._hud_view is None:
            self._hud_view = HUDView(
                self.get_screen(),
                self.get_dirty_rect_manager(),
                self.get_font(),
            )
        return self._hud_view

    # Методы для тестирования (позволяют подменять зависимости)
    def set_screen(self, screen: pygame.Surface) -> None:
        """Устанавливает поверхность экрана (для тестирования)."""
        self._screen = screen

    def set_font(self, font: pygame.font.Font) -> None:
        """Устанавливает шрифт (для тестирования)."""
        self._font = font

    def set_big_font(self, big_font: pygame.font.Font) -> None:
        """Устанавливает большой шрифт (для тестирования)."""
        self._big_font = big_font

    def set_game_state(self, game_state: GameState) -> None:
        """Устанавливает состояние игры (для тестирования)."""
        self._game_state = game_state

    def set_ball(self, ball: Ball) -> None:
        """Устанавливает мяч (для тестирования)."""
        self._ball = ball

    def set_paddle(self, paddle: Paddle) -> None:
        """Устанавливает платформу (для тестирования)."""
        self._paddle = paddle

    def reset(self) -> None:
        """Сбрасывает все зависимости (для тестирования)."""
        self._game_state = None
        self._ball = None
        self._paddle = None
        self._game_controller = None
        self._input_controller = None
        self._bricks_view = None
        self._paddle_view = None
        self._ball_view = None
        self._hud_view = None
