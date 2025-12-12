#!/usr/bin/env python3
"""
Тест точности ИИ в предсказании траектории и позиционировании платформы
"""

import sys
import os
import pygame
import time
from typing import List, Tuple, Callable

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game.PyGameBall import (
    Paddle,
    Ball,
    build_bricks,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PADDLE_SPEED,
)
from src.ai.ai_player import AIPlayer
from src.ai.game_state import GameState, Point


def test_trajectory_prediction_accuracy() -> bool:
    """Тест точности предсказания траектории"""
    print("=== Trajectory Prediction Accuracy Test ===")

    pygame.init()

    # Создаем AI систему
    ai_player: AIPlayer = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    # Создаем объекты игры
    paddle: Paddle = Paddle()
    ball: Ball = Ball()
    bricks: List[object] = []

    # Тест 1: Мяч падает прямо вниз
    print("\nTest 1: Ball falling straight down")
    ball.rect.centerx = 400
    ball.rect.centery = 200
    ball.vel_x = 0
    ball.vel_y = 5

    # Обновляем состояние игры
    ai_player.update_game_state(ball, paddle, bricks, 0, int(time.time()))

    # Предсказываем точку приземления
    predicted_x: float = ai_player._predict_exact_landing_position()
    expected_x: int = 400  # Должно остаться в центре

    print(f"  Ball position: {ball.rect.centerx}, {ball.rect.centery}")
    print(f"  Ball velocity: {ball.vel_x}, {ball.vel_y}")
    print(f"  Predicted landing X: {predicted_x}")
    print(f"  Expected X: {expected_x}")
    print(f"  Difference: {abs(predicted_x - expected_x)}")

    if abs(predicted_x - expected_x) <= 10:
        print("  PASS: Trajectory prediction accurate")
        test1_pass: bool = True
    else:
        print("  FAIL: Trajectory prediction inaccurate")
        test1_pass = False

    # Тест 2: Мяч движется под углом
    print("\nTest 2: Ball moving at angle")
    ball.rect.centerx = 200
    ball.rect.centery = 100
    ball.vel_x = 3  # Движется вправо
    ball.vel_y = 4  # Движется вниз

    # Обновляем состояние
    ai_player.update_game_state(ball, paddle, bricks, 0, int(time.time()))

    # Рассчитываем ожидаемую позицию вручную
    paddle_y: int = paddle.rect.centery
    ball_y: int = ball.rect.centery
    ball_x: int = ball.rect.centerx
    vel_x: int = ball.vel_x
    vel_y: int = ball.vel_y

    time_to_paddle: float = (paddle_y - ball_y) / vel_y
    expected_x: float = ball_x + vel_x * time_to_paddle

    # Учитываем отскок от стен
    screen_width: int = SCREEN_WIDTH
    ball_radius: int = 8

    # Моделируем отскоки
    while expected_x < ball_radius or expected_x > screen_width - ball_radius:
        if expected_x < ball_radius:
            expected_x = 2 * ball_radius - expected_x
        elif expected_x > screen_width - ball_radius:
            expected_x = 2 * (screen_width - ball_radius) - expected_x

    # Предсказываем с AI
    predicted_x = ai_player._predict_exact_landing_position()

    print(f"  Ball position: {ball.rect.centerx}, {ball.rect.centery}")
    print(f"  Ball velocity: {ball.vel_x}, {ball.vel_y}")
    print(f"  Time to paddle: {time_to_paddle}")
    print(f"  Predicted landing X: {predicted_x}")
    print(f"  Expected X: {expected_x}")
    print(f"  Difference: {abs(predicted_x - expected_x)}")

    if abs(predicted_x - expected_x) <= 15:  # Допуск 15 пикселей
        print("  PASS: Trajectory prediction accurate")
        test2_pass: bool = True
    else:
        print("  FAIL: Trajectory prediction inaccurate")
        test2_pass = False

    pygame.quit()
    return test1_pass and test2_pass


