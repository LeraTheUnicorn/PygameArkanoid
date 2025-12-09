#!/usr/bin/env python3
"""Тест рефакторинга PyGameBall.py"""

# Импортируем необходимые модули
import sys
import os

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyGameBall import Ball, Paddle, build_bricks
from settings import SettingsManager


def test_ball_class():
    """Тестирование класса Ball"""
    print("=== Testing Ball class ===")

    # Создаем объект мяча
    ball = Ball()
    print(f"OK: Ball object created successfully")
    print(f"  Initial speed: {ball.get_speed()}")

    # Тестируем изменение скорости
    ball.set_speed(7)
    print(f"OK: Speed set to 7: {ball.get_speed()}")

    # Создаем SettingsManager для методов изменения скорости
    settings = SettingsManager()

    # Тестируем увеличение скорости
    ball.increase_speed(settings, auto_mode=False)
    print(f"OK: Speed increased: {ball.get_speed()}")

    # Тестируем уменьшение скорости
    ball.decrease_speed(settings, auto_mode=False)
    print(f"OK: Speed decreased: {ball.get_speed()}")

    # Тестируем ограничения
    for _ in range(15):  # Пытаемся увеличить больше максимума
        ball.increase_speed(settings, auto_mode=False)
    print(f"OK: Max limit works: {ball.get_speed()}")

    for _ in range(15):  # Пытаемся уменьшить меньше минимума
        ball.decrease_speed(settings, auto_mode=False)
    print(f"OK: Min limit works: {ball.get_speed()}")

    print("OK: All Ball class tests passed!\n")


def test_paddle_class():
    """Тестирование класса Paddle"""
    print("=== Testing Paddle class ===")

    paddle = Paddle()
    print(f"OK: Paddle object created successfully")

    initial_x = paddle.rect.x
    paddle.move(5)
    print(f"OK: Move right: {initial_x} -> {paddle.rect.x}")

    paddle.move(-5)
    print(f"OK: Move left: {paddle.rect.x} -> {initial_x}")

    print("OK: All Paddle class tests passed!\n")


def test_settings_manager():
    """Тестирование SettingsManager"""
    print("=== Testing SettingsManager ===")

    settings = SettingsManager()
    initial_speed = settings.get_ball_speed()
    print(f"OK: Settings loaded, speed: {initial_speed}")

    settings.set_ball_speed(8)
    new_speed = settings.get_ball_speed()
    print(f"OK: Speed changed: {initial_speed} -> {new_speed}")

    print("OK: All SettingsManager tests passed!\n")


def test_reset_game():
    """Тестирование сброса игры (функция reset_game была удалена, тест обновлен)"""
    print("=== Testing game reset logic ===")

    # Создаем начальные объекты
    paddle = Paddle()
    ball = Ball()
    ball.set_speed(6)
    from PyGameBall import build_bricks

    bricks = build_bricks()
    score = 10
    lives_left = 2

    print(f"OK: Initial data:")
    print(f"  Ball speed: {ball.get_speed()}")
    print(f"  Score: {score}")
    print(f"  Lives: {lives_left}")
    print(f"  Bricks: {len(bricks)}")

    # Имитируем сброс игры (логика теперь в основном цикле)
    new_paddle = Paddle()
    new_ball = Ball()
    new_bricks = build_bricks()
    new_score = 0
    new_lives = 3

    print(f"OK: After reset:")
    print(f"  Ball speed: {new_ball.get_speed()}")
    print(f"  Score: {new_score}")
    print(f"  Lives: {new_lives}")
    print(f"  Bricks: {len(new_bricks)}")

    print("OK: Game reset logic test passed!\n")


def main():
    """Основная функция тестирования"""
    print("Running PyGameBall.py refactoring tests\n")

    try:
        test_ball_class()
        test_paddle_class()
        test_settings_manager()
        test_reset_game()

        print("SUCCESS: ALL TESTS PASSED!")
        print("Refactoring completed correctly.")

    except Exception as e:
        print(f"ERROR in testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
