# Arkanoid game
# Version tracking
VERSION = "1.2.0"

import random
import math
from dataclasses import dataclass, field
from typing import List

import pygame

# Game tuning constants
# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

PADDLE_WIDTH = 120
PADDLE_HEIGHT = 15
PADDLE_SPEED = 9

BALL_SIZE = 16
BALL_SPEED = 5

BRICK_ROWS = 5
BRICK_COLS = 10
BRICK_WIDTH = 60
BRICK_HEIGHT = 20
BRICK_PADDING = 10
BRICK_OFFSET_TOP = 60

MAX_LIVES = 3


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
        """direction = -1 (left) / 1 (right)."""
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
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Арканоид")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)
    big_font = pygame.font.SysFont("arial", 42, bold=True)

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
    ball_trail = []  # List to store ball positions for trail
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

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

        # Handle restart after game over
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

        if not game_over:
            if keys[pygame.K_LEFT]:
                paddle.move(-1)
            if keys[pygame.K_RIGHT]:
                paddle.move(1)

            if game_started:
                ball.update()
                ball_trail.append(ball.rect.center)
                if len(ball_trail) > 10:
                    ball_trail.pop(0)

                if ball.rect.colliderect(paddle.rect) and ball.vel_y > 0:
                    ball.bounce_vertical()
                    offset = (ball.rect.centerx - paddle.rect.centerx) / (paddle.rect.width / 2)
                    ball.vel_x = int(max(-BALL_SPEED, min(BALL_SPEED, BALL_SPEED * offset)))
                    hits += 1

                hit_index = ball.rect.collidelist(bricks)
                if hit_index != -1:
                    ball.bounce_vertical()
                    bricks.pop(hit_index)
                    score += 1

                if ball.rect.bottom >= SCREEN_HEIGHT:
                    lives_left -= 1
                    if lives_left <= 0:
                        game_over = True
                    else:
                        ball.reset(paddle.rect)
                        ball.vel_y = 0
                        game_started = False

                if not bricks:
                    game_over = True

        screen.fill((10, 10, 30))
        draw_bricks(screen, bricks)
        # Draw paddle with colored sections for bounce direction hint
        left_rect = pygame.Rect(paddle.rect.x, paddle.rect.y, paddle.rect.width // 3, paddle.rect.height)
        pygame.draw.rect(screen, (255, 0, 0), left_rect)  # Red for left bounce
        mid_rect = pygame.Rect(paddle.rect.x + paddle.rect.width // 3, paddle.rect.y, paddle.rect.width // 3, paddle.rect.height)
        pygame.draw.rect(screen, (240, 240, 240), mid_rect)  # White for straight
        right_rect = pygame.Rect(paddle.rect.x + 2 * paddle.rect.width // 3, paddle.rect.y, paddle.rect.width - 2 * paddle.rect.width // 3, paddle.rect.height)
        pygame.draw.rect(screen, (0, 0, 255), right_rect)  # Blue for right bounce
        # Draw ball trail only when game is started
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

        if game_over:
            message = "Игра окончена" if lives_left <= 0 else "Победа! Все кубики сбиты"
            show_message(screen, big_font, message)
            # Draw restart hint
            restart_text = "Press R to restart"
            restart_surf = font.render(restart_text, True, (255, 255, 255))
            restart_rect = restart_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            screen.blit(restart_surf, restart_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()









    main()














    main()






