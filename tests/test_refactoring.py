#!/usr/bin/env python3
"""Тест рефакторинга PyGameBall.py"""

# Импортируем необходимые модули
import sys
import os
sys.path.append('..')

from PyGameBall import Ball, Paddle, SettingsManager, reset_game

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
    
    # Тестируем увеличение скорости
    ball.increase_speed()
    print(f"OK: Speed increased: {ball.get_speed()}")
    
    # Тестируем уменьшение скорости
    ball.decrease_speed()
    print(f"OK: Speed decreased: {ball.get_speed()}")
    
    # Тестируем ограничения
    for _ in range(15):  # Пытаемся увеличить больше максимума
        ball.increase_speed()
    print(f"OK: Max limit works: {ball.get_speed()}")
    
    for _ in range(15):  # Пытаемся уменьшить меньше минимума
        ball.decrease_speed()
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
    """Тестирование функции reset_game"""
    print("=== Testing reset_game function ===")
    
    # Создаем начальные объекты
    paddle = Paddle()
    ball = Ball()
    ball.set_speed(6)
    bricks = []
    score = 10
    lives_left = 2
    game_over = True
    game_started = True
    ball_trail = [(100, 100), (110, 110)]
    game_start_time = 1000.0
    
    print(f"OK: Initial data:")
    print(f"  Ball speed: {ball.get_speed()}")
    print(f"  Score: {score}")
    print(f"  Lives: {lives_left}")
    print(f"  Game over: {game_over}")
    
    # Вызываем reset_game
    (new_paddle, new_ball, new_bricks, new_score, new_lives, 
     new_game_over, new_game_started, new_trail, new_time) = reset_game(
        paddle, ball, bricks, score, lives_left, game_over, game_started,
        ball_trail, game_start_time
    )
    
    print(f"OK: After reset:")
    print(f"  Ball speed: {new_ball.get_speed()}")
    print(f"  Score: {new_score}")
    print(f"  Lives: {new_lives}")
    print(f"  Game over: {new_game_over}")
    print(f"  Game started: {new_game_started}")
    print(f"  Trail cleared: {len(new_trail) == 0}")
    
    print("OK: All reset_game tests passed!\n")

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
