#!/usr/bin/env python3
"""
Тест инициализации игры без запуска pygame
Проверяет, что все модули загружаются корректно
"""

import sys
import os
from typing import List, Tuple, Callable


def test_imports() -> bool:
    """Тест импорта всех модулей"""
    print("Testing imports...")

    # Добавляем родительскую директорию в путь
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from src.game.PyGameBall import Paddle, Ball, build_bricks

        print("PASS: Main game modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import main game modules: {e}")
        return False

    try:
        from src.ai.ai_player import AIPlayer
        from src.ai.learning_system import LearningSystem
        from src.ai.position_optimizer import PositionOptimizer
        from src.ai.trajectory_predictor import TrajectoryPredictor
        from src.ai.game_state import GameState

        print("✓ AI modules imported successfully")
    except Exception as e:
        print(f"✗ Failed to import AI modules: {e}")
        return False

    return True


def test_ai_initialization() -> bool:
    """Тест инициализации AI системы"""
    print("\nTesting AI initialization...")

    try:
        from src.ai.ai_player import AIPlayer

        # Создаем AIPlayer
        ai_player: AIPlayer = AIPlayer(800, 600, debug_mode=False)
        ai_player.activate()

        print(f"✓ AIPlayer created and activated: {ai_player.is_active}")

        # Создаем другие компоненты
        from src.ai.learning_system import LearningSystem
        from src.ai.position_optimizer import PositionOptimizer

        learning_system: LearningSystem = LearningSystem()
        position_optimizer: PositionOptimizer = PositionOptimizer(800, 600)

        print("✓ All AI components initialized successfully")

        return True

    except Exception as e:
        print(f"✗ Failed to initialize AI components: {e}")
        return False


def test_game_objects() -> bool:
    """Тест создания игровых объектов"""
    print("\nTesting game object creation...")

    try:
        # Импортируем pygame для создания Rect объектов
        import pygame

        pygame.init()

        from src.game.PyGameBall import Paddle, Ball, build_bricks

        # Создаем объекты
        paddle: Paddle = Paddle()
        ball: Ball = Ball()
        bricks: List[object] = build_bricks()

        print(f"✓ Paddle created at position: {paddle.rect.center}")
        print(f"✓ Ball created at position: {ball.rect.center}")
        print(f"✓ Bricks created: {len(bricks)} bricks")

        pygame.quit()
        return True

    except Exception as e:
        print(f"✗ Failed to create game objects: {e}")
        return False


def main() -> bool:
    """Запуск всех тестов"""
    print("=== Testing Game Initialization (No Pygame Display) ===\n")

    tests: List[Tuple[str, Callable[[], bool]]] = [
        ("Import Test", test_imports),
        ("AI Initialization Test", test_ai_initialization),
        ("Game Objects Test", test_game_objects),
    ]

    passed: int = 0
    total: int = len(tests)

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
