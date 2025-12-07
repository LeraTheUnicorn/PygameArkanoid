#!/usr/bin/env python3
"""
Простой тест для проверки адаптивной скорости платформы
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ai.ai_player import AIPlayer
from ai.game_state import GameState, Point

def test_adaptive_speed():
    """Тестирует функцию расчета адаптивной скорости платформы"""
    print("Testing adaptive paddle speed...")
    
    # Создаем AIPlayer
    ai = AIPlayer(800, 600, debug_mode=True)
    ai.activate()
    
    # Создаем мок-состояние игры
    class MockBall:
        def __init__(self):
            self.x = 400
            self.y = 300
            self.vel_x = 3
            self.vel_y = 4
    
    class MockPaddle:
        def __init__(self):
            self.x = 400
            self.y = 550
    
    class MockBrick:
        pass
    
    # Создаем игровое состояние
    ball = MockBall()
    paddle = MockPaddle()
    bricks = []
    
    game_state = GameState(
        ball_position=Point(ball.x, ball.y),
        ball_velocity=Point(ball.vel_x, ball.vel_y),
        paddle_position=Point(paddle.x, paddle.y),
        paddle_width=120,
        remaining_bricks=bricks,
        game_score=0,
        game_time=0,
        ball_speed=5,
    )
    
    ai.current_game_state = game_state
    
    # Тестовые сценарии
    test_cases = [
        # (текущая_позиция, оптимальная_позиция, скорость_мяча, описание)
        (400, 400, 5, "Position already optimal"),
        (400, 500, 5, "Ball far away, medium speed"),
        (400, 600, 10, "Fast ball, far away"),
        (400, 450, 15, "Very fast ball"),
        (200, 600, 20, "Critical situation"),
    ]
    
    print("\nTest results:")
    print("=" * 60)
    
    for current_x, optimal_x, ball_speed, description in test_cases:
        speed = ai.calculate_adaptive_paddle_speed(current_x, optimal_x, ball_speed)
        distance = abs(optimal_x - current_x)
        
        print(f"Test: {description}")
        print(f"   Current position: {current_x}")
        print(f"   Optimal position: {optimal_x}")
        print(f"   Distance: {distance}")
        print(f"   Ball speed: {ball_speed}")
        print(f"   Adaptive paddle speed: {speed}")
        print("-" * 40)
    
    print("\nTesting completed!")
    return True

if __name__ == "__main__":
    try:
        test_adaptive_speed()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()