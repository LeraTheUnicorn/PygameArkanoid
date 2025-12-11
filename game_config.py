"""
Централизованная конфигурация игры Арканоид.

Все константы игры вынесены в этот файл для удобства управления
и улучшения поддерживаемости кода.
"""

# Размеры экрана
SCREEN_WIDTH: int = 800
SCREEN_HEIGHT: int = 600
FPS: int = 60

# Размеры и скорость платформы
PADDLE_WIDTH: int = 120
PADDLE_HEIGHT: int = 15
PADDLE_SPEED: int = 15  # Увеличено с 9 до 15 для лучшей скорости платформы

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
BRICK_COLORS = [
    (200, 80, 80),
    (200, 160, 80),
    (80, 200, 120),
    (80, 140, 220),
    (150, 80, 220),
]

# Цвета интерфейса
BACKGROUND_COLOR = (10, 10, 30)
BRICK_BORDER_COLOR = (30, 30, 30)
TEXT_COLOR = (255, 255, 255)

# Настройки шрифтов
FONT_NAME = "arial"
FONT_SIZE = 20
BIG_FONT_SIZE = 42
MONO_FONT_SIZE = 18

# Резервные моноширинные шрифты для кросс-платформенной совместимости
MONO_FONT_NAMES = ["consolas", "courier new", "courier", "monospace", "liberation mono"]

# Настройки звука
SOUND_DEFAULT_VOLUME = 0.3
MUSIC_DEFAULT_VOLUME = 0.3
PADDLE_SOUND_FREQUENCY = 330  # E4
PADDLE_SOUND_DURATION = 0.15
PADDLE_SOUND_VOLUME = 0.4

# Настройки оптимизации отрисовки
USE_DIRTY_RECTS = True  # Использовать оптимизацию "грязных прямоугольников"
DIRTY_RECT_BUFFER = 2  # Дополнительные пиксели вокруг измененной области
