# Игра Арканоид
# Отслеживание версий
VERSION = "1.4.0"

import random
import math
import time
from dataclasses import dataclass, field
from typing import List

import pygame
from highscores import HighScoreManager

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
BALL_SPEED = 5

# Параметры кубиков
BRICK_ROWS = 5
BRICK_COLS = 10
BRICK_WIDTH = 60
BRICK_HEIGHT = 20
BRICK_PADDING = 10
BRICK_OFFSET_TOP = 60

MAX_LIVES = 3  # Максимальное количество жизней


def get_player_name(screen: pygame.Surface, font: pygame.font.Font, big_font: pygame.font.Font) -> str:
    """Возвращает имя игрока, введенное с клавиатуры"""
    input_text = ""
    input_active = True
    
    while input_active:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if input_text.strip():
                        input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif len(input_text) < 20:  # Ограничение длины имени
                    input_text += event.unicode
        
        # Отрисовка экрана
        screen.fill((10, 10, 30))
        
        # Заголовок
        title = big_font.render("Введите ваше имя:", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        screen.blit(title, title_rect)
        
        # Поле ввода
        input_surface = font.render(input_text, True, (255, 255, 255))
        input_rect = input_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        pygame.draw.rect(screen, (255, 255, 255), input_rect.inflate(20, 10), 2)
        screen.blit(input_surface, input_rect)
        
        # Подсказка
        hint = font.render("Нажмите Enter для продолжения", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(hint, hint_rect)
        
        pygame.display.flip()
    
    return input_text.strip()


def show_highscores(screen: pygame.Surface, font: pygame.font.Font, highscore_manager: HighScoreManager) -> None:
    """Отображает таблицу рекордов"""
    # Получаем текст рекордов
    highscores_text = highscore_manager.display_highscores()
    
    # Отображаем экран рекордов
    screen.fill((10, 10, 30))
    
    # Разбиваем текст на строки и отображаем каждую
    lines = highscores_text.split('\n')
    y_offset = 50
    
    for line in lines:
        if line.strip():  # Пропускаем пустые строки
            color = (255, 255, 255) if line.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'ТОП')) else (200, 200, 200)
            surf = font.render(line, True, color)
            screen.blit(surf, (50, y_offset))
            y_offset += 25
    
    # Подсказка для возврата
    hint = font.render("Нажмите ESC для возврата к игре", True, (150, 150, 150))
    hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
    screen.blit(hint, hint_rect)
    
    pygame.display.flip()
    
    # Ждем нажатия ESC
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                waiting = False


