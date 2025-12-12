"""
Система управления настройками игры Арканоид
Сохраняет и загружает настройки в файл с валидацией и версионированием

Улучшения:
- Валидация загружаемых данных
- Версионирование настроек
- Инъекция зависимостей для тестирования
- Атомарное сохранение
- Константы вместо магических чисел
- Улучшенная обработка ошибок
- Безопасная работа с путями (защита от path traversal)
- Ленивая загрузка настроек
- Кэширование путей
- Интерфейс для файловой системы (для тестирования)
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Protocol доступен в typing начиная с Python 3.8
try:
    from typing import Protocol
except ImportError:
    # Fallback для старых версий (хотя мы уже проверили версию)
    from typing_extensions import Protocol

# Проверка версии Python
if sys.version_info < (3, 8):
    raise RuntimeError("Требуется Python 3.8 или выше")

# Настройка логирования
# Используем стандартный logger, но root logger будет настроен через ai.logging_config
# когда импортируется AIPlayer
logger = logging.getLogger(__name__)
# Устанавливаем уровень из корневого логгера (будет настроен через setup_root_logger)
# На случай, если root logger еще не настроен, устанавливаем уровень напрямую
if logger.level == logging.NOTSET:
    # Пытаемся импортировать настройку из ai, если доступно
    try:
        import sys
        import os
        # Добавляем путь к ai модулю
        ai_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ai')
        if ai_path not in sys.path:
            sys.path.insert(0, ai_path)
        from logging_config import get_log_level
        logger.setLevel(get_log_level())
    except (ImportError, ModuleNotFoundError):
        # Если не можем импортировать, используем DEBUG по умолчанию
        logger.setLevel(logging.DEBUG)


# ============================================================================
# Константы
# ============================================================================

class SettingsConstants:
    """
    Константы для настроек игры Арканоид
    
    Содержит все константы, связанные с игровой механикой и настройками.
    Используется для централизованного управления параметрами игры.
    """
    
    # Скорость мяча
    DEFAULT_BALL_SPEED: int = 8  # Средняя скорость по умолчанию
    MIN_BALL_SPEED: int = 1       # Минимальная скорость мяча
    MAX_BALL_SPEED_MANUAL: int = 10  # Макс. скорость в ручном режиме
    MAX_BALL_SPEED_AUTO: int = 8     # Макс. скорость в авторежиме (ограничено временем расчета)
    
    # Ограничения производительности
    FRAME_TIME_MS: float = 16.67      # Время на кадр при 60 FPS
    TRAJECTORY_CALC_TIME_MS: float = 5.0  # Время расчета траектории
    SAFETY_MARGIN_MS: float = 5.0      # Запас для стабильности
    
    # Файл настроек
    MAX_SETTINGS_FILE_SIZE: int = 1024 * 1024  # 1 MB - максимальный размер файла настроек
    SETTINGS_VERSION: int = 1                   # Текущая версия формата настроек
    
    @classmethod
    def get_max_ball_speed(cls, auto_mode: bool) -> int:
        """
        Возвращает максимальную скорость мяча в зависимости от режима игры
        
        Args:
            auto_mode: True для авторежима, False для ручного
        
        Returns:
            Максимально допустимая скорость мяча
        """
        return cls.MAX_BALL_SPEED_AUTO if auto_mode else cls.MAX_BALL_SPEED_MANUAL
    
    @classmethod
    def validate_ball_speed_range(cls, speed: int, auto_mode: bool) -> bool:
        """
        Проверяет, что скорость мяча находится в допустимом диапазоне
        
        Args:
            speed: Скорость мяча для проверки
            auto_mode: Режим игры
        
        Returns:
            True если скорость допустима, False в противном случае
        """
        max_speed = cls.get_max_ball_speed(auto_mode)
        return cls.MIN_BALL_SPEED <= speed <= max_speed


# ============================================================================
# Валидатор настроек
# ============================================================================

class SettingsValidator:
    """Валидатор настроек игры"""
    
    @staticmethod
    def validate_ball_speed(speed: Any, auto_mode: bool = False) -> int:
        """
        Валидирует скорость мяча.
        
        Args:
            speed: Значение скорости (любой тип)
            auto_mode: Режим игры (авто/ручной)
        
        Returns:
            Валидная скорость мяча
        """
        if not isinstance(speed, (int, float)):
            logger.warning(f"Некорректный тип скорости: {type(speed)}, используется значение по умолчанию")
            return SettingsConstants.DEFAULT_BALL_SPEED
        
        max_speed = (
            SettingsConstants.MAX_BALL_SPEED_AUTO 
            if auto_mode 
            else SettingsConstants.MAX_BALL_SPEED_MANUAL
        )
        
        speed_int = int(speed)
        
        if not (SettingsConstants.MIN_BALL_SPEED <= speed_int <= max_speed):
            logger.warning(
                f"Скорость {speed_int} вне допустимого диапазона "
                f"[{SettingsConstants.MIN_BALL_SPEED}, {max_speed}], "
                f"используется значение по умолчанию"
            )
            return SettingsConstants.DEFAULT_BALL_SPEED
        
        return speed_int
    
    @staticmethod
    def validate_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидирует все настройки.
        
        Args:
            settings: Словарь с настройками
        
        Returns:
            Валидированный словарь настроек
        """
        validated: Dict[str, Any] = {
            "version": int(settings.get("version", SettingsConstants.SETTINGS_VERSION)),
            "ball_speed": SettingsValidator.validate_ball_speed(
                settings.get("ball_speed", SettingsConstants.DEFAULT_BALL_SPEED)
            )
        }
        
        return validated


