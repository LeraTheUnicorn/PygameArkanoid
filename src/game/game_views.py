"""
Представления (View) для игры Арканоид.

Содержит классы для отрисовки различных элементов игры,
разделяя логику представления от бизнес-логики.
"""

from typing import List, Optional, Tuple

import pygame

from game_config import (
    BACKGROUND_COLOR,
    BRICK_BORDER_COLOR,
    BRICK_COLORS,
    BRICK_COLS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TEXT_COLOR,
)
from game_models import Ball, Paddle
from dirty_rects import DirtyRectManager
from ai.ai_player import AIPlayer


class GameView:
    """Базовый класс для представлений игры."""

    def __init__(self, screen: pygame.Surface, dirty_rect_manager: DirtyRectManager):
        """
        Инициализирует представление.
        
        Args:
            screen: Поверхность pygame для отрисовки
            dirty_rect_manager: Менеджер грязных прямоугольников
        """
        self.screen = screen
        self.dirty_rects = dirty_rect_manager

    def clear_screen(self) -> None:
        """Очищает экран."""
        self.screen.fill(BACKGROUND_COLOR)
        # При полной очистке помечаем весь экран как измененный
        self.dirty_rects.add(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))


class BricksView(GameView):
    """Представление для отрисовки кирпичей."""

    def draw(self, bricks: List[pygame.Rect]) -> None:
        """
        Отрисовывает все кирпичи на экране.
        
        Args:
            bricks: Список прямоугольников кирпичей
        """
        for idx, brick in enumerate(bricks):
            color = BRICK_COLORS[idx // BRICK_COLS % len(BRICK_COLORS)]
            pygame.draw.rect(self.screen, color, brick)
            pygame.draw.rect(self.screen, BRICK_BORDER_COLOR, brick, 2)
            self.dirty_rects.add(brick)


class PaddleView(GameView):
    """Представление для отрисовки платформы."""

    def draw(self, paddle: Paddle, old_rect: Optional[pygame.Rect] = None) -> None:
        """
        Отрисовывает платформу.
        
        Args:
            paddle: Объект платформы
            old_rect: Предыдущая позиция платформы (для обновления старой области)
        """
        # Очищаем старую позицию
        if old_rect and old_rect != paddle.rect:
            pygame.draw.rect(self.screen, BACKGROUND_COLOR, old_rect)
            self.dirty_rects.add(old_rect)

        # Рисуем новую позицию
        pygame.draw.rect(self.screen, (255, 255, 255), paddle.rect)
        self.dirty_rects.add(paddle.rect)


class BallView(GameView):
    """Представление для отрисовки мяча."""

    def draw(self, ball: Ball, old_rect: Optional[pygame.Rect] = None) -> None:
        """
        Отрисовывает мяч.
        
        Args:
            ball: Объект мяча
            old_rect: Предыдущая позиция мяча (для обновления старой области)
        """
        # Очищаем старую позицию
        if old_rect and old_rect != ball.rect:
            pygame.draw.rect(self.screen, BACKGROUND_COLOR, old_rect)
            self.dirty_rects.add(old_rect)

        # Рисуем новую позицию
        pygame.draw.circle(
            self.screen, (255, 255, 255), ball.rect.center, ball.rect.width // 2
        )
        self.dirty_rects.add(ball.rect)


class HUDView(GameView):
    """Представление для отрисовки HUD (информации на экране)."""

    def __init__(
        self,
        screen: pygame.Surface,
        dirty_rect_manager: DirtyRectManager,
        font: pygame.font.Font,
    ):
        """
        Инициализирует HUD представление.
        
        Args:
            screen: Поверхность pygame
            dirty_rect_manager: Менеджер грязных прямоугольников
            font: Шрифт для текста
        """
        super().__init__(screen, dirty_rect_manager)
        self.font = font
        self.last_text_rect: Optional[pygame.Rect] = None

    def draw(
        self,
        score: int,
        lives_left: int,
        ball: Ball,
        auto_mode: bool = False,
        training_mode: bool = False,
        ai_player: Optional[AIPlayer] = None,
    ) -> None:
        """
        Отрисовывает HUD с информацией об игре.
        
        Args:
            score: Текущий счет
            lives_left: Количество оставшихся жизней
            ball: Объект мяча
            auto_mode: Флаг авторежима
            training_mode: Флаг режима обучения
            ai_player: Объект AI игрока (опционально)
        """
        # Очищаем старую область HUD
        if self.last_text_rect:
            pygame.draw.rect(self.screen, BACKGROUND_COLOR, self.last_text_rect)
            self.dirty_rects.add(self.last_text_rect)

        # Формируем текст
        if auto_mode or training_mode:
            text = f"Очки: {score} | Жизни: {lives_left} | Скорость мяча: {ball.get_speed()} | АВТОРЕЖИМ"
            color = (255, 255, 0)
        else:
            text = f"Очки: {score} | Жизни: {lives_left} | Скорость: {ball.get_speed()} | ↑ ↓ - скорость"
            color = TEXT_COLOR

        # Рендерим текст
        surf = self.font.render(text, True, color)
        pos = (SCREEN_WIDTH - surf.get_width() - 20, 20)
        self.screen.blit(surf, pos)

        # Сохраняем область для следующего обновления
        self.last_text_rect = pygame.Rect(pos[0], pos[1], surf.get_width(), surf.get_height())
        self.dirty_rects.add(self.last_text_rect)


class MenuView(GameView):
    """Представление для отрисовки меню."""

    def __init__(
        self,
        screen: pygame.Surface,
        dirty_rect_manager: DirtyRectManager,
        font: pygame.font.Font,
        big_font: pygame.font.Font,
    ):
        """
        Инициализирует представление меню.
        
        Args:
            screen: Поверхность pygame
            dirty_rect_manager: Менеджер грязных прямоугольников
            font: Обычный шрифт
            big_font: Большой шрифт для заголовков
        """
        super().__init__(screen, dirty_rect_manager)
        self.font = font
        self.big_font = big_font

    def render_colored_hint(
        self,
        text: str,
        pos: Tuple[int, int],
        base_color: Tuple[int, int, int] = (200, 200, 200),
        key_color: Tuple[int, int, int] = (255, 255, 0),
    ) -> int:
        """
        Отображает подсказку с выделенными ключевыми словами цветом.
        
        Args:
            text: Текст подсказки
            pos: Позиция текста
            base_color: Базовый цвет текста
            key_color: Цвет для ключевых слов
            
        Returns:
            Высота отрисованного текста
        """
        x, y = pos
        words = text.split()
        current_x = x

        for word in words:
            # Определяем цвет слова
            color = key_color if word.isupper() or word[0].isupper() else base_color

            word_surf = self.font.render(word, True, color)
            self.screen.blit(word_surf, (current_x, y))
            self.dirty_rects.add(
                pygame.Rect(current_x, y, word_surf.get_width(), word_surf.get_height())
            )

            current_x += word_surf.get_width() + self.font.size(" ")[0]

        return self.font.get_height()
