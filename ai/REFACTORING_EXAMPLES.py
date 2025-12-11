"""
Примеры рефакторинга для ai_player.py

Эти примеры демонстрируют, как можно улучшить код согласно рекомендациям.
"""

import os
import sys
import logging
import functools
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

# ============================================================================
# 1. БЕЗОПАСНОСТЬ: Валидация входных данных
# ============================================================================

def _validate_dimensions(screen_width: int, screen_height: int) -> None:
    """
    Валидирует размеры экрана.
    
    Raises:
        ValueError: Если размеры некорректны
        TypeError: Если тип данных некорректен
    """
    if not isinstance(screen_width, int):
        raise TypeError(
            f"screen_width должен быть целым числом, получено: {type(screen_width).__name__}"
        )
    if not isinstance(screen_height, int):
        raise TypeError(
            f"screen_height должен быть целым числом, получено: {type(screen_height).__name__}"
        )
    if screen_width <= 0:
        raise ValueError(
            f"screen_width должен быть положительным, получено: {screen_width}"
        )
    if screen_height <= 0:
        raise ValueError(
            f"screen_height должен быть положительным, получено: {screen_height}"
        )
    if screen_width < 400 or screen_height < 300:
        raise ValueError(
            f"Минимальные размеры экрана: 400x300, получено: {screen_width}x{screen_height}"
        )


def _get_env_bool(key: str, default: bool = True) -> bool:
    """
    Безопасно получает булево значение из переменной окружения.
    
    Args:
        key: Имя переменной окружения
        default: Значение по умолчанию
        
    Returns:
        Булево значение
    """
    try:
        value = os.getenv(key, "").strip().lower()
        if not value:
            return default
        return value in ("1", "true", "yes", "on")
    except Exception:
        # В случае ошибки возвращаем значение по умолчанию
        return default


def is_frozen() -> bool:
    """
    Проверяет, является ли приложение скомпилированным.
    
    Поддерживает:
    - PyInstaller (sys.frozen)
    - cx_Freeze (sys.frozen)
    - py2exe (_MEIPASS)
    - py2app (resource_fork)
    """
    return (
        getattr(sys, "frozen", False) or 
        hasattr(sys, "_MEIPASS") or
        hasattr(sys, "frozendllhandle")
    )


# ============================================================================
# 2. ЛОГИРОВАНИЕ: Настройка логгера
# ============================================================================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Настраивает и возвращает логгер для модуля.
    
    Args:
        name: Имя логгера (обычно __name__)
        level: Уровень логирования
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger


# ============================================================================
# 3. ПРОИЗВОДИТЕЛЬНОСТЬ: Кэширование
# ============================================================================

class BrickMapCache:
    """Менеджер кэша для карты кирпичей."""
    
    def __init__(self):
        self._cache: Optional[Tuple[str, Dict, List]] = None
        self._hits = 0
        self._misses = 0
    
    def get(self, cache_key: str) -> Optional[Tuple[Dict, List]]:
        """Получает данные из кэша."""
        if self._cache and self._cache[0] == cache_key:
            self._hits += 1
            return self._cache[1], self._cache[2]
        self._misses += 1
        return None
    
    def set(self, cache_key: str, brick_map: Dict, coordinates: List) -> None:
        """Сохраняет данные в кэш."""
        self._cache = (cache_key, brick_map, coordinates)
    
    def clear(self) -> None:
        """Очищает кэш."""
        self._cache = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


def generate_brick_cache_key(bricks: List[Any]) -> str:
    """
    Генерирует ключ кэша для списка кирпичей.
    
    Args:
        bricks: Список кирпичей
        
    Returns:
        Строковый ключ для кэша
    """
    return "|".join(
        f"{getattr(b, 'x', 0):.1f},"
        f"{getattr(b, 'y', 0):.1f},"
        f"{getattr(b, 'width', 60)},"
        f"{getattr(b, 'height', 20)}"
        for b in sorted(bricks, key=lambda b: (getattr(b, 'y', 0), getattr(b, 'x', 0)))
    )


# ============================================================================
# 4. СТРУКТУРЫ ДАННЫХ: Dataclasses
# ============================================================================

@dataclass
class BrickInfo:
    """Информация о кирпиче."""
    x: float
    y: float
    width: int
    height: int
    center_x: float
    center_y: float
    row: int
    col: int
    
    @classmethod
    def from_brick(cls, brick: Any) -> 'BrickInfo':
        """Создает BrickInfo из объекта кирпича."""
        x = getattr(brick, "x", 0)
        y = getattr(brick, "y", 0)
        width = getattr(brick, "width", 60)
        height = getattr(brick, "height", 20)
        
        return cls(
            x=x,
            y=y,
            width=width,
            height=height,
            center_x=x + width / 2,
            center_y=y + height / 2,
            row=int(y / 30),
            col=int(x / 60),
        )
    
    @property
    def key(self) -> str:
        """Возвращает ключ для карты кирпичей."""
        return f"{self.col}_{self.row}"