# ============================================================================
# Интерфейс для работы с файловой системой (для тестирования)
# ============================================================================

class FileSystemInterface(Protocol):
    """Протокол для работы с файловой системой (для тестирования и mock-объектов)"""
    
    def read_json(self, path: Path) -> Dict[str, Any]:
        """Читает JSON из файла"""
        ...
    
    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Записывает JSON в файл"""
        ...
    
    def exists(self, path: Path) -> bool:
        """Проверяет существование файла/директории"""
        ...
    
    def get_size(self, path: Path) -> int:
        """Возвращает размер файла"""
        ...
    
    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Создает директорию"""
        ...


class RealFileSystem:
    """Реальная реализация файловой системы"""
    
    def read_json(self, path: Path) -> Dict[str, Any]:
        """Читает JSON из файла"""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Записывает JSON в файл"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def exists(self, path: Path) -> bool:
        """Проверяет существование файла/директории"""
        return path.exists()
    
    def get_size(self, path: Path) -> int:
        """Возвращает размер файла"""
        return path.stat().st_size
    
    def mkdir(self, path: Path, parents: bool = True, exist_ok: bool = True) -> None:
        """Создает директорию"""
        path.mkdir(parents=parents, exist_ok=exist_ok)


# ============================================================================
# Утилиты для работы с путями
# ============================================================================

def safe_join_path(base: str, *paths: str) -> str:
    """
    Безопасно объединяет пути с проверкой на выход за пределы базовой директории.
    Защита от атак типа "path traversal".
    
    Args:
        base: Базовая директория
        *paths: Дополнительные компоненты пути
    
    Returns:
        Безопасный объединенный путь
    
    Raises:
        ValueError: Если путь выходит за пределы базовой директории
    """
    # Нормализуем базовый путь
    base_path = os.path.normpath(base)
    
    # Объединяем пути
    full_path = os.path.normpath(os.path.join(base, *paths))
    
    # Проверяем, что итоговый путь находится внутри базовой директории
    # Для Windows нужно учитывать разные форматы путей
    if os.name == 'nt':
        # Нормализуем для Windows (приводим к единому формату)
        base_path_win = os.path.normpath(base_path).replace('/', '\\')
        full_path_win = os.path.normpath(full_path).replace('/', '\\')
        
        # Проверяем, что путь начинается с базового пути
        if not full_path_win.startswith(base_path_win):
            raise ValueError(
                f"Путь выходит за пределы базовой директории: {full_path} "
                f"(базовая: {base_path})"
            )
    else:
        # Для Unix-подобных систем
        if not full_path.startswith(base_path):
            raise ValueError(
                f"Путь выходит за пределы базовой директории: {full_path} "
                f"(базовая: {base_path})"
            )
    
    return full_path


