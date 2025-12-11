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
from .platform_utils import is_frozen


def get_ai_directory() -> str:
    """
    Определяет каталог для AI файлов (логи и модели).
    Для разработки: ai в корне проекта
    Для exe: каталог установки Windows или директория exe файла
    """
    # Для разработки (запуск из IDE) всегда используем ai в корне проекта
    if not is_frozen():
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

    def default(self, obj: Any) -> Any:
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
        
        # КРИТИЧНО: Очищаем старые session логи при старте (оставляем только последний)
        self._cleanup_old_session_logs()

    def _cleanup_old_session_logs(self):
        """
        Очищает старые session логи при старте, оставляя только последний (самый новый).
        Это предотвращает накопление большого количества лог файлов.
        """
        try:
            if not os.path.exists(self.logs_dir):
                return
            
            session_files = []
            for file in os.listdir(self.logs_dir):
                if file.startswith("session_") and file.endswith(".json"):
                    file_path = os.path.join(self.logs_dir, file)
                    try:
                        mtime = os.path.getmtime(file_path)
                        session_files.append((mtime, file_path))
                    except Exception:
                        session_files.append((0, file_path))
            
            # Сортируем по времени модификации (самый новый последний)
            session_files.sort(key=lambda x: x[0])
            
            # Удаляем все session файлы, кроме последнего (самого нового)
            if len(session_files) > 1:
                for mtime, file_path in session_files[:-1]:
                    try:
                        os.remove(file_path)
                        if not is_frozen():
                            print(f"[LOG] Удален старый session лог при старте: {os.path.basename(file_path)}")
                    except Exception as e:
                        if not is_frozen():
                            print(f"[LOG] Не удалось удалить старый лог {file_path}: {e}")
        except Exception as e:
            # Не блокируем выполнение при ошибке очистки
            if not is_frozen():
                print(f"[LOG] Ошибка при очистке старых session логов: {e}")
    
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

        # Автосохранение каждые 100 действий (реже, чтобы не блокировать выполнение)
        if len(self.actions_log) % 100 == 0:
            try:
                self.save_session_log()
            except Exception as e:
                # Не блокируем выполнение при ошибке сохранения
                if not is_frozen():
                    print(f"[WARNING] Ошибка автосохранения лога: {e}")

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
    
    def log_ball_paddle_positions(
        self, 
        ball_x: float, 
        ball_y: float, 
        ball_vel_x: float, 
        ball_vel_y: float,
        paddle_x: float, 
        paddle_y: float,
        paddle_width: float,
        paddle_height: float,
        event_type: str = "frame_update"
    ):
        """
        Логирует координаты мяча и платформы для диагностики
        Включает автоматическую детекцию прилипания мяча к платформе
        
        Args:
            ball_x, ball_y: Координаты центра мяча
            ball_vel_x, ball_vel_y: Скорость мяча
            paddle_x, paddle_y: Координаты платформы (top-left)
            paddle_width, paddle_height: Размеры платформы
            event_type: Тип события (frame_update, collision, etc.)
        """
        paddle_centerx = paddle_x + paddle_width / 2
        paddle_centery = paddle_y + paddle_height / 2
        
        # КРИТИЧНО: Детекция прилипания мяча к платформе
        # Признаки прилипания:
        # 1. Горизонтальные координаты мяча синхронизируются с платформой (разница < 5px)
        # 2. Мяч не двигается по вертикали (vel_y == 0 или очень мал)
        # 3. Мяч находится внутри или очень близко к платформе
        horizontal_sync = abs(ball_x - paddle_centerx) < 5  # Мяч по горизонтали синхронизирован с платформой
        vertical_stationary = abs(ball_vel_y) < 0.1  # Мяч не двигается по вертикали
        ball_inside_paddle = (
            paddle_x <= ball_x <= paddle_x + paddle_width and
            paddle_y <= ball_y <= paddle_y + paddle_height
        )
        ball_very_close = (
            abs(ball_x - paddle_centerx) < paddle_width / 2 + 10 and
            abs(ball_y - paddle_y) < 20  # Мяч очень близко к верхней части платформы
        )
        
        # Детектируем прилипание
        sticking_detected = (
            (horizontal_sync or ball_inside_paddle or ball_very_close) and
            vertical_stationary and
            event_type != "BALL_STUCK_FIXED"  # Не детектируем, если уже исправлено
        )
        
        position_data = {
            "type": "ball_paddle_positions",
            "event_type": event_type,
            "ball": {
                "centerx": ball_x,
                "centery": ball_y,
                "velocity_x": ball_vel_x,
                "velocity_y": ball_vel_y,
            },
            "paddle": {
                "x": paddle_x,
                "y": paddle_y,
                "centerx": paddle_centerx,
                "centery": paddle_centery,
                "width": paddle_width,
                "height": paddle_height,
                "top": paddle_y,
                "bottom": paddle_y + paddle_height,
                "left": paddle_x,
                "right": paddle_x + paddle_width,
            },
            "distance": {
                "ball_to_paddle_top": ball_y - paddle_y if ball_y > paddle_y else paddle_y - ball_y,
                "ball_above_paddle": ball_y < paddle_y,
                "ball_below_paddle": ball_y > paddle_y + paddle_height,
                "horizontal_distance": abs(ball_x - paddle_centerx),
                "vertical_distance": abs(ball_y - paddle_y),
            },
            "sticking_detection": {
                "sticking_detected": sticking_detected,
                "horizontal_sync": horizontal_sync,
                "vertical_stationary": vertical_stationary,
                "ball_inside_paddle": ball_inside_paddle,
                "ball_very_close": ball_very_close,
                "horizontal_diff": ball_x - paddle_centerx,
                "vertical_diff": ball_y - paddle_y,
            }
        }
        
        # Если детектировано прилипание, меняем тип события для лучшей видимости в логах
        if sticking_detected and event_type == "frame_update":
            position_data["event_type"] = "BALL_STICKING_DETECTED"
        
        self.log_action(position_data)

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
            # КРИТИЧНО: Используем прямую запись вместо атомарной (избегаем проблем с правами доступа)
            # Если файл заблокирован или недоступен, просто пропускаем сохранение
            try:
                with open(self.session_log_file, "w", encoding="utf-8") as f:
                    json.dump(
                        session_data, f, cls=CustomJSONEncoder, ensure_ascii=False, indent=2
                    )
            except (PermissionError, OSError) as e:
                # Файл заблокирован или нет прав доступа - пропускаем сохранение
                # НЕ выводим предупреждение, чтобы не засорять консоль
                pass
        except Exception as e:
            # Не блокируем выполнение при ошибке сохранения
            # НЕ выводим предупреждение, чтобы не засорять консоль и не блокировать игру
            pass

    def finalize_and_analyze(self):
        """
        Финальная обработка логов при выходе из программы:
        1. Сохраняет финальный лог сессии
        2. Запускает анализатор логов
        3. Сохраняет результат анализа
        4. Удаляет старые session логи (оставляет только последний, если нужен)
        5. Удаляет файлы после обработки
        """
        if not self.enable_session_logging:
            return
        
        # Сохраняем финальный лог сессии
        self.save_session_log()
        
        # Запускаем анализатор логов
        try:
            from .log_analyzer import LogAnalyzer
            
            analyzer = LogAnalyzer()
            analyzer.load_logs(self.logs_dir)
            analysis_result = analyzer.analyze_movement_patterns()
            
            # Сохраняем результат анализа
            analysis_file = os.path.join(self.logs_dir, f"analysis_{self.session_id}.json")
            with open(analysis_file, "w", encoding="utf-8") as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            
            # КРИТИЧНО: Удаляем старые session логи, оставляя только последний (самый новый)
            try:
                session_files = []
                for file in os.listdir(self.logs_dir):
                    if file.startswith("session_") and file.endswith(".json"):
                        file_path = os.path.join(self.logs_dir, file)
                        try:
                            # Получаем время модификации файла
                            mtime = os.path.getmtime(file_path)
                            session_files.append((mtime, file_path))
                        except Exception:
                            # Если не удается получить время, добавляем с минимальным временем
                            session_files.append((0, file_path))
                
                # Сортируем по времени модификации (самый новый последний)
                session_files.sort(key=lambda x: x[0])
                
                # Удаляем все session файлы, кроме последнего (самого нового)
                if len(session_files) > 1:
                    # Удаляем все кроме последнего
                    for mtime, file_path in session_files[:-1]:
                        try:
                            os.remove(file_path)
                            if not is_frozen():
                                print(f"[LOG] Удален старый session лог: {os.path.basename(file_path)}")
                        except Exception as e:
                            if not is_frozen():
                                print(f"[LOG] Не удалось удалить лог {file_path}: {e}")
                
                # КРИТИЧНО: После обработки удаляем все session файлы (включая последний)
                # Они больше не нужны, так как анализ уже выполнен
                for mtime, file_path in session_files:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            if not is_frozen():
                                print(f"[LOG] Удален session лог после обработки: {os.path.basename(file_path)}")
                    except Exception as e:
                        if not is_frozen():
                            print(f"[LOG] Не удалось удалить лог {file_path}: {e}")
            except Exception as e:
                if not is_frozen():
                    print(f"[LOG] Ошибка при очистке session логов: {e}")
            
            # КРИТИЧНО: Удаляем старые analysis файлы, оставляя только последний (самый новый)
            try:
                analysis_files = []
                for file in os.listdir(self.logs_dir):
                    if file.startswith("analysis_") and file.endswith(".json"):
                        file_path = os.path.join(self.logs_dir, file)
                        try:
                            mtime = os.path.getmtime(file_path)
                            analysis_files.append((mtime, file_path))
                        except Exception:
                            analysis_files.append((0, file_path))
                
                # Сортируем по времени модификации (самый новый последний)
                analysis_files.sort(key=lambda x: x[0])
                
                # Удаляем все analysis файлы, кроме последнего (самого нового)
                if len(analysis_files) > 1:
                    for mtime, file_path in analysis_files[:-1]:
                        try:
                            os.remove(file_path)
                            if not is_frozen():
                                print(f"[LOG] Удален старый analysis файл: {os.path.basename(file_path)}")
                        except Exception as e:
                            if not is_frozen():
                                print(f"[LOG] Не удалось удалить analysis файл {file_path}: {e}")
            except Exception as e:
                if not is_frozen():
                    print(f"[LOG] Ошибка при очистке analysis файлов: {e}")
                
        except Exception as e:
            if not is_frozen():
                print(f"[LOG] Ошибка при анализе логов: {e}")

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
