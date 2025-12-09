"""
Модуль для логирования производительности AI системы
"""

import json
import time
import os
import sys
import pygame
from datetime import datetime
from typing import List, Dict, Any, Optional
from .game_state import GameState, Point


def get_ai_directory():
    """
    Определяет каталог для AI файлов (логи и модели).
    Для разработки: ai в корне проекта
    Для exe: каталог установки Windows или директория exe файла
    """
    # Для разработки (запуск из IDE) всегда используем ai в корне проекта
    if not getattr(sys, "frozen", False):
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ai_dir = os.path.join(current_dir, "ai")
        return ai_dir

    # Для exe файлов пытаемся использовать LOCALAPPDATA
    try:
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            game_dir = os.path.join(localappdata, "Games", "Arkanoid")
            ai_dir = os.path.join(game_dir, "ai")
            # Создаем директории если их нет
            try:
                os.makedirs(ai_dir, exist_ok=True)
            except (OSError, PermissionError):
                pass
            return ai_dir
    except:
        pass

    # Fallback для exe: директория exe файла
    exe_dir = os.path.dirname(sys.executable)
    ai_dir = os.path.join(exe_dir, "ai")
    try:
        os.makedirs(ai_dir, exist_ok=True)
    except (OSError, PermissionError):
        pass
    return ai_dir


class CustomJSONEncoder(json.JSONEncoder):
    """Кастомный JSON encoder для сериализации Point и других объектов"""

    def default(self, obj):
        if isinstance(obj, Point):
            return {"x": obj.x, "y": obj.y}
        elif isinstance(obj, pygame.Rect):
            return {
                "x": obj.x,
                "y": obj.y,
                "width": obj.width,
                "height": obj.height,
                "centerx": obj.centerx,
                "centery": obj.centery,
            }
        return super().default(obj)


