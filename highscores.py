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

    def add_score(self, player_name: str, score: int, game_time_seconds: int) -> None:
        """Добавляет новый результат в список рекордов"""
        game_time_formatted = f"{game_time_seconds // 60}:{game_time_seconds % 60:02d}"
        
        new_score = {
            "player_name": player_name,
            "score": score,
            "time_seconds": game_time_seconds,
            "time_formatted": game_time_formatted,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        self.highscores.append(new_score)
        self.sort_highscores()
        self.save_highscores()

    def sort_highscores(self) -> None:
        """Сортирует рекорды: сначала по очкам (по убыванию), затем по времени (по возрастанию), затем по имени"""
        def sort_key(item):
            return (-item["score"], item["time_seconds"], item["player_name"])
        
        self.highscores.sort(key=sort_key)
        
        # Оставляем только топ-10
        self.highscores = self.highscores[:10]

    def get_top_scores(self) -> List[Dict]:
        """Возвращает топ-10 рекордов"""
        return self.highscores[:10]

    def is_top_score(self, score: int) -> bool:
        """Проверяет, попадает ли результат в топ-10"""
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
        
        # Ширина колонок: длина заголовка + 2 пробела (слева и справа)
        col_widths = {
            'place': len('Место') + 2,      # 6 + 2 = 8
            'player': len('Игрок') + 2,     # 8 + 2 = 22  
            'score': len('Очки') + 2,       # 6 + 2 = 8
            'time': len('Время') + 2        # 8 + 2 = 10
        }
        
        result = "ТОП-10 РЕЗУЛЬТАТОВ:\n"
        result += "=" * sum(col_widths.values()) + "\n"
        
        # Заголовки
        headers = f"{'Место':^{col_widths['place']}} {'Игрок':^{col_widths['player']}} {'Очки':^{col_widths['score']}} {'Время':^{col_widths['time']}}"
        result += headers + "\n"
        result += "=" * sum(col_widths.values()) + "\n"
        
        # Данные
        for i, score_data in enumerate(self.highscores, 1):
            player_name = score_data["player_name"][:col_widths['player']-2]  # Обрезаем до ширины колонки
            row = f"{i:^{col_widths['place']}} {player_name:^{col_widths['player']}} {score_data['score']:^{col_widths['score']}} {score_data['time_formatted']:^{col_widths['time']}}"
            result += row + "\n"
        
        return result