def show_game_results(screen: pygame.Surface, font: pygame.font.Font, big_font: pygame.font.Font, 
                     score: int, player_name: str, game_time_seconds: int, highscore_manager: HighScoreManager) -> None:
    """Отображает экран с результатами игры и таблицей рекордов"""
    game_time_formatted = f"{game_time_seconds // 60}:{game_time_seconds % 60:02d}"
    
    # Добавляем результат в рекорды
    highscore_manager.add_score(player_name, score, game_time_seconds)
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    waiting = False
                elif event.key == pygame.K_h or event.key == pygame.K_H:
                    # Показываем таблицу рекордов
                    show_highscores(screen, font, highscore_manager)
        
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
        
        # Подсказки
        hint1 = font.render("Нажмите Enter для новой игры", True, (200, 200, 200))
        hint2 = font.render("Нажмите H для просмотра рекордов", True, (200, 200, 200))
        
        screen.blit(hint1, (SCREEN_WIDTH // 2 - 150, 400))
        screen.blit(hint2, (SCREEN_WIDTH // 2 - 150, 430))
        
        pygame.display.flip()


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
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))


@dataclass
class Ball:
    rect: pygame.Rect = field(
        default_factory=lambda: pygame.Rect(
            (SCREEN_WIDTH - BALL_SIZE) // 2,
            SCREEN_HEIGHT // 2,
            BALL_SIZE,
            BALL_SIZE,
        )
    )
    vel_x: int = field(default_factory=lambda: random.choice([-BALL_SPEED, BALL_SPEED]))
    vel_y: int = -BALL_SPEED

    def update(self) -> None:
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self.vel_x *= -1
        if self.rect.top <= 0:
            self.vel_y *= -1

    def bounce_vertical(self) -> None:
        self.vel_y *= -1

    def reset(self, paddle_rect: pygame.Rect) -> None:
        self.rect.center = paddle_rect.midtop
        self.rect.y -= BALL_SIZE
        self.vel_x = random.choice([-BALL_SPEED, BALL_SPEED])
        self.vel_y = -BALL_SPEED


def build_bricks() -> List[pygame.Rect]:
    bricks = []
    start_x = (SCREEN_WIDTH - (BRICK_COLS * BRICK_WIDTH + (BRICK_COLS - 1) * BRICK_PADDING)) // 2
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


def draw_hud(screen: pygame.Surface, score: int, hits: int, lives_left: int, font: pygame.font.Font) -> None:
    text = f"Очки: {score} | Отбито: {hits} | Жизни: {lives_left}"
    surf = font.render(text, True, (255, 255, 255))
    screen.blit(surf, (SCREEN_WIDTH - surf.get_width() - 20, 20))


def show_message(screen: pygame.Surface, font: pygame.font.Font, message: str) -> None:
    surf = font.render(message, True, (255, 255, 255))
    rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(surf, rect)


def draw_start_hint(screen: pygame.Surface, font: pygame.font.Font) -> None:
    text = "Для начала игры нажми ← или →"
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(surf, rect)


def main() -> None:
    pygame.init()
    pygame.mixer.init()  # Инициализация аудио микшера
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Арканоид")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)
    big_font = pygame.font.SysFont("arial", 42, bold=True)
    
    # Инициализация менеджера рекордов
    highscore_manager = HighScoreManager()
    
    # Загрузка звуковых эффектов
    try:
        paddle_bounce_sound = pygame.mixer.Sound("sounds/bounce.wav")
        brick_hit_sounds = [
            pygame.mixer.Sound("sounds/Jump1.wav"),
            pygame.mixer.Sound("sounds/Jump2.wav"),
            pygame.mixer.Sound("sounds/Jump3.wav"),
        ]
        # Пытаемся загрузить фоновую музыку
        try:
            pygame.mixer.music.load("sounds/S31-Night Prowler.ogg")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)  # Цикличное воспроизведение фоновой музыки
        except pygame.error:
            print("Фоновая музыка не загружена")
    except pygame.error as e:
        print(f"Звуковые эффекты не загружены: {e}")
        paddle_bounce_sound = None
        brick_hit_sounds = None

    paddle = Paddle()
    ball = Ball()
    ball.reset(paddle.rect)
    ball.vel_y = 0
    bricks = build_bricks()

    score = 0
    hits = 0
    lives_left = MAX_LIVES
    game_over = False
    game_started = False
    ball_trail = []  # Список для хранения позиций мяча для шлейфа
    running = True
    
    # Ввод имени игрока
    player_name = get_player_name(screen, font, big_font)
    
    # Отсчет времени игры
    game_start_time = time.time()
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Показываем таблицу рекордов
                show_highscores(screen, font, highscore_manager)

        keys = pygame.key.get_pressed()

        if not game_started:
            ball.rect.center = paddle.rect.midtop
            ball.rect.y -= BALL_SIZE
            if keys[pygame.K_LEFT]:
                game_started = True
                ball.vel_x = -BALL_SPEED
                ball.vel_y = -BALL_SPEED
            elif keys[pygame.K_RIGHT]:
                game_started = True
                ball.vel_x = BALL_SPEED
                ball.vel_y = -BALL_SPEED

        # Обработка перезапуска после окончания игры
        if game_over and keys[pygame.K_r]:
            paddle = Paddle()
            ball = Ball()
            ball.reset(paddle.rect)
            ball.vel_y = 0
            bricks = build_bricks()
            score = 0
            hits = 0
            lives_left = MAX_LIVES
            game_over = False
            game_started = False
            ball_trail = []
            # Сброс времени игры для новой игры
            game_start_time = time.time()

        if not game_over:
            if keys[pygame.K_LEFT]:
                paddle.move(-1)
            if keys[pygame.K_RIGHT]:
                paddle.move(1)

            if game_started:
                ball.update()
                ball_trail.append(ball.rect.center)
                if len(ball_trail) > 20:  # Увеличил длину шлейфа до 20 позиций
                    ball_trail.pop(0)

                if ball.rect.colliderect(paddle.rect) and ball.vel_y > 0:
                    ball.bounce_vertical()
                    offset = (ball.rect.centerx - paddle.rect.centerx) / (paddle.rect.width / 2)
                    ball.vel_x = int(max(-BALL_SPEED, min(BALL_SPEED, BALL_SPEED * offset)))
                    hits += 1
                    # Play paddle bounce sound
                    if paddle_bounce_sound:
                        paddle_bounce_sound.play()

                hit_index = ball.rect.collidelist(bricks)
                if hit_index != -1:
                    ball.bounce_vertical()
                    bricks.pop(hit_index)
                    score += 1
                    # Play random brick hit sound
                    if brick_hit_sounds:
                        brick_hit_sounds[random.randint(0, len(brick_hit_sounds) - 1)].play()

                if ball.rect.bottom >= SCREEN_HEIGHT:
                    lives_left -= 1
                    if lives_left <= 0:
                        game_over = True
                        # Рассчитываем время игры и сохраняем результат
                        game_time_seconds = int(time.time() - game_start_time)
                        show_game_results(screen, font, big_font, score, player_name, game_time_seconds, highscore_manager)
                    else:
                        ball.reset(paddle.rect)
                        ball.vel_y = 0
                        game_started = False

                if not bricks:
                    game_over = True
                    # Рассчитываем время игры и сохраняем результат
                    game_time_seconds = int(time.time() - game_start_time)
                    show_game_results(screen, font, big_font, score, player_name, game_time_seconds, highscore_manager)

        screen.fill((10, 10, 30))
        draw_bricks(screen, bricks)
        # Отрисовка платформы с цветными секциями для подсказки направления отскока
        left_rect = pygame.Rect(paddle.rect.x, paddle.rect.y, paddle.rect.width // 3, paddle.rect.height)
        pygame.draw.rect(screen, (255, 0, 0), left_rect)  # Красный для отскока влево
        mid_rect = pygame.Rect(paddle.rect.x + paddle.rect.width // 3, paddle.rect.y, paddle.rect.width // 3, paddle.rect.height)
        pygame.draw.rect(screen, (240, 240, 240), mid_rect)  # Белый для прямого отскока
        right_rect = pygame.Rect(paddle.rect.x + 2 * paddle.rect.width // 3, paddle.rect.y, paddle.rect.width - 2 * paddle.rect.width // 3, paddle.rect.height)
        pygame.draw.rect(screen, (0, 0, 255), right_rect)  # Синий для отскока вправо
        # Отрисовка шлейфа мяча только когда игра начата
        if game_started:
            for i in range(len(ball_trail) - 1, -1, -1):
                pos = ball_trail[i]
                radius = BALL_SIZE // 2 * (i + 1) // len(ball_trail)
                if radius > 0:
                    fade = (len(ball_trail) - 1 - i) * 20
                    color = (max(0, 230 - fade), max(0, 90 - fade // 2), max(0, 90 - fade // 2))
                    pygame.draw.circle(screen, color, pos, radius)
        pygame.draw.ellipse(screen, (230, 90, 90), ball.rect)
        draw_hud(screen, score, hits, lives_left, font)

        if not game_started:
            draw_start_hint(screen, big_font)

        # Экран окончания игры теперь обрабатывается в show_game_results()
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()








