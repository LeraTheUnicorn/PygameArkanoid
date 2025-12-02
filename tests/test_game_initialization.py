#!/usr/bin/env python3
"""
Тест инициализации игры без запуска pygame
Проверяет, что все модули загружаются корректно
"""

import sys
import os


def test_imports():
    """Тест импорта всех модулей"""
    print("Testing imports...")

    try:
        from PyGameBall import Paddle, Ball, build_bricks, AIPlayer

        print("PASS: Main game modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import main game modules: {e}")
        return False

    try:
        from ai.ai_player import AIPlayer
        from ai.learning_system import LearningSystem
        from ai.position_optimizer import PositionOptimizer
        from ai.trajectory_predictor import TrajectoryPredictor
        from ai.game_state import GameState

        print("✓ AI modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import AI modules: {e}")
        return False

    return True


def test_ai_initialization():
    """Тест инициализации AI системы"""
    print("\nTesting AI initialization...")

    try:
        from ai.ai_player import AIPlayer

        # Создаем AIPlayer
        ai_player = AIPlayer(800, 600, debug_mode=False)
        ai_player.activate()

        print(f"✓ AIPlayer created and activated: {ai_player.is_active}")

        # Создаем другие компоненты
        from ai.learning_system import LearningSystem
        from ai.position_optimizer import PositionOptimizer

        learning_system = LearningSystem()
        position_optimizer = PositionOptimizer(800, 600)

        print("✓ All AI components initialized successfully")

        return True

    except Exception as e:
        print(f"✗ Failed to initialize AI components: {e}")
        return False


def test_game_objects():
    """Тест создания игровых объектов"""
    print("\nTesting game object creation...")

    try:
        # Импортируем pygame для создания Rect объектов
        import pygame

        pygame.init()

        from PyGameBall import Paddle, Ball, build_bricks

        # Создаем объекты
        paddle = Paddle()
        ball = Ball()
        bricks = build_bricks()

        print(f"✓ Paddle created at position: {paddle.rect.center}")
        print(f"✓ Ball created at position: {ball.rect.center}")
        print(f"✓ Bricks created: {len(bricks)} bricks")

        pygame.quit()
        return True

    except Exception as e:
        print(f"✗ Failed to create game objects: {e}")
        return False


def main():
    """Запуск всех тестов"""
    print("=== Testing Game Initialization (No Pygame Display) ===\n")

    tests = [
        ("Import Test", test_imports),
        ("AI Initialization Test", test_ai_initialization),
        ("Game Objects Test", test_game_objects),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
            else:
                print(f"  Test failed")
        except Exception as e:
            print(f"  Test failed with exception: {e}")

    print(f"\n=== Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("✓ All initialization tests passed!")
        print("✓ Game should launch without import/init errors")
        return True
    else:
        print("✗ Some initialization tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