# Кэш для пути к файлу настроек
_settings_file_path_cache: Optional[str] = None


def get_game_directory() -> str:
    """
    Определяет каталог игры.
    При запуске из студии разработки использует src/resources,
    иначе использует директорию exe файла.
    
    Returns:
        Путь к каталогу игры (где находятся resources)
    """
    # Проверяем, запущено ли приложение как exe или как скрипт Python
    if not getattr(sys, "frozen", False):
        # Если приложение запущено как скрипт Python (из студии разработки)
        # Файл находится в src/game/, нужно подняться на уровень вверх и войти в src/resources/
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/game/
        src_dir = os.path.dirname(current_dir)  # src/
        resources_dir = os.path.join(src_dir, "resources")  # src/resources/
        return resources_dir
    
    # Для exe файлов используем директорию exe файла (там находятся ресурсы после сборки)
    return os.path.dirname(sys.executable)


def get_settings_file_path() -> str:
    """
    Возвращает полный путь к файлу настроек.
    Создает необходимые директории если их нет.
    Использует кэширование для оптимизации.
    
    Returns:
        Путь к файлу настроек
    
    Raises:
        OSError: При ошибках создания директорий
        ValueError: При обнаружении небезопасного пути
    """
    global _settings_file_path_cache
    
    # Используем кэш если доступен
    if _settings_file_path_cache is not None:
        return _settings_file_path_cache
    
    try:
        game_dir = get_game_directory()
        
        # Безопасное объединение путей с защитой от path traversal
        resources_dir = safe_join_path(game_dir, "resources")
        data_dir = safe_join_path(resources_dir, "data")
        
        # Создаем каталоги, если они не существуют
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                logger.warning(f"Не удалось создать каталог {data_dir}: {e}")
                # Если не удается создать каталог, используем fallback - src/resources/data
                current_dir = os.path.dirname(os.path.abspath(__file__))  # src/game/
                src_dir = os.path.dirname(current_dir)  # src/
                fallback_dir = os.path.join(src_dir, "resources")  # src/resources/
                data_dir = safe_join_path(fallback_dir, "data")
                if not os.path.exists(data_dir):
                    try:
                        os.makedirs(data_dir, exist_ok=True)
                    except (OSError, PermissionError) as e2:
                        logger.error(f"Не удалось создать резервный каталог {data_dir}: {e2}")
                        raise
        
        settings_path = os.path.join(data_dir, "settings.json")
        
        # Кэшируем путь
        _settings_file_path_cache = settings_path
        
        return settings_path
        
    except ValueError as e:
        logger.error(f"Обнаружен небезопасный путь: {e}")
        raise


# ============================================================================
# Менеджер настроек
# ============================================================================

