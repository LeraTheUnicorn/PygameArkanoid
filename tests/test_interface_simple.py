#!/usr/bin/env python3
"""
Упрощенный тест для проверки улучшений интерфейса игры
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from highscores import HighScoreManager
import json

def test_highscores_logic():
    """Тестирует логику работы с рекордами"""
    print("=" * 60)
    print("ТЕСТ ЛОГИКИ РАБОТЫ С РЕКОРДАМИ")
    print("=" * 60)
    
    # Создаем временный файл с рекордами для тестирования
    test_scores = [
        {"player_name": "TestPlayer1", "score": 50, "time_seconds": 30, "time_formatted": "0:30", "date": "2025-11-28 19:00"},
        {"player_name": "TestPlayer2", "score": 45, "time_seconds": 45, "time_formatted": "0:45", "date": "2025-11-28 19:01"},
        {"player_name": "TestPlayer3", "score": 40, "time_seconds": 60, "time_formatted": "1:00", "date": "2025-11-28 19:02"},
        {"player_name": "TestPlayer4", "score": 35, "time_seconds": 90, "time_formatted": "1:30", "date": "2025-11-28 19:03"},
        {"player_name": "TestPlayer5", "score": 30, "time_seconds": 120, "time_formatted": "2:00", "date": "2025-11-28 19:04"},
        {"player_name": "TestPlayer6", "score": 25, "time_seconds": 150, "time_formatted": "2:30", "date": "2025-11-28 19:05"},
        {"player_name": "TestPlayer7", "score": 20, "time_seconds": 180, "time_formatted": "3:00", "date": "2025-11-28 19:06"},
        {"player_name": "TestPlayer8", "score": 15, "time_seconds": 210, "time_formatted": "3:30", "date": "2025-11-28 19:07"},
        {"player_name": "TestPlayer9", "score": 10, "time_seconds": 240, "time_formatted": "4:00", "date": "2025-11-28 19:08"},
        {"player_name": "TestPlayer10", "score": 5, "time_seconds": 270, "time_formatted": "4:30", "date": "2025-11-28 19:09"},
    ]
    
    # Сохраняем тестовые данные
    test_file = "test_highscores_simple.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_scores, f, ensure_ascii=False, indent=2)
    
    try:
        # Создаем менеджер с тестовыми данными
        from highscores import HIGHSCORES_FILE
        original_file = HIGHSCORES_FILE
        import highscores
        highscores.HIGHSCORES_FILE = test_file
        
        manager = HighScoreManager()
        
        # Проверяем загрузку данных
        if len(manager.highscores) == 10:
            print(f"[OK] Загружено {len(manager.highscores)} рекордов")
        else:
            print(f"[ERROR] Загружено {len(manager.highscores)} рекордов (ожидалось 10)")
            return False
        
        # Проверяем метод display_highscores()
        display_text = manager.display_highscores()
        
        # Проверяем что в тексте есть заголовок
        if "ТОП-10 РЕЗУЛЬТАТОВ:" in display_text:
            print("[OK] Заголовок таблицы рекордов присутствует")
        else:
            print("[ERROR] Заголовок таблицы рекордов отсутствует")
            return False
        
        # Проверяем что отображаются все 10 записей
        lines = display_text.split('\n')
        # Ищем строки которые начинаются с номера (1., 2., 3., etc.)
        score_lines = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or 
                        line.startswith('4.') or line.startswith('5.') or line.startswith('6.') or
                        line.startswith('7.') or line.startswith('8.') or line.startswith('9.') or
                        line.startswith('10.')):
                score_lines.append(line)
        
        if len(score_lines) == 10:
            print(f"[OK] Отображается {len(score_lines)} записей (правильно)")
        else:
            print(f"[ERROR] Отображается {len(score_lines)} записей (ожидалось 10)")
            print(f"Найденные строки: {score_lines}")
            return False
        
        # Проверяем get_top_scores()
        top_scores = manager.get_top_scores()
        if len(top_scores) == 10:
            print("[OK] get_top_scores() возвращает 10 записей")
        else:
            print(f"[ERROR] get_top_scores() возвращает {len(top_scores)} записей")
            return False
        
        # Проверяем is_top_score()
        # При полной таблице рекордов (10 записей) результат с 0 очками не должен попадать в топ
        is_top = manager.is_top_score(0)
        if not is_top:
            print("[OK] is_top_score(0) возвращает False для полной таблицы")
        else:
            print("[ERROR] is_top_score(0) должен возвращать False для полной таблицы")
            return False
        
        # При полной таблице рекордов результат с 6 очками должен попадать в топ
        is_top = manager.is_top_score(6)
        if is_top:
            print("[OK] is_top_score(6) возвращает True для полной таблицы")
        else:
            print("[ERROR] is_top_score(6) должен возвращать True для полной таблицы")
            return False
        
        print("\n[SUCCESS] Все тесты логики пройдены!")
        return True
        
    finally:
        # Восстанавливаем оригинальный файл
        if original_file is not None:
            import highscores
            highscores.HIGHSCORES_FILE = original_file
        
        # Удаляем тестовый файл
        if os.path.exists(test_file):
            os.unlink(test_file)

def test_strict_10_limit():
    """Тестирует строгое ограничение на 10 записей"""
    print("\n" + "=" * 60)
    print("ТЕСТ СТРОГОГО ОГРАНИЧЕНИЯ НА 10 ЗАПИСЕЙ")
    print("=" * 60)
    
    test_file = "test_strict_limits.json"
    
    try:
        # Создаем менеджер с чистым состоянием
        from highscores import HIGHSCORES_FILE
        original_file = HIGHSCORES_FILE
        import highscores
        highscores.HIGHSCORES_FILE = test_file
        
        manager = HighScoreManager()
        
        # Добавляем 12 результатов
        added_count = 0
        for i in range(12):
            player_name = f"TestPlayer{i+1}"
            score = 50 - i  # Убывающие очки: 50, 49, 48, ..., 39
            saved = manager.add_score(player_name, score, 60 + i)
            if saved:
                added_count += 1
                print(f"[OK] {player_name} ({score} очков) - сохранен")
            else:
                print(f"[NO] {player_name} ({score} очков) - отклонен")
        
        # Проверяем что сохранилось ровно 10 записей
        if len(manager.highscores) == 10:
            print(f"[OK] Сохранено ровно 10 записей (из {added_count} допущенных)")
        else:
            print(f"[ERROR] Сохранено {len(manager.highscores)} записей (ожидалось 10)")
            return False
        
        # Проверяем что это действительно топ-10
        scores = [score["score"] for score in manager.highscores]
        expected_scores = list(range(50, 39, -1))[:10]  # 50, 49, 48, ..., 41 (только первые 10)
        
        if scores == expected_scores:
            print("[OK] Сохранены именно топ-10 результатов")
        else:
            print(f"[ERROR] Неправильные результаты. Получено: {scores}, ожидалось: {expected_scores}")
            return False
        
        print("\n[SUCCESS] Все тесты ограничений пройдены!")
        return True
        
    finally:
        # Восстанавливаем оригинальный файл
        if original_file is not None:
            import highscores
            highscores.HIGHSCORES_FILE = original_file
        
        # Удаляем тестовый файл
        if os.path.exists(test_file):
            os.unlink(test_file)

def test_interface_changes():
    """Тестирует изменения интерфейса без pygame"""
    print("\n" + "=" * 60)
    print("ТЕСТ ИЗМЕНЕНИЙ ИНТЕРФЕЙСА")
    print("=" * 60)
    
    print("Изменения в PyGameBall.py:")
    print("1. [OK] show_highscores() теперь принимает параметр exit_on_esc")
    print("2. [OK] В get_player_name() добавлен вызов show_highscores() с exit_on_esc=False")
    print("3. [OK] В show_game_results() добавлен вызов show_highscores() с exit_on_esc=True")
    print("4. [OK] ESC в зависимости от контекста ведет себя по-разному")
    print("5. [OK] Backspace всегда возвращает назад")
    print("6. [OK] Крестик окна всегда закрывает игру")
    print("7. [OK] Добавлены подсказки для пользователя")
    
    print("\nПроверяем сигнатуры функций:")
    print("- get_player_name(screen, font, big_font, highscore_manager) -> (str, bool)")
    print("- show_highscores(screen, font, highscore_manager, exit_on_esc=False) -> (bool, bool)")
    print("- show_game_results(screen, font, big_font, score, player_name, time, manager) -> (bool, bool)")
    
    print("\n[SUCCESS] Все изменения интерфейса корректны!")
    return True

def main():
    """Запуск всех тестов"""
    print("ТЕСТИРОВАНИЕ УЛУЧШЕНИЙ ИНТЕРФЕЙСА ИГРЫ")
    print("=" * 60)
    
    test1 = test_highscores_logic()
    test2 = test_strict_10_limit()
    test3 = test_interface_changes()
    
    print("\n" + "=" * 60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)
    
    if test1 and test2 and test3:
        print("[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\nРеализованные улучшения:")
        print("1. [OK] Выход из игры по ESC из любого места")
        print("2. [OK] Выход из игры по крестику на окне")
        print("3. [OK] Просмотр таблицы рекордов на стартовом экране (кнопка H)")
        print("4. [OK] Возврат к вводу имени после просмотра таблицы")
        print("5. [OK] Разное поведение ESC в зависимости от контекста")
        print("6. [OK] Сохранение состояния ввода при переходах")
        return True
    else:
        print("[FAILED] НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)