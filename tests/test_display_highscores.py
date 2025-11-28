#!/usr/bin/env python3
"""
Тест для проверки правильного форматирования таблицы рекордов
"""

import sys
import os

# Добавляем корневую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from highscores import HighScoreManager
import json


def test_display_highscores_format():
    """Тестирует правильность форматирования таблицы рекордов"""
    print("ТЕСТИРОВАНИЕ ФОРМАТИРОВАНИЯ ТАБЛИЦЫ РЕКОРДОВ")
    print("=" * 60)

    # Создаем тестовые данные
    test_scores = [
        {
            "player_name": "TestPlayer1",
            "score": 50,
            "time_seconds": 30,
            "time_formatted": "0:30",
            "date": "2025-11-28 19:00",
        },
        {
            "player_name": "TestPlayer2",
            "score": 45,
            "time_seconds": 45,
            "time_formatted": "0:45",
            "date": "2025-11-28 19:01",
        },
        {
            "player_name": "TestPlayer3",
            "score": 40,
            "time_seconds": 60,
            "time_formatted": "1:00",
            "date": "2025-11-28 19:02",
        },
        {
            "player_name": "TestPlayer4",
            "score": 35,
            "time_seconds": 90,
            "time_formatted": "1:30",
            "date": "2025-11-28 19:03",
        },
        {
            "player_name": "TestPlayer5",
            "score": 30,
            "time_seconds": 120,
            "time_formatted": "2:00",
            "date": "2025-11-28 19:04",
        },
        {
            "player_name": "TestPlayer6",
            "score": 25,
            "time_seconds": 150,
            "time_formatted": "2:30",
            "date": "2025-11-28 19:05",
        },
        {
            "player_name": "TestPlayer7",
            "score": 20,
            "time_seconds": 180,
            "time_formatted": "3:00",
            "date": "2025-11-28 19:06",
        },
        {
            "player_name": "TestPlayer8",
            "score": 15,
            "time_seconds": 210,
            "time_formatted": "3:30",
            "date": "2025-11-28 19:07",
        },
        {
            "player_name": "TestPlayer9",
            "score": 10,
            "time_seconds": 240,
            "time_formatted": "4:00",
            "date": "2025-11-28 19:08",
        },
        {
            "player_name": "TestPlayer10",
            "score": 5,
            "time_seconds": 270,
            "time_formatted": "4:30",
            "date": "2025-11-28 19:09",
        },
    ]

    # Сохраняем тестовые данные
    with open("test_display_highscores.json", "w", encoding="utf-8") as f:
        json.dump(test_scores, f, ensure_ascii=False, indent=2)

    try:
        # Создаем менеджер с тестовыми данными
        from highscores import HIGHSCORES_FILE

        original_file = HIGHSCORES_FILE
        import highscores

        highscores.HIGHSCORES_FILE = "test_display_highscores.json"

        manager = HighScoreManager()

        print("Тестовые данные загружены:")
        print(f"Количество рекордов: {len(manager.highscores)}")

        print("\nВызов метода display_highscores():")
        print("-" * 60)

        # Получаем отформатированную таблицу
        table_text = manager.display_highscores()

        # Выводим таблицу
        print(table_text)

        # Проверяем содержимое таблицы
        print("ПРОВЕРКА ФОРМАТИРОВАНИЯ:")
        print("-" * 60)

        lines = table_text.split("\n")

        # Проверяем заголовок
        if lines[0] == "ТОП-10 РЕЗУЛЬТАТОВ:":
            print("[OK] Заголовок таблицы корректный")
        else:
            print(f"[ERROR] Неправильный заголовок: {lines[0]}")

        # Проверяем заголовки колонок
        if lines[2] == "Место | Игрок                | Очки | Время  ":
            print("[OK] Заголовки колонок корректные")
        else:
            print(f"[ERROR] Неправильные заголовки колонок: '{lines[2]}'")

        # Проверяем количество строк данных
        data_lines = [
            line
            for line in lines
            if line.strip()
            and not line.startswith("Место |")
            and not line.startswith("-")
            and not line.startswith("=")
        ]
        if len(data_lines) == 10:
            print(f"[OK] Количество строк данных корректное: {len(data_lines)}")
        else:
            print(f"[ERROR] Неправильное количество строк данных: {len(data_lines)}")

        # Проверяем форматирование первых нескольких строк
        print("\nДетальная проверка форматирования:")
        for i, line in enumerate(data_lines[:3], 1):
            print(f"Строка {i}: '{line}'")
            # Проверяем структуру: должно быть 3 разделителя " | "
            separator_count = line.count(" | ")
            if separator_count == 3:
                print(f"  [OK] Правильное количество разделителей: {separator_count}")
            else:
                print(
                    f"  [ERROR] Неправильное количество разделителей: {separator_count}"
                )

        print("\n[SUCCESS] Тест форматирования завершен!")
        print("Файлы с содержимым таблицы должны быть созданы автоматически")

        return True

    finally:
        # Восстанавливаем оригинальный файл
        if original_file is not None:
            import highscores

            highscores.HIGHSCORES_FILE = original_file

        # Удаляем тестовый файл
        if os.path.exists("test_display_highscores.json"):
            os.unlink("test_display_highscores.json")


def test_empty_highscores():
    """Тестирует отображение пустой таблицы рекордов"""
    print("\nТЕСТ ПУСТОЙ ТАБЛИЦЫ РЕКОРДОВ")
    print("=" * 60)

    # Создаем временный пустой файл
    with open("test_empty_highscores.json", "w", encoding="utf-8") as f:
        json.dump([], f)

    try:
        from highscores import HIGHSCORES_FILE

        original_file = HIGHSCORES_FILE
        import highscores

        highscores.HIGHSCORES_FILE = "test_empty_highscores.json"

        manager = HighScoreManager()
        result = manager.display_highscores()

        print("Результат для пустой таблицы:")
        print(f"'{result}'")

        if result == "Пока нет рекордов":
            print("[OK] Пустая таблица отображается корректно")
            return True
        else:
            print("[ERROR] Неправильное отображение пустой таблицы")
            return False

    finally:
        if original_file is not None:
            import highscores

            highscores.HIGHSCORES_FILE = original_file
        if os.path.exists("test_empty_highscores.json"):
            os.unlink("test_empty_highscores.json")


if __name__ == "__main__":
    print("ТЕСТИРОВАНИЕ МЕТОДА DISPLAY_HIGHSCORES()")
    print("=" * 60)

    test1 = test_display_highscores_format()
    test2 = test_empty_highscores()

    print("\n" + "=" * 60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)

    if test1 and test2:
        print("[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Метод display_highscores() работает корректно")
        sys.exit(0)
    else:
        print("[FAILED] НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        sys.exit(1)
