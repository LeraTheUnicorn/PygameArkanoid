"""
Централизованная конфигурация игры Арканоид.

Все константы игры вынесены в этот файл для удобства управления
и улучшения поддерживаемости кода.
"""

from typing import List, Tuple

# Размеры экрана
SCREEN_WIDTH: int = 800
SCREEN_HEIGHT: int = 600
FPS: int = 60

# Размеры и скорость платформы
PADDLE_WIDTH: int = 120
PADDLE_HEIGHT: int = 15
PADDLE_SPEED: int = 45  # КРИТИЧНО: Увеличено до 45 для достаточной скорости реакции в углах

# Размеры и скорость мяча
BALL_SIZE: int = 16
BALL_SPEED_DEFAULT: int = 5  # Значение по умолчанию

# Параметры кубиков
BRICK_ROWS: int = 5
BRICK_COLS: int = 10
BRICK_WIDTH: int = 60
BRICK_HEIGHT: int = 20
BRICK_PADDING: int = 10
BRICK_OFFSET_TOP: int = 60

MAX_LIVES: int = 3  # Максимальное количество жизней

# Зона разделения - область между кубиками и платформой
# Платформа должна двигаться только когда мяч находится в этой зоне и движется вниз
SEPARATION_ZONE_TOP: int = 226  # Верхняя граница зоны разделения
SEPARATION_ZONE_BOTTOM: int = 540  # Нижняя граница зоны разделения (высота платформы)

# Цвета кирпичей
BRICK_COLORS: List[Tuple[int, int, int]] = [
    (200, 80, 80),
    (200, 160, 80),
    (80, 200, 120),
    (80, 140, 220),
    (150, 80, 220),
]

# Цвета интерфейса
BACKGROUND_COLOR: Tuple[int, int, int] = (10, 10, 30)
BRICK_BORDER_COLOR: Tuple[int, int, int] = (30, 30, 30)
TEXT_COLOR: Tuple[int, int, int] = (255, 255, 255)

# Настройки шрифтов
FONT_NAME: str = "arial"
FONT_SIZE: int = 20
BIG_FONT_SIZE: int = 42
MONO_FONT_SIZE: int = 18

# Резервные моноширинные шрифты для кросс-платформенной совместимости
MONO_FONT_NAMES: List[str] = ["consolas", "courier new", "courier", "monospace", "liberation mono"]

# Настройки звука
SOUND_DEFAULT_VOLUME: float = 0.3
MUSIC_DEFAULT_VOLUME: float = 0.3
PADDLE_SOUND_FREQUENCY: int = 330  # E4
PADDLE_SOUND_DURATION: float = 0.15
PADDLE_SOUND_VOLUME: float = 0.4

# Настройки оптимизации отрисовки
USE_DIRTY_RECTS: bool = True  # Использовать оптимизацию "грязных прямоугольников"
DIRTY_RECT_BUFFER: int = 2  # Дополнительные пиксели вокруг измененной области
