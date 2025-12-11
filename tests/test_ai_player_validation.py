#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для валидации входных данных AIPlayer
"""

import sys
import os

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Tuple, Callable


def test_valid_dimensions() -> bool:
    """Тестирует успешную инициализацию с валидными размерами"""
    print("Testing valid dimensions...")
    
    try:
        from ai.ai_player import AIPlayer
        
        # Стандартные размеры
        ai1 = AIPlayer(800, 600, debug_mode=False)
        assert ai1.screen_width == 800
        assert ai1.screen_height == 600
        print("  PASS: Standard dimensions (800x600)")
        
        # Минимальные размеры
        ai2 = AIPlayer(400, 300, debug_mode=False)
        assert ai2.screen_width == 400
        assert ai2.screen_height == 300
        print("  PASS: Minimum dimensions (400x300)")
        
        # Большие размеры
        ai3 = AIPlayer(1920, 1080, debug_mode=True)
        assert ai3.screen_width == 1920
        assert ai3.screen_height == 1080
        assert ai3.debug_mode is True
        print("  PASS: Large dimensions (1920x1080)")
        
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_type_validation() -> bool:
    """Тестирует валидацию типов данных"""
    print("Testing type validation...")
    
    try:
        from ai.ai_player import AIPlayer
        
        test_cases: List[Tuple[any, any, str]] = [
            ("800", 600, "screen_width as string"),
            (800, "600", "screen_height as string"),
            (800.5, 600, "screen_width as float"),
            (800, 600.5, "screen_height as float"),
            (None, 600, "screen_width as None"),
            (800, None, "screen_height as None"),
            ([800], 600, "screen_width as list"),
            (800, [600], "screen_height as list"),
        ]
        
        for width, height, description in test_cases:
            try:
                AIPlayer(width, height, debug_mode=False)
                print(f"  FAIL: Should raise TypeError for {description}")
                return False
            except TypeError as e:
                print(f"  PASS: TypeError raised for {description}: {str(e)[:50]}")
            except Exception as e:
                print(f"  FAIL: Wrong exception type for {description}: {type(e).__name__}")
                return False
        
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_negative_values() -> bool:
    """Тестирует валидацию отрицательных значений"""
    print("Testing negative values...")
    
    try:
        from ai.ai_player import AIPlayer
        
        test_cases: List[Tuple[int, int, str]] = [
            (-1, 600, "negative screen_width"),
            (800, -1, "negative screen_height"),
            (-100, -200, "both negative"),
            (0, 600, "zero screen_width"),
            (800, 0, "zero screen_height"),
            (0, 0, "both zero"),
        ]
        
        for width, height, description in test_cases:
            try:
                AIPlayer(width, height, debug_mode=False)
                print(f"  FAIL: Should raise ValueError for {description}")
                return False
            except ValueError as e:
                print(f"  PASS: ValueError raised for {description}: {str(e)[:50]}")
            except Exception as e:
                print(f"  FAIL: Wrong exception type for {description}: {type(e).__name__}")
                return False
        
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_minimum_dimensions() -> bool:
    """Тестирует валидацию минимальных размеров"""
    print("Testing minimum dimensions...")
    
    try:
        from ai.ai_player import AIPlayer
        
        test_cases: List[Tuple[int, int, str]] = [
            (399, 300, "width too small"),
            (400, 299, "height too small"),
            (399, 299, "both too small"),
            (100, 100, "very small dimensions"),
        ]
        
        for width, height, description in test_cases:
            try:
                AIPlayer(width, height, debug_mode=False)
                print(f"  FAIL: Should raise ValueError for {description}")
                return False
            except ValueError as e:
                error_msg = str(e)
                if "Минимальные размеры" in error_msg:
                    print(f"  PASS: ValueError raised for {description}: {error_msg[:60]}")
                else:
                    print(f"  PASS: ValueError raised for {description} (different message)")
            except Exception as e:
                print(f"  FAIL: Wrong exception type for {description}: {type(e).__name__}")
                return False
        
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_debug_mode_validation() -> bool:
    """Тестирует валидацию debug_mode"""
    print("Testing debug_mode validation...")
    
    try:
        from ai.ai_player import AIPlayer
        
        # debug_mode должен преобразовываться в bool
        ai1 = AIPlayer(800, 600, debug_mode=1)
        assert ai1.debug_mode is True
        print("  PASS: debug_mode=1 converts to True")
        
        ai2 = AIPlayer(800, 600, debug_mode=0)
        assert ai2.debug_mode is False
        print("  PASS: debug_mode=0 converts to False")
        
        ai3 = AIPlayer(800, 600, debug_mode="truthy")
        assert ai3.debug_mode is True
        print("  PASS: debug_mode='truthy' converts to True")
        
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def main() -> bool:
    """Запускает все тесты"""
    print("=== AIPlayer Input Validation Tests ===\n")
    
    tests: List[Tuple[Callable[[], bool], str]] = [
        (test_valid_dimensions, "Valid dimensions"),
        (test_type_validation, "Type validation"),
        (test_negative_values, "Negative values"),
        (test_minimum_dimensions, "Minimum dimensions"),
        (test_debug_mode_validation, "Debug mode validation"),
    ]
    
    passed: int = 0
    total: int = len(tests)
    
    for test_func, test_name in tests:
        print(f"\n[{test_name}]")
        if test_func():
            passed += 1
        else:
            print(f"  FAILED: {test_name}")
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("SUCCESS: All validation tests passed!")
        return True
    else:
        print("FAILURE: Some tests failed")
        return False


if __name__ == "__main__":
    success: bool = main()
    sys.exit(0 if success else 1)