@dataclass
class TargetingSystem:
    """Система прицельного отбивания."""
    target_brick: Optional[Any] = None
    optimal_offset: float = 0.0
    successful_hits: List[Dict[str, Any]] = field(default_factory=list)
    brick_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    trajectory_targets: List[Any] = field(default_factory=list)
    hit_patterns: Dict[str, Any] = field(default_factory=dict)
    brick_coordinates: List[Dict[str, Any]] = field(default_factory=list)
    visible_targets: List[Dict[str, Any]] = field(default_factory=list)
    recent_target_positions: List[float] = field(default_factory=list)
    
    def reset(self) -> None:
        """Сбрасывает состояние системы."""
        self.target_brick = None
        self.optimal_offset = 0.0
        self.successful_hits.clear()
        self.brick_map.clear()
        self.trajectory_targets.clear()
        self.hit_patterns.clear()
        self.brick_coordinates.clear()
        self.visible_targets.clear()
        self.recent_target_positions.clear()


@dataclass
class SeparationZoneTracker:
    """Отслеживание зоны разделения."""
    ball_entered_separation_zone: bool = False
    target_position_set: bool = False
    target_position: Optional[float] = None
    separation_zone_start: int = 226
    paddle_zone_start: int = 540
    paddle_moved_after_set: bool = False
    paddle_reached_target: bool = False
    last_movement_frame: int = 0
    frames_since_target_set: int = 0
    saved_ball_vel_x: Optional[float] = None
    game_restart_required: bool = False
    
    def reset(self) -> None:
        """Сбрасывает состояние."""
        self.ball_entered_separation_zone = False
        self.target_position_set = False
        self.target_position = None
        self.paddle_moved_after_set = False
        self.paddle_reached_target = False
        self.last_movement_frame = 0
        self.frames_since_target_set = 0
        self.saved_ball_vel_x = None
        self.game_restart_required = False


# ============================================================================
# 5. КОНФИГУРАЦИЯ: Вынос констант
# ============================================================================

@dataclass(frozen=True)
class GameZones:
    """Конфигурация игровых зон."""
    bricks_zone_end: int = 210
    ball_diameter: int = 16
    paddle_zone_offset: int = 60
    
    @property
    def separation_zone_start(self) -> int:
        """Начало зоны разделения."""
        return self.bricks_zone_end + self.ball_diameter
    
    def paddle_zone_start(self, screen_height: int) -> int:
        """Начало зоны платформы."""
        return screen_height - self.paddle_zone_offset


@dataclass(frozen=True)
class PaddleConfig:
    """Конфигурация платформы."""
    width: int = 120
    safe_margin: int = 30  # Безопасный отступ от края
    min_movement_distance: int = 5


@dataclass(frozen=True)
class AIConfig:
    """Основная конфигурация AI."""
    zones: GameZones = field(default_factory=GameZones)
    paddle: PaddleConfig = field(default_factory=PaddleConfig)
    debug_log_interval: int = 100
    loop_detection_threshold: int = 5
    max_empty_bounces: int = 1


# ============================================================================
# 6. РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ: Класс для управления кирпичами
# ============================================================================

class BrickMapManager:
    """Управляет картой кирпичей с кэшированием."""
    
    def __init__(self):
        self.cache = BrickMapCache()
    
    def update_brick_map(
        self, 
        bricks: List[Any]
    ) -> Tuple[Dict[str, BrickInfo], List[Dict[str, Any]]]:
        """
        Обновляет карту кирпичей с кэшированием.
        
        Args:
            bricks: Список объектов кирпичей
            
        Returns:
            Кортеж (brick_map, coordinates)
        """
        if not bricks:
            return {}, []
        
        cache_key = generate_brick_cache_key(bricks)
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        brick_map, coordinates = self._build_map(bricks)
        self.cache.set(cache_key, brick_map, coordinates)
        return brick_map, coordinates
    
    def _build_map(
        self, 
        bricks: List[Any]
    ) -> Tuple[Dict[str, BrickInfo], List[Dict[str, Any]]]:
        """Строит карту кирпичей."""
        brick_map: Dict[str, BrickInfo] = {}
        coordinates: List[Dict[str, Any]] = []
        
        for brick in bricks:
            info = BrickInfo.from_brick(brick)
            brick_map[info.key] = info
            
            coordinates.append({
                "x": info.center_x,
                "y": info.center_y,
                "brick": brick,
                "key": info.key,
            })
        
        return brick_map, coordinates
    
    def clear_cache(self) -> None:
        """Очищает кэш."""
        self.cache.clear()


# ============================================================================
# 7. ОБРАБОТКА ИСКЛЮЧЕНИЙ: Конкретные типы
# ============================================================================

class AIPlayerError(Exception):
    """Базовое исключение для AIPlayer."""
    pass


class InvalidStateError(AIPlayerError):
    """Ошибка недопустимого состояния."""
    pass


class CalculationError(AIPlayerError):
    """Ошибка расчета."""
    pass


