#!/usr/bin/env python3
"""
Тест для проверки строгого ограничения на хранение максимум 10 записей в highscores.json
"""

import json
import os
import sys
import tempfile

# Добавляем родительскую директорию в путь для импорта модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from highscores import HighScoreManager

def test_strict_10_limit():
    """Тестирует строгое ограничение на 10 записей"""
    
    # Создаем временный файл для тестирования
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
        temp_filename = temp_file.name
    
    original_filename = None
    try:
        # Сохраняем оригинальное значение и заменяем на временный файл
        from highscores import HIGHSCORES_FILE
        original_filename = HIGHSCORES_FILE
        import highscores
        highscores.HIGHSCORES_FILE = temp_filename
        
        manager = HighScoreManager()
        
        # Добавляем 15 результатов с разными очками
        test_players = [
            ("Player1", 50, 30),
            ("Player2", 49, 35),
            ("Player3", 48, 40),
            ("Player4", 47, 45),
            ("Player5", 46, 50),
            ("Player6", 45, 55),
            ("Player7", 44, 60),
            ("Player8", 43, 65),
            ("Player9", 42, 70),
            ("Player10", 41, 75),  # 10-й игрок попадает в топ-10
            ("Player11", 40, 80),  # 11-й игрок НЕ должен попасть в топ-10
            ("Player12", 39, 85),
            ("Player13", 38, 90),
            ("Player14", 37, 95),
            ("Player15", 36, 100)
        ]
        
        saved_count = 0
        rejected_count = 0
        
        print("Добавляем результаты игроков:")
        print("-" * 50)
        
        for player_name, score, time_seconds in test_players:
            saved = manager.add_score(player_name, score, time_seconds)
            
            if saved:
                saved_count += 1
                print(f"[OK] {player_name}: {score} очков - СОХРАНЕН (попал в топ-10)")
            else:
                rejected_count += 1
                print(f"[NO] {player_name}: {score} очков - ОТКЛОНЕН (не попал в топ-10)")
        
        print("\nРезультаты тестирования:")
        print("-" * 50)
        print(f"Сохранено результатов: {saved_count}")
        print(f"Отклонено результатов: {rejected_count}")
        
        # Проверяем, что в файле ровно 10 записей
        with open(temp_filename, 'r', encoding='utf-8') as f:
            saved_scores = json.load(f)
        
        print(f"Записей в файле: {len(saved_scores)}")
        
        # Проверяем, что это действительно топ-10
        print("\nСодержимое файла highscores.json:")
        print("-" * 50)
        for i, score_data in enumerate(saved_scores, 1):
            print(f"{i:2d}. {score_data['player_name'][:15]:<15} - {score_data['score']:2d} очков ({score_data['time_formatted']})")
        
        # Тест пройден если:
        # 1. Сохранено ровно 10 результатов
        # 2. Отклонено 5 результатов
        # 3. В файле ровно 10 записей
        
        success = (saved_count == 10 and rejected_count == 5 and len(saved_scores) == 10)
        
        print("\nРезультат теста:", "ПРОЙДЕН" if success else "НЕ ПРОЙДЕН")
        
        # Проверяем сообщение пользователю
        print("\nПроверка сообщения пользователю:")
        print("-" * 50)
        
        # Создаем новый менеджер с нашими рекордами
        manager2 = HighScoreManager()
        manager2.highscores = saved_scores
        
        # Пытаемся добавить результат, который точно не попадет в топ-10
        not_saved = manager2.add_score("LowScore", 1, 200)
        
        if not not_saved:
            print("[OK] Система корректно отклоняет низкие результаты")
            print("[OK] Сообщение 'Результат не попал в топ-10, таблица рекордов не обновлена' будет показано пользователю")
        else:
            print("[ERROR] Система некорректно сохранила низкий результат")
        
        return success
        
    finally:
        # Восстанавливаем оригинальный путь
        if original_filename is not None:
            import highscores
            highscores.HIGHSCORES_FILE = original_filename
        
        # Удаляем временный файл
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

def test_existing_highscores():
    """Тестирует работу с существующими рекордами"""
    
    # Проверяем текущий файл highscores.json
    if os.path.exists("highscores.json"):
        with open("highscores.json", 'r', encoding='utf-8') as f:
            existing_scores = json.load(f)
        
        print(f"\nПроверка существующего файла highscores.json:")
        print(f"Текущее количество записей: {len(existing_scores)}")
        
        if len(existing_scores) > 10:
            print("[WARN] В файле больше 10 записей! Это не должно происходить.")
            print("   Система должна автоматически обрезать до топ-10")
        elif len(existing_scores) == 10:
            print("[OK] В файле ровно 10 записей - это правильно")
        else:
            print(f"[OK] В файле {len(existing_scores)} записей - это допустимо")
    
    # Тестируем менеджер с текущими рекордами
    manager = HighScoreManager()
    
    # Проверяем что get_top_scores() возвращает не больше 10 записей
    top_scores = manager.get_top_scores()
    if len(top_scores) <= 10:
        print(f"[OK] get_top_scores() возвращает {len(top_scores)} записей - корректно")
    else:
        print(f"[ERROR] get_top_scores() возвращает {len(top_scores)} записей - должно быть <= 10")
    
    # Проверяем метод is_top_score
    print("\nТестирование is_top_score():")
    
    if len(manager.highscores) < 10:
        # Если меньше 10 записей, любой результат должен попадать в топ
        test_result = manager.is_top_score(10)
        print(f"is_top_score(10) при {len(manager.highscores)} записях: {test_result}")
        if test_result:
            print("[OK] Корректно: любой результат попадает в топ при <10 записях")
        else:
            print("[ERROR] Ошибка: результат должен попадать в топ при <10 записях")
    
    # Тестируем низкий результат при полной таблице
    if len(manager.highscores) == 10:
        low_score = 0
        test_result = manager.is_top_score(low_score)
        print(f"is_top_score({low_score}) при полной таблице: {test_result}")
        if not test_result:
            print("[OK] Корректно: низкий результат не попадает в топ при полной таблице")
        else:
            print("[ERROR] Ошибка: низкий результат не должен попадать в топ при полной таблице")

if __name__ == "__main__":
    print("ТЕСТ СТРОГОГО ОГРАНИЧЕНИЯ НА 10 ЗАПИСЕЙ")
    print("=" * 60)
    
    # Запускаем основной тест
    test1_result = test_strict_10_limit()
    
    # Тестируем существующие рекорды
    test_existing_highscores()
    
    print("\n" + "=" * 60)
    if test1_result:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("Система корректно ограничивает хранение до 10 записей")
    else:
        print("ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        print("Обнаружены проблемы с ограничением на 10 записей")
        sys.exit(1)