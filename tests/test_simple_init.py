#!/usr/bin/env python3
"""
Простой тест инициализации игры
"""


import sys
import os

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports() -> bool:
    print("Testing imports...")

    try:
        from src.game.PyGameBall import Paddle, Ball, build_bricks

        print("PASS: Main game modules imported")
    except Exception as e:
        print(f"FAIL: Main game modules: {e}")
        return False

    try:
        from src.ai.ai_player import AIPlayer
        from src.ai.learning_system import LearningSystem
        from src.ai.position_optimizer import PositionOptimizer
        from src.ai.trajectory_predictor import TrajectoryPredictor

        print("PASS: AI modules imported")
    except Exception as e:
        print(f"FAIL: AI modules: {e}")
        return False

    return True


def test_ai_init() -> bool:
    print("\nTesting AI initialization...")

    try:
        from src.ai.ai_player import AIPlayer

        ai_player: AIPlayer = AIPlayer(800, 600, debug_mode=False)
        ai_player.activate()
        print(f"PASS: AIPlayer created, active: {ai_player.is_active}")
        return True
    except Exception as e:
        print(f"FAIL: AI initialization: {e}")
        return False


def main() -> bool:
    print("=== Game Initialization Test ===")

    from typing import List, Callable
    tests: List[Callable[[], bool]] = [test_imports, test_ai_init]
    passed: int = sum(1 for test in tests if test())

    print(f"\nResults: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("SUCCESS: All initialization tests passed!")
        return True
    else:
        print("FAILURE: Some tests failed")
        return False


if __name__ == "__main__":
    import sys

    success: bool = main()
    sys.exit(0 if success else 1)