class PerformanceLogger:
    """Класс для логирования производительности AI системы"""

    def __init__(
        self, session_id: Optional[str] = None, enable_session_logging: bool = False
    ):
        self.session_id = session_id or self._generate_session_id()
        self.session_start_time = time.time()
        self.actions_log = []
        self.game_results = []
        self.enable_session_logging = enable_session_logging

        # Создаем директорию для логов если её нет
        ai_dir = get_ai_directory()
        self.logs_dir = os.path.join(ai_dir, "logs")
        try:
            os.makedirs(self.logs_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Если не удается создать каталог, используем текущую директорию
            print(
                f"Предупреждение: не удалось создать каталог логов {self.logs_dir}: {e}"
            )
            self.logs_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "logs"
            )
            os.makedirs(self.logs_dir, exist_ok=True)

        # Файл для сохранения логов сессии (только если включено)
        if self.enable_session_logging:
            self.session_log_file = os.path.join(
                self.logs_dir, f"session_{self.session_id}.json"
            )
        else:
            self.session_log_file = None

    def _generate_session_id(self) -> str:
        """Генерирует уникальный ID сессии"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{int(time.time() % 1000)}"

    def log_action(self, action_data: Dict[str, Any]):
        """
        Логирует действие AI

        Args:
            action_data: Данные о действии
        """
        if not self.enable_session_logging:
            return

        log_entry = {
            "timestamp": time.time(),
            "session_time": time.time() - self.session_start_time,
            **action_data,
        }

        self.actions_log.append(log_entry)

        # Автосохранение каждые 100 действий
        if len(self.actions_log) % 100 == 0:
            self.save_session_log()

    def log_game_start(self, game_state: GameState):
        """Логирует начало новой игры"""
        start_data = {
            "type": "game_start",
            "initial_bricks_count": len(game_state.remaining_bricks),
            "initial_ball_position": {
                "x": game_state.ball_position.x,
                "y": game_state.ball_position.y,
            },
            "initial_ball_velocity": {
                "x": game_state.ball_velocity.x,
                "y": game_state.ball_velocity.y,
            },
        }

        self.log_action(start_data)

    def log_game_end(self, game_state: GameState, success: bool, final_score: int):
        """Логирует окончание игры"""
        end_data = {
            "type": "game_end",
            "success": success,
            "final_score": final_score,
            "final_bricks_remaining": len(game_state.remaining_bricks),
            "game_duration": time.time() - self.session_start_time,
            "total_actions": len(self.actions_log),
        }

        self.log_action(end_data)
        self.game_results.append(end_data)

        # Сохраняем результат игры
        self.save_game_result(end_data)

    def log_paddle_movement(
        self, from_x: int, to_x: int, reason: str, confidence: float = 1.0
    ):
        """Логирует движение платформы"""
        movement_data = {
            "type": "paddle_movement",
            "from_position": from_x,
            "to_position": to_x,
            "movement_distance": abs(to_x - from_x),
            "reason": reason,
            "confidence": confidence,
        }

        self.log_action(movement_data)

    def log_trajectory_prediction(
        self, predicted_trajectory: List[Dict], actual_result: Optional[Dict] = None
    ):
        """Логирует предсказание траектории"""
        trajectory_data = {
            "type": "trajectory_prediction",
            "predicted_points_count": len(predicted_trajectory),
            "predicted_trajectory": predicted_trajectory,
            "actual_result": actual_result,
        }

        self.log_action(trajectory_data)

    def log_brick_interaction(
        self,
        brick_hit: bool,
        bricks_destroyed: List[Dict],
        predicted_bricks: Optional[List[Dict]] = None,
    ):
        """Логирует взаимодействие с кубиками"""
        interaction_data = {
            "type": "brick_interaction",
            "brick_hit": brick_hit,
            "bricks_destroyed": bricks_destroyed,
            "destroyed_count": len(bricks_destroyed),
            "predicted_bricks": predicted_bricks,
            "prediction_accuracy": (
                self._calculate_prediction_accuracy(bricks_destroyed, predicted_bricks)
                if predicted_bricks
                else None
            ),
        }

        self.log_action(interaction_data)

    def log_decision_making(
        self,
        decision_reason: str,
        considered_options: List[Dict],
        chosen_option: Dict,
        decision_confidence: float,
    ):
        """Логирует процесс принятия решений"""
        decision_data = {
            "type": "decision_making",
            "decision_reason": decision_reason,
            "considered_options_count": len(considered_options),
            "chosen_option": chosen_option,
            "decision_confidence": decision_confidence,
        }

        self.log_action(decision_data)

    def log_performance_metrics(self, metrics: Dict[str, float]):
        """Логирует метрики производительности"""
        metrics_data = {"type": "performance_metrics", **metrics}

        self.log_action(metrics_data)

    def _calculate_prediction_accuracy(
        self, actual_bricks: List[Dict], predicted_bricks: Optional[List[Dict]]
    ) -> float:
        """Рассчитывает точность предсказания"""
        if not predicted_bricks:
            return 0.0

        actual_brick_positions = set(
            (getattr(brick, "x", 0), getattr(brick, "y", 0)) for brick in actual_bricks
        )
        predicted_brick_positions = set(
            (getattr(brick, "x", 0), getattr(brick, "y", 0))
            for brick in predicted_bricks
        )

        if not actual_brick_positions:
            return 1.0 if not predicted_brick_positions else 0.0

        correct_predictions = len(actual_brick_positions & predicted_brick_positions)
        return correct_predictions / len(actual_brick_positions)

    def save_session_log(self):
        """Сохраняет логи сессии в файл"""
        if not self.enable_session_logging or not self.session_log_file:
            return

        session_data = {
            "session_id": self.session_id,
            "session_start": self.session_start_time,
            "session_end": time.time(),
            "total_duration": time.time() - self.session_start_time,
            "total_actions": len(self.actions_log),
            "actions": self.actions_log,
            "game_results": self.game_results,
        }

        try:
            with open(self.session_log_file, "w", encoding="utf-8") as f:
                json.dump(
                    session_data, f, cls=CustomJSONEncoder, ensure_ascii=False, indent=2
                )
        except Exception as e:
            print(f"Ошибка при сохранении лога сессии: {e}")

    def save_game_result(self, game_result: Dict[str, Any]):
        """Сохраняет результат игры в общий файл"""
        results_file = os.path.join(self.logs_dir, "all_game_results.json")

        # Загружаем существующие результаты
        existing_results = []
        if os.path.exists(results_file):
            try:
                with open(results_file, "r", encoding="utf-8") as f:
                    existing_results = json.load(f)
            except Exception:
                existing_results = []

        # Добавляем новый результат
        existing_results.append(game_result)

        try:
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(
                    existing_results,
                    f,
                    cls=CustomJSONEncoder,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            print(f"Ошибка при сохранении результата игры: {e}")

    def generate_performance_report(self) -> Dict[str, Any]:
        """Генерирует отчет о производительности"""
        if not self.actions_log:
            return {"error": "Нет данных для анализа"}

        report = {
            "session_info": {
                "session_id": self.session_id,
                "duration": time.time() - self.session_start_time,
                "total_actions": len(self.actions_log),
            },
            "game_performance": {},
            "paddle_movements": {},
            "prediction_accuracy": {},
            "learning_progress": {},
        }

        # Анализ производительности игры
        game_actions = [a for a in self.actions_log if a.get("type") == "game_end"]
        if game_actions:
            successful_games = [g for g in game_actions if g.get("success", False)]
            report["game_performance"] = {
                "total_games": len(game_actions),
                "successful_games": len(successful_games),
                "success_rate": (
                    len(successful_games) / len(game_actions) if game_actions else 0
                ),
                "average_score": sum(g.get("final_score", 0) for g in game_actions)
                / len(game_actions),
                "average_duration": sum(g.get("game_duration", 0) for g in game_actions)
                / len(game_actions),
            }

        # Анализ движений платформы
        movement_actions = [
            a for a in self.actions_log if a.get("type") == "paddle_movement"
        ]
        if movement_actions:
            total_distance = sum(
                a.get("movement_distance", 0) for a in movement_actions
            )
            report["paddle_movements"] = {
                "total_movements": len(movement_actions),
                "total_distance": total_distance,
                "average_distance": (
                    total_distance / len(movement_actions) if movement_actions else 0
                ),
            }

        # Анализ точности предсказаний
        interaction_actions = [
            a for a in self.actions_log if a.get("type") == "brick_interaction"
        ]
        if interaction_actions:
            accuracies = [
                a.get("prediction_accuracy", 0)
                for a in interaction_actions
                if a.get("prediction_accuracy") is not None
            ]
            if accuracies:
                report["prediction_accuracy"] = {
                    "total_predictions": len(accuracies),
                    "average_accuracy": sum(accuracies) / len(accuracies),
                    "best_accuracy": max(accuracies),
                    "worst_accuracy": min(accuracies),
                }

        return report

    def get_recent_actions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Возвращает последние действия"""
        return self.actions_log[-count:] if self.actions_log else []

    def analyze_trends(self) -> Dict[str, Any]:
        """Анализирует тренды в производительности"""
        if len(self.actions_log) < 10:
            return {"error": "Недостаточно данных для анализа трендов"}

        trends = {
            "performance_trend": "stable",
            "accuracy_trend": "stable",
            "efficiency_trend": "stable",
        }

        # Простой анализ трендов на основе последних действий
        recent_actions = self.actions_log[-20:]  # Последние 20 действий

        # Анализ успешности действий
        successful_actions = [a for a in recent_actions if a.get("success", False)]
        if len(successful_actions) > 15:
            trends["performance_trend"] = "improving"
        elif len(successful_actions) < 5:
            trends["performance_trend"] = "declining"

        return trends

    def clear_session_data(self):
        """Очищает данные текущей сессии"""
        self.actions_log = []
        self.game_results = []
        self.session_start_time = time.time()

    def __del__(self):
        """Деструктор для автосохранения"""
        if (
            hasattr(self, "actions_log")
            and self.actions_log
            and self.enable_session_logging
        ):
            self.save_session_log()

    def test_json_serialization(self):
        """Тестирует JSON сериализацию различных объектов"""
        from .game_state import Point

        # Создаем тестовые данные
        test_point = Point(100, 200)
        test_rect = pygame.Rect(50, 50, 100, 30)
        test_data = {
            "point": test_point,
            "rect": test_rect,
            "string": "test string",
            "number": 42,
            "list": [1, 2, 3],
        }

        try:
            # Тестируем сериализацию
            json_str = json.dumps(
                test_data, cls=CustomJSONEncoder, ensure_ascii=False, indent=2
            )
            print("JSON Serialization Test:")
            print(json_str)

            # Тестируем десериализацию
            parsed_data = json.loads(json_str)
            print("\nDeserialized data:")
            print(parsed_data)

            return True
        except Exception as e:
            print(f"Error in JSON serialization test: {e}")
            return False
