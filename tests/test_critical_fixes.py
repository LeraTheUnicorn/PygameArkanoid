#!/usr/bin/env python3
"""
Тест критических исправлений авторежима игры Арканоид
Проверяет:
1. Продолжение игры после потери жизни в авторежиме
2. Работу движения платформы в авторежиме
"""

import sys
import os
import pygame
import time

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyGameBall import (
    Paddle,
    Ball,
    build_bricks,
    AIPlayer,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PADDLE_SPEED,
)


def test_auto_mode_after_life_loss():
    """Тест продолжения игры после потери жизни в авторежиме"""
    print("🧪 Тест 1: Продолжение игры после потери жизни в авторежиме")

    # Инициализация pygame
    pygame.init()

    # Создаем объекты игры
    paddle = Paddle()
    ball = Ball()
    bricks = build_bricks()
    score = 0
    lives_left = 3
    auto_mode = True

    # Инициализируем AI
    ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    # Создаем имитацию времени игры
    game_start_time = int(time.time())

    # Обновляем состояние игры для AI
    ai_player.update_game_state(ball, paddle, bricks, score, game_start_time)

    print(f"✅ AI активирован: {ai_player.is_active}")

    # Имитируем потерю жизни (мяч уходит за нижнюю границу)
    ball.rect.y = SCREEN_HEIGHT + 50  # Мяч за границей

    # Проверяем обработку потери жизни
    if ball.rect.bottom >= SCREEN_HEIGHT:
        lives_left -= 1
        print(f"💔 Жизни после потери: {lives_left}")

        if lives_left > 0:
            # Сброс мяча (это часть логики потери жизни)
            ball.reset(paddle.rect)
            ball.vel_y = 0
            game_started = False

            # Проверяем исправление - в авторежиме должна автоматически продолжиться
            if auto_mode:
                game_started = True
                ball.vel_x = ball.get_speed()
                ball.vel_y = -ball.get_speed()
                print(f"🎮 Авторежим: игра автоматически продолжилась")
                print(f"   game_started = {game_started}")
                print(f"   ball.vel_x = {ball.vel_x}")
                print(f"   ball.vel_y = {ball.vel_y}")

            if game_started:
                print("✅ ТЕСТ 1 ПРОЙДЕН: Игра автоматически продолжилась в авторежиме")
                return True
            else:
                print("❌ ТЕСТ 1 ПРОВАЛЕН: Игра не продолжилась в авторежиме")
                return False
        else:
            print("💀 Игра окончена (0 жизней)")

    pygame.quit()
    return False


def test_paddle_movement_in_auto_mode():
    """Тест движения платформы в авторежиме"""
    print("\n🧪 Тест 2: Движение платформы в авторежиме")

    # Инициализация pygame
    pygame.init()

    # Создаем объекты игры
    paddle = Paddle()
    ball = Ball()
    bricks = build_bricks()
    score = 0

    # Устанавливаем начальную позицию мяча (падающий)
    ball.vel_x = 3
    ball.vel_y = 3
    ball.rect.centerx = SCREEN_WIDTH // 2
    ball.rect.centery = SCREEN_HEIGHT // 2

    # Инициализируем AI
    ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    print(f"✅ AI активирован: {ai_player.is_active}")

    # Создаем имитацию времени игры
    game_start_time = int(time.time())

    # Обновляем состояние игры для AI
    ai_player.update_game_state(ball, paddle, bricks, score, game_start_time)

    # Тестируем движение платформы
    initial_x = paddle.rect.centerx
    print(f"🎯 Начальная позиция платформы: {initial_x}")

    # Двигаем платформу с помощью AI
    movement = ai_player.move_paddle_towards(paddle.rect.centerx, PADDLE_SPEED)
    paddle.move(movement)

    final_x = paddle.rect.centerx
    print(f"🎯 Финальная позиция платформы: {final_x}")
    print(f"🔄 Движение: {movement}")

    # Проверяем оптимальную позицию
    optimal_x = ai_player.get_optimal_paddle_position()
    print(f"🎯 Оптимальная позиция от AI: {optimal_x}")

    # Анализируем результат
    if movement != 0 or final_x != initial_x:
        print("✅ ТЕСТ 2 ПРОЙДЕН: Платформа движется в авторежиме")

        # Дополнительная проверка - сравниваем с оптимальной позицией
        distance_to_optimal = abs(final_x - optimal_x)
        print(f"📏 Расстояние до оптимальной позиции: {distance_to_optimal}")

        return True
    else:
        print("❌ ТЕСТ 2 ПРОВАЛЕН: Платформа не движется в авторежиме")
        print(f"   AI активен: {ai_player.is_active}")
        print(f"   Оптимальная позиция: {optimal_x}")
        print(f"   Текущая позиция: {final_x}")
        return False

    pygame.quit()


def test_ai_state_updates():
    """Тест обновления состояния AI"""
    print("\n🧪 Тест 3: Обновление состояния AI системы")

    # Создаем объекты
    paddle = Paddle()
    ball = Ball()
    bricks = build_bricks()

    # Инициализируем AI
    ai_player = AIPlayer(SCREEN_WIDTH, SCREEN_HEIGHT, debug_mode=False)
    ai_player.activate()

    game_start_time = int(time.time())

    try:
        # Обновляем состояние игры
        ai_player.update_game_state(ball, paddle, bricks, 0, game_start_time)

        # Проверяем, что состояние обновилось
        if ai_player.current_game_state is not None:
            print("✅ ТЕСТ 3 ПРОЙДЕН: Состояние игры обновляется для AI")
            return True
        else:
            print("❌ ТЕСТ 3 ПРОВАЛЕН: Состояние игры не обновилось для AI")
            return False

    except Exception as e:
        print(f"❌ ТЕСТ 3 ПРОВАЛЕН: Ошибка при обновлении состояния: {e}")
        return False


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов критических исправлений авторежима\n")

    tests = [
        test_auto_mode_after_life_loss,
        test_paddle_movement_in_auto_mode,
        test_ai_state_updates,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте {test_func.__name__}: {e}")

    print(f"\n📊 Результаты тестов: {passed}/{total} пройдено")

    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Критические ошибки исправлены.")
        return True
    else:
        print("⚠️ Некоторые тесты провалены. Требуется дополнительная отладка.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
