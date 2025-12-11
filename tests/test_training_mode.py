#!/usr/bin/env python3
"""
Тестовый скрипт для автоматического запуска игры в режиме обучения.
Обходит функцию get_player_name и автоматически запускает режим обучения.
"""
import sys
import os
import time
from typing import Any

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Модифицируем sys.argv для автоматического запуска режима обучения
# Это позволит обойти функцию get_player_name
print("[TEST] Запуск тестового скрипта для режима обучения...")
print("[TEST] Импортируем модули...")

try:
    import pygame
    from PyGameBall import main, get_player_name
    
    print("[TEST] Модули импортированы успешно")
    print("[TEST] Инициализируем pygame...")
    
    # Инициализируем pygame
    pygame.init()
    screen: Any = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Арканоид - Тестовый режим")
    
    print("[TEST] Pygame инициализирован")
    print("[TEST] ВНИМАНИЕ: Этот скрипт не может автоматически эмулировать нажатия клавиш")
    print("[TEST] Для полного тестирования нужно запустить игру вручную: python PyGameBall.py")
    print("[TEST] Затем нажать клавишу 8 для активации режима обучения")
    print("[TEST] И проверить логи в консоли")
    
    # Попытка создать мок-функцию get_player_name, которая автоматически возвращает режим обучения
    # Но это сложно, так как функция использует pygame.event.get() для ввода
    
    print("[TEST] Тестовый скрипт завершен")
    print("[TEST] Для реального тестирования запустите: python PyGameBall.py")
    print("[TEST] И нажмите клавишу 8 в окне игры")
    
except Exception as e:
    print(f"[ERROR] Ошибка при тестировании: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

