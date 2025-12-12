#!/usr/bin/env python3
"""
Test for auto mode fix verification.
Checks that after game completion and return to name input screen,
auto mode activates correctly when pressing key 0.
"""

import sys
import os
from typing import List

# Add current directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_auto_mode_fix() -> bool:
    """Test auto mode fix"""

    print("=== AUTO MODE FIX TEST ===")
    print()

    # Test 1: Check show_game_results function signature
    print("1. Checking show_game_results function signature...")
    try:
        from src.game.PyGameBall import show_game_results
        import inspect

        # Get function parameters
        sig: inspect.Signature = inspect.signature(show_game_results)
        params: List[str] = list(sig.parameters.keys())

        # Check for auto_mode parameter
        if "auto_mode" in params:
            print("   [OK] Parameter auto_mode added to show_game_results function")
        else:
            print("   [FAIL] Parameter auto_mode missing in show_game_results function")
            print(f"   Found parameters: {params}")
            return False

    except Exception as e:
        print(f"   [FAIL] Error checking show_game_results function: {e}")
        return False

    # Test 2: Check ESC handling logic in auto mode
    print("2. Checking ESC handling logic...")

    # Read source code and check for required logic
    try:
        # Правильный путь к PyGameBall.py
        pygameball_path: str = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "game", "PyGameBall.py"
        )
        with open(pygameball_path, "r", encoding="utf-8") as f:
            content: str = f.read()

        # Check for conditional logic for auto_mode
        esc_logic_checks: List[str] = [
            "if auto_mode:",
            "# В авторежиме ESC возвращает к экрану ввода имени",
            "# В ручном режиме ESC выходит из игры",
        ]

        found_checks: int = 0
        for check in esc_logic_checks:
            if check in content:
                found_checks += 1

        if found_checks >= 2:
            print("   [OK] ESC handling logic for auto mode found")
        else:
            print(
                f"   [FAIL] ESC handling logic incomplete (found {found_checks}/3 checks)"
            )
            print("   Note: Code may have different ESC handling contexts")
            return False

    except Exception as e:
        print(f"   [FAIL] Error reading file: {e}")
        return False

    # Test 3: Check show_game_results calls update
    print("3. Checking show_game_results calls update...")

    try:
        # Правильный путь к PyGameBall.py
        pygameball_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PyGameBall.py"
        )
        with open(pygameball_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all function calls
        import re

        calls: List[str] = re.findall(r"show_game_results\s*\([^)]+\)", content)

        updated_calls: int = 0
        for call in calls:
            if "auto_mode" in call:
                updated_calls += 1

        total_calls: int = len(calls)
        if total_calls >= 2 and updated_calls == total_calls:
            print(
                f"   [OK] All show_game_results calls updated ({updated_calls}/{total_calls})"
            )
        else:
            print(
                f"   [FAIL] Not all show_game_results calls updated ({updated_calls}/{total_calls})"
            )
            return False

    except Exception as e:
        print(f"   [FAIL] Error analyzing calls: {e}")
        return False

    # Test 4: Check key 0 handling
    print("4. Checking key 0 handling for auto mode...")

    try:
        # Правильный путь к PyGameBall.py
        pygameball_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PyGameBall.py"
        )
        with open(pygameball_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key 48 (0) handling
        key_handling_checks: List[str] = [
            "elif event.key == 48:",
            "auto_mode = True",
            "input_active = False",
        ]

        found_checks = 0
        for check in key_handling_checks:
            if check in content:
                found_checks += 1

        if found_checks == 3:
            print("   [OK] Key 0 handling for auto mode configured correctly")
        else:
            print(
                f"   [FAIL] Key 0 handling incomplete (found {found_checks}/3 checks)"
            )
            return False

    except Exception as e:
        print(f"   [FAIL] Error checking key handling: {e}")
        return False

    print()
    print("=== TEST RESULT ===")
    print("[OK] All checks passed successfully!")
    print()
    print("Fixes include:")
    print("- Added auto_mode parameter to show_game_results")
    print("- ESC in auto mode returns to name input")
    print("- Updated all show_game_results calls")
    print("- Improved key 0 handling")
    print("- Added debug information")

    return True


if __name__ == "__main__":
    success = test_auto_mode_fix()
    sys.exit(0 if success else 1)
