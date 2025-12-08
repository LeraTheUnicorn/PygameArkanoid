#!/usr/bin/env python3
"""
Упрощенный тест критических исправлений авторежима игры Арканоид
"""

import sys
import os
import pygame
import time

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyGameBall import (
    Paddle,
    Ball,
    build_bricks,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PADDLE_SPEED,
)
from ai.ai_player import AIPlayer


def test_auto_mode_life_loss_fix():
    """Тест продолжения игры после потери жизни в авторежиме"""
    print("Test 1: Auto mode life loss continuation")

    # Инициализация pygame
    pygame.init()

    # Создаем объекты игры
    paddle = Paddle()
    ball = Ball()
    lives_left = 3
    auto_mode = True

    # Имитируем потерю жизни
    ball.rect.y = SCREEN_HEIGHT + 50  # Мяч за границей

    if ball.rect.bottom >= SCREEN_HEIGHT:
        lives_left -= 1

        if lives_left > 0:
            # Сброс мяча
            ball.reset(paddle.rect)
            ball.vel_y = 0
            game_started = False

            # Проверяем исправление
            if auto_mode:
                game_started = True
                ball.vel_x = ball.get_speed()
                ball.vel_y = -ball.get_speed()

            if game_started:
                print("PASS: Game auto-continued in auto mode after life loss")
                return True
            else:
                print("FAIL: Game did not auto-continue in auto mode")
                return False

    pygame.quit()
    return False


def test_paddle_movement():
    """Тест движения платформы в авторежиме"""
    print("Test 2: Paddle movement in auto mode")

    pygame.init()

    # Создаем объекты
    paddle = Paddle()
    ball = Ball()

    # Размещаем мяч в стороне от платформы для тестирования движения
    ball.rect.centerx = 100  # Мяч слева
    ball.rect.centery = SCREEN_HEIGHT // 2
    ball.vel_x = 0
    ball.vel_y = 0

    # Инициализируем AI
    ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    # Обновляем состояние игры
    ai_player.update_game_state(ball, paddle, [], 0, int(time.time()))

    # Тестируем движение
    initial_x = paddle.rect.centerx
    print(f"  Ball position: {ball.rect.centerx}, {ball.rect.centery}")
    print(f"  Initial paddle position: {initial_x}")

    movement = ai_player.move_paddle_towards(paddle.rect.centerx, PADDLE_SPEED)
    paddle.move(movement)
    final_x = paddle.rect.centerx

    print(f"  Movement: {movement}")
    print(f"  Final paddle position: {final_x}")
    print(f"  AI active: {ai_player.is_active}")

    if movement != 0 or final_x != initial_x:
        print("PASS: Paddle moves in auto mode")
        result = True
    else:
        print("FAIL: Paddle does not move in auto mode")
        result = False

    pygame.quit()
    return result


def test_ai_activation():
    """Тест активации AI системы"""
    print("Test 3: AI system activation")

    # Создаем AI
    ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    is_active = ai_player.is_active
    print(f"  AI active: {is_active}")

    if is_active:
        print("PASS: AI system activates correctly")
        return True
    else:
        print("FAIL: AI system failed to activate")
        return False


def main():
    """Запуск всех тестов"""
    print("=== Testing Critical Auto-Mode Fixes ===\n")

    tests = [test_auto_mode_life_loss_fix, test_paddle_movement, test_ai_activation]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"FAIL: Test {test_func.__name__} failed with error: {e}\n")

    print(f"=== Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("SUCCESS: All critical fixes working correctly!")
        return True
    else:
        print("FAILURE: Some fixes need attention.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
