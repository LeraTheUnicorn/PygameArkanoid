# Игра Арканоид
# Отслеживание версий
VERSION = "2.2"

import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Скрыть сообщение поддержки pygame

import random
import time
import numpy as np
import sys
import os
from dataclasses import dataclass, field
from typing import List

import pygame
from highscores import HighScoreManager
from settings import SettingsManager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ai.ai_player import AIPlayer


def resource_path(relative_path):
    """Получает абсолютный путь к ресурсу, работает как в разработке, так и в exe"""
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Настройки игры
# Размеры экрана
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Размеры и скорость платформы
PADDLE_WIDTH = 120
PADDLE_HEIGHT = 15
PADDLE_SPEED = 9

# Размеры и скорость мяча
BALL_SIZE = 16
BALL_SPEED_DEFAULT = 5  # Значение по умолчанию

# Параметры кубиков
BRICK_ROWS = 5
BRICK_COLS = 10
BRICK_WIDTH = 60
BRICK_HEIGHT = 20
BRICK_PADDING = 10
BRICK_OFFSET_TOP = 60

MAX_LIVES = 3  # Максимальное количество жизней


def generate_tone_sound(
    frequency: float, duration: float, sample_rate: int = 44100, volume: float = 0.3
) -> pygame.mixer.Sound:
    """Генерирует короткий тональный звук для звуковых эффектов"""
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
    """Проверяет, является ли символ допустимым для имени игрока"""
    if not char:  # Проверяем пустые строки
        return False
    # Разрешаем только буквы
    return char.isalpha()


def generate_paddle_sound() -> pygame.mixer.Sound:
    """Генерирует 16-битный звук отскока от платформы (всегда одинаковый)"""
    return generate_tone_sound(330, 0.15, volume=0.4)  # E4 - 330 Гц


