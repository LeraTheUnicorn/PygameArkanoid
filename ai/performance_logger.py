"""
Модуль для логирования производительности AI системы
"""

import json
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .game_state import GameState


class PerformanceLogger:
    """Класс для логирования производительности AI системы"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.session_start_time = time.time()
        self.actions_log = []
        self.game_results = []

        # Создаем директорию для логов если её нет
        self.logs_dir = "ai/logs"
        os.makedirs(self.logs_dir, exist_ok=True)

        # Файл для сохранения логов сессии
        self.session_log_file = os.path.join(
            self.logs_dir, f"session_{self.session_id}.json"
        )

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
            (brick.get("x"), brick.get("y")) for brick in actual_bricks
        )
        predicted_brick_positions = set(
            (brick.get("x"), brick.get("y")) for brick in predicted_bricks
        )

        if not actual_brick_positions:
            return 1.0 if not predicted_brick_positions else 0.0

        correct_predictions = len(actual_brick_positions & predicted_brick_positions)
        return correct_predictions / len(actual_brick_positions)

    def save_session_log(self):
        """Сохраняет логи сессии в файл"""
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
                json.dump(session_data, f, ensure_ascii=False, indent=2)
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
                json.dump(existing_results, f, ensure_ascii=False, indent=2)
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
        if hasattr(self, "actions_log") and self.actions_log:
            self.save_session_log()
