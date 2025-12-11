#!/usr/bin/env python3
"""
Скрипт для тестирования исправлений AI системы
Запускает игру в авторежиме на короткое время для проверки логов
"""

import subprocess
import time
import os
import signal
import sys
from typing import List, Dict, Any, Optional


def test_ai_fix() -> None:
    """Тестирует исправления AI системы"""
    print("Запуск тестирования AI исправлений...")

    # Включаем логирование сессий для тестирования
    import os

    os.environ["AI_ENABLE_SESSION_LOGGING"] = "1"

    # Команда для запуска игры в venv
    cmd: List[str] = [".venv\\Scripts\\python.exe", "PyGameBall.py"]

    try:
        # Запускаем процесс
        process: subprocess.Popen[str] = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd(),
        )

        print("Игра запущена, ждем инициализации...")

        # Ждем 2 секунды для загрузки
        time.sleep(2)

        # Имитируем ввод имени "robot" и авторежим (клавиша 0)
        try:
            # Вводим имя
            if process.stdin:
                process.stdin.write("robot\n")
                process.stdin.flush()

            # Ждем немного
            time.sleep(0.5)

            # Нажимаем 0 для авторежима
            if process.stdin:
                process.stdin.write("0\n")
                process.stdin.flush()

            print("Авторежим активирован, ждем 10 секунд игры...")

            # Ждем 10 секунд игры
            time.sleep(10)

            print("Завершаем тест...")

            # Завершаем процесс
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        except Exception as e:
            print(f"Ошибка ввода: {e}")
            process.kill()

        # Получаем вывод
        stdout: str
        stderr: str
        stdout, stderr = process.communicate()

        print("Вывод игры:")
        print(stdout)
        if stderr:
            print("Ошибки:")
            print(stderr)

        # Проверяем логи
        check_logs()

    except Exception as e:
        print(f"Ошибка запуска: {e}")


def check_logs() -> None:
    """Проверяет последние логи на наличие вертикальных паттернов"""
    print("\nПроверка логов...")

    logs_dir: str = "../ai/logs"
    if not os.path.exists(logs_dir):
        print("Директория логов не найдена")
        return

    # Находим последний лог
    log_files: List[str] = [
        f
        for f in os.listdir(logs_dir)
        if f.startswith("session_") and f.endswith(".json")
    ]
    if not log_files:
        print("Логи не найдены")
        return

    latest_log: str = max(log_files)
    log_path: str = os.path.join(logs_dir, latest_log)

    print(f"Анализ лога: {latest_log}")

    try:
        import json

        with open(log_path, "r", encoding="utf-8") as f:
            log_data: Dict[str, Any] = json.load(f)

        # Проверяем на ai_deactivated (означает завершение сессии)
        if "ai_deactivated" in log_data:
            print("Сессия была завершена без AI активности")
            return

        # Анализируем действия
        actions: List[Dict[str, Any]] = log_data.get("actions", [])
        vertical_hits: int = 0
        total_hits: int = 0
        left_positions: int = 0
        total_positions: int = 0

        for action in actions:
            trajectory: Dict[str, Any] = action.get("trajectory", {})
            dx: float = trajectory.get("dx", 0)
            dy: float = trajectory.get("dy", 0)

            # Проверяем вертикальность
            if abs(dx) < 5 and abs(dy) > 0:
                vertical_hits += 1
            total_hits += 1

            # Проверяем позицию платформы
            position: Dict[str, Any] = action.get("position", {})
            x: int = position.get("x", 400)
            if x < 100:  # Левая сторона
                left_positions += 1
            total_positions += 1

        print("Результаты анализа:")
        print(f"   Вертикальные удары: {vertical_hits}/{total_hits}")
        print(f"   Позиции слева: {left_positions}/{total_positions}")

        if vertical_hits > 0:
            print("Обнаружены вертикальные удары - проблема не решена")
        else:
            print("Вертикальных ударов не обнаружено")

        if left_positions > total_positions * 0.7:
            print("Платформа часто фиксируется слева")
        else:
            print("Платформа распределяется нормально")

    except Exception as e:
        print(f"Ошибка анализа лога: {e}")


if __name__ == "__main__":
    test_ai_fix()
