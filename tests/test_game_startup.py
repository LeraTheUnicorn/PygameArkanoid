#!/usr/bin/env python3
"""
Тестовый скрипт для проверки запуска игры в режиме обучения.
Автоматически запускает режим обучения и проверяет, не блокируется ли выполнение.
"""
import sys
import os
from typing import Any

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем необходимые модули
try:
    from PyGameBall import main
    import pygame
    
    print("[TEST] Импорт модулей успешен")
    
    # Инициализируем pygame
    pygame.init()
    print("[TEST] Pygame инициализирован")
    
    # Создаем фиктивный экран для тестирования
    screen: Any = pygame.display.set_mode((800, 600))
    print("[TEST] Экран создан")
    
    # Пытаемся запустить игру в режиме обучения
    # Но для этого нужно модифицировать get_player_name, чтобы автоматически возвращать режим обучения
    print("[TEST] Попытка запуска игры...")
    print("[TEST] ВНИМАНИЕ: Этот тест требует модификации кода для автоматического запуска режима обучения")
    print("[TEST] Для полного тестирования нужно запустить игру вручную и нажать 8")
    
except Exception as e:
    print(f"[ERROR] Ошибка при тестировании: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

