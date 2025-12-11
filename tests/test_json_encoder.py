#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы кастомного JSON encoder
"""

import sys
import os
from typing import List, Dict, Any, Callable

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.performance_logger import CustomJSONEncoder
from ai.game_state import Point
import pygame
import json


def test_point_serialization() -> bool:
    """Тестирует сериализацию Point объектов"""
    print("Testing Point serialization...")

    point: Point = Point(100, 150)
    point_data: Dict[str, Any] = {"position": point, "type": "test_point"}

    try:
        json_str: str = json.dumps(
            point_data, cls=CustomJSONEncoder, ensure_ascii=False, indent=2
        )
        print("[OK] Point serialization successful:")
        print(json_str)

        # Проверяем десериализацию
        parsed: Dict[str, Any] = json.loads(json_str)
        print("[OK] Point deserialization successful:")
        print(parsed)
        return True
    except Exception as e:
        print(f"[FAIL] Point serialization failed: {e}")
        return False


def test_rect_serialization() -> bool:
    """Тестирует сериализацию pygame.Rect объектов"""
    print("\nTesting pygame.Rect serialization...")

    rect: pygame.Rect = pygame.Rect(50, 75, 120, 25)
    rect_data: Dict[str, Any] = {"brick": rect, "type": "test_rect"}

    try:
        json_str: str = json.dumps(
            rect_data, cls=CustomJSONEncoder, ensure_ascii=False, indent=2
        )
        print("[OK] Rect serialization successful:")
        print(json_str)

        # Проверяем десериализацию
        parsed: Dict[str, Any] = json.loads(json_str)
        print("[OK] Rect deserialization successful:")
        print(parsed)
        return True
    except Exception as e:
        print(f"[FAIL] Rect serialization failed: {e}")
        return False


def test_mixed_data() -> bool:
    """Тестирует сериализацию смешанных данных"""
    print("\nTesting mixed data serialization...")

    point: Point = Point(200, 300)
    rect: pygame.Rect = pygame.Rect(10, 20, 80, 15)

    mixed_data: Dict[str, Any] = {
        "ball_position": point,
        "brick": rect,
        "score": 1500,
        "moves": ["left", "right", "hit"],
        "metadata": {
            "timestamp": "2025-12-02T19:23:28",
            "session_id": "test_session_123",
        },
    }

    try:
        json_str: str = json.dumps(
            mixed_data, cls=CustomJSONEncoder, ensure_ascii=False, indent=2
        )
        print("[OK] Mixed data serialization successful:")
        print(json_str)

        # Проверяем десериализацию
        parsed: Dict[str, Any] = json.loads(json_str)
        print("[OK] Mixed data deserialization successful:")
        print(parsed)
        return True
    except Exception as e:
        print(f"[FAIL] Mixed data serialization failed: {e}")
        return False


def main() -> bool:
    """Основная функция тестирования"""
    print("=== JSON Encoder Test Suite ===\n")

    pygame.init()

    tests: List[Callable[[], bool]] = [
        test_point_serialization,
        test_rect_serialization,
        test_mixed_data,
    ]

    results: List[bool] = []
    for test in tests:
        results.append(test())

    print("\n=== Test Results ===")
    passed: int = sum(results)
    total: int = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("[SUCCESS] All tests passed! JSON encoder is working correctly.")
    else:
        print("[ERROR] Some tests failed. Please check the implementation.")

    pygame.quit()
    return passed == total


if __name__ == "__main__":
    main()
