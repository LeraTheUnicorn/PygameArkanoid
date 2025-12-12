"""
Система управления рекордами игры Арканоид
Сохраняет и загружает результаты игроков в файл
"""

import json
import os
import sys
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Настройка логирования
# Используем стандартный logger, root logger будет настроен через ai.logging_config
logger = logging.getLogger(__name__)
# Устанавливаем уровень из корневого логгера (будет настроен через setup_root_logger)
# На случай, если root logger еще не настроен, устанавливаем уровень напрямую
if logger.level == logging.NOTSET:
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
# КОНСТАНТЫ
# ============================================================================

# Ограничения игры
MIN_SCORE: int = 0
MAX_SCORE: int = 50
MAX_TIME_SECONDS: int = 3599  # 59:59
TOP_SCORES_LIMIT: int = 10
MAX_PLAYER_NAME_LENGTH: int = 20

# Форматирование таблицы
TABLE_WIDTH: int = 69
TABLE_HEADER: str = "ТОП-10 РЕЗУЛЬТАТОВ:"

# Разрешенные символы для имени игрока (буквы, цифры, пробел, дефис, подчеркивание)
ALLOWED_NAME_CHARS: str = r"^[a-zA-Zа-яА-ЯёЁ0-9\s\-_]+$"


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def validate_player_name(name: str) -> str:
    """
    Валидирует и санитизирует имя игрока.
    
    Args:
        name: Исходное имя игрока
        
    Returns:
        Очищенное и валидированное имя
        
    Raises:
        ValueError: Если имя пустое или содержит только пробелы
        TypeError: Если имя не является строкой
    """
    if not isinstance(name, str):
        raise TypeError(f"Имя должно быть строкой, получен тип: {type(name).__name__}")
    
    # Удаляем ведущие и завершающие пробелы
    name = name.strip()
    
    if not name:
        raise ValueError("Имя игрока не может быть пустым")
    
    # Удаляем опасные символы (пути, управляющие символы, HTML-теги)
    # Оставляем только буквы, цифры, пробелы, дефисы и подчеркивания
    safe_name = re.sub(r'[^\w\s\-_]', '', name, flags=re.UNICODE)
    
    # Удаляем множественные пробелы
    safe_name = re.sub(r'\s+', ' ', safe_name)
    
    # Обрезаем до максимальной длины
    safe_name = safe_name[:MAX_PLAYER_NAME_LENGTH]
    
    if not safe_name:
        raise ValueError("Имя игрока после очистки стало пустым")
    
    return safe_name


def get_game_directory() -> str:
    """
    Определяет каталог игры с поддержкой кроссплатформенности.
    
    Для разработки: src/resources/
    Для exe: каталог установки (Windows: LOCALAPPDATA, Linux/Mac: XDG_DATA_HOME или ~/.local/share)
    
    Returns:
        Путь к каталогу игры
    """
    # Для разработки (запуск из IDE) используем src/resources/
    if not getattr(sys, "frozen", False):
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/game/
        src_dir = os.path.dirname(current_dir)  # src/
        resources_dir = os.path.join(src_dir, "resources")  # src/resources/
        return resources_dir

    # Для exe файлов используем системные каталоги
    if sys.platform == "win32":
        # Windows: используем LOCALAPPDATA
        try:
            localappdata = os.environ.get("LOCALAPPDATA")
            if localappdata:
                game_dir = os.path.join(localappdata, "Games", "Arkanoid")
                return game_dir
        except (KeyError, OSError) as e:
            logger.warning(f"Не удалось получить LOCALAPPDATA: {e}")
    else:
        # Linux/Mac: используем XDG_DATA_HOME или ~/.local/share
        try:
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if xdg_data_home:
                game_dir = os.path.join(xdg_data_home, "Arkanoid")
            else:
                home = os.path.expanduser("~")
                game_dir = os.path.join(home, ".local", "share", "Arkanoid")
            return game_dir
        except (KeyError, OSError) as e:
            logger.warning(f"Не удалось получить путь к данным пользователя: {e}")

    # Fallback для exe: директория exe файла
    return os.path.dirname(sys.executable)


def get_highscores_file_path(custom_path: Optional[str] = None) -> str:
    """
    Возвращает полный путь к файлу рекордов.
    
    Args:
        custom_path: Опциональный пользовательский путь (для тестирования)
        
    Returns:
        Полный путь к файлу рекордов
    """
    if custom_path:
        return custom_path
    
    game_dir = get_game_directory()
    resources_dir = os.path.join(game_dir, "resources")
    data_dir = os.path.join(resources_dir, "data")

    # Создаем каталоги, если они не существуют
    try:
        os.makedirs(data_dir, exist_ok=True)
    except (OSError, PermissionError) as e:
        logger.warning(f"Не удалось создать каталог {data_dir}: {e}")
        # Если не удается создать каталог, используем fallback - src/resources/data
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/game/
        src_dir = os.path.dirname(current_dir)  # src/
        fallback_resources = os.path.join(src_dir, "resources")  # src/resources/
        data_dir = os.path.join(fallback_resources, "data")
        try:
            os.makedirs(data_dir, exist_ok=True)
        except (OSError, PermissionError) as e2:
            logger.warning(f"Не удалось создать fallback каталог {data_dir}: {e2}")
            # Последний fallback: каталог без resources/data
            data_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(data_dir, "highscores.json")