def get_player_name(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    highscore_manager: HighScoreManager,
) -> tuple[str, bool, bool, bool]:
    """Возвращает имя игрока, введенное с клавиатуры, состояние звука, флаг выхода из игры и флаг авторежима"""
    input_text = ""
    input_active = True
    sound_enabled = True
    exit_game = False
    auto_mode = False  # Всегда начинаем с сброса флага авторежима

    while input_active:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game = True
                return "", sound_enabled, exit_game, False  # Выход из игры по крестику
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
                    return "", sound_enabled, True, False
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
                    print(
                        f"Авторежим активирован через клавишу 0, имя: {input_text}"
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

        pygame.display.flip()

    # ФИНАЛЬНАЯ ВАЛИДАЦИЯ: убеждаемся, что имя корректно
    final_name = input_text.strip()
    if not final_name:
        final_name = "robot"  # Крайний случай для авторежима

    return final_name, sound_enabled, exit_game, auto_mode


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
    try:
        mono_font = pygame.font.SysFont("consolas", 18)  # Моноширинный шрифт Windows
    except:
        try:
            mono_font = pygame.font.SysFont(
                "courier", 18
            )  # Альтернативный моноширинный шрифт
        except:
            mono_font = font  # Если не получилось, используем обычный шрифт

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
    """Отображает экран с результатами игры и таблицей рекордов. Возвращает (состояние_звука, перезапуск_игры, выход_из_игры)."""
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
                    paused = True
                    sound_enabled = show_settings_window(
                        screen,
                        font,
                        big_font,
                        settings_manager,
                        ball,
                        sound_enabled,
                        auto_mode,
                    )
                    paused = False

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


@dataclass
class Paddle:
    rect: pygame.Rect = field(
        default_factory=lambda: pygame.Rect(
            (SCREEN_WIDTH - PADDLE_WIDTH) // 2,
            SCREEN_HEIGHT - 60,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        )
    )

    def move(self, direction: int) -> None:
        """direction = -1 (влево) / 1 (вправо)."""
        self.rect.x += direction * PADDLE_SPEED
        # Строгие границы для центра платформы: половина ширины платформы = 60 пикселей
        paddle_half_width = PADDLE_WIDTH // 2  # 60 пикселей
        min_center_x = paddle_half_width
        max_center_x = SCREEN_WIDTH - paddle_half_width
        self.rect.centerx = max(min_center_x, min(max_center_x, self.rect.centerx))


@dataclass
class Ball:
    """Класс мяча с интегрированным управлением скоростью"""

    rect: pygame.Rect = field(
        default_factory=lambda: pygame.Rect(
            (SCREEN_WIDTH - BALL_SIZE) // 2,
            SCREEN_HEIGHT // 2,
            BALL_SIZE,
            BALL_SIZE,
        )
    )
    vel_x: int = field(
        default_factory=lambda: random.choice([-BALL_SPEED_DEFAULT, BALL_SPEED_DEFAULT])
    )
    vel_y: int = field(default_factory=lambda: -BALL_SPEED_DEFAULT)
    current_speed: int = field(default_factory=lambda: BALL_SPEED_DEFAULT)

    def update(self) -> None:
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        # Строгие границы для центра мяча: радиус мяча = 8 пикселей
        ball_radius = BALL_SIZE // 2  # 8 пикселей
        min_center_x = ball_radius
        max_center_x = SCREEN_WIDTH - ball_radius

        # Ограничиваем позицию мяча
        self.rect.centerx = max(min_center_x, min(max_center_x, self.rect.centerx))

        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self.vel_x *= -1
            # Дополнительная защита от зацикливания у стен
            # Если мяч слишком долго отскакивает от стен, добавляем случайность
            if hasattr(self, "_wall_bounce_count"):
                self._wall_bounce_count += 1
            else:
                self._wall_bounce_count = 1

            if self._wall_bounce_count > 10:  # Если много раз отскочил от стен подряд
                # Добавляем небольшое случайное изменение вертикальной скорости
                self.vel_y += random.choice([-1, 0, 1])
                self._wall_bounce_count = 0  # Сбрасываем счетчик

        if self.rect.top <= 0:
            self.vel_y *= -1
            # Сбрасываем счетчик отскоков от стен при отскоке от верхней стенки
            if hasattr(self, "_wall_bounce_count"):
                self._wall_bounce_count = 0

    def bounce_vertical(self) -> None:
        self.vel_y *= -1

    def reset(self, paddle_rect: pygame.Rect) -> None:
        """Сброс мяча на платформу с текущей скоростью"""
        self.rect.center = paddle_rect.midtop
        self.rect.y -= BALL_SIZE
        self.vel_x = random.choice([-self.current_speed, self.current_speed])
        self.vel_y = -self.current_speed

    def set_speed(
        self,
        speed: int,
        settings_manager: SettingsManager = None,
        auto_mode: bool = False,
    ) -> None:
        """Устанавливает скорость мяча и обновляет настройки"""
        max_speed = 30 if auto_mode else 10
        if 1 <= speed <= max_speed:
            old_speed = self.current_speed
            self.current_speed = speed
            self.vel_x = (
                int(self.vel_x * speed / old_speed) if old_speed != 0 else speed
            )
            self.vel_y = (
                int(self.vel_y * speed / old_speed) if old_speed != 0 else -speed
            )

            if settings_manager:
                settings_manager.set_ball_speed(speed, auto_mode)

    def increase_speed(
        self, settings_manager: SettingsManager = None, auto_mode: bool = False
    ) -> None:
        """Увеличивает скорость на 1 (максимум зависит от режима)"""
        max_speed = 30 if auto_mode else 10
        if self.current_speed < max_speed:
            self.set_speed(self.current_speed + 1, settings_manager, auto_mode)

    def decrease_speed(
        self, settings_manager: SettingsManager = None, auto_mode: bool = False
    ) -> None:
        """Уменьшает скорость на 1 (минимум 1)"""
        if self.current_speed > 1:
            self.set_speed(self.current_speed - 1, settings_manager, auto_mode)

    def get_speed(self) -> int:
        """Возвращает текущую скорость мяча"""
        return self.current_speed


def build_bricks() -> List[pygame.Rect]:
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
    colors = [
        (200, 80, 80),
        (200, 160, 80),
        (80, 200, 120),
        (80, 140, 220),
        (150, 80, 220),
    ]
    for idx, brick in enumerate(bricks):
        pygame.draw.rect(screen, colors[idx // BRICK_COLS % len(colors)], brick)
        pygame.draw.rect(screen, (30, 30, 30), brick, 2)


def draw_hud(
    screen: pygame.Surface,
    score: int,
    lives_left: int,
    font: pygame.font.Font,
    ball: Ball,
    auto_mode: bool = False,
    ai_player = None,
) -> None:
    # Добавляем индикатор авторежима
    if auto_mode:
        # Показываем адаптивную скорость платформы в авторежиме
        adaptive_speed_text = ""
        if ai_player and hasattr(ai_player, 'current_game_state') and ai_player.current_game_state:
            optimal_x = ai_player.get_optimal_paddle_position()
            paddle_x = ai_player.current_game_state.paddle_position.x
            adaptive_speed = ai_player.calculate_adaptive_paddle_speed(
                paddle_x, optimal_x, ball.get_speed()
            )
            adaptive_speed_text = f" | Платформа: {adaptive_speed}"
        
        text = f"Очки: {score} | Жизни: {lives_left} | Скорость мяча: {ball.get_speed()}{adaptive_speed_text} | АВТОРЕЖИМ"
    else:
        text = f"Очки: {score} | Жизни: {lives_left} | Скорость: {ball.get_speed()} | ↑ ↓ - скорость"

    surf = font.render(text, True, (255, 255, 255) if not auto_mode else (255, 255, 0))
    screen.blit(surf, (SCREEN_WIDTH - surf.get_width() - 20, 20))


def render_colored_hint(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: tuple,
    base_color=(200, 200, 200),
    key_color=(255, 255, 0),
) -> None:
    """Отображает подсказку с выделенными ключевыми словами цветом"""
    words = text.split()
    x, y = pos
    key_words = ["Enter", "H", "M", "ESC", "↑", "↓", "0"]

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
    pygame.init()
    pygame.mixer.init()  # Инициализация аудио микшера
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Арканоид")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)
    big_font = pygame.font.SysFont("arial", 42, bold=True)

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
            pygame.mixer.music.load(resource_path("resources/audio/Night_Prowler.ogg"))
            pygame.mixer.music.set_volume(0.3)
            # Музыка будет запущена после ввода имени игрока
        except pygame.error:
            print("Фоновая музыка не загружена")
    except pygame.error as e:
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
        lives_left = MAX_LIVES
        game_over = False
        game_started = False

        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Пересоздаем AI-систему НО сначала сохраняем предыдущие данные обучения
        if "ai_player" in locals() and ai_player is not None:
            # Сохраняем данные обучения от предыдущего экземпляра
            ai_player.save_learning_data()

        # Создаем новый AI-систему, которая загрузит обновленные данные
        ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=True)
        print(f"[AI DEBUG] Новый AIPlayer создан. Обучение будет продолжено...")

        # Ввод имени игрока
        player_name, sound_enabled, exit_game, auto_mode = get_player_name(
            screen, font, big_font, highscore_manager
        )
        if exit_game:
            pygame.quit()
            return

        # Запускаем музыку после ввода имени (если звук включен)
        if sound_enabled:
            try:
                pygame.mixer.music.play(-1)  # Цикличное воспроизведение фоновой музыки
            except pygame.error:
                print("Не удалось запустить фоновую музыку")

        # В авторежиме сразу устанавливаем нужную скорость и запускаем игру
        if auto_mode:
            ai_player.activate()  # ВАЖНО: активируем AI систему
            ball.set_speed(
                15, settings_manager, auto_mode=True
            )  # Стартовая скорость 15 для авторежима
            game_started = True  # Игра начинается сразу
            ball.vel_x = ball.get_speed()  # Направление вправо
            ball.vel_y = -ball.get_speed()
            print(
                f"Авторежим: Игра запущена автоматически. AI активен: {ai_player.is_active}"
            )
        else:
            ai_player.deactivate()  # Деактивируем в ручном режиме

        # Отсчет времени игры
        game_start_time = time.time()

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # В ручном режиме QUIT немедленно закрывает приложение
                    pygame.quit()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Выход из игры
                        if auto_mode:
                            # В авторежиме ESC полностью закрывает приложение
                            pygame.quit()
                            return
                        else:
                            # В ручном режиме ESC полностью закрывает приложение
                            pygame.quit()
                            return
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

            keys = pygame.key.get_pressed()

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
                ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
                ai_player.activate()

            if not game_over:
                # Обновляем состояние игры для AI системы
                if auto_mode:
                    ai_player.update_game_state(
                        ball, paddle, bricks, score, int(game_start_time)
                    )

                # Движение платформы
                if auto_mode:
                    # В авторежиме используем адаптивную скорость платформы
                    # AI система сама рассчитает оптимальную скорость
                    movement = ai_player.move_paddle_towards(
                        paddle.rect.centerx, PADDLE_SPEED
                    )
                    # Применяем движение с учетом адаптивной скорости
                    paddle.rect.x += movement
                    # Строгие границы для центра платформы: половина ширины платформы = 60 пикселей
                    paddle_half_width = PADDLE_WIDTH // 2  # 60 пикселей
                    min_center_x = paddle_half_width
                    max_center_x = SCREEN_WIDTH - paddle_half_width
                    paddle.rect.centerx = max(
                        min_center_x, min(max_center_x, paddle.rect.centerx)
                    )

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
                    ball.update()

                    if ball.rect.colliderect(paddle.rect) and ball.vel_y > 0:
                        # Вычисляем точное смещение от центра платформы
                        paddle_center = paddle.rect.centerx
                        ball_center = ball.rect.centerx
                        offset = (ball_center - paddle_center) / (paddle.rect.width / 2)

                        # Ограничиваем offset в диапазоне [-1, 1]
                        offset = max(-1.0, min(1.0, offset))

                        # Устанавливаем новые скорости
                        ball.bounce_vertical()
                        ball.vel_x = int(offset * ball.get_speed())

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
                        if hasattr(ball, "_last_vel_x"):
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

                        # Play paddle bounce sound if sound is enabled
                        if sound_enabled and paddle_bounce_sound:
                            paddle_bounce_sound.play()

                        # Обучаем AI на результате отскока
                        if auto_mode:
                            ai_result = {
                                "action_type": "paddle_bounce",
                                "success": True,  # Отскок от платформы всегда успешен
                                "confidence": 0.8,
                                "movement_distance": abs(offset * paddle.rect.width),
                                "ball_speed": ball.get_speed(),
                                "remaining_bricks": len(bricks),
                            }
                            ai_player.learn_from_result(ai_result)

                    hit_index = ball.rect.collidelist(bricks)
                    if hit_index != -1:
                        ball.bounce_vertical()
                        destroyed_brick = bricks.pop(hit_index)
                        score += 1

                        # Обучаем AI на результате попадания в кубик
                        if auto_mode:
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

                        # Play random brick hit sound if sound is enabled
                        if sound_enabled and brick_hit_sounds:
                            brick_hit_sounds[
                                random.randint(0, len(brick_hit_sounds) - 1)
                            ].play()

                    if ball.rect.bottom >= SCREEN_HEIGHT:
                        lives_left -= 1
                        if lives_left <= 0:
                            game_over = True
                            # Рассчитываем время игры и сохраняем результат
                            game_time_seconds = int(time.time() - game_start_time)

                            # Обучаем AI на результате игры (проигрыш)
                            if auto_mode:
                                ai_result = {
                                    "action_type": "game_end",
                                    "success": False,  # Игра проиграна
                                    "final_score": score,
                                    "game_duration": game_time_seconds,
                                    "bricks_remaining": len(bricks),
                                }
                                ai_player.learn_from_result(ai_result)
                                ai_player.on_game_end(False, score)

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
                                        SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False
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

                    if not bricks:
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
                                    SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False
                                )
                                ai_player.activate()
                                # Перезапускаем отсчет времени игры
                                game_start_time = time.time()

            screen.fill((10, 10, 30))
            draw_bricks(screen, bricks)
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
            if auto_mode:
                ai_player.visualize_debug_info(screen)

            draw_hud(screen, score, lives_left, font, ball, auto_mode, ai_player)

            if not game_started:
                if auto_mode:
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

            # Выход из игрового цикла при необходимости (только для ручного режима)
            if not running and not auto_mode:
                break

            # Проверяем завершение авторежима
            if auto_mode_complete:
                break  # Выход для возврата к вводу имени

            # Проверяем, нужно ли остановить игру в ручном режиме
            if not running:
                # В ручном режиме при остановке игры полностью закрываем приложение
                if not auto_mode:
                    pygame.quit()
                    return
                break  # Выход для возврата к вводу имени

    # Сохраняем данные обучения AI при выходе из игры
    if auto_mode:
        ai_player.save_learning_data()

    pygame.quit()


if __name__ == "__main__":
    main()
