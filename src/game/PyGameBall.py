# Игра Арканоид
# Версия импортируется из централизованного файла version.py


import os
import warnings
from contextlib import contextmanager
from typing import Generator

# Контекстный менеджер для ограниченного подавления предупреждений
@contextmanager
def suppress_pkg_resources_warnings() -> Generator[None, None, None]:
    """Временно подавляет предупреждения о pkg_resources от pygame в ограниченной области"""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=UserWarning)
        yield

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Скрыть сообщение поддержки pygame

import random
import time
import numpy as np
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any

# Исправление для запуска файла напрямую: добавляем корневую директорию проекта в sys.path
if __name__ == "__main__":
    # Получаем путь к директории, содержащей этот файл
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    # Поднимаемся на два уровня вверх: src/game -> src -> project_root
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# КРИТИЧНО: Настраиваем логирование ПЕРЕД импортом всех модулей
# Это гарантирует, что ВСЕ модули используют централизованную конфигурацию
try:
    from src.ai.logging_config import setup_root_logger
    setup_root_logger()
except (ImportError, ModuleNotFoundError):
    # Если модуль недоступен, настраиваем базовое логирование
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Импортируем pygame с ограниченным подавлением предупреждений
with suppress_pkg_resources_warnings():
    import pygame

# Импорты с поддержкой как относительных, так и абсолютных путей
try:
    # Пытаемся использовать относительные импорты (когда запускается как модуль)
    from .highscores import HighScoreManager
    from .settings import SettingsManager
    from .game_models import Ball, Paddle
except ImportError:
    # Если относительные импорты не работают (когда запускается напрямую), используем абсолютные
    from src.game.highscores import HighScoreManager
    from src.game.settings import SettingsManager
    from src.game.game_models import Ball, Paddle

from src.ai.ai_player import AIPlayer


def resource_path(relative_path: str) -> str:
    """
    Получает абсолютный путь к ресурсу, работает как в разработке, так и в exe.
    
    Кросс-платформенная функция для получения правильного пути к ресурсам.
    Использует os.path.join для корректной работы на разных ОС.
    
    Args:
        relative_path: Относительный путь к ресурсу (например, "audio/file.ogg" или "images/d2.gif")
                      Путь должен быть относительно src/resources/
        
    Returns:
        Абсолютный путь к ресурсу, нормализованный для текущей ОС
        
    Note:
        В режиме разработки использует директорию src/resources/.
        В скомпилированном exe (PyInstaller) ресурсы находятся в _MEIPASS/src/resources/.
    """
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
        # В exe ресурсы находятся в src/resources/ (как указано в --add-data)
        resources_path = os.path.join(base_path, "src", "resources")
    except AttributeError:
        # В режиме разработки файл находится в src/game/, нужно подняться на уровень вверх и войти в src/resources/
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/game/
        src_dir = os.path.dirname(current_dir)  # src/
        resources_path = os.path.join(src_dir, "resources")  # src/resources/

    # Используем os.path.join для кросс-платформенной совместимости
    # и нормализуем путь для корректной работы на всех ОС
    full_path = os.path.join(resources_path, relative_path)
    return os.path.normpath(full_path)


# Импортируем конфигурацию из централизованного файла
try:
    from .game_config import (
        BALL_SIZE,
        BALL_SPEED_DEFAULT,
        BRICK_COLS,
        BRICK_HEIGHT,
        BRICK_OFFSET_TOP,
        BRICK_PADDING,
        BRICK_ROWS,
        BRICK_WIDTH,
        FPS,
        MAX_LIVES,
        PADDLE_HEIGHT,
        PADDLE_SPEED,
        PADDLE_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )
except ImportError:
    from src.game.game_config import (
        BALL_SIZE,
        BALL_SPEED_DEFAULT,
        BRICK_COLS,
        BRICK_HEIGHT,
        BRICK_OFFSET_TOP,
        BRICK_PADDING,
        BRICK_ROWS,
        BRICK_WIDTH,
        FPS,
        MAX_LIVES,
        PADDLE_HEIGHT,
        PADDLE_SPEED,
        PADDLE_WIDTH,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
        SEPARATION_ZONE_BOTTOM,
        SEPARATION_ZONE_TOP,
    )


def generate_tone_sound(
    frequency: float, duration: float, sample_rate: int = 44100, volume: float = 0.3
) -> pygame.mixer.Sound:
    """
    Генерирует короткий тональный звук для звуковых эффектов.
    
    Создает синусоидальную волну с гармониками и затуханием для более естественного звука.
    
    Args:
        frequency: Частота звука в герцах
        duration: Длительность звука в секундах
        sample_rate: Частота дискретизации (по умолчанию 44100 Гц)
        volume: Громкость звука от 0.0 до 1.0 (по умолчанию 0.3)
        
    Returns:
        pygame.mixer.Sound объект со сгенерированным звуком
    """
    frames = int(duration * sample_rate)
    t = np.linspace(0, duration, frames)

    # Генерируем синусоидальную волну с небольшим количеством гармоник для более богатого звука
    wave = np.sin(2 * np.pi * frequency * t)
    wave += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)  # Первая гармоника
    wave += 0.1 * np.sin(2 * np.pi * frequency * 3 * t)  # Вторая гармоника

    # Добавляем затухание
    envelope = np.exp(-3 * t)  # Быстрое затухание
    wave = wave * envelope

    # Нормализуем и приводим к 16-битному формату
    wave = np.clip(wave * volume, -1.0, 1.0)
    wave_16bit = (wave * 32767).astype(np.int16)

    # Создаем pygame Sound объект
    stereo_wave = np.zeros((len(wave_16bit), 2), dtype=np.int16)
    stereo_wave[:, 0] = wave_16bit
    stereo_wave[:, 1] = wave_16bit

    return pygame.sndarray.make_sound(stereo_wave)


def is_valid_player_name_char(char: str) -> bool:
    """
    Проверяет, является ли символ допустимым для имени игрока.
    
    Args:
        char: Символ для проверки
        
    Returns:
        True если символ допустим (латинские или кириллические буквы), False иначе
    """
    if not char or len(char) != 1:  # Проверяем пустые строки и многосимвольные строки
        return False
    # Разрешаем только буквы (латинские и кириллические)
    # isalpha() поддерживает Unicode, включая кириллицу
    return char.isalpha() and not char.isspace()


def generate_paddle_sound() -> pygame.mixer.Sound:
    """
    Генерирует звук отскока от платформы.
    
    Returns:
        pygame.mixer.Sound объект со звуком отскока (нота E4, 330 Гц)
    """
    return generate_tone_sound(330, 0.15, volume=0.4)  # E4 - 330 Гц


def get_player_name(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    highscore_manager: HighScoreManager,
) -> tuple[str, bool, bool, bool, bool]:
    """
    Получает имя игрока через ввод с клавиатуры.
    
    Отображает экран ввода имени с возможностью переключения режимов игры.
    Поддерживает валидацию ввода (только буквы).
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для обычного текста
        big_font: Шрифт для заголовков
        highscore_manager: Менеджер рекордов для отображения таблицы
        
    Returns:
        Кортеж из 5 элементов:
        - Имя игрока (str)
        - Состояние звука (bool)
        - Флаг выхода из игры (bool)
        - Флаг авторежима (bool, активируется клавишей 0)
        - Флаг режима обучения (bool, активируется клавишей 8)
    """
    input_text = ""
    input_active = True
    sound_enabled = True
    exit_game = False
    auto_mode = False  # Всегда начинаем с сброса флага авторежима
    training_mode = False  # Режим обучения (клавиша 8)

    while input_active:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game = True
                return (
                    "",
                    sound_enabled,
                    exit_game,
                    False,
                    False,
                )  # Выход из игры по крестику
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Имя обязательно для ввода!
                    cleaned_name = input_text.strip()
                    if not cleaned_name:
                        # Имя пустое - не запускаем игру, показываем предупреждение
                        # Игрок должен либо ввести имя, либо нажать 0 для robot
                        input_text = ""  # Очищаем поле для повторного ввода
                        continue  # Продолжаем ввод
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif (
                    len(input_text) < 20
                    and event.unicode
                    and is_valid_player_name_char(event.unicode)
                ):  # Ограничение длины имени и допустимых символов
                    input_text += event.unicode
                elif event.key == pygame.K_ESCAPE:
                    # Выход из игры
                    return "", sound_enabled, True, False, False
                elif event.key == pygame.K_m:
                    # Переключение всех звуков (музыки и эффектов)
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True
                elif event.key == 48:
                    # Авторежим - запуск игры сразу после нажатия 0
                    input_text = "robot"
                    auto_mode = True
                    input_active = False
                    # Не выводим в exe файле
                    if not getattr(sys, "frozen", False):
                        print(
                            f"Авторежим активирован через клавишу 0, имя: {input_text}"
                        )  # Отладочная информация
                elif event.key == 56:  # Клавиша 8
                    # Режим обучения - запуск игры сразу после нажатия 8
                    input_text = "training"
                    auto_mode = True
                    training_mode = True
                    input_active = False
                    # Не выводим в exe файле
                    if not getattr(sys, "frozen", False):
                        print(
                            f"Режим обучения активирован через клавишу 8, имя: {input_text}"
                        )  # Отладочная информация

        # Отрисовка экрана
        screen.fill((10, 10, 30))

        # Заголовок
        title = big_font.render("Введите ваше имя:", True, (255, 255, 255))
        title_rect = title.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100)
        )
        screen.blit(title, title_rect)

        # Поле ввода
        input_surface = font.render(input_text, True, (255, 255, 255))
        input_rect = input_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
        )

        # Рамка поля ввода (красная для пустого поля)
        if not input_text.strip():
            pygame.draw.rect(
                screen, (255, 100, 100), input_rect.inflate(20, 10), 2
            )  # Красная рамка для пустого поля
        else:
            pygame.draw.rect(
                screen, (255, 255, 255), input_rect.inflate(20, 10), 2
            )  # Белая рамка для заполненного
        screen.blit(input_surface, input_rect)

        # Подсказка
        render_colored_hint(
            screen,
            font,
            "Введите имя игрока и нажмите Enter",
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 20),
        )

        # Подсказка о звуке
        render_colored_hint(
            screen,
            font,
            "Нажмите M для отключения всех звуков",
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 50),
        )

        # Подсказка о настройках
        render_colored_hint(
            screen,
            font,
            "Для управления скоростью мяча нажимайте ↑ ↓",
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 80),
        )

        # Подсказка об авторежиме
        render_colored_hint(
            screen,
            font,
            "0 - авторежим",
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 110),
        )

        # Подсказка о режиме обучения
        render_colored_hint(
            screen,
            font,
            "8 - режим обучения ИИ",
            (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 140),
        )

        pygame.display.flip()

    # ФИНАЛЬНАЯ ВАЛИДАЦИЯ: убеждаемся, что имя корректно
    final_name = input_text.strip()
    if not final_name:
        final_name = "robot"  # Крайний случай для авторежима

    return final_name, sound_enabled, exit_game, auto_mode, training_mode


