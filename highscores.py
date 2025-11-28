"""
Система управления рекордами игры Арканоид
Сохраняет и загружает результаты игроков в файл
"""

import json
import os
from typing import List, Dict
from datetime import datetime

HIGHSCORES_FILE = "highscores.json"


class HighScoreManager:
    def __init__(self):
        self.highscores = []
        self.load_highscores()

    def load_highscores(self) -> None:
        """Загружает рекорды из файла"""
        try:
            if os.path.exists(HIGHSCORES_FILE):
                with open(HIGHSCORES_FILE, 'r', encoding='utf-8') as f:
                    self.highscores = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.highscores = []

    def save_highscores(self) -> None:
        """Сохраняет рекорды в файл"""
        try:
            with open(HIGHSCORES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.highscores, f, ensure_ascii=False, indent=2)
        except IOError:
            print("Ошибка сохранения рекордов")

    def add_score(self, player_name: str, score: int, game_time_seconds: int) -> bool:
        """
        Добавляет новый результат в список рекордов
        Возвращает True если результат попал в топ-10 и сохранен, False если не попал
        """
        # СТРОГОЕ ограничение диапазона очков от 0 до 50 баллов
        if not (0 <= score <= 50):
            raise ValueError(f"Очки должны быть в диапазоне от 0 до 50. Получено: {score}")

        # Ограничиваем время до 59:59 (3599 секунд)
        if game_time_seconds > 3599:
            game_time_seconds = 3599

        # Форматирование времени в М:СС формат с ведущими нулями для секунд
        game_time_formatted = f"{game_time_seconds // 60}:{game_time_seconds % 60:02d}"

        new_score = {
            "player_name": player_name,
            "score": score,
            "time_seconds": game_time_seconds,
            "time_formatted": game_time_formatted,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # Проверяем, попадет ли результат в топ-10 БЕЗ обрезки до 10
        temp_scores = self.highscores.copy()
        temp_scores.append(new_score)
        
        # Сортируем временный список БЕЗ обрезки
        temp_scores.sort(key=lambda item: (-item["score"], item["time_seconds"], item["player_name"]))
        
        # Проверяем позицию нового результата в отсортированном списке
        for i, score_data in enumerate(temp_scores):
            if score_data["player_name"] == player_name and score_data["score"] == score and score_data["time_seconds"] == game_time_seconds:
                if i >= 10:  # 11-я позиция или ниже (индексы начинаются с 0)
                    # Результат не попал в топ-10
                    return False
                break
        
        # Результат попал в топ-10, добавляем и сохраняем
        self.highscores.append(new_score)
        self.sort_highscores()  # Теперь сортируем и обрезаем основной список
        self.save_highscores()
        return True

    def sort_highscores(self) -> None:
        """Сортирует рекорды: сначала по очкам (по убыванию), затем по времени (по возрастанию), затем по имени"""

        def sort_key(item):
            return (-item["score"], item["time_seconds"], item["player_name"])

        self.highscores.sort(key=sort_key)

        # Обрезаем до топ-10 (это нужно только для совместимости, основная логика в add_score)
        self.highscores = self.highscores[:10]

    def get_top_scores(self) -> List[Dict]:
        """Возвращает топ-10 рекордов"""
        return self.highscores[:10]

    def is_top_score(self, score: int) -> bool:
        """Проверяет, попадает ли результат в топ-10"""
        # Сначала проверяем диапазон очков
        if not (0 <= score <= 50):
            return False

        if len(self.highscores) < 10:
            return True
        if score > self.highscores[-1]["score"]:
            return True
        if score == self.highscores[-1]["score"]:
            return True
        return False

    def display_highscores(self) -> str:
        """Возвращает строку для отображения таблицы рекордов"""
        if not self.highscores:
            return "Пока нет рекордов"

        # Создаем таблицу с правильным форматированием
        result = "ТОП-10 РЕЗУЛЬТАТОВ:\n"
        result += "=" * 70 + "\n"

        # Заголовки с четким разделением колонок
        result += "Место | Игрок                | Очки | Время  \n"
        result += "-" * 70 + "\n"

        # Данные с точным форматированием
        for i, score_data in enumerate(self.highscores, 1):
            player_name = score_data["player_name"]

            # СТРОГОЕ форматирование поля места: для <10: "   1.  |", для >=10: "  11.  |"
            if i < 10:
                place_field = f"   {i}.  |"  # 3 пробела + значение + точка + 2 пробела + разделитель
            else:
                place_field = f"  {i}.  |"   # 2 пробела + значение + точка + 2 пробела
            
            player_field = f"{player_name[:20]:<20}"  # 20 символов для имени игрока
            score_field = f"{score_data['score']:3d}"  # 3 символа для очков
            time_field = f"{score_data['time_formatted']:>5}"  # 5 символов для времени

            # Объединяем колонки с разделителями
            row = f"{place_field} {player_field} | {score_field} | {time_field}"
            result += row + "\n"

        return result