class SettingsManager:
    """
    Менеджер настроек игры с валидацией и версионированием.
    
    Поддерживает:
    - Валидацию загружаемых данных
    - Версионирование настроек
    - Атомарное сохранение
    - Инъекцию зависимостей для тестирования
    - Ленивую загрузку настроек
    - Безопасную работу с путями
    """
    
    def __init__(
        self, 
        settings_file: Optional[str] = None,
        lazy_load: bool = False,
        fs: Optional[FileSystemInterface] = None
    ) -> None:
        """
        Инициализация менеджера настроек.
        
        Args:
            settings_file: Путь к файлу настроек (опционально, для тестирования)
                          Если не указан, используется путь по умолчанию
            lazy_load: Если True, настройки загружаются при первом обращении
            fs: Интерфейс файловой системы (для тестирования)
        """
        self._settings_file = Path(settings_file) if settings_file else Path(get_settings_file_path())
        self._validator = SettingsValidator()
        self._fs = fs if fs is not None else RealFileSystem()
        
        # Настройки по умолчанию
        self._settings: Dict[str, Any] = {
            "version": SettingsConstants.SETTINGS_VERSION,
            "ball_speed": SettingsConstants.DEFAULT_BALL_SPEED
        }
        
        # Флаги состояния
        self._loaded = not lazy_load  # Загружены ли настройки
        self._dirty = False  # Были ли изменения
        
        # Загружаем настройки если не ленивая загрузка
        if not lazy_load:
            self.load_settings()
            # Мигрируем настройки если нужно
            self._migrate_settings()
            # Создаем файл только если его нет
            if not self._fs.exists(self._settings_file):
                self.save_settings()
    
    @property
    def settings(self) -> Dict[str, Any]:
        """
        Свойство для доступа к настройкам с ленивой загрузкой.
        
        Returns:
            Словарь с настройками
        """
        if not self._loaded:
            self.load_settings()
            self._migrate_settings()
            self._loaded = True
        return self._settings
    
    def load_settings(self) -> None:
        """
        Загружает настройки из файла с валидацией.
        
        При ошибках использует настройки по умолчанию.
        """
        if not self._fs.exists(self._settings_file):
            logger.debug(f"Файл настроек не существует: {self._settings_file}")
            return
        
        try:
            # Проверка размера файла (защита от больших файлов)
            file_size = self._fs.get_size(self._settings_file)
            if file_size > SettingsConstants.MAX_SETTINGS_FILE_SIZE:
                logger.error(
                    f"Файл настроек слишком большой: {file_size} байт "
                    f"(максимум: {SettingsConstants.MAX_SETTINGS_FILE_SIZE} байт)"
                )
                raise ValueError(
                    f"Файл настроек превышает максимальный размер "
                    f"({SettingsConstants.MAX_SETTINGS_FILE_SIZE} байт)"
                )
            
            # Загрузка JSON через интерфейс файловой системы
            loaded_settings = self._fs.read_json(self._settings_file)
            
            # Валидация и обновление настроек
            validated = self._validator.validate_settings(loaded_settings)
            self._settings.update(validated)
            self._dirty = False  # После загрузки данные не изменены
            
            logger.debug(f"Настройки загружены из {self._settings_file}")
            
        except json.JSONDecodeError as e:
            logger.warning(
                f"Ошибка парсинга JSON в файле настроек {self._settings_file}: {e}. "
                f"Используются настройки по умолчанию"
            )
            # Используем значения по умолчанию
        except OSError as e:
            logger.error(
                f"Ошибка доступа к файлу настроек {self._settings_file}: {e}. "
                f"Используются настройки по умолчанию"
            )
            # Не пробрасываем, используем значения по умолчанию
        except ValueError as e:
            logger.error(f"Ошибка валидации настроек: {e}. Используются настройки по умолчанию")
            # Используем значения по умолчанию
    
    def save_settings(self, force: bool = False) -> None:
        """
        Сохраняет настройки в файл атомарно.
        Сохраняет только если были изменения (если не указан force).
        
        Args:
            force: Принудительное сохранение даже если ничего не изменилось
        
        Raises:
            OSError: При ошибках записи файла
        """
        # Проверяем, нужно ли сохранять
        if not force:
            # Если данные не изменены, пропускаем сохранение
            if not self._dirty:
                logger.debug("Настройки не изменены, пропускаем сохранение")
                return
            
            # Проверяем, изменились ли настройки по сравнению с файлом
            if self._fs.exists(self._settings_file):
                try:
                    existing = self._fs.read_json(self._settings_file)
                    if existing == self._settings:
                        logger.debug("Настройки не изменились, пропускаем сохранение")
                        self._dirty = False
                        return
                except (OSError, json.JSONDecodeError):
                    pass  # Если не удалось прочитать, сохраняем
        
        try:
            # Создаем директорию если нужно
            self._fs.mkdir(self._settings_file.parent, parents=True, exist_ok=True)
            
            # Атомарное сохранение через временный файл
            temp_file = self._settings_file.with_suffix('.tmp')
            
            # Сохраняем во временный файл через интерфейс
            self._fs.write_json(temp_file, self._settings)
            
            # Атомарная замена (если поддерживается файловой системой)
            try:
                temp_file.replace(self._settings_file)
            except AttributeError:
                # Fallback для старых версий pathlib
                import shutil
                shutil.move(str(temp_file), str(self._settings_file))
            
            self._dirty = False  # Данные сохранены
            logger.debug(f"Настройки сохранены в {self._settings_file}")
            
        except OSError as e:
            logger.error(f"Ошибка сохранения настроек в {self._settings_file}: {e}")
            # Удаляем временный файл если он остался
            temp_file = self._settings_file.with_suffix('.tmp')
            if self._fs.exists(temp_file):
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise
    
    def _migrate_settings(self) -> None:
        """
        Мигрирует настройки со старых версий на текущую.
        
        Вызывается автоматически при загрузке настроек.
        """
        current_version = self._settings.get("version", 0)
        
        if current_version < SettingsConstants.SETTINGS_VERSION:
            logger.info(
                f"Миграция настроек с версии {current_version} "
                f"на {SettingsConstants.SETTINGS_VERSION}"
            )
            
            # Здесь можно добавить логику миграции для разных версий
            # Например:
            # if current_version < 2:
            #     # Миграция с версии 1 на 2
            #     # Добавляем новые поля, преобразуем старые и т.д.
            #     pass
            
            # Обновляем версию
            self._settings["version"] = SettingsConstants.SETTINGS_VERSION
            self._dirty = True  # Отмечаем как измененные для сохранения
            self.save_settings(force=True)
    
    def get_ball_speed(self) -> int:
        """
        Возвращает скорость мяча.
        
        Returns:
            Скорость мяча (1-10 для ручного режима, 1-8 для авто)
        """
        speed = self.settings.get("ball_speed", SettingsConstants.DEFAULT_BALL_SPEED)
        return self._validator.validate_ball_speed(speed)
    
    def set_ball_speed(self, speed: int, auto_mode: bool = False) -> None:
        """
        Устанавливает скорость мяча с учетом режима игры.
        
        Ограничения скорости основаны на ограничении времени расчета:
        - FPS = 60 (16.67 мс на кадр)
        - Расчет траектории: ~1-5 мс
        - Запас для стабильности: ~5 мс
        - Максимальная скорость: 8 для авторежима, 10 для ручного режима
        
        Args:
            speed: Скорость мяча (1-10 для ручного режима, 1-8 для авто)
            auto_mode: Режим игры (True - авто, False - ручной)
        
        Raises:
            ValueError: Если скорость вне допустимого диапазона
        """
        # Используем метод из констант для проверки
        if not SettingsConstants.validate_ball_speed_range(speed, auto_mode):
            max_speed = SettingsConstants.get_max_ball_speed(auto_mode)
            mode_text = "авторежиме" if auto_mode else "ручном режиме"
            raise ValueError(
                f"Скорость мяча должна быть в диапазоне от "
                f"{SettingsConstants.MIN_BALL_SPEED} до {max_speed} в {mode_text}"
            )
        
        self._settings["ball_speed"] = speed
        self._dirty = True  # Отмечаем как измененные
        self.save_settings()


# ============================================================================
# Обратная совместимость
# ============================================================================

# Для обратной совместимости сохраняем глобальную переменную
# (но она больше не используется внутри класса)
SETTINGS_FILE: str = get_settings_file_path()