def validate_score_data(score_data: Any) -> bool:
    """
    Валидирует структуру записи рекорда.
    
    Args:
        score_data: Данные для проверки
        
    Returns:
        True если данные валидны, False иначе
    """
    if not isinstance(score_data, dict):
        return False
    
    required_fields = {"player_name", "score", "time_seconds", "time_formatted", "date"}
    if not required_fields.issubset(score_data.keys()):
        return False
    
    # Проверка типов
    if not isinstance(score_data["player_name"], str):
        return False
    if not isinstance(score_data["score"], int):
        return False
    if not isinstance(score_data["time_seconds"], int):
        return False
    if not isinstance(score_data["time_formatted"], str):
        return False
    if not isinstance(score_data["date"], str):
        return False
    
    # Проверка диапазонов
    if not (MIN_SCORE <= score_data["score"] <= MAX_SCORE):
        return False
    if not (0 <= score_data["time_seconds"] <= MAX_TIME_SECONDS):
        return False
    
    return True


# Путь к файлу рекордов (теперь с полным путем)
HIGHSCORES_FILE: str = get_highscores_file_path()


# ============================================================================
# КЛАСС МЕНЕДЖЕРА РЕКОРДОВ
# ============================================================================


class HighScoreManager:
    """
    Менеджер для управления рекордами игры.
    
    Обеспечивает загрузку, сохранение и управление списком рекордов.
    Поддерживает максимум TOP_SCORES_LIMIT записей.
    """
    
    def __init__(self, highscores_file: Optional[str] = None) -> None:
        """
        Инициализирует менеджер рекордов.
        
        Args:
            highscores_file: Опциональный путь к файлу рекордов (для тестирования)
        """
        self.highscores_file: str = highscores_file or HIGHSCORES_FILE
        self.highscores: List[Dict[str, Any]] = []
        self.load_highscores()

    def load_highscores(self) -> None:
        """
        Загружает рекорды из файла с валидацией данных.
        
        В случае ошибок инициализирует пустой список рекордов.
        """
        try:
            if not os.path.exists(self.highscores_file):
                self.highscores = []
                return
            
            with open(self.highscores_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Проверяем, что данные - это список
            if not isinstance(data, list):
                logger.warning(f"Файл {self.highscores_file} не содержит список, инициализируем пустой список")
                self.highscores = []
                return
            
            # Валидируем каждую запись
            validated_scores = []
            for i, score_data in enumerate(data):
                if validate_score_data(score_data):
                    validated_scores.append(score_data)
                else:
                    logger.warning(f"Пропущена невалидная запись #{i} в файле рекордов")
            
            self.highscores = validated_scores
            # Сортируем и обрезаем до лимита
            self.sort_highscores()
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON в файле {self.highscores_file}: {e}")
            self.highscores = []
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Ошибка чтения файла {self.highscores_file}: {e}")
            self.highscores = []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке рекордов: {e}", exc_info=True)
            self.highscores = []

    def save_highscores(self) -> None:
        """
        Сохраняет рекорды в файл.
        
        В случае ошибки пытается сохранить в fallback файл.
        """
        try:
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.highscores_file), exist_ok=True)
            
            with open(self.highscores_file, "w", encoding="utf-8") as f:
                json.dump(self.highscores, f, ensure_ascii=False, indent=2)
                
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Ошибка сохранения рекордов в {self.highscores_file}: {e}")
            # Пытаемся сохранить в src/local_game_files как fallback
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))  # src/game/
                src_dir = os.path.dirname(current_dir)  # src/
                fallback_dir = os.path.join(src_dir, "local_game_files")  # src/local_game_files/
                os.makedirs(fallback_dir, exist_ok=True)
                fallback_path = os.path.join(fallback_dir, "highscores_backup.json")
                
                with open(fallback_path, "w", encoding="utf-8") as f:
                    json.dump(self.highscores, f, ensure_ascii=False, indent=2)
                logger.info(f"Рекорды сохранены в fallback файл: {fallback_path}")
            except (IOError, OSError, PermissionError) as fallback_error:
                logger.error(f"Не удалось сохранить рекорды даже в fallback: {fallback_error}")

    def add_score(self, player_name: str, score: int, game_time_seconds: int) -> bool:
        """
        Добавляет новый результат в список рекордов.
        
        Args:
            player_name: Имя игрока (будет валидировано и санитизировано)
            score: Количество очков (0-50)
            game_time_seconds: Время игры в секундах (максимум 3599)
            
        Returns:
            True если результат попал в топ-10 и сохранен, False если не попал
            
        Raises:
            ValueError: Если параметры вне допустимого диапазона
            TypeError: Если имя игрока не является строкой
        """
        # Валидация и санитизация имени
        player_name = validate_player_name(player_name)
        
        # Валидация очков
        if not isinstance(score, int):
            raise TypeError(f"Очки должны быть целым числом, получен тип: {type(score).__name__}")
        if not (MIN_SCORE <= score <= MAX_SCORE):
            raise ValueError(
                f"Очки должны быть в диапазоне от {MIN_SCORE} до {MAX_SCORE}. Получено: {score}"
            )

        # Валидация и ограничение времени
        if not isinstance(game_time_seconds, int):
            raise TypeError(f"Время должно быть целым числом, получен тип: {type(game_time_seconds).__name__}")
        if game_time_seconds < 0:
            game_time_seconds = 0
        elif game_time_seconds > MAX_TIME_SECONDS:
            game_time_seconds = MAX_TIME_SECONDS

        # Форматирование времени в М:СС формат с ведущими нулями для секунд
        game_time_formatted = f"{game_time_seconds // 60}:{game_time_seconds % 60:02d}"

        new_score = {
            "player_name": player_name,
            "score": score,
            "time_seconds": game_time_seconds,
            "time_formatted": game_time_formatted,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Оптимизированная проверка: попадет ли результат в топ-10
        # Вместо полной сортировки проверяем минимальный порог
        if len(self.highscores) >= TOP_SCORES_LIMIT:
            # Список уже отсортирован (после load_highscores)
            # Проверяем, лучше ли новый результат последнего в топ-10
            worst_score = self.highscores[-1]
            
            # Сравниваем по приоритету: очки (убывание), время (возрастание), имя (возрастание)
            if score < worst_score["score"]:
                return False
            elif score == worst_score["score"]:
                if game_time_seconds > worst_score["time_seconds"]:
                    return False
                elif game_time_seconds == worst_score["time_seconds"]:
                    if player_name > worst_score["player_name"]:
                        return False

        # Результат попал в топ-10, добавляем и сохраняем
        self.highscores.append(new_score)
        self.sort_highscores()  # Сортируем и обрезаем до лимита
        self.save_highscores()
        return True

    def sort_highscores(self) -> None:
        """
        Сортирует рекорды: сначала по очкам (по убыванию), 
        затем по времени (по возрастанию), затем по имени (по возрастанию).
        Обрезает список до TOP_SCORES_LIMIT записей.
        """
        def sort_key(item: Dict[str, Any]) -> tuple[int, int, str]:
            """Ключ сортировки: (-очки, время, имя)"""
            return (-item["score"], item["time_seconds"], item["player_name"])

        self.highscores.sort(key=sort_key)
        # Обрезаем до лимита
        self.highscores = self.highscores[:TOP_SCORES_LIMIT]

    def get_top_scores(self) -> List[Dict[str, Any]]:
        """
        Возвращает топ рекордов.
        
        Returns:
            Список до TOP_SCORES_LIMIT записей, отсортированный по убыванию очков
        """
        return self.highscores[:TOP_SCORES_LIMIT]

    def is_top_score(self, score: int) -> bool:
        """
        Проверяет, попадает ли результат в топ-10.
        
        Args:
            score: Количество очков для проверки
            
        Returns:
            True если результат попадает в топ-10, False иначе
        """
        # Проверяем диапазон очков
        if not isinstance(score, int):
            return False
        if not (MIN_SCORE <= score <= MAX_SCORE):
            return False

        # Если в списке меньше 10 записей, любой валидный результат попадет
        if len(self.highscores) < TOP_SCORES_LIMIT:
            return True
        
        # Список отсортирован, проверяем последний элемент
        worst_score = self.highscores[-1]["score"]
        return score >= worst_score

    def display_highscores(self) -> str:
        """
        Возвращает строку для отображения таблицы рекордов с заголовком.
        
        Returns:
            Отформатированная строка с таблицей рекордов
        """
        if not self.highscores:
            return "Пока нет рекордов"

        # Формируем полную таблицу с заголовком
        result = f"{TABLE_HEADER}\n"
        result += "=" * TABLE_WIDTH + "\n"
        result += "Место | Игрок                | Очки | Время  \n"
        result += "=" * TABLE_WIDTH + "\n"

        # Данные с точным форматированием каждой колонки
        for i, score_data in enumerate(self.highscores, 1):
            # Форматирование места
            if i < 10:
                place = f"   {i}.  "  # 3 пробела + число + точка + 2 пробела
            else:
                place = f"  {i}.  "  # 2 пробела + число + точка + 2 пробела

            # Форматирование имени игрока: 20 символов, выравнивание слева
            player_name = score_data["player_name"]
            player = f"{player_name[:MAX_PLAYER_NAME_LENGTH]:<{MAX_PLAYER_NAME_LENGTH}}"

            # Форматирование очков: 3 символа, выравнивание справа
            score = f"{score_data['score']:>3}"

            # Форматирование времени: 5 символов, выравнивание справа
            time = f"{score_data['time_formatted']:>5}"

            # Собираем строку
            row = f"{place}| {player}| {score}  | {time}"
            result += row + "\n"

        return result