def test_paddle_positioning_accuracy() -> bool:
    """Тест точности позиционирования платформы"""
    print("\n=== Paddle Positioning Accuracy Test ===")

    pygame.init()

    # Создаем AI систему
    ai_player: AIPlayer = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    # Создаем объекты
    paddle: Paddle = Paddle()
    ball: Ball = Ball()
    bricks: List[object] = []

    # Тест: Слежение за движущимся мячом
    print("\nTest: Paddle tracking moving ball")

    # Размещаем мяч слева от платформы
    ball.rect.centerx = 150
    ball.rect.centery = 300
    ball.vel_x = 2  # Движется вправо
    ball.vel_y = 0

    # Начальная позиция платформы (центр экрана)
    paddle.rect.centerx = 400

    # Обновляем состояние
    ai_player.update_game_state(ball, paddle, bricks, 0, int(time.time()))

    # Получаем целевую позицию от AI
    target_x: int = ai_player.get_optimal_paddle_position()

    print(f"  Ball position: {ball.rect.centerx}, {ball.rect.centery}")
    print(f"  Ball velocity: {ball.vel_x}, {ball.vel_y}")
    print(f"  Paddle initial position: {paddle.rect.centerx}")
    print(f"  AI target position: {target_x}")

    # AI должен предсказать движение мяча и переместиться к нему
    # Поскольку мяч движется вправо с скоростью 2, AI должен предсказать это
    if target_x > 150:  # Должен двигаться вправо от текущей позиции мяча
        print("  PASS: AI correctly predicts ball movement")
        test_pass: bool = True
    else:
        print("  FAIL: AI fails to predict ball movement")
        test_pass = False

    # Тестируем движение
    movement: int = ai_player.move_paddle_towards(paddle.rect.centerx, PADDLE_SPEED)
    paddle.move(movement)

    print(f"  Movement direction: {movement}")
    print(f"  Paddle final position: {paddle.rect.centerx}")

    if movement != 0:
        print("  PASS: Paddle moves in response to AI")
    else:
        print("  FAIL: Paddle does not move")
        test_pass = False

    pygame.quit()
    return test_pass


def test_edge_case_handling() -> bool:
    """Тест обработки граничных случаев"""
    print("\n=== Edge Case Handling Test ===")

    pygame.init()

    # Создаем AI систему
    ai_player: AIPlayer = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    # Создаем объекты
    paddle: Paddle = Paddle()
    ball: Ball = Ball()
    bricks: List[object] = []

    # Тест: Мяч очень близко к краю
    print("\nTest: Ball near screen edge")

    ball.rect.centerx = 50  # Очень близко к левому краю
    ball.rect.centery = 100
    ball.vel_x = 5  # Быстро движется вправо
    ball.vel_y = 3  # Движется вниз

    ai_player.update_game_state(ball, paddle, bricks, 0, int(time.time()))

    predicted_x: float = ai_player._predict_exact_landing_position()

    print(f"  Ball position: {ball.rect.centerx}, {ball.rect.centery}")
    print(f"  Ball velocity: {ball.vel_x}, {ball.vel_y}")
    print(f"  Predicted landing X: {predicted_x}")

    # Проверяем, что предсказанная позиция в пределах экрана
    screen_width: int = SCREEN_WIDTH
    ball_radius: int = 8
    min_x: int = ball_radius
    max_x: int = screen_width - ball_radius

    if min_x <= predicted_x <= max_x:
        print("  PASS: Prediction within screen bounds")
        test_pass: bool = True
    else:
        print("  FAIL: Prediction outside screen bounds")
        test_pass = False

    pygame.quit()
    return test_pass


def main() -> bool:
    """Запуск всех тестов точности"""
    print("=== AI Accuracy and Precision Tests ===")

    tests: List[Tuple[str, Callable[[], bool]]] = [
        ("Trajectory Prediction", test_trajectory_prediction_accuracy),
        ("Paddle Positioning", test_paddle_positioning_accuracy),
        ("Edge Cases", test_edge_case_handling),
    ]

    passed: int = 0
    total: int = len(tests)

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"  FAIL: Test failed with exception: {e}")

    print(f"\n=== Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("SUCCESS: All accuracy tests passed!")
        print(
            "AI should now provide better paddle positioning and trajectory prediction"
        )
        return True
    else:
        print("WARNING: Some accuracy tests failed")
        print("AI performance may still need improvement")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