def show_highscores(
    screen: pygame.Surface,
    font: pygame.font.Font,
    highscore_manager: HighScoreManager,
    exit_on_esc: bool = False,
) -> tuple[bool, bool]:
    """
    Отображает таблицу рекордов.
    Возвращает (состояние_звука, exit_game).
    Если exit_on_esc=True, то ESC выходит из игры полностью, иначе возвращает False.
    """
    # Создаем моноширинный шрифт для правильного отображения таблицы
    # Используем список резервных шрифтов для кросс-платформенной совместимости
    mono_font_names = ["consolas", "courier new", "courier", "monospace", "liberation mono"]
    mono_font = None
    
    for font_name in mono_font_names:
        try:
            mono_font = pygame.font.SysFont(font_name, 18)
            break
        except (OSError, ValueError):
            continue
    
    # Если ни один системный шрифт не доступен, используем встроенный моноширинный шрифт pygame
    if mono_font is None:
        try:
            mono_font = pygame.font.Font(pygame.font.get_default_font(), 18)
        except:
            mono_font = font  # Последний резерв - используем обычный шрифт

    # Состояние звука
    sound_enabled = True

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return sound_enabled, True  # Выход из игры по крестику
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if exit_on_esc:
                        return sound_enabled, True  # Выход из игры
                    else:
                        waiting = False  # Возвращаемся назад
                elif event.key == pygame.K_BACKSPACE:
                    waiting = False  # Возвращаемся назад
                elif event.key == pygame.K_m:
                    # Переключение всех звуков
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True

        # Отрисовка экрана рекордов
        screen.fill((10, 10, 30))

        # Заголовок
        title = font.render("ТАБЛИЦА РЕКОРДОВ", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 30))
        screen.blit(title, title_rect)

        # Получаем отформатированные данные для отображения
        highscores = highscore_manager.get_top_scores()

        if not highscores:
            no_scores = font.render("Пока нет рекордов", True, (200, 200, 200))
            no_scores_rect = no_scores.get_rect(center=(SCREEN_WIDTH // 2, 150))
            screen.blit(no_scores, no_scores_rect)
        else:
            # Линии разделителя
            separator_line = "=" * 69
            separator_surf = mono_font.render(separator_line, True, (150, 150, 150))
            separator_rect = separator_surf.get_rect(center=(SCREEN_WIDTH // 2, 70))
            screen.blit(separator_surf, separator_rect)

            # Заголовки колонок
            headers = "   Место | Игрок               | Очки | Время  "
            headers_surf = mono_font.render(headers, True, (255, 255, 255))
            headers_rect = headers_surf.get_rect(center=(SCREEN_WIDTH // 2, 95))
            screen.blit(headers_surf, headers_rect)

            # Вторая линия разделителя
            separator_surf2 = mono_font.render(separator_line, True, (150, 150, 150))
            separator_rect2 = separator_surf2.get_rect(center=(SCREEN_WIDTH // 2, 120))
            screen.blit(separator_surf2, separator_rect2)

            # Данные таблицы
            y_offset = 145
            for i, score_data in enumerate(highscores, 1):
                # Форматируем данные точно как в правильном файле
                if i < 10:
                    place = f"   {i}.  "
                else:
                    place = f"  {i}.  "

                player_name = score_data["player_name"]
                player = f"{player_name[:20]:<20}"
                score = f"{score_data['score']:>3}"
                time = f"{score_data['time_formatted']:>5}"

                # Собираем строку
                row = f"{place}| {player}| {score}  | {time}"

                # Отображаем строку
                row_surf = mono_font.render(row, True, (255, 255, 255))
                row_rect = row_surf.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(row_surf, row_rect)

                y_offset += 25

        # Подсказки для возврата
        if exit_on_esc:
            render_colored_hint(
                screen,
                font,
                "Backspace - возврат, ESC - выход из игры",
                (SCREEN_WIDTH // 2 - 180, SCREEN_HEIGHT - 70),
            )
        else:
            render_colored_hint(
                screen,
                font,
                "BackSpace - возврат",
                (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 70),
            )

        pygame.display.flip()

    return sound_enabled, False  # Возвращаемся, не выходя из игры


def trigger_instant_victory(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    score: int,
    player_name: str,
    game_time_seconds: int,
    highscore_manager: "HighScoreManager",
    settings_manager: "SettingsManager",
    ball: "Ball",
    auto_mode: bool = False,
) -> tuple[bool, bool, bool]:
    """
    Показывает заставку победы и экран результатов.
    Используется для немедленной победы (например, при тройном нажатии "1").
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для обычного текста
        big_font: Шрифт для заголовков
        score: Финальный счет игрока
        player_name: Имя игрока
        game_time_seconds: Время игры в секундах
        highscore_manager: Менеджер рекордов
        settings_manager: Менеджер настроек игры
        ball: Объект мяча
        auto_mode: Флаг авторежима
        
    Returns:
        Кортеж из 3 элементов:
        - Состояние звука (bool)
        - Флаг перезапуска игры (bool)
        - Флаг выхода из игры (bool)
    """
    # Показываем заставку победы
    if not getattr(sys, "frozen", False):
        print("[TRIGGER VICTORY] Вызываем show_victory_splash...")
    try:
        show_victory_splash(screen, duration_seconds=5.0)
        if not getattr(sys, "frozen", False):
            print("[TRIGGER VICTORY] show_victory_splash завершена")
    except Exception as e:
        if not getattr(sys, "frozen", False):
            print(f"[TRIGGER VICTORY] ОШИБКА в show_victory_splash: {e}")
            import traceback
            traceback.print_exc()
    
    # Показываем экран результатов
    return show_game_results(
        screen,
        font,
        big_font,
        score,
        player_name,
        game_time_seconds,
        highscore_manager,
        settings_manager,
        ball,
        auto_mode,
    )


def show_victory_splash(screen: pygame.Surface, duration_seconds: float = 5.0) -> None:
    # Сохраняем исходный размер экрана в начале функции
    initial_screen_size = screen.get_size()
    if not getattr(sys, "frozen", False):
        print(f"[VICTORY SPLASH] Начальный размер экрана при входе в функцию: {initial_screen_size}")
    """
    Показывает заставку победы с анимированным изображением.
    Использует Pyglet для загрузки анимированного GIF.
    
    Args:
        screen: Поверхность pygame для отрисовки
        duration_seconds: Длительность показа заставки в секундах (по умолчанию 5)
    """
    if not getattr(sys, "frozen", False):
        print(f"[VICTORY SPLASH] Начало функции show_victory_splash, длительность: {duration_seconds} сек")
    
    # Загружаем изображение
    image_path = resource_path("images/d2.gif")
    
    if not getattr(sys, "frozen", False):
        print(f"[VICTORY SPLASH] Путь к изображению: {image_path}")
    
    try:
        # Используем PIL для загрузки и изменения размера GIF (НЕ МЕНЯЕМ размер окна!)
        try:
            from PIL import Image, ImageSequence
            
            # Получаем размеры экрана (НЕ МЕНЯЕМ их!)
            screen_width, screen_height = screen.get_size()
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Размер экрана: {screen_width}x{screen_height} (НЕ МЕНЯЕМ!)")
                print(f"[VICTORY SPLASH] Загружаем GIF через PIL: {image_path}")
            
            # Определяем правильный фильтр для изменения размера (совместимость с разными версиями Pillow)
            # Pillow >= 9.0.0 использует Image.Resampling.LANCZOS, старые версии - Image.LANCZOS
            if hasattr(Image, 'Resampling'):
                lanczos_filter = Image.Resampling.LANCZOS
            else:
                # Для старых версий Pillow используем getattr для безопасного доступа
                # Совместимость со старыми версиями Pillow, где LANCZOS это int
                lanczos_filter: Any = getattr(Image, 'LANCZOS', 1)  # type: ignore[no-redef]  # 1 - это числовая константа LANCZOS
            
            # Загружаем GIF с помощью PIL
            with Image.open(image_path) as im:
                # Получаем длительность кадров из метаданных
                default_duration = im.info.get("duration", 100)
                
                # Изменяем размер каждого кадра до размера экрана (800x600)
                frames = []
                frame_durations = []
                
                for i, frame in enumerate(ImageSequence.Iterator(im)):
                    # Копируем кадр и изменяем размер до размера экрана
                    resized_frame = frame.copy().resize((screen_width, screen_height), lanczos_filter)
                    
                    # Получаем длительность кадра
                    duration = frame.info.get("duration", default_duration)
                    frame_durations.append(duration)
                    
                    # Конвертируем PIL Image в pygame Surface
                    # Конвертируем в RGBA для поддержки прозрачности
                    if resized_frame.mode != 'RGBA':
                        resized_frame = resized_frame.convert('RGBA')
                    
                    # Получаем данные изображения
                    img_data = resized_frame.tobytes()
                    
                    # Создаем pygame Surface
                    try:
                        frame_surface = pygame.image.fromstring(
                            img_data, (screen_width, screen_height), 'RGBA'
                        )
                    except (AttributeError, TypeError):
                        # Fallback для новых версий pygame
                        frame_surface = pygame.image.frombuffer(
                            img_data, (screen_width, screen_height), 'RGBA'
                        )
                    frame_surface = frame_surface.convert_alpha()
                    
                    frames.append(frame_surface)
                    
                    if i < 3 and not getattr(sys, "frozen", False):
                        print(f"[VICTORY SPLASH] Кадр {i}: длительность {duration} мс, размер {frame_surface.get_size()}")
            
            if len(frames) == 0:
                raise ValueError("Не удалось загрузить кадры анимации")
            
            # Изображение уже имеет размер экрана, координаты (0, 0)
            x = 0
            y = 0
            
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Загружено кадров: {len(frames)}, размер каждого: {screen_width}x{screen_height}")
            
            # Время начала показа
            start_time = time.time()
            clock = pygame.time.Clock()
            frame_index = 0
            frame_accumulator = 0.0
            last_frame_time = time.time()
            
            # Показываем заставку в течение указанного времени
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Длительность показа: {duration_seconds} сек")
                if len(frames) > 1:
                    print(f"[VICTORY SPLASH] Длительности кадров (мс): {frame_durations[:5]}...")  # Показываем первые 5
            
            # Если только один кадр, просто показываем его
            if len(frames) == 1:
                while time.time() - start_time < duration_seconds:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                    screen.fill((0, 0, 0))
                    screen.blit(frames[0], (x, y))
                    pygame.display.flip()
                    clock.tick(30)
            else:
                # Анимация с несколькими кадрами
                while time.time() - start_time < duration_seconds:
                    # Обрабатываем события (чтобы окно не зависало)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                    
                    # Вычисляем время, прошедшее с последнего кадра
                    current_frame_time = time.time()
                    delta_time = current_frame_time - last_frame_time
                    last_frame_time = current_frame_time
                    frame_accumulator += delta_time
                    
                    # Переключаем кадры анимации на основе длительности кадра
                    frame_duration_sec = frame_durations[frame_index] / 1000.0
                    # Минимальная длительность кадра - 30 FPS (33 мс)
                    if frame_duration_sec < 0.033:
                        frame_duration_sec = 0.033
                    
                    # Если накопилось достаточно времени, переключаем кадр
                    if frame_accumulator >= frame_duration_sec:
                        old_index = frame_index
                        frame_index = (frame_index + 1) % len(frames)
                        frame_accumulator -= frame_duration_sec
                        
                        # Отладочный вывод для первых нескольких переключений
                        if old_index < 5 and not getattr(sys, "frozen", False):
                            print(f"[VICTORY SPLASH] Кадр изменен: {old_index} -> {frame_index}")
                    
                    # Очищаем экран
                    screen.fill((0, 0, 0))
                    
                    # Рисуем текущий кадр (уже размером с экран)
                    screen.blit(frames[frame_index], (x, y))
                    
                    # Обновляем экран
                    pygame.display.flip()
                    
                    # Ограничиваем FPS для плавной анимации
                    clock.tick(30)
                    
        except (ImportError, Exception) as e:
            # Если PIL не установлен или произошла ошибка, используем pygame для загрузки первого кадра
            if not getattr(sys, "frozen", False):
                print(f"[VICTORY SPLASH] Ошибка при загрузке через PIL: {e}, используем pygame для статического изображения")
            # Загружаем статическое изображение через pygame (только первый кадр)
            try:
                image = pygame.image.load(image_path)
                if not getattr(sys, "frozen", False):
                    print(f"[VICTORY SPLASH] Изображение загружено через pygame, размер: {image.get_size()}")
                
                # Получаем размеры экрана (НЕ МЕНЯЕМ их!)
                screen_width, screen_height = screen.get_size()
                
                # Конвертируем изображение в формат, поддерживающий smoothscale
                if image.get_bitsize() not in (24, 32):
                    image = image.convert()
                
                # Растягиваем изображение до размера экрана
                try:
                    image = pygame.transform.smoothscale(image, (screen_width, screen_height))
                except ValueError:
                    # Если smoothscale не работает, используем обычный scale
                    image = pygame.transform.scale(image, (screen_width, screen_height))
                
                # Координаты (0, 0) - изображение уже размером с экран
                x = 0
                y = 0
                
                # Показываем статическое изображение
                start_time = time.time()
                clock = pygame.time.Clock()
                
                while time.time() - start_time < duration_seconds:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                    
                    screen.fill((0, 0, 0))
                    screen.blit(image, (x, y))
                    pygame.display.flip()
                    clock.tick(30)
                    
            except Exception as e2:
                # Если даже pygame не может загрузить, просто выходим и переходим к результатам
                if not getattr(sys, "frozen", False):
                    print(f"[VICTORY SPLASH] Критическая ошибка: не удалось загрузить изображение: {e2}")
                    import traceback
                    traceback.print_exc()
                # Выходим из функции, чтобы сразу перейти к экрану результатов
                return
                
    except Exception as e:
        # Если не удалось загрузить изображение, просто выходим и переходим к результатам
        if not getattr(sys, "frozen", False):
            print(f"[VICTORY SPLASH] ОШИБКА при загрузке изображения победы: {e}")
            import traceback
            traceback.print_exc()
        # Выходим из функции, чтобы сразу перейти к экрану результатов
        return


def show_game_results(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    score: int,
    player_name: str,
    game_time_seconds: int,
    highscore_manager: HighScoreManager,
    settings_manager: SettingsManager,
    ball: "Ball",
    auto_mode: bool = False,
) -> tuple[bool, bool, bool]:
    """
    Отображает экран с результатами игры и таблицей рекордов.
    
    Показывает финальный счет, время игры, таблицу рекордов и позволяет
    игроку перезапустить игру или выйти.
    
    Args:
        screen: Поверхность pygame для отрисовки
        font: Шрифт для обычного текста
        big_font: Шрифт для заголовков
        score: Финальный счет игрока
        player_name: Имя игрока
        game_time_seconds: Время игры в секундах
        highscore_manager: Менеджер рекордов для сохранения и отображения
        settings_manager: Менеджер настроек игры
        ball: Объект мяча для доступа к настройкам
        auto_mode: Флаг авторежима
        
    Returns:
        Кортеж из 3 элементов:
        - Состояние звука (bool)
        - Флаг перезапуска игры (bool)
        - Флаг выхода из игры (bool)
    """
    game_time_formatted = f"{game_time_seconds // 60}:{game_time_seconds % 60:02d}"

    # Добавляем результат в рекорды и проверяем, попал ли он в топ-10
    score_saved = highscore_manager.add_score(player_name, score, game_time_seconds)

    # Состояние звука
    sound_enabled = True
    restart_game = False
    exit_game = False

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game = True
                return sound_enabled, False, exit_game  # Выход из игры по крестику
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if auto_mode:
                        # В авторежиме ESC возвращает к экрану ввода имени
                        restart_game = True
                        waiting = False
                    else:
                        # В ручном режиме ESC выходит из игры
                        exit_game = True
                        return sound_enabled, False, exit_game
                elif event.key == pygame.K_RETURN:
                    waiting = False
                    restart_game = True
                elif event.key == pygame.K_h:
                    # Показываем таблицу рекордов (ESC выходит из игры)
                    sound_enabled, exit_game = show_highscores(
                        screen, font, highscore_manager, exit_on_esc=True
                    )
                    if exit_game:
                        exit_game = True
                        return sound_enabled, False, exit_game  # Выход из игры
                elif event.key == pygame.K_m:
                    # Переключение всех звуков
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True
                elif event.key == pygame.K_UP:
                    # Открытие окна настроек
                    sound_enabled = show_settings_window(
                        screen,
                        font,
                        big_font,
                        settings_manager,
                        ball,
                        sound_enabled,
                        auto_mode,
                    )

        # Отрисовка экрана результатов
        screen.fill((10, 10, 30))

        # Заголовок
        if score > 0:
            title = big_font.render("Игра окончена!", True, (255, 255, 255))
        else:
            title = big_font.render("Игра окончена", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        # Результаты игрока
        result_text = f"Игрок: {player_name}"
        score_text = f"Очки: {score}"
        time_text = f"Время игры: {game_time_formatted}"

        surf1 = font.render(result_text, True, (255, 255, 255))
        surf2 = font.render(score_text, True, (255, 255, 255))
        surf3 = font.render(time_text, True, (255, 255, 255))

        screen.blit(surf1, (SCREEN_WIDTH // 2 - 100, 200))
        screen.blit(surf2, (SCREEN_WIDTH // 2 - 100, 250))
        screen.blit(surf3, (SCREEN_WIDTH // 2 - 100, 300))

        # Сообщение о топ-10
        if not score_saved:
            warning_text = "Результат не попал в топ-10, таблица рекордов не обновлена"
            warning_surface = font.render(warning_text, True, (255, 200, 100))
            warning_rect = warning_surface.get_rect(center=(SCREEN_WIDTH // 2, 360))
            screen.blit(warning_surface, warning_rect)

        # Подсказки
        render_colored_hint(
            screen,
            font,
            "Enter - новая игра, H - рекорды",
            (SCREEN_WIDTH // 2 - 150, 400),
        )
        render_colored_hint(
            screen, font, "ESC - выход из игры", (SCREEN_WIDTH // 2 - 150, 430)
        )

        pygame.display.flip()

    return sound_enabled, restart_game, exit_game


# КРИТИЧНО: Классы Paddle и Ball импортируются из game_models.py
# для устранения дубликатов кода (см. docs/DUPLICATE_ANALYSIS.md)


def build_bricks() -> List[pygame.Rect]:
    """
    Создает сетку кирпичей для игры.
    
    Returns:
        Список pygame.Rect объектов, представляющих кирпичи на экране
        
    Note:
        Для использования новой архитектуры см. game_controllers.GameController.build_bricks()
    """
    bricks = []
    start_x = (
        SCREEN_WIDTH - (BRICK_COLS * BRICK_WIDTH + (BRICK_COLS - 1) * BRICK_PADDING)
        ) // 2
    for row in range(BRICK_ROWS):
        for col in range(BRICK_COLS):
            x = start_x + col * (BRICK_WIDTH + BRICK_PADDING)
            y = BRICK_OFFSET_TOP + row * (BRICK_HEIGHT + BRICK_PADDING)
            bricks.append(pygame.Rect(x, y, BRICK_WIDTH, BRICK_HEIGHT))
    return bricks


def draw_bricks(screen: pygame.Surface, bricks: List[pygame.Rect]) -> None:
    """
    Отрисовывает все кирпичи на экране.
    
    Каждый ряд кирпичей имеет свой цвет из палитры. Кирпичи отрисовываются
    с цветной заливкой и темной рамкой.
    
    Args:
        screen: Поверхность pygame для отрисовки
        bricks: Список прямоугольников кирпичей для отрисовки
        
    Note:
        Для использования новой архитектуры с оптимизацией отрисовки см. game_views.BricksView
    """
    try:
        from .game_config import BRICK_COLORS, BRICK_BORDER_COLOR
    except ImportError:
        from src.game.game_config import BRICK_COLORS, BRICK_BORDER_COLOR
    
    for idx, brick in enumerate(bricks):
        color = BRICK_COLORS[idx // BRICK_COLS % len(BRICK_COLORS)]
        pygame.draw.rect(screen, color, brick)
        pygame.draw.rect(screen, BRICK_BORDER_COLOR, brick, 2)


def draw_hud(
    screen: pygame.Surface,
    score: int,
    lives_left: int,
    font: pygame.font.Font,
    ball: Ball,
    auto_mode: bool = False,
    training_mode: bool = False,
    ai_player: Optional[AIPlayer] = None,
) -> None:
    # Добавляем индикатор авторежима или режима обучения
    if auto_mode or training_mode:
        text = f"Очки: {score} | Жизни: {lives_left} | Скорость мяча: {ball.get_speed()} | АВТОРЕЖИМ"
    else:
        text = f"Очки: {score} | Жизни: {lives_left} | Скорость: {ball.get_speed()} | ↑ ↓ - скорость"

    surf = font.render(
        text,
        True,
        (255, 255, 255) if not (auto_mode or training_mode) else (255, 255, 0),
    )
    screen.blit(surf, (SCREEN_WIDTH - surf.get_width() - 20, 20))


def render_colored_hint(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: Tuple[int, int],
    base_color: Tuple[int, int, int] = (200, 200, 200),
    key_color: Tuple[int, int, int] = (255, 255, 0),
) -> int:
    """Отображает подсказку с выделенными ключевыми словами цветом"""
    words = text.split()
    x, y = pos
    key_words = ["Enter", "H", "M", "ESC", "↑", "↓", "0", "8"]

    for word in words:
        # Убираем знаки препинания для сравнения
        clean_word = word.rstrip(".,:!?")

        if clean_word in key_words:
            # Выделяем ключевое слово цветом
            color = key_color
        else:
            color = base_color

        surf = font.render(word, True, color)
        screen.blit(surf, (x, y))
        x += surf.get_width() + font.size(" ")[0]  # добавляем пробел

    return x - pos[0]  # возвращаем ширину текста


def draw_start_hint(screen: pygame.Surface, font: pygame.font.Font) -> None:
    text = "Для начала игры нажми ← или →"
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(surf, rect)


def show_settings_window(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    settings_manager: SettingsManager,
    ball: Ball,
    sound_enabled: bool,
    auto_mode: bool = False,
) -> bool:
    """Отображает окно настроек с слайдером скорости мяча. Возвращает состояние звука."""
    # Параметры слайдера
    slider_x = 200
    slider_y = 250
    slider_width = 400
    slider_height = 20
    knob_radius = 15

    # Максимальная скорость в зависимости от режима
    max_speed = 30 if auto_mode else 10

    # Текущая скорость
    current_speed = ball.get_speed()

    # Ограничиваем текущую скорость максимально допустимой
    if current_speed > max_speed:
        current_speed = max_speed
        ball.set_speed(current_speed, settings_manager, auto_mode)

    dragging = False
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    waiting = False  # Закрыть окно
                elif event.key == pygame.K_m:
                    # Переключение всех звуков
                    if sound_enabled:
                        pygame.mixer.music.stop()
                        sound_enabled = False
                    else:
                        pygame.mixer.music.play(-1)
                        sound_enabled = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Левая кнопка мыши
                    mouse_x, mouse_y = event.pos
                    # Проверить, нажали ли на бегунок
                    knob_x = slider_x + (current_speed - 1) * (
                        slider_width / (max_speed - 1)
                    )
                    knob_y = slider_y + slider_height // 2
                    if (mouse_x - knob_x) ** 2 + (
                        mouse_y - knob_y
                    ) ** 2 <= knob_radius**2:
                        dragging = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    mouse_x, _ = event.pos
                    # Вычислить новую скорость
                    relative_x = mouse_x - slider_x
                    if relative_x < 0:
                        new_speed = 1
                    elif relative_x > slider_width:
                        new_speed = max_speed
                    else:
                        new_speed = int(
                            1 + (relative_x / slider_width) * (max_speed - 1)
                        )
                    if new_speed != current_speed:
                        current_speed = new_speed
                        ball.set_speed(current_speed, settings_manager, auto_mode)

        # Отрисовка оверлея
        pygame.draw.rect(screen, (100, 100, 100), (150, 100, 500, 400), 5)  # Рамка
        pygame.draw.rect(screen, (50, 50, 50), (150, 100, 500, 400))  # Фон

        # Заголовок
        title = big_font.render("Настройки", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        # Текст скорости
        speed_text = font.render(
            f"Скорость мяча: {current_speed}", True, (255, 255, 255)
        )
        speed_rect = speed_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(speed_text, speed_rect)

        # Слайдер
        # Полоса
        pygame.draw.rect(
            screen, (100, 100, 100), (slider_x, slider_y, slider_width, slider_height)
        )
        # Бегунок
        knob_x = slider_x + (current_speed - 1) * (slider_width / (max_speed - 1))
        knob_y = slider_y + slider_height // 2
        pygame.draw.circle(screen, (255, 255, 255), (int(knob_x), knob_y), knob_radius)
        pygame.draw.circle(screen, (0, 0, 0), (int(knob_x), knob_y), knob_radius, 2)

        # Подсказки
        render_colored_hint(
            screen,
            font,
            "Перетащите бегунок для изменения скорости",
            (SCREEN_WIDTH // 2 - 150, 350),
        )
        render_colored_hint(
            screen,
            font,
            "ESC - закрыть настройки, M - все звуки",
            (SCREEN_WIDTH // 2 - 150, 380),
        )

        pygame.display.flip()

    return sound_enabled


def main() -> None:
    startup_start_time = time.time()
    if not getattr(sys, "frozen", False):
        print(f"[STARTUP] Начало инициализации игры...")
    
    pygame.init()
    pygame.mixer.init()  # Инициализация аудио микшера
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Арканоид")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)
    big_font = pygame.font.SysFont("arial", 42, bold=True)
    
    if not getattr(sys, "frozen", False):
        pygame_init_time = time.time() - startup_start_time
        print(f"[STARTUP] pygame инициализирован за {pygame_init_time:.3f} сек")

    # Инициализация менеджеров
    highscore_manager = HighScoreManager()
    settings_manager = SettingsManager()

    # AI система будет создана в основном цикле для каждого нового запуска

    # Загрузка звуковых эффектов и генерация звуков удара по кубикам
    try:
        # Генерируем звук отскока от платформы
        paddle_bounce_sound = generate_paddle_sound()

        # Генерируем разные тональные звуки для ударов по кубикам
        brick_hit_sounds = [
            generate_tone_sound(440, 0.2),  # A4 - 440 Гц
            generate_tone_sound(523.25, 0.2),  # C5 - ~523 Гц
            generate_tone_sound(659.25, 0.2),  # E5 - ~659 Гц
        ]
        # Пытаемся загрузить фоновую музыку (но не запускаем автоматически)
        try:
            music_path = resource_path("audio/Night_Prowler.ogg")
            # Нормализуем путь для корректной работы на Windows
            music_path = os.path.normpath(music_path)
            
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(0.3)
                # Музыка будет запущена после ввода имени игрока
            else:
                # Файл не найден - выводим отладочную информацию только в режиме разработки
                if not getattr(sys, "frozen", False):
                    print(f"[DEBUG] Файл музыки не найден по пути: {music_path}")
                    # Пробуем альтернативный путь относительно текущей директории
                    alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "audio", "Night_Prowler.ogg")
                    alt_path = os.path.normpath(alt_path)
                    if os.path.exists(alt_path):
                        print(f"[DEBUG] Найден альтернативный путь: {alt_path}")
                        pygame.mixer.music.load(alt_path)
                        pygame.mixer.music.set_volume(0.3)
        except (pygame.error, FileNotFoundError, OSError) as e:
            # Музыка не загружена - выводим информацию только в режиме разработки
            if not getattr(sys, "frozen", False):
                print(f"[DEBUG] Не удалось загрузить фоновую музыку: {e}")
    except pygame.error as e:
        # Не выводим в exe файле
        if not getattr(sys, "frozen", False):
            print(f"Звуковые эффекты не загружены: {e}")
        paddle_bounce_sound = None
        brick_hit_sounds = None

    # Инициализация переменных
    score = 0
    lives_left = MAX_LIVES
    game_over = False
    game_started = False
    running = True
    sound_enabled = True
    auto_mode = False
    training_mode = False
    training_rounds = 0  # Счетчик раундов в режиме обучения
    ai_player: Optional[AIPlayer] = None  # Инициализация AI-игрока

    while True:  # Внешний цикл для возврата к вводу имени в авторежиме
        # Сбрасываем флаг завершения авторежима для каждого нового запуска
        auto_mode_complete = False
        running = True  # Всегда начинаем с флага running=True

        # ПОЛНЫЙ СБРОС СОСТОЯНИЯ ИГРЫ ПРИ КАЖДОМ НОВОМ ЗАПУСКЕ
        paddle = Paddle()
        ball = Ball()
        ball_speed = settings_manager.get_ball_speed()
        ball.set_speed(ball_speed)
        ball.reset(paddle.rect)
        ball.vel_y = 0
        bricks = build_bricks()
        score = 0
        game_over = False
        game_started = False

        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Пересоздаем AI-систему НО сначала сохраняем предыдущие данные обучения
        if "ai_player" in locals() and ai_player is not None:
            # Сохраняем данные обучения от предыдущего экземпляра
            ai_player.save_learning_data()

        # Ввод имени игрока (ПЕРЕД созданием AI, чтобы не создавать лишние логи)
        # ФЛАГ ДЛЯ АВТОМАТИЧЕСКОГО ЗАПУСКА РЕЖИМА ОБУЧЕНИЯ (для тестирования)
        AUTO_START_TRAINING_MODE = False  # Установите True только для тестирования
        
        if AUTO_START_TRAINING_MODE:
            # Автоматически запускаем режим обучения (mode 8)
            player_name = "training"
            sound_enabled = True
            exit_game = False
            auto_mode = True
            training_mode = True
            if not getattr(sys, "frozen", False):
                print(f"[AUTO] Автоматический запуск режима обучения (mode 8)")
        else:
            # Обычный режим - выбор через меню
            player_name, sound_enabled, exit_game, auto_mode, training_mode = (
                get_player_name(screen, font, big_font, highscore_manager)
            )
        if exit_game:
            pygame.quit()
            return
        
        # Создаем новый AI-систему ПОСЛЕ выбора режима (только если нужен AI)
        ai_player = None
        if auto_mode or training_mode:
            # Не выводим в exe файле
            if not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Создание AIPlayer... auto_mode={auto_mode}, training_mode={training_mode}")
            try:
                # КРИТИЧНО: Создаем AIPlayer БЕЗ блокирующего сообщения на экране
                # Сообщение может остаться на экране, если создание занимает время
                ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
                # Не выводим в exe файле
                if not getattr(sys, "frozen", False):
                    print(f"[AI DEBUG] Новый AIPlayer создан. Обучение будет продолжено...")
            except Exception as e:
                # Не выводим в exe файле
                if not getattr(sys, "frozen", False):
                    print(f"[ERROR] Ошибка при создании AIPlayer: {e}")
                import traceback
                traceback.print_exc()
                # Создаем базовый AI без логирования в случае ошибки
                try:
                    ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
                except:
                    # Если и это не работает, создаем минимальный AI
                    if not getattr(sys, "frozen", False):
                        print(f"[ERROR] Критическая ошибка: не удалось создать AIPlayer")
                    raise
        else:
            # В ручном режиме создаем неактивный AI (для совместимости)
            ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
            ai_player.deactivate()

        # ИСПРАВЛЕНИЕ: Устанавливаем жизни ПОСЛЕ получения training_mode
        # В режиме обучения используем 3 жизни для оценки эффективности
        lives_left = MAX_LIVES  # Всегда 3 жизни, даже в режиме обучения

        # Запускаем музыку после ввода имени (если звук включен)
        if sound_enabled:
            try:
                pygame.mixer.music.play(-1)  # Цикличное воспроизведение фоновой музыки
            except pygame.error:
                # Не выводим в exe файле
                if not getattr(sys, "frozen", False):
                    print("Не удалось запустить фоновую музыку")

        # В авторежиме и режиме обучения активируем AI систему
        if auto_mode or training_mode:
            ai_player.activate()  # ВАЖНО: активируем AI систему

            if training_mode:
                # В режиме обучения используем оптимальную скорость из обучения
                try:
                    optimal_speed = ai_player.get_optimal_ball_speed()
                    if optimal_speed > 10:
                        ball.current_speed = optimal_speed
                        # Устанавливаем начальные скорости движения
                        ball.vel_x = optimal_speed
                        ball.vel_y = -optimal_speed
                    else:
                        ball.set_speed(optimal_speed, settings_manager, auto_mode=False)
                    # Не выводим в exe файле
                    if not getattr(sys, "frozen", False):
                        print(
                            f"Режим обучения: Игра запущена. AI активен: {ai_player.is_active}, "
                            f"Скорость мяча: {optimal_speed}, Множитель платформы: {ai_player.get_optimal_paddle_speed_multiplier():.2f}"
                        )
                except Exception as e:
                    # Не выводим в exe файле
                    if not getattr(sys, "frozen", False):
                        print(f"[ERROR] Ошибка при настройке скорости в режиме обучения: {e}")
                        import traceback
                        traceback.print_exc()
                    # Используем скорость по умолчанию
                    ball.set_speed(8, settings_manager, auto_mode=False)
            else:
                # Авторежим
                ball.set_speed(
                    15, settings_manager, auto_mode=True
                )  # Стартовая скорость 15 для авторежима
                # Не выводим в exe файле
                if not getattr(sys, "frozen", False):
                    print(
                        f"Авторежим: Игра запущена автоматически. AI активен: {ai_player.is_active}"
                    )

            game_started = True  # Игра начинается сразу
            ball.vel_x = ball.get_speed()  # Направление вправо
            ball.vel_y = -ball.get_speed()
            # Не выводим в exe файле
            if not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Игра настроена, game_started={game_started}, ball.vel_x={ball.vel_x}, ball.vel_y={ball.vel_y}")
        else:
            ai_player.deactivate()  # Деактивируем в ручном режиме

        # Отсчет времени игры
        game_start_time = time.time()

        # Счетчик кадров для обновления скорости в режиме обучения
        frame_counter = 0
        
        # Отслеживание тройного нажатия "1" для немедленной победы
        key_1_press_count = 0
        key_1_last_press_time = 0.0
        KEY_1_RESET_TIME = 2.0  # Время в секундах для сброса счетчика

        # КРИТИЧНО: Обновляем состояние игры для AI перед входом в основной цикл
        if auto_mode or training_mode:
            ai_player.update_game_state(
                ball, paddle, bricks, score, int(game_start_time)
            )
            # Не выводим в exe файле
            if not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Состояние игры обновлено для AI перед входом в цикл")
        
        # КРИТИЧНО: Обновляем экран перед входом в основной цикл
        if not getattr(sys, "frozen", False):
            print(f"[AI DEBUG] Вход в основной цикл игры, running={running}, game_started={game_started}")
        
        # Очистка экрана выполняется в основном цикле для корректной отрисовки

        while running:
            frame_counter += 1
            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Кадр {frame_counter}, running={running}, game_started={game_started}")
            
            # КРИТИЧНО: Обработка событий должна быть первой и всегда выполняться
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    # QUIT всегда закрывает приложение немедленно
                    running = False
                    pygame.quit()
                    sys.exit(0)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # ESC всегда закрывает приложение немедленно
                        running = False
                        pygame.quit()
                        sys.exit(0)
                    elif event.key == pygame.K_m:
                        # Переключение всех звуков
                        if sound_enabled:
                            pygame.mixer.music.stop()
                            sound_enabled = False
                        else:
                            pygame.mixer.music.play(-1)
                            sound_enabled = True
                    elif event.key == pygame.K_UP:
                        # Увеличение скорости мяча
                        ball.increase_speed(settings_manager, auto_mode)
                    elif event.key == pygame.K_DOWN:
                        # Уменьшение скорости мяча
                        ball.decrease_speed(settings_manager, auto_mode)
                    elif event.key == pygame.K_1 or event.key == ord('1'):
                        # Обработка тройного нажатия "1" для немедленной победы
                        current_time = time.time()
                        # Если прошло больше времени сброса, сбрасываем счетчик
                        if current_time - key_1_last_press_time > KEY_1_RESET_TIME:
                            key_1_press_count = 0
                        
                        key_1_press_count += 1
                        key_1_last_press_time = current_time
                        
                        # Если нажали три раза подряд
                        if key_1_press_count >= 3:
                            # Очищаем кирпичи для победы
                            bricks = []
                            key_1_press_count = 0  # Сбрасываем счетчик
                            if not getattr(sys, "frozen", False):
                                print(f"[CHEAT] Активирована немедленная победа (тройное нажатие '1')")
                                print(f"[CHEAT] auto_mode={auto_mode}, training_mode={training_mode}, lives_left={lives_left}")
                            
                            # Устанавливаем победу и показываем заставку только в обычном режиме
                            if not auto_mode and not training_mode and lives_left > 0:
                                if not getattr(sys, "frozen", False):
                                    print("[CHEAT] Условия выполнены, вызываем trigger_instant_victory...")
                                game_over = True
                                game_time_seconds = int(time.time() - game_start_time)
                                
                                # Используем отдельный метод для показа заставки и результатов
                                try:
                                    sound_enabled, restart_game, exit_game = trigger_instant_victory(
                                        screen,
                                        font,
                                        big_font,
                                        score,
                                        player_name,
                                        game_time_seconds,
                                        highscore_manager,
                                        settings_manager,
                                        ball,
                                        auto_mode,
                                    )
                                    if not getattr(sys, "frozen", False):
                                        print(f"[CHEAT] trigger_instant_victory завершена: restart_game={restart_game}, exit_game={exit_game}")
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[CHEAT] ОШИБКА в trigger_instant_victory: {e}")
                                        import traceback
                                        traceback.print_exc()
                                    # Продолжаем выполнение даже при ошибке
                                    restart_game = False
                                    exit_game = False
                                
                                # Обработка выхода или перезапуска
                                if exit_game:
                                    pygame.quit()
                                    return
                                
                                if restart_game:
                                    # Перезапускаем игру
                                    paddle = Paddle()
                                    ball = Ball()
                                    ball_speed = settings_manager.get_ball_speed()
                                    ball.set_speed(ball_speed)
                                    ball.reset(paddle.rect)
                                    ball.vel_y = 0
                                    bricks = build_bricks()
                                    score = 0
                                    lives_left = MAX_LIVES
                                    game_over = False
                                    game_started = False
                                    ai_player = AIPlayer(
                                        SCREEN_WIDTH,
                                        SCREEN_HEIGHT,
                                        debug_mode=True,
                                    )
                                    ai_player.activate()
                                    game_start_time = time.time()
                                    key_1_press_count = 0  # Сбрасываем счетчик
                                    key_1_last_press_time = 0.0

            keys = pygame.key.get_pressed()
            
            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] После обработки событий, game_started={game_started}, game_over={game_over}, auto_mode={auto_mode}, training_mode={training_mode}")

            if not game_started and not auto_mode:
                ball.rect.center = paddle.rect.midtop
                ball.rect.y -= BALL_SIZE
                if keys[pygame.K_LEFT]:
                    game_started = True
                    ball.vel_x = -ball.get_speed()
                    ball.vel_y = -ball.get_speed()
                elif keys[pygame.K_RIGHT]:
                    game_started = True
                    ball.vel_x = ball.get_speed()
                    ball.vel_y = -ball.get_speed()
            elif not game_started and auto_mode:
                # В авторежиме мяч всегда на платформе
                ball.rect.center = paddle.rect.midtop
                ball.rect.y -= BALL_SIZE

            # Обработка перезапуска после окончания игры (только для ручного режима)
            if game_over and keys[pygame.K_r]:
                # В ручном режиме R перезапускает игру
                # Сброс состояния игры
                paddle = Paddle()
                ball = Ball()
                ball_speed = settings_manager.get_ball_speed()
                ball.set_speed(ball_speed)
                ball.reset(paddle.rect)
                ball.vel_y = 0
                bricks = build_bricks()
                score = 0
                lives_left = MAX_LIVES
                game_over = False
                game_started = False
                # Пересоздаем AI для новой игры
                ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
                ai_player.activate()

            if not game_over:
                # Отладочное сообщение только в первых 3 кадрах
                if frame_counter <= 3 and not getattr(sys, "frozen", False):
                    print(f"[AI DEBUG] В блоке if not game_over, обновляем состояние игры")
                
                # Обновляем состояние игры для AI системы
                if auto_mode or training_mode:
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Вызываем update_game_state...")
                    ai_player.update_game_state(
                        ball, paddle, bricks, score, int(game_start_time)
                    )
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] update_game_state завершен")
                    
                    # КРИТИЧНО: Проверяем нарушение правила фиксации позиции
                    # Теперь вместо перезапуска игры просто сбрасываем целевую позицию
                    if hasattr(ai_player, 'separation_zone_tracker') and ai_player.separation_zone_tracker.game_restart_required:
                        # Нарушение правила - сбрасываем целевую позицию вместо перезапуска игры
                        if not getattr(sys, "frozen", False):
                            print(f"[WARNING] Обнаружено нарушение правила фиксации позиции! Сбрасываем целевую позицию.")
                        # Сбрасываем целевую позицию
                        if hasattr(ai_player, 'target_tracker'):
                            ai_player.target_tracker.reset_target_position()
                        elif hasattr(ai_player.separation_zone_tracker, 'target_position_set'):
                            ai_player.separation_zone_tracker.target_position_set = False
                            ai_player.separation_zone_tracker.target_position = None
                        # Сбрасываем флаг
                        ai_player.separation_zone_tracker.game_restart_required = False
                    
                    # В режиме обучения обновляем статистику и управляем скоростью мяча
                    if training_mode:
                        # Обновляем статистику обучения
                        total_bricks = (BRICK_ROWS * BRICK_COLS) - len(bricks)
                        time_elapsed = time.time() - game_start_time
                        lives_lost = MAX_LIVES - lives_left
                        ai_player.update_training_stats(
                            total_bricks, time_elapsed, lives_lost
                        )

                        # ИИ управляет скоростью мяча во время игры (проверяем каждые 60 кадров = 1 секунда)
                        if frame_counter % FPS == 0:  # Каждую секунду (60 кадров)
                            optimal_ball_speed = ai_player.get_optimal_ball_speed()
                            current_ball_speed = ball.get_speed()
                            if current_ball_speed != optimal_ball_speed:
                                # Устанавливаем оптимальную скорость (обходя ограничение для режима обучения)
                                if optimal_ball_speed > 10:
                                    ball.current_speed = optimal_ball_speed
                                    # Обновляем скорости движения с сохранением направления
                                    if ball.vel_x != 0:
                                        ball.vel_x = int(
                                            ball.vel_x
                                            * optimal_ball_speed
                                            / max(current_ball_speed, 1)
                                        )
                                    if ball.vel_y != 0:
                                        ball.vel_y = int(
                                            abs(ball.vel_y)
                                            * optimal_ball_speed
                                            / max(current_ball_speed, 1)
                                        ) * (1 if ball.vel_y > 0 else -1)
                                else:
                                    ball.set_speed(
                                        optimal_ball_speed,
                                        settings_manager,
                                        auto_mode=False,
                                    )

                # Движение платформы
                if auto_mode or training_mode:
                    # В авторежиме и режиме обучения используем адаптивную скорость платформы
                    if training_mode:
                        # В режиме обучения ИИ управляет скоростью платформы
                        paddle_speed_multiplier = (
                            ai_player.get_optimal_paddle_speed_multiplier()
                        )
                        base_speed = PADDLE_SPEED * paddle_speed_multiplier
                    else:
                        # В авторежиме используем стандартную логику
                        base_speed = max(
                            PADDLE_SPEED, ball.get_speed() * 0.8
                        )  # Минимум 15 или 80% от скорости мяча
                        base_speed = max(
                            base_speed, PADDLE_SPEED * 1.5
                        )  # Минимум 22.5 для авторежима
                    
                    # КРИТИЧНО: При малом количестве блоков увеличиваем скорость платформы
                    try:
                        bricks_remaining = len(bricks) if bricks is not None else 50
                    except (NameError, TypeError):
                        bricks_remaining = 50
                    if bricks_remaining <= 5:
                        # Увеличиваем скорость в критических ситуациях
                        base_speed = int(base_speed * 1.5)  # Увеличиваем на 50%
                    if bricks_remaining == 1:
                        # При 1 кубике максимальная скорость для гарантированного попадания
                        base_speed = int(base_speed * 2.5)  # Увеличиваем в 2.5 раза
                        # Также увеличиваем скорость пропорционально скорости мяча
                        if ball.get_speed() > 20:
                            base_speed = int(base_speed * (ball.get_speed() / 20.0))

                    # КРИТИЧНО: Платформа начинает движение когда мяч в зоне разделения
                    # Правила работы:
                    # 1. Мяч улетает (вверх) - платформа стоит на месте
                    # 2. Мяч в зоне кубиков (выше зоны разделения) - платформа стоит на месте
                    # 3. Мяч падает вниз и вошел в зону разделения - платформа начинает движение к точке падения
                    # 4. Если целевая позиция уже установлена - платформа продолжает движение к ней,
                    #    даже если мяч временно не в зоне разделения (например, близко к платформе)
                    # Мяч движется вниз (ball.vel_y > 0)
                    ball_in_separation_zone = (
                        SEPARATION_ZONE_TOP <= ball.rect.centery <= SEPARATION_ZONE_BOTTOM
                        and ball.vel_y > 0  # Мяч движется вниз
                    )
                    
                    # Проверяем, установлена ли целевая позиция
                    target_position_set = (
                        hasattr(ai_player, 'separation_zone_tracker') and
                        hasattr(ai_player.separation_zone_tracker, 'target_position_set') and
                        ai_player.separation_zone_tracker.target_position_set
                    )
                    
                    # Проверяем, что мяч не потерян (не ниже платформы)
                    ball_not_lost = ball.rect.bottom <= paddle.rect.top
                    
                    # Начинаем движение когда мяч в зоне разделения ИЛИ если целевая позиция уже установлена
                    # (это позволяет платформе завершить движение к цели, даже если мяч близко к платформе)
                    # НО только если мяч не потерян
                    should_move = (ball_in_separation_zone or target_position_set) and ball_not_lost
                    
                    # КРИТИЧНО: Логируем для диагностики проблем с движением
                    if should_move and pygame.time.get_ticks() % 1000 < 16:  # Каждые ~1 секунду
                        if not getattr(sys, "frozen", False):
                            print(f"[PADDLE MOVEMENT DEBUG] ball_in_separation_zone={ball_in_separation_zone}, "
                                  f"target_position_set={target_position_set}, ball_not_lost={ball_not_lost}, "
                                  f"ball_y={ball.rect.centery:.1f}, paddle_x={paddle.rect.centerx:.1f}")
                    
                    if should_move:
                        # Используем AI систему для автоматического управления
                        movement = ai_player.move_paddle_towards(
                            paddle.rect.centerx, int(base_speed)
                        )
                        
                        # КРИТИЧНО: Логируем результат движения для диагностики
                        if movement == 0 and target_position_set and pygame.time.get_ticks() % 1000 < 16:
                            if not getattr(sys, "frozen", False):
                                target_pos = ai_player.separation_zone_tracker.target_position if hasattr(ai_player, 'separation_zone_tracker') else None
                                distance = abs(paddle.rect.centerx - target_pos) if target_pos is not None else 0
                                print(f"[PADDLE MOVEMENT WARNING] movement=0, но target_position_set=True! "
                                      f"paddle_x={paddle.rect.centerx:.1f}, target_pos={target_pos}, distance={distance:.1f}")
                        # Получаем скорректированную скорость от AI (с учетом адаптации)
                        adjusted_speed = ai_player.get_adjusted_paddle_speed(
                            int(base_speed)
                        )
                        
                        # КРИТИЧНО: Используем адаптивную скорость для предотвращения перескакивания через цель
                        # Получаем целевую позицию от AI
                        target_pos = ai_player.separation_zone_tracker.target_position if hasattr(ai_player, 'separation_zone_tracker') else None
                        if target_pos is not None:
                            distance_to_target = abs(paddle.rect.centerx - target_pos)
                            # Если платформа близко к цели (distance < speed), уменьшаем скорость
                            # Это предотвращает перескакивание через цель и дергание
                            if distance_to_target < adjusted_speed:
                                # Двигаемся только на расстояние до цели, не больше
                                adjusted_speed = max(1, int(distance_to_target))
                        
                        # КРИТИЧНО: Используем centerx для движения, чтобы избежать конфликта с x
                        # Применяем движение с адаптивной скоростью
                        new_center_x = paddle.rect.centerx + movement * adjusted_speed
                        
                        # Строгие границы для центра платформы: половина ширины платформы = 60 пикселей
                        paddle_half_width = PADDLE_WIDTH // 2  # 60 пикселей
                        min_center_x = paddle_half_width
                        max_center_x = SCREEN_WIDTH - paddle_half_width
                        paddle.rect.centerx = max(
                            min_center_x, min(max_center_x, new_center_x)
                        )
                    # Если мяч не в зоне разделения - платформа остается на месте (movement = 0)

                    # Отладочная информация (выводим периодически)
                    if pygame.time.get_ticks() % 1000 < 16:  # Каждые ~1 секунду
                        optimal_x = ai_player.get_optimal_paddle_position()
                        # print(
                        #     f"AI Debug: Платформа X={paddle.rect.centerx}, Оптимальная X={optimal_x}, Движение={movement}, AI активен={ai_player.is_active}"
                        # )
                else:
                    # Ручное управление платформой
                    if keys[pygame.K_LEFT]:
                        paddle.move(-1)
                    if keys[pygame.K_RIGHT]:
                        paddle.move(1)

                if game_started:
                    # КРИТИЧНО: Проверяем отскок от потолка БЕЗ попадания в кубики ПЕРЕД обновлением мяча
                    # Это позволяет отследить отбитие в пустоту
                    ball_was_at_top = ball.rect.top <= 0 and ball.vel_y < 0
                    
                    # Обычное обновление мяча (непрерывная проверка столкновений встроена в update)
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Вызываем ball.update()...")
                    try:
                        ball.update()
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] ball.update() завершен")
                    except Exception as e:
                        if not getattr(sys, "frozen", False):
                            print(f"[ERROR] Ошибка в ball.update(): {e}")
                            import traceback
                            traceback.print_exc()
                        raise
                    
                    # КРИТИЧНО: Проверяем, не попал ли мяч обратно в платформу после ball.update()
                    # Это может произойти, если мяч был установлен слишком близко к платформе
                    # НО: не обрабатываем, если мяч только что отскочил (предотвращаем ложные срабатывания)
                    just_bounced = getattr(ball, '_just_bounced', False)
                    bounce_frame = getattr(ball, '_bounce_frame', -1)
                    if (ball.rect.colliderect(paddle.rect) and ball.vel_y > 0 
                        and not (just_bounced and (bounce_frame == frame_counter or bounce_frame == frame_counter - 1))):
                        # Мяч попал обратно в платформу - принудительно перемещаем его выше
                        ball_radius = BALL_SIZE // 2
                        min_distance = abs(ball.vel_y) + 15  # Скорость + запас
                        ball.rect.centery = paddle.rect.top - ball_radius - min_distance
                        # Убеждаемся, что мяч движется вверх
                        if ball.vel_y >= 0:
                            ball.vel_y = -ball.get_speed()
                        # Устанавливаем флаг отскока
                        ball._just_bounced = True
                        ball._bounce_frame = frame_counter
                    
                    # Сбрасываем флаг отскока через несколько кадров (чтобы не блокировать новые столкновения)
                    if just_bounced and frame_counter - bounce_frame > 3:
                        ball._just_bounced = False
                    
                    # КРИТИЧНО: Защита от vel_y == 0 во время игры (кроме начального состояния)
                    # Если мяч не двигается по вертикали и игра запущена - это ошибка
                    if game_started and ball.vel_y == 0:
                        # Мяч застрял с нулевой скоростью - принудительно запускаем его
                        ball.vel_y = -ball.get_speed()
                        # Логируем для диагностики
                        if auto_mode or training_mode:
                            ai_player.performance_logger.log_ball_paddle_positions(
                                ball.rect.centerx,
                                ball.rect.centery,
                                ball.vel_x,
                                ball.vel_y,
                                paddle.rect.x,
                                paddle.rect.y,
                                paddle.rect.width,
                                paddle.rect.height,
                                "VEL_Y_ZERO_FIXED"
                            )
                    
                    # КРИТИЧНО: Логируем координаты мяча и платформы для диагностики
                    # Логируем каждый 10-й кадр для экономии, НО всегда логируем при обнаружении прилипания
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Проверяем логирование координат...")
                    should_log = False
                    if (auto_mode or training_mode):
                        # Логируем каждый 10-й кадр или при обнаружении прилипания
                        if frame_counter % 10 == 0:
                            should_log = True
                        # Также проверяем возможное прилипание каждый кадр (для детекции)
                        elif ball.rect.colliderect(paddle.rect) and abs(ball.vel_y) < 0.1:
                            # Возможное прилипание - логируем для анализа
                            should_log = True
                    
                    if should_log:
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Вызываем log_ball_paddle_positions...")
                        try:
                            ai_player.performance_logger.log_ball_paddle_positions(
                                ball.rect.centerx,
                                ball.rect.centery,
                                ball.vel_x,
                                ball.vel_y,
                                paddle.rect.x,
                                paddle.rect.y,
                                paddle.rect.width,
                                paddle.rect.height,
                                "frame_update"
                            )
                            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                                print(f"[AI DEBUG] log_ball_paddle_positions завершен")
                        except Exception as e:
                            if not getattr(sys, "frozen", False):
                                print(f"[ERROR] Ошибка в log_ball_paddle_positions: {e}")
                    
                    # КРИТИЧНО: После обновления проверяем, отскочил ли мяч от потолка
                    # Если мяч был у потолка и теперь движется вниз - это отскок от потолка
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Проверяем отскок от потолка...")
                    if ball_was_at_top and ball.vel_y > 0:
                        # Мяч отскочил от потолка - проверяем, попадет ли он в кубики
                        # Если в следующем кадре не будет попадания в кубик - это отбитие в пустоту
                        if auto_mode or training_mode:
                            # Увеличиваем счетчик отскоков от потолка
                            ai_player.empty_bounce_tracker["ceiling_bounces"] += 1
                            # Будем проверять попадание в кубики ниже

                    # КРИТИЧНО: Проверяем столкновение ТОЛЬКО с верхней поверхностью платформы
                    # ВАЖНО: Проверка столкновения должна быть ДО проверки потери мяча!
                    # Мяч может быть отбит только верхней поверхностью платформы
                    # Если мяч попадает на боковую сторону - это потеря мяча
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Проверяем столкновения с платформой...")
                    
                    # КРИТИЧНО: Проверяем столкновение ТОЛЬКО с верхней поверхностью платформы
                    # Верхняя поверхность: мяч должен быть по горизонтали в пределах платформы
                    # и нижняя часть мяча должна касаться верхней части платформы
                    # Боковое столкновение: мяч касается боковой стороны платформы (левой или правой)
                    
                    # Проверяем, попадает ли мяч в верхнюю поверхность платформы
                    # Условия для верхней поверхности:
                    # 1. Мяч движется вниз (vel_y > 0)
                    # 2. Центр мяча по горизонтали в пределах платформы (с небольшим запасом)
                    # 3. Нижняя часть мяча касается верхней части платформы
                    # 4. Мяч НЕ находится слишком глубоко внутри платформы (не боковой удар)
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Вычисляем ball_hits_paddle_top...")
                    try:
                        # КРИТИЧНО: Проверяем, не отскочил ли мяч только что (предотвращаем повторную обработку)
                        just_bounced = getattr(ball, '_just_bounced', False)
                        bounce_frame = getattr(ball, '_bounce_frame', -1)
                        # Если мяч отскочил в текущем или предыдущем кадре, не обрабатываем столкновение
                        if just_bounced and (bounce_frame == frame_counter or bounce_frame == frame_counter - 1):
                            ball_hits_paddle_top = False
                        else:
                            ball_hits_paddle_top = (
                                ball.rect.colliderect(paddle.rect) 
                                and ball.vel_y > 0  # Мяч движется вниз
                                and paddle.rect.left - 5 <= ball.rect.centerx <= paddle.rect.right + 5  # Мяч по горизонтали в пределах платформы (с запасом 5px)
                                and ball.rect.bottom >= paddle.rect.top  # Нижняя часть мяча касается или ниже верхней части платформы
                                and ball.rect.bottom <= paddle.rect.top + 15  # Мяч в пределах 15 пикселей от верха платформы
                                and ball.rect.top < paddle.rect.top + 10  # КРИТИЧНО: Мяч не слишком глубоко внутри платформы (верхняя часть мяча не ниже 10px от верха платформы)
                            )
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] ball_hits_paddle_top={ball_hits_paddle_top}")
                    except Exception as e:
                        if not getattr(sys, "frozen", False):
                            print(f"[ERROR] Ошибка в вычислении ball_hits_paddle_top: {e}")
                            import traceback
                            traceback.print_exc()
                        raise
                    
                    # Проверяем боковое столкновение - это потеря мяча
                    # Боковое столкновение: мяч касается платформы, но НЕ попадает в верхнюю поверхность
                    # Это происходит, когда мяч касается левой или правой стороны платформы
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Вычисляем ball_hits_paddle_side...")
                    try:
                        ball_hits_paddle_side = (
                            ball.rect.colliderect(paddle.rect)
                            and ball.vel_y > 0
                            and not ball_hits_paddle_top  # Не верхняя поверхность
                            and (
                                # Мяч касается левой стороны платформы
                                (ball.rect.right >= paddle.rect.left and ball.rect.right <= paddle.rect.left + 10 and ball.rect.centerx < paddle.rect.left)
                                or
                                # Мяч касается правой стороны платформы
                                (ball.rect.left <= paddle.rect.right and ball.rect.left >= paddle.rect.right - 10 and ball.rect.centerx > paddle.rect.right)
                                or
                                # Мяч полностью сбоку от платформы (не попадает в верхнюю поверхность)
                                (ball.rect.bottom < paddle.rect.top and (ball.rect.centerx < paddle.rect.left or ball.rect.centerx > paddle.rect.right))
                            )
                        )
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] ball_hits_paddle_side={ball_hits_paddle_side}")
                    except Exception as e:
                        if not getattr(sys, "frozen", False):
                            print(f"[ERROR] Ошибка в вычислении ball_hits_paddle_side: {e}")
                            import traceback
                            traceback.print_exc()
                        raise
                    
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Проверяем условия ball_hits_paddle_side и ball_hits_paddle_top...")
                        try:
                            print(f"[AI DEBUG] ball_hits_paddle_side={ball_hits_paddle_side}, ball_hits_paddle_top={ball_hits_paddle_top}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка при выводе значений: {e}")
                            print(f"[AI DEBUG] ball_hits_paddle_side type: {type(ball_hits_paddle_side) if 'ball_hits_paddle_side' in locals() else 'NOT DEFINED'}")
                            print(f"[AI DEBUG] ball_hits_paddle_top type: {type(ball_hits_paddle_top) if 'ball_hits_paddle_top' in locals() else 'NOT DEFINED'}")
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Перед проверкой if ball_hits_paddle_side...")
                    if ball_hits_paddle_side:
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] ball_hits_paddle_side=True, обрабатываем боковое столкновение")
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Боковое столкновение! Обрабатываем...")
                        # Мяч попал на боковую сторону платформы - это потеря мяча
                        lives_left -= 1
                        if lives_left > 0:
                            # КРИТИЧНО: Правильно сбрасываем мяч после бокового удара
                            # Сначала сбрасываем позицию и скорость
                            ball.reset(paddle.rect)
                            # КРИТИЧНО: Принудительно устанавливаем мяч ВЫШЕ платформы, чтобы избежать прилипания
                            ball_radius = BALL_SIZE // 2
                            ball.rect.centery = paddle.rect.top - ball_radius - 5  # Мяч должен быть минимум на 5 пикселей выше платформы
                            # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
                            if ball.rect.colliderect(paddle.rect):
                                # Если мяч все еще внутри платформы, перемещаем его еще выше
                                ball.rect.centery = paddle.rect.top - ball_radius - 15
                            # КРИТИЧНО: После бокового удара мяч потерян, но не устанавливаем vel_y = 0
                            # Вместо этого мяч будет обработан в логике потери жизни ниже
                            # КРИТИЧНО: Сбрасываем все трекеры после бокового удара
                            if auto_mode or training_mode:
                                ai_player._reset_game_state_trackers()
                        else:
                            game_over = True
                            # КРИТИЧНО: В режиме обучения перезапускаем игру после потери всех жизней
                            if training_mode and lives_left <= 0:
                                # Рассчитываем время игры и сохраняем результат
                                game_time_seconds = int(time.time() - game_start_time)
                                
                                # В режиме обучения считаем кубики за весь матч
                                total_bricks_destroyed = (
                                    BRICK_ROWS * BRICK_COLS
                                ) - len(bricks)
                                
                                # Обновляем финальную статистику обучения
                                ai_player.update_training_stats(
                                    total_bricks_destroyed,
                                    game_time_seconds,
                                    MAX_LIVES,  # Все жизни потрачены
                                )
                                
                                ai_result = {
                                    "action_type": "game_end",
                                    "success": False,  # Игра проиграна
                                    "final_score": score,
                                    "game_duration": game_time_seconds,
                                    "bricks_remaining": len(bricks),
                                    "bricks_destroyed": total_bricks_destroyed,
                                    "lives_lost": MAX_LIVES,  # Все жизни потрачены
                                }
                                try:
                                    ai_player.learn_from_result(ai_result)
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART ERROR] Ошибка в learn_from_result: {e}")
                                        import traceback
                                        traceback.print_exc()
                                
                                try:
                                    if hasattr(ai_player, 'on_game_end'):
                                        ai_player.on_game_end(
                                            False, score, training_mode=training_mode
                                        )
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART ERROR] Ошибка в on_game_end: {e}")
                                        import traceback
                                        traceback.print_exc()
                                
                                # КРИТИЧНО: Сбрасываем все трекеры состояния AI перед новой игрой
                                ai_player._reset_game_state_trackers()
                                
                                # Автоматически перезапускаем игру в режиме обучения
                                paddle = Paddle()
                                ball = Ball()
                                optimal_ball_speed = ai_player.get_optimal_ball_speed()
                                if optimal_ball_speed > 10:
                                    ball.current_speed = optimal_ball_speed
                                else:
                                    ball.set_speed(
                                        optimal_ball_speed,
                                        settings_manager,
                                        auto_mode=False,
                                    )
                                ball.reset(paddle.rect)
                                ball.vel_y = 0
                                bricks = build_bricks()
                                score = 0
                                lives_left = MAX_LIVES  # Восстанавливаем жизни для нового матча
                                game_over = False
                                game_started = True  # Автоматически запускаем
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()
                                game_start_time = time.time()
                                
                                # КРИТИЧНО: Сразу обновляем состояние игры для AI после перезапуска
                                ai_player.update_game_state(
                                    ball, paddle, bricks, score, int(game_start_time)
                                )
                                
                                if frame_counter <= 3 and not getattr(sys, "frozen", False):
                                    print(f"[AI DEBUG] Игра перезапущена после бокового удара, lives_left={lives_left}")
                                
                                continue  # Пропускаем остальную обработку кадра
                        
                        # Логируем потерю мяча из-за бокового удара
                        if auto_mode or training_mode:
                            ai_result = {
                                "action_type": "paddle_side_hit",
                                "success": False,
                                "confidence": 0.0,
                                "ball_speed": ball.get_speed(),
                                "remaining_bricks": len(bricks),
                            }
                            ai_player.learn_from_result(ai_result)
                            ai_player._log_paddle_movement(
                                paddle.rect.centerx,
                                paddle.rect.centerx,
                                f"ПОТЕРЯ МЯЧА: боковой удар о платформу. Мяч X={ball.rect.centerx}, Платформа X={paddle.rect.centerx}, Платформа left={paddle.rect.left}, right={paddle.rect.right}",
                                0.0
                            )
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Боковое столкновение обработано, continue")
                        continue  # Пропускаем проверку верхней поверхности после бокового удара
                    
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] ball_hits_paddle_side=False, проверяем прилипание мяча...")
                    # КРИТИЧНО: Проверяем, что мяч не "прилип" к платформе
                    # Если мяч находится слишком близко к платформе и не движется вниз - это ошибка
                    # Это может произойти после бокового удара или других ошибок координат
                    # Улучшенная проверка: мяч считается "прилипшим", если он внутри платформы или слишком близко
                    try:
                        # КРИТИЧНО: Прилипание определяется только если мяч ВНУТРИ платформы и НЕ движется
                        # Не проверяем прилипание, если мяч просто находится над платформой и движется вверх - это нормально
                        # КРИТИЧНО: Прилипание определяется только если мяч ВНУТРИ платформы и НЕ движется
                        # НО: не проверяем прилипание, если игра только что запущена (game_started=True, но мяч еще не двигался)
                        ball_stuck = (
                            ball.rect.colliderect(paddle.rect)  # Мяч ВНУТРИ платформы (пересекается с ней)
                            and ball.vel_y == 0  # КРИТИЧНО: Мяч неподвижен по вертикали (vel_y == 0)
                            and not ball_hits_paddle_top  # Не обрабатываем, если это нормальный отскок
                            and game_started  # КРИТИЧНО: Игра должна быть запущена (не начальное состояние ожидания)
                        )
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] ball_stuck={ball_stuck}")
                    except Exception as e:
                        if not getattr(sys, "frozen", False):
                            print(f"[ERROR] Ошибка в вычислении ball_stuck: {e}")
                            import traceback
                            traceback.print_exc()
                        ball_stuck = False
                    
                    if ball_stuck:
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Мяч прилип! Обрабатываем...")
                        # КРИТИЧНО: Логируем прилипание мяча для диагностики
                        if auto_mode or training_mode:
                            ai_player.performance_logger.log_ball_paddle_positions(
                                ball.rect.centerx,
                                ball.rect.centery,
                                ball.vel_x,
                                ball.vel_y,
                                paddle.rect.x,
                                paddle.rect.y,
                                paddle.rect.width,
                                paddle.rect.height,
                                "BALL_STUCK_DETECTED"
                            )
                        
                        # Мяч "прилип" к платформе - принудительно перемещаем его выше
                        ball_radius = BALL_SIZE // 2
                        # КРИТИЧНО: Перемещаем мяч ВЫШЕ платформы, используя centerx/centery для согласованности
                        ball.rect.centery = paddle.rect.top - ball_radius - 15  # Увеличиваем расстояние для надежности
                        # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
                        if ball.rect.colliderect(paddle.rect):
                            # Если мяч все еще внутри платформы, перемещаем его еще выше
                            ball.rect.centery = paddle.rect.top - ball_radius - 25
                        # Устанавливаем скорость вверх, чтобы мяч оторвался
                        if ball.vel_y <= 0:
                            ball.vel_y = -ball.get_speed()
                        # Также устанавливаем горизонтальную скорость, чтобы мяч не оставался на месте
                        if abs(ball.vel_x) < 2:
                            ball.vel_x = random.choice([-ball.get_speed(), ball.get_speed()])
                        # КРИТИЧНО: Убеждаемся, что координаты согласованы (используем только centerx/centery)
                        # Не используем x/y напрямую, чтобы избежать конфликтов координат
                        
                        # КРИТИЧНО: Логируем исправление прилипания
                        if auto_mode or training_mode:
                            ai_player.performance_logger.log_ball_paddle_positions(
                                ball.rect.centerx,
                                ball.rect.centery,
                                ball.vel_x,
                                ball.vel_y,
                                paddle.rect.x,
                                paddle.rect.y,
                                paddle.rect.width,
                                paddle.rect.height,
                                "BALL_STUCK_FIXED"
                            )
                        
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Прилипание обработано, continue")
                        continue  # Пропускаем обработку отскока, так как мяч уже перемещен
                    
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] ball_stuck=False, проверяем ball_hits_paddle_top...")
                    if ball_hits_paddle_top:
                        # КРИТИЧНО: Логируем столкновение с верхней поверхностью платформы
                        if auto_mode or training_mode:
                            ai_player.performance_logger.log_ball_paddle_positions(
                                ball.rect.centerx,
                                ball.rect.centery,
                                ball.vel_x,
                                ball.vel_y,
                                paddle.rect.x,
                                paddle.rect.y,
                                paddle.rect.width,
                                paddle.rect.height,
                                "PADDLE_TOP_HIT"
                            )
                        
                        # КРИТИЧНО: Сначала вычисляем и устанавливаем скорости, ПОТОМ корректируем позицию
                        # Это важно, чтобы мяч начал двигаться в правильном направлении ДО корректировки позиции
                        
                        # Вычисляем точное смещение от центра платформы
                        paddle_center = paddle.rect.centerx
                        ball_center = ball.rect.centerx
                        offset = (ball_center - paddle_center) / (paddle.rect.width / 2)

                        # Ограничиваем offset в диапазоне [-1, 1]
                        offset = max(-1.0, min(1.0, offset))

                        # Устанавливаем новые скорости ПЕРВЫМ ДЕЛОМ
                        ball.bounce_vertical()
                        # КРИТИЧНО: Убеждаемся, что мяч движется вверх (vel_y < 0)
                        if ball.vel_y >= 0:
                            ball.vel_y = -ball.get_speed()
                        ball.vel_x = int(offset * ball.get_speed())
                        
                        # ТЕПЕРЬ корректируем позицию мяча, чтобы он был выше платформы
                        # Используем centery для согласованности с методом update()
                        ball_radius = BALL_SIZE // 2
                        # КРИТИЧНО: Устанавливаем мяч достаточно далеко от платформы
                        # Расстояние должно быть больше скорости мяча, чтобы в следующем кадре мяч не попал обратно
                        # Минимум: скорость мяча + запас 10 пикселей
                        min_distance = abs(ball.vel_y) + 10  # Скорость + запас
                        ball.rect.centery = paddle.rect.top - ball_radius - min_distance
                        
                        # КРИТИЧНО: Убеждаемся, что мяч не находится внутри платформы
                        if ball.rect.colliderect(paddle.rect):
                            # Если мяч все еще внутри платформы, перемещаем его еще выше
                            ball.rect.centery = paddle.rect.top - ball_radius - (min_distance + 10)
                        
                        # КРИТИЧНО: Убеждаемся, что нижняя часть мяча выше верхней части платформы
                        if ball.rect.bottom >= paddle.rect.top:
                            ball.rect.centery = paddle.rect.top - ball_radius - (min_distance + 5)
                        
                        # КРИТИЧНО: Устанавливаем флаг, что мяч только что отскочил
                        # Это предотвратит повторную обработку столкновения в следующем кадре
                        ball._just_bounced = True
                        if not hasattr(ball, '_bounce_frame'):
                            ball._bounce_frame = 0
                        ball._bounce_frame = frame_counter

                        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Предотвращение зацикливания
                        # Если offset слишком мал, принудительно устанавливаем значительное горизонтальное движение
                        min_horizontal_speed = max(
                            2, ball.get_speed() // 2
                        )  # Минимум 2 пикселя или половина скорости
                        if abs(ball.vel_x) < min_horizontal_speed:
                            # Принудительно устанавливаем направление в сторону от текущего положения
                            if ball.rect.centerx < SCREEN_WIDTH // 2:
                                ball.vel_x = min_horizontal_speed  # Двигаемся вправо
                            else:
                                ball.vel_x = -min_horizontal_speed  # Двигаемся влево

                            # Добавляем небольшую случайность для разнообразия
                            ball.vel_x += random.choice([-1, 0, 1])

                        # Дополнительная защита от зацикливания - проверяем, не была ли предыдущая скорость слишком малой
                        # Если предыдущая горизонтальная скорость была очень малой, а новая тоже
                        if abs(ball._last_vel_x) <= 1 and abs(ball.vel_x) <= 1:
                            # Принудительно меняем направление
                            ball.vel_x = random.choice(
                                [-min_horizontal_speed, min_horizontal_speed]
                            )

                        # Сохраняем текущую скорость для следующей проверки
                        ball._last_vel_x = ball.vel_x

                        # Ограничиваем горизонтальную скорость (но оставляем место для мин. скорости)
                        max_horizontal = ball.get_speed()
                        ball.vel_x = max(
                            -max_horizontal, min(max_horizontal, ball.vel_x)
                        )
                        
                        # КРИТИЧНО: Финальная проверка - убеждаемся, что мяч находится выше платформы и движется вверх
                        # Проверяем несколько раз, чтобы гарантировать, что мяч не пересекается с платформой
                        max_attempts = 5
                        for attempt in range(max_attempts):
                            if ball.rect.colliderect(paddle.rect) or ball.rect.bottom >= paddle.rect.top:
                                # Если мяч все еще пересекается с платформой, перемещаем его еще выше
                                ball.rect.centery = paddle.rect.top - ball_radius - (25 + attempt * 5)
                            else:
                                break
                        
                        # КРИТИЧНО: Убеждаемся, что мяч движется вверх с достаточной скоростью
                        # НИКОГДА не допускаем vel_y == 0 после отскока (кроме начального состояния)
                        if ball.vel_y == 0:
                            # КРИТИЧНО: Если vel_y == 0, это ошибка - устанавливаем скорость вверх
                            ball.vel_y = -ball.get_speed()
                        elif ball.vel_y >= 0:
                            ball.vel_y = -ball.get_speed()
                        # Дополнительная проверка: если скорость слишком мала, увеличиваем её
                        if abs(ball.vel_y) < ball.get_speed():
                            ball.vel_y = -ball.get_speed()
                        
                        # КРИТИЧНО: Сбрасываем флаг отскока через несколько кадров
                        # Это позволит обрабатывать новые столкновения, но предотвратит повторную обработку сразу после отскока

                        # Play paddle bounce sound if sound is enabled
                        if sound_enabled and paddle_bounce_sound:
                            paddle_bounce_sound.play()

                        # Обучаем AI на результате отскока
                        if auto_mode or training_mode:
                            ai_result = {
                                "action_type": "paddle_bounce",
                                "success": True,  # Отскок от платформы всегда успешен
                                "confidence": 0.8,
                                "movement_distance": abs(offset * paddle.rect.width),
                                "ball_speed": ball.get_speed(),
                                "remaining_bricks": len(bricks),
                            }
                            ai_player.learn_from_result(ai_result)
                            # КРИТИЧНО: Сбрасываем отслеживание зоны разделения после отскока
                            ai_player._reevaluate_after_bounce()
                    
                    if frame_counter <= 3 and not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Проверяем потерю мяча...")
                    # КРИТИЧНО: Проверяем потерю мяча ПОСЛЕ проверки столкновения с платформой
                    # Если мяч ниже верхней границы платформы И не было столкновения - он потерян
                    if ball.rect.bottom > paddle.rect.top and not ball_hits_paddle_top:
                        # КРИТИЧНО: Подробное логирование потери мяча для диагностики
                        if auto_mode or training_mode:
                            if not getattr(sys, "frozen", False):
                                # Получаем информацию о состоянии для диагностики
                                ball_x = ball.rect.centerx
                                ball_y = ball.rect.centery
                                ball_bottom = ball.rect.bottom
                                paddle_x = paddle.rect.centerx
                                paddle_top = paddle.rect.top
                                paddle_left = paddle.rect.left
                                paddle_right = paddle.rect.right
                                ball_vel_x = ball.vel_x
                                ball_vel_y = ball.vel_y
                                ball_speed = ball.get_speed()
                                
                                # Получаем информацию от AI о целевой позиции
                                optimal_x = ai_player.get_optimal_paddle_position() if hasattr(ai_player, 'get_optimal_paddle_position') else paddle_x
                                distance_to_optimal = abs(paddle_x - optimal_x) if optimal_x is not None else 0
                                
                                # Получаем информацию о зонах
                                separation_zone_start = ai_player.separation_zone_tracker.separation_zone_start if hasattr(ai_player, 'separation_zone_tracker') else 226
                                paddle_zone_start = ai_player.separation_zone_tracker.paddle_zone_start if hasattr(ai_player, 'separation_zone_tracker') else 540
                                
                                # Получаем информацию о скорости платформы
                                base_speed = PADDLE_SPEED
                                adjusted_speed = ai_player.get_adjusted_paddle_speed(base_speed) if hasattr(ai_player, 'get_adjusted_paddle_speed') else base_speed
                                
                                # Рассчитываем, где должна была быть платформа
                                ball_was_in_separation_zone = separation_zone_start <= ball_y < paddle_zone_start
                                
                                # Рассчитываем расстояние от мяча до платформы по горизонтали
                                horizontal_distance = abs(ball_x - paddle_x)
                                
                                # Определяем, в какую зону относительно платформы находится мяч
                                # ВАЖНО: Это НЕ означает, что мяч ударился о платформу!
                                # Это показывает, где находится мяч относительно платформы
                                paddle_zone_size = PADDLE_WIDTH / 3
                                ball_offset_from_paddle_center = ball_x - paddle_x
                                if ball_offset_from_paddle_center < -paddle_zone_size:
                                    ball_zone = "LEFT (слева от платформы)"
                                elif ball_offset_from_paddle_center > paddle_zone_size:
                                    ball_zone = "RIGHT (справа от платформы)"
                                else:
                                    ball_zone = "CENTER (над платформой)"
                                
                                # Проверяем, действительно ли мяч попал в платформу
                                ball_hit_paddle = (paddle_left <= ball_x <= paddle_right and 
                                                  ball_bottom >= paddle_top and 
                                                  ball_bottom <= paddle_top + 5)
                                
                                print(f"[BALL LOST] ========== ДИАГНОСТИКА ПОТЕРИ МЯЧА ==========")
                                print(f"  Мяч: pos=({ball_x:.1f}, {ball_y:.1f}) bottom={ball_bottom:.1f} vel=({ball_vel_x:.1f}, {ball_vel_y:.1f}) speed={ball_speed:.1f}")
                                print(f"  Платформа: center_x={paddle_x:.1f} top={paddle_top:.1f} left={paddle_left:.1f} right={paddle_right:.1f}")
                                print(f"  Расстояние: horizontal={horizontal_distance:.1f}px vertical={ball_bottom - paddle_top:.1f}px")
                                print(f"  Мяч относительно платформы: {ball_zone} (offset={ball_offset_from_paddle_center:.1f}px)")
                                print(f"  Мяч ударился о платформу: {ball_hit_paddle} (если False - мяч пролетел мимо)")
                                print(f"  Целевая позиция AI: optimal_x={optimal_x:.1f} distance_to_optimal={distance_to_optimal:.1f}px")
                                print(f"  Скорость платформы: base={base_speed} adjusted={adjusted_speed}")
                                print(f"  Зоны: separation_start={separation_zone_start} paddle_start={paddle_zone_start} ball_was_in_zone={ball_was_in_separation_zone}")
                                print(f"  Целевая позиция установлена: {ai_player.separation_zone_tracker.target_position_set if hasattr(ai_player, 'separation_zone_tracker') else False}")
                                if hasattr(ai_player, 'separation_zone_tracker') and ai_player.separation_zone_tracker.target_position:
                                    target_pos = ai_player.separation_zone_tracker.target_position
                                    if target_pos is not None:
                                        print(f"  Сохраненная целевая позиция: {target_pos:.1f} distance={abs(paddle_x - target_pos):.1f}px")
                                print(f"  Жизни: {lives_left}")
                                print(f"========================================================")
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Мяч потерян! Обрабатываем...")
                        # Мяч ниже верхней границы платформы и не отскочил - он потерян
                        lives_left -= 1
                        # КРИТИЧНО: Логируем после уменьшения жизней
                        if auto_mode or training_mode:
                            if not getattr(sys, "frozen", False):
                                print(f"[LIFE LOSS] Жизни уменьшены! lives_left={lives_left}, game_over={game_over}")
                        if lives_left > 0:
                            ball.reset(paddle.rect)
                            ball.vel_y = 0
                            # Логируем потерю мяча для AI
                            if auto_mode or training_mode:
                                ai_result = {
                                    "action_type": "ball_lost",
                                    "success": False,
                                    "confidence": 0.0,
                                    "ball_speed": ball.get_speed(),
                                    "remaining_bricks": len(bricks),
                                }
                                ai_player.learn_from_result(ai_result)
                                ai_player._log_paddle_movement(
                                    paddle.rect.centerx,
                                    paddle.rect.centerx,
                                    f"ПОТЕРЯ МЯЧА: мяч ниже платформы. Мяч Y={ball.rect.bottom}, Платформа top={paddle.rect.top}",
                                    0.0
                                )
                                # КРИТИЧНО: Сбрасываем все трекеры после потери мяча
                                ai_player._reset_game_state_trackers()
                        else:
                            # КРИТИЧНО: Логируем окончание жизней
                            if auto_mode or training_mode:
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME END] Все жизни потрачены (ball.rect.bottom > paddle.rect.top)! lives_left={lives_left}, training_mode={training_mode}")
                            game_over = True
                            # Рассчитываем время игры и сохраняем результат
                            game_time_seconds = int(time.time() - game_start_time)

                            # Обучаем AI на результате игры (проигрыш)
                            if auto_mode or training_mode:
                                # В режиме обучения считаем кубики за весь матч (пока не потратятся все жизни)
                                total_bricks_destroyed = (
                                    BRICK_ROWS * BRICK_COLS
                                ) - len(bricks)

                                # Обновляем финальную статистику обучения
                                if training_mode:
                                    ai_player.update_training_stats(
                                        total_bricks_destroyed,
                                        game_time_seconds,
                                        MAX_LIVES,  # Все жизни потрачены
                                    )

                                ai_result = {
                                    "action_type": "game_end",
                                    "success": False,  # Игра проиграна
                                    "final_score": score,
                                    "game_duration": game_time_seconds,
                                    "bricks_remaining": len(bricks),
                                    "bricks_destroyed": total_bricks_destroyed,
                                    "lives_lost": MAX_LIVES,  # Все жизни потрачены
                                }
                                try:
                                    ai_player.learn_from_result(ai_result)
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART ERROR] Ошибка в learn_from_result: {e}")
                                        import traceback
                                        traceback.print_exc()
                                
                                try:
                                    if hasattr(ai_player, 'on_game_end'):
                                        ai_player.on_game_end(
                                            False, score, training_mode=training_mode
                                        )
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART ERROR] Ошибка в on_game_end: {e}")
                                        import traceback
                                        traceback.print_exc()

                            # В режиме обучения не показываем экран результатов, сразу перезапускаем
                            if training_mode:
                                # КРИТИЧНО: Логируем начало перезапуска
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME RESTART] Начинаем перезапуск игры в режиме обучения после потери всех жизней...")
                                
                                # КРИТИЧНО: Сбрасываем все трекеры состояния AI перед новой игрой
                                ai_player._reset_game_state_trackers()
                                
                                # Автоматически перезапускаем игру в режиме обучения
                                paddle = Paddle()
                                ball = Ball()
                                optimal_ball_speed = ai_player.get_optimal_ball_speed()
                                if optimal_ball_speed > 10:
                                    ball.current_speed = optimal_ball_speed
                                else:
                                    ball.set_speed(
                                        optimal_ball_speed,
                                        settings_manager,
                                        auto_mode=False,
                                    )
                                ball.reset(paddle.rect)
                                ball.vel_y = 0
                                bricks = build_bricks()
                                score = 0
                                lives_left = (
                                    MAX_LIVES  # Восстанавливаем жизни для нового матча
                                )
                                game_over = False
                                game_started = True  # Автоматически запускаем
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()
                                game_start_time = time.time()
                                
                                # КРИТИЧНО: Сразу обновляем состояние игры для AI после перезапуска
                                # Это гарантирует, что current_game_state будет установлен до первого вызова move_paddle_towards
                                ai_player.update_game_state(
                                    ball, paddle, bricks, score, int(game_start_time)
                                )
                                
                                # КРИТИЧНО: Логируем перезапуск игры для диагностики
                                if auto_mode or training_mode:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART] Игра перезапущена после потери всех жизней!")
                                        print(f"[GAME RESTART] lives_left={lives_left}, game_over={game_over}, game_started={game_started}")
                                        print(f"[GAME RESTART] ball.vel_x={ball.vel_x}, ball.vel_y={ball.vel_y}, paddle.x={paddle.rect.x}, bricks={len(bricks)}")
                                    ai_player.performance_logger.log_ball_paddle_positions(
                                        ball.rect.centerx,
                                        ball.rect.centery,
                                        ball.vel_x,
                                        ball.vel_y,
                                        paddle.rect.x,
                                        paddle.rect.y,
                                        paddle.rect.width,
                                        paddle.rect.height,
                                        "GAME_RESTART_AFTER_LOSS"
                                    )
                                    # Логируем начало новой игры
                                    if ai_player.current_game_state:
                                        ai_player.performance_logger.log_game_start(ai_player.current_game_state)
                            else:
                                # В ручном режиме показываем экран результатов
                                sound_enabled, restart_game, exit_game = (
                                    show_game_results(
                                        screen,
                                        font,
                                        big_font,
                                        score,
                                        player_name,
                                        game_time_seconds,
                                        highscore_manager,
                                        settings_manager,
                                        ball,
                                        auto_mode,
                                    )
                                )

                                # Если игрок хочет выйти из игры
                                if exit_game:
                                    # Сохраняем данные обучения перед выходом
                                    if auto_mode:
                                        ai_player.save_learning_data()
                                    pygame.quit()
                                    return

                                # Обработка перезапуска в зависимости от режима
                                if restart_game:
                                    if auto_mode:
                                        # В авторежиме возвращаемся к вводу имени
                                        auto_mode_complete = True
                                        running = False  # Останавливаем текущую игру
                                        break  # Выход из игрового цикла
                                    else:
                                        # В ручном режиме перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
                                        paddle = Paddle()
                                        ball = Ball()
                                        ball_speed = settings_manager.get_ball_speed()
                                        ball.set_speed(ball_speed)
                                        ball.reset(paddle.rect)
                                        ball.vel_y = 0
                                        bricks = build_bricks()
                                        score = 0
                                        lives_left = MAX_LIVES
                                        game_over = False
                                        game_started = False
                                        # Пересоздаем AI для новой игры
                                        ai_player = AIPlayer(
                                            SCREEN_WIDTH,
                                            SCREEN_HEIGHT,
                                            debug_mode=True,
                                        )
                                        ai_player.activate()
                                        # Перезапускаем отсчет времени игры
                                        game_start_time = time.time()
                        continue  # Пропускаем остальную обработку кадра

                    # Оптимизация: проверяем столкновения только если есть кирпичи
                    # и мяч находится в области кирпичей (выше зоны разделения)
                    hit_index = -1
                    if bricks and ball.rect.bottom <= SEPARATION_ZONE_TOP + 50:
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Проверяем столкновения с кубиками...")
                        try:
                            hit_index = ball.rect.collidelist(bricks)
                            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                                print(f"[AI DEBUG] hit_index={hit_index}")
                        except Exception as e:
                            if not getattr(sys, "frozen", False):
                                print(f"[ERROR] Ошибка в collidelist: {e}")
                                import traceback
                                traceback.print_exc()
                            hit_index = -1
                    if hit_index != -1:
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Попадание в кубик! hit_index={hit_index}")
                        ball.bounce_vertical()
                        destroyed_brick = bricks.pop(hit_index)
                        score += 1

                        # КРИТИЧНО: При попадании в кубик сбрасываем счетчик отбитий в пустоту
                        if auto_mode or training_mode:
                            ai_player.empty_bounce_tracker["consecutive_empty_bounces"] = 0
                            ai_player.empty_bounce_tracker["ceiling_bounces"] = 0

                        # Обучаем AI на результате попадания в кубик
                        if auto_mode or training_mode:
                            # destroyed_brick определена выше в этом же блоке (строка 2237)
                            try:
                                ai_result = {
                                    "action_type": "brick_hit",
                                    "success": True,
                                    "confidence": 1.0,
                                    "bricks_destroyed": [
                                        {"x": destroyed_brick.x, "y": destroyed_brick.y}
                                    ],
                                    "remaining_bricks": len(bricks),
                                    "ball_speed": ball.get_speed(),
                                }
                                ai_player.learn_from_result(ai_result)
                            except Exception as e:
                                if not getattr(sys, "frozen", False):
                                    print(f"[ERROR] Ошибка при обучении AI: {e}")
                                    import traceback
                                    traceback.print_exc()

                        # Play random brick hit sound if sound is enabled
                        if sound_enabled and brick_hit_sounds:
                            brick_hit_sounds[
                                random.randint(0, len(brick_hit_sounds) - 1)
                            ].play()
                    else:
                        if frame_counter <= 3 and not getattr(sys, "frozen", False):
                            print(f"[AI DEBUG] Столкновений с кубиками нет")
                        # КРИТИЧНО: Мяч не попал в кубики - проверяем, был ли отскок от потолка
                        # Если был отскок от потолка и мяч не попал в кубики - это отбитие в пустоту
                        ceiling_bounces = ai_player.empty_bounce_tracker.get("ceiling_bounces", 0) or 0
                        if (auto_mode or training_mode) and ceiling_bounces > 0:
                            # Мяч отскочил от потолка и не попал в кубики - увеличиваем счетчик
                            ai_player.empty_bounce_tracker["consecutive_empty_bounces"] += 1
                            ai_player.empty_bounce_tracker["last_bounce_position"] = paddle.rect.centerx
                            ai_player.empty_bounce_tracker["last_bounce_time"] = time.time()
                            # Логируем отбитие в пустоту
                            brick_coords_count = len(ai_player.targeting_system.brick_coordinates if hasattr(ai_player, 'targeting_system') else [])
                            ai_player._log_paddle_movement(
                                paddle.rect.centerx,
                                paddle.rect.centerx,
                                f"ОТБИТИЕ В ПУСТОТУ #{ai_player.empty_bounce_tracker['consecutive_empty_bounces']} (отскок от потолка без попадания). Координаты кубиков: {brick_coords_count}",
                                0.5
                            )
                            # Сбрасываем счетчик отскоков от потолка для следующей проверки
                            ai_player.empty_bounce_tracker["ceiling_bounces"] = 0
                        
                        # КРИТИЧНО: Проверяем победу (все кубики сбиты) и перезапускаем в режиме обучения
                        if not bricks:
                            game_over = True
                            game_time_seconds = int(time.time() - game_start_time)
                            
                            # Обучаем AI на результате игры (победа)
                            if auto_mode or training_mode:
                                ai_result = {
                                    "action_type": "game_end",
                                    "success": True,  # Игра выиграна
                                    "final_score": score,
                                    "game_duration": game_time_seconds,
                                    "bricks_remaining": 0,
                                    "bricks_destroyed": BRICK_ROWS * BRICK_COLS,
                                    "lives_lost": MAX_LIVES - lives_left,
                                }
                                ai_player.learn_from_result(ai_result)
                                ai_player.on_game_end(
                                    True, score, training_mode=training_mode
                                )
                            
                            # В режиме обучения не показываем экран результатов, сразу перезапускаем
                            if training_mode:
                                # КРИТИЧНО: Сбрасываем все трекеры состояния AI перед новой игрой
                                ai_player._reset_game_state_trackers()
                                
                                # Автоматически перезапускаем игру в режиме обучения
                                paddle = Paddle()
                                ball = Ball()
                                optimal_ball_speed = ai_player.get_optimal_ball_speed()
                                if optimal_ball_speed > 10:
                                    ball.current_speed = optimal_ball_speed
                                else:
                                    ball.set_speed(
                                        optimal_ball_speed,
                                        settings_manager,
                                        auto_mode=False,
                                    )
                                ball.reset(paddle.rect)
                                ball.vel_y = 0
                                bricks = build_bricks()
                                score = 0
                                lives_left = MAX_LIVES  # Восстанавливаем жизни для нового матча
                                game_over = False
                                game_started = True  # Автоматически запускаем
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()
                                game_start_time = time.time()
                                
                                # КРИТИЧНО: Сразу обновляем состояние игры для AI после перезапуска
                                # Это гарантирует, что current_game_state будет установлен до первого вызова move_paddle_towards
                                ai_player.update_game_state(
                                    ball, paddle, bricks, score, int(game_start_time)
                                )
                                
                                # КРИТИЧНО: Сбрасываем все трекеры состояния AI после перезапуска
                                ai_player._reset_game_state_trackers()
                                
                                # КРИТИЧНО: Логируем успешный перезапуск
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME RESTART] Игра успешно перезапущена! lives_left={lives_left}, game_over={game_over}, game_started={game_started}")
                                    print(f"[GAME RESTART] ball.vel_x={ball.vel_x}, ball.vel_y={ball.vel_y}, paddle.x={paddle.rect.x}")
                                
                                continue  # Пропускаем остальную обработку кадра

                    if ball.rect.bottom >= SCREEN_HEIGHT:
                        # КРИТИЧНО: Логируем потерю мяча (мяч за границей экрана)
                        if auto_mode or training_mode:
                            if not getattr(sys, "frozen", False):
                                print(f"[LIFE LOSS] Мяч за границей экрана (ball.rect.bottom={ball.rect.bottom} >= SCREEN_HEIGHT={SCREEN_HEIGHT})! lives_left={lives_left}")
                        # Уменьшаем жизни (в режиме обучения тоже)
                        lives_left -= 1
                        # КРИТИЧНО: Логируем потерю жизни для диагностики
                        if auto_mode or training_mode:
                            if not getattr(sys, "frozen", False):
                                print(f"[LIFE LOSS] Жизни уменьшены! lives_left={lives_left}, training_mode={training_mode}, game_over={game_over}")
                        
                        # КРИТИЧНО: Проверяем, не закончились ли жизни
                        if lives_left <= 0:
                            # КРИТИЧНО: Логируем окончание жизней
                            if auto_mode or training_mode:
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME END] Все жизни потрачены! lives_left={lives_left}, training_mode={training_mode}, game_over={game_over}")
                            game_over = True
                            # Рассчитываем время игры и сохраняем результат
                            game_time_seconds = int(time.time() - game_start_time)

                            # Обучаем AI на результате игры (проигрыш)
                            if auto_mode or training_mode:
                                # В режиме обучения считаем кубики за весь матч (пока не потратятся все жизни)
                                total_bricks_destroyed = (
                                    BRICK_ROWS * BRICK_COLS
                                ) - len(bricks)

                                # Обновляем финальную статистику обучения
                                if training_mode:
                                    ai_player.update_training_stats(
                                        total_bricks_destroyed,
                                        game_time_seconds,
                                        MAX_LIVES,  # Все жизни потрачены
                                    )

                                ai_result = {
                                    "action_type": "game_end",
                                    "success": False,  # Игра проиграна
                                    "final_score": score,
                                    "game_duration": game_time_seconds,
                                    "bricks_remaining": len(bricks),
                                    "bricks_destroyed": total_bricks_destroyed,
                                    "lives_lost": MAX_LIVES,  # Все жизни потрачены
                                }
                                try:
                                    ai_player.learn_from_result(ai_result)
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART ERROR] Ошибка в learn_from_result: {e}")
                                        import traceback
                                        traceback.print_exc()
                                
                                try:
                                    if hasattr(ai_player, 'on_game_end'):
                                        ai_player.on_game_end(
                                            False, score, training_mode=training_mode
                                        )
                                except Exception as e:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART ERROR] Ошибка в on_game_end: {e}")
                                        import traceback
                                        traceback.print_exc()

                            # В режиме обучения не показываем экран результатов, сразу перезапускаем
                            if training_mode:
                                # КРИТИЧНО: Логируем начало перезапуска
                                if not getattr(sys, "frozen", False):
                                    print(f"[GAME RESTART] Начинаем перезапуск игры в режиме обучения после потери всех жизней...")
                                
                                # КРИТИЧНО: Сбрасываем все трекеры состояния AI перед новой игрой
                                ai_player._reset_game_state_trackers()
                                
                                # Автоматически перезапускаем игру в режиме обучения
                                paddle = Paddle()
                                ball = Ball()
                                optimal_ball_speed = ai_player.get_optimal_ball_speed()
                                if optimal_ball_speed > 10:
                                    ball.current_speed = optimal_ball_speed
                                else:
                                    ball.set_speed(
                                        optimal_ball_speed,
                                        settings_manager,
                                        auto_mode=False,
                                    )
                                ball.reset(paddle.rect)
                                ball.vel_y = 0
                                bricks = build_bricks()
                                score = 0
                                lives_left = (
                                    MAX_LIVES  # Восстанавливаем жизни для нового матча
                                )
                                game_over = False
                                game_started = True  # Автоматически запускаем
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()
                                game_start_time = time.time()
                                
                                # КРИТИЧНО: Сразу обновляем состояние игры для AI после перезапуска
                                # Это гарантирует, что current_game_state будет установлен до первого вызова move_paddle_towards
                                ai_player.update_game_state(
                                    ball, paddle, bricks, score, int(game_start_time)
                                )
                                
                                # КРИТИЧНО: Логируем перезапуск игры для диагностики
                                if auto_mode or training_mode:
                                    if not getattr(sys, "frozen", False):
                                        print(f"[GAME RESTART] Игра перезапущена после потери всех жизней!")
                                        print(f"[GAME RESTART] lives_left={lives_left}, game_over={game_over}, game_started={game_started}")
                                        print(f"[GAME RESTART] ball.vel_x={ball.vel_x}, ball.vel_y={ball.vel_y}, paddle.x={paddle.rect.x}, bricks={len(bricks)}")
                                    ai_player.performance_logger.log_ball_paddle_positions(
                                        ball.rect.centerx,
                                        ball.rect.centery,
                                        ball.vel_x,
                                        ball.vel_y,
                                        paddle.rect.x,
                                        paddle.rect.y,
                                        paddle.rect.width,
                                        paddle.rect.height,
                                        "GAME_RESTART_AFTER_LOSS"
                                    )
                                    # Логируем начало новой игры
                                    if ai_player.current_game_state:
                                        ai_player.performance_logger.log_game_start(ai_player.current_game_state)
                            else:
                                # В обычном режиме показываем экран результатов
                                sound_enabled, restart_game, exit_game = (
                                    show_game_results(
                                        screen,
                                        font,
                                        big_font,
                                        score,
                                        player_name,
                                        game_time_seconds,
                                        highscore_manager,
                                        settings_manager,
                                        ball,
                                        auto_mode,
                                    )
                                )

                                # Если игрок хочет выйти из игры
                                if exit_game:
                                    # Сохраняем данные обучения перед выходом
                                    if auto_mode:
                                        ai_player.save_learning_data()
                                    pygame.quit()
                                    return

                                # Обработка перезапуска в зависимости от режима
                                if restart_game:
                                    if auto_mode:
                                        # В авторежиме возвращаемся к вводу имени
                                        auto_mode_complete = True
                                        running = False  # Останавливаем текущую игру
                                        break  # Выход из игрового цикла
                                    else:
                                        # В ручном режиме перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
                                        paddle = Paddle()
                                        ball = Ball()
                                        ball_speed = settings_manager.get_ball_speed()
                                        ball.set_speed(ball_speed)
                                        ball.reset(paddle.rect)
                                        ball.vel_y = 0
                                        bricks = build_bricks()
                                        score = 0
                                        lives_left = MAX_LIVES
                                        game_over = False
                                        game_started = False
                                        # Пересоздаем AI для новой игры
                                        ai_player = AIPlayer(
                                            SCREEN_WIDTH,
                                            SCREEN_HEIGHT,
                                            debug_mode=True,
                                        )
                                        ai_player.activate()
                                        # Перезапускаем отсчет времени игры
                                        game_start_time = time.time()
                        else:
                            ball.reset(paddle.rect)
                            ball.vel_y = 0
                            game_started = False

                            # В авторежиме автоматически запускаем игру заново
                            if auto_mode:
                                game_started = True
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()

                            # В режиме обучения также автоматически запускаем игру заново (если есть жизни)
                            if training_mode and lives_left > 0:
                                game_started = True
                                ball.vel_x = ball.get_speed()
                                ball.vel_y = -ball.get_speed()

                    if not bricks:
                        # В режиме обучения автоматически перезапускаем игру
                        if training_mode:
                            # Обучаем AI на результате игры (победа)
                            game_time_seconds = int(time.time() - game_start_time)
                            total_bricks_destroyed = BRICK_ROWS * BRICK_COLS
                            lives_lost = MAX_LIVES - lives_left

                            # Обновляем финальную статистику обучения
                            ai_player.update_training_stats(
                                total_bricks_destroyed, game_time_seconds, lives_lost
                            )

                            ai_result = {
                                "action_type": "game_end",
                                "success": True,  # Игра выиграна
                                "final_score": score,
                                "game_duration": game_time_seconds,
                                "bricks_remaining": 0,
                                "bricks_destroyed": total_bricks_destroyed,
                                "lives_lost": lives_lost,  # Сколько жизней потрачено
                            }
                            ai_player.learn_from_result(ai_result)
                            ai_player.on_game_end(
                                True, score, training_mode=training_mode
                            )

                            # Увеличиваем счетчик раундов
                            training_rounds += 1

                            # ИСПРАВЛЕНИЕ: Используем оптимальную скорость из обучения
                            optimal_ball_speed = ai_player.get_optimal_ball_speed()

                            # Автоматически перезапускаем игру
                            paddle = Paddle()
                            ball = Ball()
                            # ИСПРАВЛЕНИЕ: Используем оптимальную скорость из обучения
                            # В режиме обучения разрешаем любую скорость (до 30)
                            if optimal_ball_speed > 10:
                                # Если скорость больше 10, устанавливаем напрямую, обходя ограничение set_speed
                                ball.current_speed = optimal_ball_speed
                                # Не обновляем настройки, так как они имеют ограничение max_speed=10
                            else:
                                ball.set_speed(
                                    optimal_ball_speed,
                                    settings_manager,
                                    auto_mode=False,
                                )
                            ball.reset(paddle.rect)
                            ball.vel_y = 0
                            bricks = build_bricks()
                            score = 0
                            # В режиме обучения восстанавливаем жизни для нового матча
                            lives_left = MAX_LIVES
                            game_over = False
                            game_started = True  # Автоматически запускаем
                            ball.vel_x = ball.get_speed()
                            ball.vel_y = -ball.get_speed()
                            # Перезапускаем отсчет времени игры
                            game_start_time = time.time()
                            
                            # КРИТИЧНО: Обновляем состояние игры для AI после перезапуска
                            ai_player.update_game_state(
                                ball, paddle, bricks, score, int(game_start_time)
                            )
                            
                            # КРИТИЧНО: Логируем перезапуск игры после победы для диагностики
                            if auto_mode or training_mode:
                                ai_player.performance_logger.log_ball_paddle_positions(
                                    ball.rect.centerx,
                                    ball.rect.centery,
                                    ball.vel_x,
                                    ball.vel_y,
                                    paddle.rect.x,
                                    paddle.rect.y,
                                    paddle.rect.width,
                                    paddle.rect.height,
                                    "GAME_RESTART_AFTER_WIN"
                                )
                                # Логируем начало новой игры
                                if ai_player.current_game_state:
                                    ai_player.performance_logger.log_game_start(ai_player.current_game_state)
                        else:
                            # Обычный режим - показываем экран результатов
                            game_over = True
                            # Рассчитываем время игры и сохраняем результат
                            game_time_seconds = int(time.time() - game_start_time)

                            # Обучаем AI на результате игры (победа)
                            if auto_mode:
                                ai_result = {
                                    "action_type": "game_end",
                                    "success": True,  # Игра выиграна
                                    "final_score": score,
                                    "game_duration": game_time_seconds,
                                    "bricks_remaining": 0,
                                }
                                ai_player.learn_from_result(ai_result)
                                ai_player.on_game_end(True, score)

                            # Показываем заставку победы только в обычном режиме (с вводом имени)
                            # и если у игрока остались жизни (победа)
                            if not auto_mode and not training_mode and lives_left > 0:
                                show_victory_splash(screen, duration_seconds=5.0)

                            # В любом режиме показываем экран результатов
                            sound_enabled, restart_game, exit_game = show_game_results(
                                screen,
                                font,
                                big_font,
                                score,
                                player_name,
                                game_time_seconds,
                                highscore_manager,
                                settings_manager,
                                ball,
                                auto_mode,
                            )

                            # Если игрок хочет выйти из игры
                            if exit_game:
                                # Сохраняем данные обучения перед выходом
                                if auto_mode:
                                    ai_player.save_learning_data()
                                pygame.quit()
                                return

                            # Обработка перезапуска в зависимости от режима
                            if restart_game:
                                if auto_mode:
                                    # В авторежиме возвращаемся к вводу имени
                                    auto_mode_complete = True
                                    running = False  # Останавливаем текущую игру
                                    break  # Выход из игрового цикла
                                else:
                                    # В ручном режиме перезапускаем игру - ПОЛНЫЙ СБРОС СОСТОЯНИЯ
                                    paddle = Paddle()
                                    ball = Ball()
                                    ball_speed = settings_manager.get_ball_speed()
                                    ball.set_speed(ball_speed)
                                    ball.reset(paddle.rect)
                                    ball.vel_y = 0
                                    bricks = build_bricks()
                                    score = 0
                                    lives_left = MAX_LIVES
                                    game_over = False
                                    game_started = False
                                    # Пересоздаем AI для новой игры
                                    ai_player = AIPlayer(
                                        SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True
                                    )
                                    ai_player.activate()
                                    # Перезапускаем отсчет времени игры
                                    game_start_time = time.time()

            # Отладочное сообщение только в первых 3 кадрах
            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Конец блока if not game_over, переходим к отрисовке")
                print(f"[AI DEBUG] Начинаем отрисовку, game_over={game_over}, bricks={len(bricks) if 'bricks' in locals() else 'N/A'}")
            
            # КРИТИЧНО: Отрисовка игры
            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Вызываем screen.fill()...")
            screen.fill((10, 10, 30))  # Темно-синий фон
            if frame_counter <= 3 and not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] screen.fill() завершен")
            draw_bricks(screen, bricks)  # Отрисовка кубиков
            # Отрисовка платформы с цветными секциями для подсказки направления отскока
            left_rect = pygame.Rect(
                paddle.rect.x, paddle.rect.y, paddle.rect.width // 3, paddle.rect.height
            )
            pygame.draw.rect(
                screen, (255, 0, 0), left_rect
            )  # Красный для отскока влево
            mid_rect = pygame.Rect(
                paddle.rect.x + paddle.rect.width // 3,
                paddle.rect.y,
                paddle.rect.width // 3,
                paddle.rect.height,
            )
            pygame.draw.rect(
                screen, (240, 240, 240), mid_rect
            )  # Белый для прямого отскока
            right_rect = pygame.Rect(
                paddle.rect.x + 2 * paddle.rect.width // 3,
                paddle.rect.y,
                paddle.rect.width - 2 * paddle.rect.width // 3,
                paddle.rect.height,
            )
            pygame.draw.rect(
                screen, (0, 0, 255), right_rect
            )  # Синий для отскока вправо
            pygame.draw.ellipse(screen, (230, 90, 90), ball.rect)

            # Визуализация отладочной информации AI системы
            if auto_mode or training_mode:
                ai_player.visualize_debug_info(screen)

            draw_hud(
                screen,
                score,
                lives_left,
                font,
                ball,
                auto_mode,
                training_mode,
                ai_player,
            )

            if not game_started:
                if training_mode:
                    # В режиме обучения показываем специальную подсказку
                    training_hint = big_font.render(
                        f"РЕЖИМ ОБУЧЕНИЯ | Раунд: {training_rounds + 1}",
                        True,
                        (0, 255, 255),
                    )
                    training_rect = training_hint.get_rect(
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    )
                    screen.blit(training_hint, training_rect)
                elif auto_mode:
                    # В авторежиме показываем другую подсказку
                    auto_hint = big_font.render(
                        "АВТОРЕЖИМ АКТИВЕН", True, (255, 255, 0)
                    )
                    auto_rect = auto_hint.get_rect(
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    )
                    screen.blit(auto_hint, auto_rect)
                else:
                    draw_start_hint(screen, big_font)

            pygame.display.flip()
            clock.tick(FPS)
            
            # Отладочное сообщение только в первом кадре
            if frame_counter == 1 and not getattr(sys, "frozen", False):
                print(f"[AI DEBUG] Первый кадр отрисован, bricks={len(bricks)}, paddle.x={paddle.rect.x}, ball.x={ball.rect.centerx}, game_started={game_started}")

            # Проверяем завершение авторежима
            if auto_mode_complete:
                break  # Выход для возврата к вводу имени

        # В режиме обучения выводим статистику перед выходом
        if training_mode:
            # Сохраняем данные обучения
            try:
                if ai_player and ai_player.performance_metrics.get("games_played", 0) > 0:
                    ai_player.save_learning_data()
                    if not getattr(sys, "frozen", False):
                        print(
                            f"[AI] Режим обучения завершен. Сыграно матчей: {training_rounds}"
                        )
                        print("[AI] Данные обучения сохранены.")
                else:
                    # КРИТИЧНО: Не сохраняем данные, если не было сыграно ни одной игры
                    if not getattr(sys, "frozen", False):
                        print(f"[AI DEBUG] Данные обучения не сохранены - не было сыграно игр (games_played={ai_player.performance_metrics.get('games_played', 0) if ai_player else 0})")
            except Exception as e:
                if not getattr(sys, "frozen", False):
                    print(f"[AI] Предупреждение: не удалось сохранить данные обучения: {e}")
        
        # Продолжаем внешний цикл для возврата к вводу имени
        continue


if __name__ == "__main__":
    main()
