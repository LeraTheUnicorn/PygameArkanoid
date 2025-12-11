"""
Система оптимизации отрисовки с использованием "грязных прямоугольников".

Отслеживает измененные области экрана и перерисовывает только их,
вместо полной перерисовки всего экрана каждый кадр.
"""

from typing import List, Set
import pygame

from game_config import DIRTY_RECT_BUFFER, USE_DIRTY_RECTS


class DirtyRectManager:
    """Менеджер для отслеживания измененных областей экрана."""

    def __init__(self, screen_width: int, screen_height: int):
        """
        Инициализирует менеджер грязных прямоугольников.
        
        Args:
            screen_width: Ширина экрана
            screen_height: Высота экрана
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.dirty_rects: List[pygame.Rect] = []
        self.enabled = USE_DIRTY_RECTS

    def add(self, rect: pygame.Rect) -> None:
        """
        Добавляет прямоугольник в список измененных областей.
        
        Args:
            rect: Прямоугольник, который нужно перерисовать
        """
        if not self.enabled:
            return

        # Добавляем буфер вокруг прямоугольника для корректной отрисовки
        expanded_rect = rect.inflate(DIRTY_RECT_BUFFER * 2, DIRTY_RECT_BUFFER * 2)
        
        # Ограничиваем прямоугольник границами экрана
        expanded_rect.clamp_ip(pygame.Rect(0, 0, self.screen_width, self.screen_height))
        
        self.dirty_rects.append(expanded_rect)

    def add_point(self, x: int, y: int, width: int = 1, height: int = 1) -> None:
        """
        Добавляет точку как прямоугольник в список измененных областей.
        
        Args:
            x: Координата X
            y: Координата Y
            width: Ширина области
            height: Высота области
        """
        self.add(pygame.Rect(x, y, width, height))

    def clear(self) -> None:
        """Очищает список измененных областей."""
        self.dirty_rects.clear()

    def get_dirty_rects(self) -> List[pygame.Rect]:
        """
        Возвращает список измененных прямоугольников и очищает его.
        
        Returns:
            Список прямоугольников для перерисовки
        """
        rects = self.dirty_rects.copy()
        self.clear()
        return rects

    def optimize(self) -> List[pygame.Rect]:
        """
        Оптимизирует список прямоугольников, объединяя перекрывающиеся.
        
        Returns:
            Оптимизированный список прямоугольников
        """
        if not self.dirty_rects:
            return []

        # Если прямоугольников мало, просто возвращаем их
        if len(self.dirty_rects) <= 2:
            return self.get_dirty_rects()

        # Объединяем перекрывающиеся прямоугольники
        optimized: List[pygame.Rect] = []
        used: Set[int] = set()

        for i, rect1 in enumerate(self.dirty_rects):
            if i in used:
                continue

            merged = rect1.copy()
            used.add(i)

            # Ищем перекрывающиеся прямоугольники
            for j, rect2 in enumerate(self.dirty_rects[i + 1:], start=i + 1):
                if j in used:
                    continue

                if merged.colliderect(rect2):
                    merged.union_ip(rect2)
                    used.add(j)

            optimized.append(merged)

        self.dirty_rects = optimized
        return self.get_dirty_rects()

    def update_display(self, screen: pygame.Surface, full_update: bool = False) -> None:
        """
        Обновляет отображение, перерисовывая только измененные области.
        
        Args:
            screen: Поверхность экрана
            full_update: Если True, обновляет весь экран
        """
        if full_update or not self.enabled:
            pygame.display.flip()
            self.clear()
        else:
            dirty = self.optimize()
            if dirty:
                pygame.display.update(dirty)
            else:
                # Если нет изменений, все равно обновляем для плавности
                pygame.display.flip()