def safe_calculate_landing_position(
    trajectory_predictor: Any,
    game_state: Any,
    logger: logging.Logger
) -> Optional[float]:
    """
    Безопасно рассчитывает позицию приземления.
    
    Args:
        trajectory_predictor: Предиктор траектории
        game_state: Состояние игры
        logger: Логгер
        
    Returns:
        Позиция приземления или None при ошибке
    """
    try:
        return trajectory_predictor.predict_exact_landing_position(game_state)
    except (AttributeError, TypeError) as e:
        logger.warning(
            f"Ошибка типов при расчете позиции приземления: {e}",
            exc_info=True
        )
        return None
    except ValueError as e:
        logger.error(
            f"Некорректные данные при расчете позиции: {e}",
            exc_info=True
        )
        return None
    except Exception as e:
        logger.critical(
            f"Неожиданная ошибка при расчете позиции: {e}",
            exc_info=True
        )
        return None


# ============================================================================
# 8. ОПТИМИЗАЦИЯ ЛОГИРОВАНИЯ: Умное логирование
# ============================================================================

class DebugLogger:
    """Умный логгер для отладочной информации."""
    
    def __init__(self, debug_mode: bool = False, log_interval: int = 100):
        self.debug_mode = debug_mode
        self.log_interval = log_interval
        self.frame_counter = 0
        self.logger = logging.getLogger(__name__)
    
    def should_log(self, probability: float = 1.0) -> bool:
        """
        Определяет, нужно ли логировать.
        
        Args:
            probability: Вероятность логирования (0.0-1.0)
            
        Returns:
            True если нужно логировать
        """
        if not self.debug_mode:
            return False
        
        self.frame_counter += 1
        
        if probability >= 1.0:
            return self.frame_counter % self.log_interval == 0
        
        return (self.frame_counter % max(1, int(1 / probability))) == 0
    
    def debug(self, message: str, probability: float = 1.0) -> None:
        """Логирует отладочное сообщение с вероятностью."""
        if self.should_log(probability):
            self.logger.debug(message)
    
    def reset_counter(self) -> None:
        """Сбрасывает счетчик кадров."""
        self.frame_counter = 0


# ============================================================================
# 9. ИНЪЕКЦИЯ ЗАВИСИМОСТЕЙ: Пример использования
# ============================================================================

class RefactoredAIPlayerInit:
    """
    Пример улучшенного конструктора с инъекцией зависимостей.
    
    Это демонстрация того, как должен выглядеть __init__ после рефакторинга.
    """
    
    def __init__(
        self,
        screen_width: int = 800,
        screen_height: int = 600,
        debug_mode: bool = False,
        config: Optional[AIConfig] = None,
        # Зависимости (опциональные для инъекции)
        trajectory_predictor: Optional[Any] = None,
        position_optimizer: Optional[Any] = None,
        learning_system: Optional[Any] = None,
        performance_logger: Optional[Any] = None,
        brick_map_manager: Optional[BrickMapManager] = None,
    ):
        """Инициализация с валидацией и инъекцией зависимостей."""
        # Валидация входных данных
        _validate_dimensions(screen_width, screen_height)
        
        # Сохранение параметров
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = bool(debug_mode)
        self.config = config or AIConfig()
        
        # Настройка логирования
        self.logger = setup_logger(__name__)
        self.debug_logger = DebugLogger(
            debug_mode=self.debug_mode,
            log_interval=self.config.debug_log_interval
        )
        
        # Инъекция зависимостей с fallback
        self.trajectory_predictor = (
            trajectory_predictor 
            or self._create_default_trajectory_predictor()
        )
        self.position_optimizer = (
            position_optimizer 
            or self._create_default_position_optimizer()
        )
        self.learning_system = (
            learning_system 
            or self._create_default_learning_system()
        )
        
        enable_session_logging = _get_env_bool("AI_ENABLE_SESSION_LOGGING", True)
        self.performance_logger = (
            performance_logger 
            or self._create_default_performance_logger(enable_session_logging)
        )
        
        self.brick_map_manager = brick_map_manager or BrickMapManager()
        
        # Инициализация структур данных
        self.targeting_system = TargetingSystem()
        self.separation_zone_tracker = SeparationZoneTracker()
        
        # Инициализация состояния
        self._init_state()
    
    def _create_default_trajectory_predictor(self) -> Any:
        """Создает предиктор траектории по умолчанию."""
        # Здесь должна быть реальная реализация
        pass
    
    def _create_default_position_optimizer(self) -> Any:
        """Создает оптимизатор позиции по умолчанию."""
        # Здесь должна быть реальная реализация
        pass
    
    def _create_default_learning_system(self) -> Any:
        """Создает систему обучения по умолчанию."""
        # Здесь должна быть реальная реализация
        pass
    
    def _create_default_performance_logger(self, enable: bool) -> Any:
        """Создает логгер производительности по умолчанию."""
        # Здесь должна быть реальная реализация
        pass
    
    def _init_state(self) -> None:
        """Инициализирует состояние AI."""
        # Инициализация всех атрибутов состояния
        pass
    
    def reset_for_testing(self) -> None:
        """Сбрасывает состояние для тестирования."""
        self.targeting_system.reset()
        self.separation_zone_tracker.reset()
        self.brick_map_manager.clear_cache()
        self.debug_logger.reset_counter()
        # ... остальные сбросы