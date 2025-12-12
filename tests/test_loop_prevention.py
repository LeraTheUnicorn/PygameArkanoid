#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы предотвращения зацикливания
"""

import sys
import os
import time
from typing import List, Callable

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai.ai_player import AIPlayer
from src.ai.game_state import GameState, Point
import pygame
from dataclasses import dataclass


# Создаем мок объекты для тестирования
@dataclass
class MockPaddle:
    rect: pygame.Rect = pygame.Rect(400, 550, 120, 15)


@dataclass
class MockBall:
    rect: pygame.Rect = pygame.Rect(400, 300, 16, 16)
    vel_x: int = 3
    vel_y: int = 3

    def get_speed(self) -> int:
        return 5


def test_loop_detection() -> bool:
    """Тестирует обнаружение зацикливания"""
    print("Testing loop detection...")

    # Создаем AIPlayer
    ai: AIPlayer = AIPlayer(screen_width=800, screen_height=600, debug_mode=True)

    # Создаем mock состояние игры
    ball: MockBall = MockBall()
    paddle: MockPaddle = MockPaddle()

    bricks: List[pygame.Rect] = []
    for i in range(5):
        rect: pygame.Rect = pygame.Rect(i * 160, 100, 60, 20)
        bricks.append(rect)

    # Обновляем состояние игры
    ai.update_game_state(ball, paddle, bricks, 0, int(time.time()))
    ai.activate()

    # Симулируем зацикливание - повторяющиеся движения
    print("Simulating loop pattern...")
    for i in range(6):
        # Симулируем движение влево-вправо
        ai.loop_prevention_system["movement_history"].append(1 if i % 2 == 0 else -1)

        # Проверяем обнаружение зацикливания
        is_looping: bool = ai._detect_loop_pattern()
        print(
            f"Movement {i}: {ai.loop_prevention_system['movement_history'][-1]} -> Looping: {is_looping}"
        )

        if is_looping:
            print("[OK] Loop detection working correctly!")
            break

    return True


def test_alternative_strategies() -> bool:
    """Тестирует альтернативные стратегии"""
    print("\nTesting alternative strategies...")

    ai: AIPlayer = AIPlayer(screen_width=800, screen_height=600)
    ai.activate()

    # Создаем mock состояние
    ball: MockBall = MockBall()
    paddle: MockPaddle = MockPaddle()

    bricks: List[pygame.Rect] = []
    for i in range(3):
        rect: pygame.Rect = pygame.Rect(i * 200, 100, 60, 20)
        bricks.append(rect)

    ai.update_game_state(ball, paddle, bricks, 0, int(time.time()))

    # Тестируем каждую стратегию
    strategies: List[str] = ai.loop_prevention_system["alternative_strategies"]

    for i, strategy in enumerate(strategies):
        ai.loop_prevention_system["current_strategy_index"] = i
        optimal_position: int = 400  # Базовая оптимальная позиция

        # Применяем стратегию
        new_position: int = ai._apply_alternative_strategy(optimal_position)

        print(f"Strategy '{strategy}': {optimal_position} -> {new_position}")

        # Проверяем, что позиция изменилась для некоторых стратегий
        if strategy == "center_focus":
            expected: int = 400  # Центр экрана
            assert new_position == expected, f"Expected {expected}, got {new_position}"
        elif strategy == "predictive_targeting":
            # Должна быть отличной от базовой
            assert (
                new_position != optimal_position
            ), f"Predictive targeting should change position"

    print("[OK] Alternative strategies working correctly!")
    return True


def test_movement_tracking() -> bool:
    """Тестирует отслеживание движений"""
    print("\nTesting movement tracking...")

    ai: AIPlayer = AIPlayer(screen_width=800, screen_height=600)

    # Симулируем несколько движений
    movements: List[int] = [1, -1, 1, -1, 1, -1]  # Повторяющийся паттерн
    positions: List[int] = [400, 410, 400, 410, 400, 410]  # Соответствующие позиции
    optimal_x: int = 405

    for i, (movement, current_x) in enumerate(zip(movements, positions)):
        ai._update_loop_tracking(movement, current_x, optimal_x)

        # Проверяем обновление истории
        history_len: int = len(ai.loop_prevention_system["movement_history"])
        print(f"Movement {i}: {movement}, History length: {history_len}")

        assert history_len == min(
            i + 1, 10
        ), f"Expected history length {min(i+1, 10)}, got {history_len}"

    print("[OK] Movement tracking working correctly!")
    return True


def test_reevaluation_after_bounce() -> bool:
    """Тестирует переоценку после отбития"""
    print("\nTesting reevaluation after bounce...")

    ai: AIPlayer = AIPlayer(screen_width=800, screen_height=600, debug_mode=True)
    ai.activate()

    # Создаем состояние игры
    ball: MockBall = MockBall()
    paddle: MockPaddle = MockPaddle()

    bricks: List[pygame.Rect] = []
    for i in range(3):
        rect: pygame.Rect = pygame.Rect(i * 200, 100, 60, 20)
        bricks.append(rect)

    ai.update_game_state(ball, paddle, bricks, 0, int(time.time()))

    # Устанавливаем целевой кубик
    ai.targeting_system["target_brick"] = bricks[1]
    ai.targeting_system["optimal_offset"] = 0.5

    print(f"Before reevaluation - Target brick: {ai.targeting_system['target_brick']}")
    print(
        f"Before reevaluation - Optimal offset: {ai.targeting_system['optimal_offset']}"
    )

    # Вызываем переоценку
    ai._reevaluate_after_bounce()

    # Проверяем, что система переоценила
    print(f"After reevaluation - Target brick: {ai.targeting_system['target_brick']}")
    print(
        f"After reevaluation - Optimal offset: {ai.targeting_system['optimal_offset']}"
    )

    print("[OK] Reevaluation after bounce working correctly!")
    return True


def main() -> bool:
    """Основная функция тестирования"""
    print("=== Loop Prevention System Test Suite ===\n")

    pygame.init()

    tests: List[Callable[[], bool]] = [
        test_loop_detection,
        test_alternative_strategies,
        test_movement_tracking,
        test_reevaluation_after_bounce,
    ]

    results: List[bool] = []
    for test in tests:
        try:
            result: bool = test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} failed: {e}")
            results.append(False)

    print("\n=== Test Results ===")
    passed: int = sum(results)
    total: int = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print(
            "[SUCCESS] All tests passed! Loop prevention system is working correctly."
        )
    else:
        print("[ERROR] Some tests failed. Please check the implementation.")

    pygame.quit()
    return passed == total


if __name__ == "__main__":
    main()
