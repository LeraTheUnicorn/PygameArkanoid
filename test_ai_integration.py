#!/usr/bin/env python3
"""
Тест интеграции AI системы с игрой Арканоид
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai'))

from ai.ai_player import AIPlayer
from ai.game_state import GameState, Point
import pygame
from dataclasses import dataclass

# Создаем мок объекты для тестирования
@dataclass
class MockPaddle:
    rect = pygame.Rect(400, 580, 120, 15)

@dataclass  
class MockBall:
    rect = pygame.Rect(400, 400, 16, 16)
    vel_x = 3
    vel_y = 3
    def get_speed(self):
        return 5

def create_test_bricks():
    """Создает тестовые кубики"""
    bricks = []
    for i in range(5):
        for j in range(10):
            x = 100 + j * 70
            y = 100 + i * 30
            bricks.append(pygame.Rect(x, y, 60, 20))
    return bricks

def test_ai_player_creation():
    """Тестирует создание AIPlayer"""
    print("Тест 1: Создание AIPlayer...")
    ai = AIPlayer(800, 600, debug_mode=True)
    assert ai is not None
    assert ai.is_active == False
    print("PASS: AIPlayer успешно создан")

def test_ai_activation():
    """Тестирует активацию AI"""
    print("\nТест 2: Активация AI...")
    ai = AIPlayer()
    ai.activate()
    assert ai.is_active == True
    print("PASS: AI успешно активирован")

def test_game_state_update():
    """Тестирует обновление состояния игры"""
    print("\nТест 3: Обновление состояния игры...")
    ai = AIPlayer()
    ai.activate()
    
    paddle = MockPaddle()
    ball = MockBall()
    bricks = create_test_bricks()
    
    # Обновляем состояние игры
    ai.update_game_state(ball, paddle, bricks, 0, 1600000000)
    
    assert ai.current_game_state is not None
    assert len(ai.current_game_state.remaining_bricks) == 50
    print("PASS: Состояние игры успешно обновлено")

def test_optimal_position_calculation():
    """Тестирует расчет оптимальной позиции"""
    print("\nТест 4: Расчет оптимальной позиции...")
    ai = AIPlayer()
    ai.activate()
    
    paddle = MockPaddle()
    ball = MockBall()
    bricks = create_test_bricks()
    
    ai.update_game_state(ball, paddle, bricks, 0, 1600000000)
    
    # Получаем оптимальную позицию
    optimal_x = ai.get_optimal_paddle_position()
    
    assert isinstance(optimal_x, int)
    assert 60 <= optimal_x <= 740  # В пределах экрана с учетом ширины платформы
    print(f"PASS: Оптимальная позиция: {optimal_x}")

def test_paddle_movement():
    """Тестирует движение платформы"""
    print("\nТест 5: Движение платформы...")
    ai = AIPlayer()
    ai.activate()
    
    paddle = MockPaddle()
    ball = MockBall()
    bricks = create_test_bricks()
    
    ai.update_game_state(ball, paddle, bricks, 0, 1600000000)
    
    # Тестируем движение платформы
    movement = ai.move_paddle_towards(paddle.rect.centerx, 9)
    
    assert movement in [-1, 0, 1]
    print(f"PASS: Движение платформы: {movement}")

def test_learning_system():
    """Тестирует систему обучения"""
    print("\nТест 6: Система обучения...")
    ai = AIPlayer()
    
    # Тестовый результат действия
    test_result = {
        "action_type": "paddle_bounce",
        "success": True,
        "confidence": 0.8,
        "movement_distance": 10,
        "ball_speed": 5,
        "remaining_bricks": 49
    }
    
    # Проверяем, что система обучения работает без ошибок
    try:
        ai.learn_from_result(test_result)
        print("PASS: Система обучения работает корректно")
    except Exception as e:
        print(f"FAIL: Ошибка в системе обучения: {e}")
        raise

def run_all_tests():
    """Запускает все тесты"""
    print("=== ЗАПУСК ТЕСТОВ AI СИСТЕМЫ АРКАНОИД ===\n")
    
    try:
        test_ai_player_creation()
        test_ai_activation()
        test_game_state_update()
        test_optimal_position_calculation()
        test_paddle_movement()
        test_learning_system()
        
        print("\n=== ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! ===")
        print("\nРЕЗЮМЕ:")
        print("- AIPlayer создан и работает")
        print("- Состояние игры корректно обновляется")
        print("- Оптимальная позиция рассчитывается")
        print("- Движение платформы функционирует")
        print("- Система обучения активна")
        print("\n=== ИНТЕГРАЦИЯ AI СИСТЕМЫ ЗАВЕРШЕНА УСПЕШНО! ===")
        
    except Exception as e:
        print(f"\n=== ОШИБКА В ТЕСТАХ: {e} ===")
        sys.exit(1)

if __name__ == "__main__":
    # Инициализируем pygame для тестов
    pygame.init()
    run_all_tests()
    pygame.quit()
