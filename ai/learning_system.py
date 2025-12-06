"""
Модуль системы обучения для AI с кластеризацией траекторий и обработкой промпта
"""

import json
import os
from typing import Dict, List, Any, Optional
import math
from collections import defaultdict
from sklearn.cluster import KMeans
import numpy as np


class LearningSystem:
    """Система обучения для AI"""

    def __init__(self, model_path: str = "ai/models/ai_model.json"):
        self.model_path = model_path
        self.learning_data = {
            "strategy_weights": {
                "aggressive": 0.5,
                "conservative": 0.5,
                "precision": 0.5,
                "speed": 0.5,
            },
            "position_preferences": {},
            "trajectory_patterns": {},
            "success_factors": {},
            "historical_performance": [],
            "learning_stats": {
                "total_learning_iterations": 0,
                "successful_adaptations": 0,
                "failed_adaptations": 0,
                "average_improvement": 0.0,
            },
        }

        # Создаем директорию для модели если её нет
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        # Загружаем существующую модель если она есть
        self.load_model()

    def update_strategy(self, action_result: Dict[str, Any]):
        """
        Обновляет стратегию на основе результата действия

        Args:
            action_result: Результат последнего действия
        """
        # Извлекаем ключевые параметры результата
        success = action_result.get("success", False)
        action_type = action_result.get("action_type", "unknown")
        confidence = action_result.get("confidence", 0.5)
        game_state_before = action_result.get("game_state_before")
        game_state_after = action_result.get("game_state_after")

        # Обновляем веса стратегий на основе успешности
        if success:
            self._reinforce_successful_strategy(action_result)
        else:
            self._penalize_failed_strategy(action_result)

        # Обновляем предпочтения позиций
        if game_state_before and game_state_after:
            self._update_position_preferences(
                game_state_before, game_state_after, success
            )

        # Анализируем паттерны траекторий
        if "trajectory_prediction" in action_result:
            self._analyze_trajectory_pattern(
                action_result["trajectory_prediction"], success
            )

        # Обновляем факторы успеха
        self._update_success_factors(action_result)

        # Обновляем статистику обучения
        self._update_learning_stats(success)

        # Сохраняем модель
        self.save_model()

    def _reinforce_successful_strategy(self, action_result: Dict[str, Any]):
        """Усиливает успешную стратегию"""
        confidence = action_result.get("confidence", 0.5)
        reinforcement_factor = 0.1 * confidence  # Усиление пропорционально уверенности

        strategy_type = self._determine_strategy_type(action_result)

        if strategy_type in self.learning_data["strategy_weights"]:
            current_weight = self.learning_data["strategy_weights"][strategy_type]
            self.learning_data["strategy_weights"][strategy_type] = min(
                1.0, current_weight + reinforcement_factor
            )

    def _penalize_failed_strategy(self, action_result: Dict[str, Any]):
        """Наказывает неуспешную стратегию"""
        confidence = action_result.get("confidence", 0.5)
        penalty_factor = 0.05 * confidence  # Штраф пропорционально уверенности

        trajectory_data = action_result.get("trajectory_prediction")
        if trajectory_data and trajectory_data.get("intersection_point"):
            intersection = trajectory_data["intersection_point"]
            ball_pos = action_result.get("game_state_before", {}).get("ball_position", {})
            if ball_pos and abs(intersection.get("x", 0) - ball_pos.get("x", 0)) < 10:
                penalty_factor *= 2.0

        strategy_type = self._determine_strategy_type(action_result)

        if strategy_type in self.learning_data["strategy_weights"]:
            current_weight = self.learning_data["strategy_weights"][strategy_type]
            self.learning_data["strategy_weights"][strategy_type] = max(
                0.0, current_weight - penalty_factor
            )

    def _determine_strategy_type(self, action_result: Dict[str, Any]) -> str:
        """Определяет тип стратегии на основе результата действия"""
        action_type = action_result.get("action_type", "")
        movement_distance = action_result.get("movement_distance", 0)
        time_taken = action_result.get("time_taken", 1.0)

        if movement_distance > 50:
            if time_taken < 0.1:
                return "aggressive"
            else:
                return "speed"
        elif movement_distance < 10:
            return "precision"
        else:
            return "conservative"

    def _update_position_preferences(
        self, state_before: Dict, state_after: Dict, success: bool
    ):
        """Обновляет предпочтения позиций платформы"""
        paddle_x_before = state_before.get("paddle_position", {}).get("x", 0)
        paddle_x_after = state_after.get("paddle_position", {}).get("x", 0)

        position_segment = int(paddle_x_before / 80)

        if position_segment not in self.learning_data["position_preferences"]:
            self.learning_data["position_preferences"][position_segment] = {
                "success_count": 0,
                "total_count": 0,
                "success_rate": 0.0,
            }

        pref = self.learning_data["position_preferences"][position_segment]
        pref["total_count"] += 1

        if success:
            pref["success_count"] += 1

        pref["success_rate"] = pref["success_count"] / pref["total_count"]

    def _analyze_trajectory_pattern(self, trajectory_data: Dict, success: bool):
        """Анализирует паттерны траекторий"""
        if trajectory_data is None:
            return

        predicted_points = trajectory_data.get("predicted_points", [])
        actual_points = trajectory_data.get("actual_points", [])

        if not predicted_points or not actual_points:
            return

        accuracy = self._calculate_trajectory_accuracy(predicted_points, actual_points)
        pattern_key = self._create_trajectory_pattern_key(predicted_points[:3])

        if pattern_key not in self.learning_data["trajectory_patterns"]:
            self.learning_data["trajectory_patterns"][pattern_key] = {
                "accuracy_scores": [],
                "success_rates": [],
                "pattern_frequency": 0,
            }

        pattern = self.learning_data["trajectory_patterns"][pattern_key]
        pattern["accuracy_scores"].append(accuracy)
        pattern["success_rates"].append(1.0 if success else 0.0)
        pattern["pattern_frequency"] += 1

        if len(pattern["accuracy_scores"]) > 100:
            pattern["accuracy_scores"] = pattern["accuracy_scores"][-50:]
            pattern["success_rates"] = pattern["success_rates"][-50:]

    def _calculate_trajectory_accuracy(
        self, predicted: List[Dict], actual: List[Dict]
    ) -> float:
        """Рассчитывает точность предсказания траектории"""
        if len(predicted) != len(actual):
            min_len = min(len(predicted), len(actual))
            predicted = predicted[:min_len]
            actual = actual[:min_len]

        if not predicted:
            return 0.0

        total_distance_error = 0.0
        for pred_point, actual_point in zip(predicted, actual):
            pred_x, pred_y = pred_point.get("x", 0), pred_point.get("y", 0)
            actual_x, actual_y = actual_point.get("x", 0), actual_point.get("y", 0)
            distance_error = math.sqrt((pred_x - actual_x) ** 2 + (pred_y - actual_y) ** 2)
            total_distance_error += distance_error

        average_error = total_distance_error / len(predicted)
        max_possible_error = 200
        accuracy = max(0.0, 1.0 - (average_error / max_possible_error))
        return accuracy

    def _create_trajectory_pattern_key(self, initial_points: List[Dict]) -> str:
        """Создает ключ для паттерна траектории на основе начальных точек"""
        if not initial_points:
            return "unknown"

        pattern_data = []
        for point in initial_points[:3]:
            x = round(point.get("x", 0) / 20)
            y = round(point.get("y", 0) / 20)
            pattern_data.append(f"{x}_{y}")

        return "_".join(pattern_data)

    def _update_success_factors(self, action_result: Dict[str, Any]):
        """Обновляет факторы успеха"""
        success = action_result.get("success", False)
        bricks_remaining = action_result.get("remaining_bricks", [])
        if isinstance(bricks_remaining, list):
            bricks_count = len(bricks_remaining)
        else:
            bricks_count = bricks_remaining if isinstance(bricks_remaining, int) else 0

        factors = {
            "ball_speed": action_result.get("ball_speed", 5),
            "bricks_remaining": bricks_count,
            "paddle_distance": action_result.get("movement_distance", 0),
            "prediction_confidence": action_result.get("confidence", 0.5),
        }

        for factor_name, factor_value in factors.items():
            if factor_name not in self.learning_data["success_factors"]:
                self.learning_data["success_factors"][factor_name] = {
                    "total_cases": 0,
                    "successful_cases": 0,
                    "factor_values": [],
                }

            factor_data = self.learning_data["success_factors"][factor_name]
            factor_data["total_cases"] += 1

            if success:
                factor_data["successful_cases"] += 1

            factor_data["factor_values"].append(factor_value)

            if len(factor_data["factor_values"]) > 200:
                factor_data["factor_values"] = factor_data["factor_values"][-100:]

    def _update_learning_stats(self, success: bool):
        """Обновляет статистику обучения"""
        stats = self.learning_data["learning_stats"]
        stats["total_learning_iterations"] += 1

        if success:
            stats["successful_adaptations"] += 1
        else:
            stats["failed_adaptations"] += 1

        total_attempts = stats["successful_adaptations"] + stats["failed_adaptations"]
        if total_attempts > 0:
            improvement_rate = stats["successful_adaptations"] / total_attempts
            stats["average_improvement"] = (
                stats["average_improvement"] * 0.9 + improvement_rate * 0.1
            )

    def cluster_trajectories(self, n_clusters=5):
        """Кластеризует траектории на основе начальных точек"""
        if not self.learning_data["trajectory_patterns"]:
            return []

        pattern_keys = list(self.learning_data["trajectory_patterns"].keys())
        vectors = []
        for key in pattern_keys:
            coords = [int(x) for x in key.split('_')]
            vectors.append(coords[:6])

        if len(vectors) < n_clusters:
            n_clusters = len(vectors)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(vectors)

        return [{"pattern": pattern_keys[i], "cluster": clusters[i]} for i in range(len(clusters))]

    def generate_behavior_prompt(self, current_situation: Dict[str, Any]) -> str:
        """Генерирует промпт для описания правил поведения и стратегий ИИ"""
        weights = self.learning_data["strategy_weights"]
        prompt = f"""
        Опиши правила поведения и стратегии ИИ в игре на основе следующих параметров:
        - Веса стратегий: aggressive={weights['aggressive']}, conservative={weights['conservative']}, precision={weights['precision']}, speed={weights['speed']}
        - Текущая ситуация: количество кирпичей={current_situation.get('bricks_remaining', 25)}, скорость мяча={current_situation.get('ball_speed', 5)}, давление времени={current_situation.get('time_pressure', False)}
        - История успешных/неуспешных действий: {self.learning_data['learning_stats']}
        - Предпочтительные позиции: {self.learning_data['position_preferences']}
        - Паттерны траекторий: {self.learning_data['trajectory_patterns']}

        Сформулируй рекомендации по поведению для текущей ситуации и объясни логику выбора стратегии.
        """
        return prompt

    def get_strategy_recommendation(
        self, current_situation: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Возвращает рекомендации по стратегии для текущей ситуации

        Args:
            current_situation: Текущая ситуация в игре

        Returns:
            Рекомендуемые веса стратегий
        """
        base_weights = self.learning_data["strategy_weights"].copy()

        bricks_count = current_situation.get("bricks_remaining", 25)
        ball_speed = current_situation.get("ball_speed", 5)
        time_pressure = current_situation.get("time_pressure", False)

        if bricks_count <= 5:
            base_weights["precision"] *= 1.3
            base_weights["aggressive"] *= 0.8
        elif bricks_count >= 20:
            base_weights["aggressive"] *= 1.2
            base_weights["precision"] *= 0.9

        if ball_speed >= 80:
            base_weights["speed"] *= 1.3
            base_weights["conservative"] *= 0.8

        total_weight = sum(base_weights.values())
        if total_weight > 0:
            base_weights = {k: v / total_weight for k, v in base_weights.items()}

        return base_weights

    def get_optimal_position_preference(self, paddle_x: int) -> float:
        """
        Возвращает предпочтительность позиции на основе исторических данных

        Args:
            paddle_x: X-координата платформы

        Returns:
            Предпочтительность позиции (0.0 - 1.0)
        """
        position_segment = int(paddle_x / 80)

        if position_segment in self.learning_data["position_preferences"]:
            return self.learning_data["position_preferences"][position_segment]["success_rate"]

        return 0.5

    def predict_success_probability(self, action_plan: Dict[str, Any]) -> float:
        """
        Предсказывает вероятность успеха для плана действия

        Args:
            action_plan: План действия

        Returns:
            Предсказанная вероятность успеха (0.0 - 1.0)
        """
        base_probability = 0.5

        factors = self.learning_data["success_factors"]

        if "ball_speed" in factors:
            factor_data = factors["ball_speed"]
            if factor_data["total_cases"] > 10:
                speed = action_plan.get("ball_speed", 5)
                speed_factor = 1.0 - abs(speed - 50) * 0.01
                base_probability *= speed_factor

        if "paddle_distance" in factors:
            distance = action_plan.get("movement_distance", 0)
            if distance > 100:
                base_probability *= 0.8
            elif distance < 20:
                base_probability *= 1.1

        return max(0.0, min(1.0, base_probability))

    def save_model(self):
        """Сохраняет модель в файл"""
        try:
            with open(self.model_path, "w", encoding="utf-8") as f:
                json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении модели: {e}")

    def load_model(self):
        """Загружает модель из файла"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)

                for key, value in loaded_data.items():
                    if key in self.learning_data:
                        self.learning_data[key] = value

            except Exception as e:
                print(f"Ошибка при загрузке модели: {e}")

    def reset_learning_data(self):
        """Сбрасывает данные обучения"""
        self.learning_data = {
            "strategy_weights": {
                "aggressive": 0.5,
                "conservative": 0.5,
                "precision": 0.5,
                "speed": 0.5,
            },
            "position_preferences": {},
            "trajectory_patterns": {},
            "success_factors": {},
            "historical_performance": [],
            "learning_stats": {
                "total_learning_iterations": 0,
                "successful_adaptations": 0,
                "failed_adaptations": 0,
                "average_improvement": 0.0,
            },
        }
        self.save_model()

    def get_learning_progress(self) -> Dict[str, Any]:
        """Возвращает прогресс обучения"""
        stats = self.learning_data["learning_stats"]

        if stats["total_learning_iterations"] == 0:
            return {"message": "Обучение еще не начато"}

        success_rate = stats["successful_adaptations"] / stats["total_learning_iterations"]

        return {
            "total_iterations": stats["total_learning_iterations"],
            "success_rate": success_rate,
            "average_improvement": stats["average_improvement"],
            "strategy_weights": self.learning_data["strategy_weights"],
            "learned_positions": len(self.learning_data["position_preferences"]),
            "trajectory_patterns": len(self.learning_data["trajectory_patterns"]),
        }




"""
Модуль системы обучения для AI
"""

import json
import os
from typing import Dict, List, Any, Optional
import math
from collections import defaultdict


class LearningSystem:
    """Система обучения для AI"""

    def __init__(self, model_path: str = "ai/models/ai_model.json"):
        self.model_path = model_path
        self.learning_data = {
            "strategy_weights": {
                "aggressive": 0.5,  # Агрессивная стратегия (быстрые движения)
                "conservative": 0.5,  # Консервативная стратегия (осторожные движения)
                "precision": 0.5,  # Точная стратегия (прецизионное позиционирование)
                "speed": 0.5,  # Скоростная стратегия (быстрые решения)
            },
            "position_preferences": {},  # Предпочтения позиций
            "trajectory_patterns": {},  # Паттерны траекторий
            "success_factors": {},  # Факторы успеха
            "historical_performance": [],  # Историческая производительность
            "learning_stats": {
                "total_learning_iterations": 0,
                "successful_adaptations": 0,
                "failed_adaptations": 0,
                "average_improvement": 0.0,
            },
        }

        # Создаем директорию для модели если её нет
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        # Загружаем существующую модель если она есть
        self.load_model()

    def update_strategy(self, action_result: Dict[str, Any]):
        """
        Обновляет стратегию на основе результата действия

        Args:
            action_result: Результат последнего действия
        """
        # Извлекаем ключевые параметры результата
        success = action_result.get("success", False)
        action_type = action_result.get("action_type", "unknown")
        confidence = action_result.get("confidence", 0.5)
        game_state_before = action_result.get("game_state_before")
        game_state_after = action_result.get("game_state_after")

        # Обновляем веса стратегий на основе успешности
        if success:
            self._reinforce_successful_strategy(action_result)
        else:
            self._penalize_failed_strategy(action_result)

        # Обновляем предпочтения позиций
        if game_state_before and game_state_after:
            self._update_position_preferences(
                game_state_before, game_state_after, success
            )

        # Анализируем паттерны траекторий
        if "trajectory_prediction" in action_result:
            self._analyze_trajectory_pattern(
                action_result["trajectory_prediction"], success
            )

        # Обновляем факторы успеха
        self._update_success_factors(action_result)

        # Обновляем статистику обучения
        self._update_learning_stats(success)

        # Сохраняем модель
        self.save_model()

    def _reinforce_successful_strategy(self, action_result: Dict[str, Any]):
        """Усиливает успешную стратегию"""
        confidence = action_result.get("confidence", 0.5)
        reinforcement_factor = 0.1 * confidence  # Усиление пропорционально уверенности

        # Определяем тип стратегии на основе действия
        strategy_type = self._determine_strategy_type(action_result)

        if strategy_type in self.learning_data["strategy_weights"]:
            current_weight = self.learning_data["strategy_weights"][strategy_type]
            self.learning_data["strategy_weights"][strategy_type] = min(
                1.0, current_weight + reinforcement_factor
            )

    def _penalize_failed_strategy(self, action_result: Dict[str, Any]):
        """Наказывает неуспешную стратегию"""
        confidence = action_result.get("confidence", 0.5)
        penalty_factor = 0.05 * confidence  # Штраф пропорционально уверенности

        # Усиливаем штраф за вертикальные удары (паттерн зацикливания)
        trajectory_data = action_result.get("trajectory_prediction")
        if trajectory_data and trajectory_data.get("intersection_point"):
            intersection = trajectory_data["intersection_point"]
            ball_pos = action_result.get("game_state_before", {}).get("ball_position", {})
            if ball_pos and abs(intersection.get("x", 0) - ball_pos.get("x", 0)) < 10:
                # Вертикальный удар - усиливаем штраф
                penalty_factor *= 2.0

        strategy_type = self._determine_strategy_type(action_result)

        if strategy_type in self.learning_data["strategy_weights"]:
            current_weight = self.learning_data["strategy_weights"][strategy_type]
            self.learning_data["strategy_weights"][strategy_type] = max(
                0.0, current_weight - penalty_factor
            )

    def _determine_strategy_type(self, action_result: Dict[str, Any]) -> str:
        """Определяет тип стратегии на основе результата действия"""
        action_type = action_result.get("action_type", "")
        movement_distance = action_result.get("movement_distance", 0)
        time_taken = action_result.get("time_taken", 1.0)

        # Определяем стратегию по характеристикам действия
        if movement_distance > 50:
            if time_taken < 0.1:
                return "aggressive"  # Быстрые большие движения
            else:
                return "speed"  # Большие движения средней скорости
        elif movement_distance < 10:
            return "precision"  # Точные маленькие движения
        else:
            return "conservative"  # Умеренные движения

    def _update_position_preferences(
        self, state_before: Dict, state_after: Dict, success: bool
    ):
        """Обновляет предпочтения позиций платформы"""
        paddle_x_before = state_before.get("paddle_position", {}).get("x", 0)
        paddle_x_after = state_after.get("paddle_position", {}).get("x", 0)

        # Квантуем позицию (делим на сегменты)
        position_segment = int(
            paddle_x_before / 80
        )  # 80 пикселей на сегмент для экрана 800px

        if position_segment not in self.learning_data["position_preferences"]:
            self.learning_data["position_preferences"][position_segment] = {
                "success_count": 0,
                "total_count": 0,
                "success_rate": 0.0,
            }

        pref = self.learning_data["position_preferences"][position_segment]
        pref["total_count"] += 1

        if success:
            pref["success_count"] += 1

        # Пересчитываем success rate
        pref["success_rate"] = pref["success_count"] / pref["total_count"]

    def _analyze_trajectory_pattern(self, trajectory_data: Dict, success: bool):
        """Анализирует паттерны траекторий"""
        if trajectory_data is None:
            return  # Пропускаем анализ если данных нет

        predicted_points = trajectory_data.get("predicted_points", [])
        actual_points = trajectory_data.get("actual_points", [])

        if not predicted_points or not actual_points:
            return

        # Анализируем точность предсказания
        accuracy = self._calculate_trajectory_accuracy(predicted_points, actual_points)

        # Создаем ключ паттерна на основе начальных условий
        pattern_key = self._create_trajectory_pattern_key(predicted_points[:3])

        if pattern_key not in self.learning_data["trajectory_patterns"]:
            self.learning_data["trajectory_patterns"][pattern_key] = {
                "accuracy_scores": [],
                "success_rates": [],
                "pattern_frequency": 0,
            }

        pattern = self.learning_data["trajectory_patterns"][pattern_key]
        pattern["accuracy_scores"].append(accuracy)
        pattern["success_rates"].append(1.0 if success else 0.0)
        pattern["pattern_frequency"] += 1

        # Ограничиваем размер списков для экономии памяти
        if len(pattern["accuracy_scores"]) > 100:
            pattern["accuracy_scores"] = pattern["accuracy_scores"][-50:]
            pattern["success_rates"] = pattern["success_rates"][-50:]

    def _calculate_trajectory_accuracy(
        self, predicted: List[Dict], actual: List[Dict]
    ) -> float:
        """Рассчитывает точность предсказания траектории"""
        if len(predicted) != len(actual):
            # Нормализуем длины
            min_len = min(len(predicted), len(actual))
            predicted = predicted[:min_len]
            actual = actual[:min_len]

        if not predicted:
            return 0.0

        total_distance_error = 0.0

        for pred_point, actual_point in zip(predicted, actual):
            pred_x, pred_y = pred_point.get("x", 0), pred_point.get("y", 0)
            actual_x, actual_y = actual_point.get("x", 0), actual_point.get("y", 0)

            distance_error = math.sqrt(
                (pred_x - actual_x) ** 2 + (pred_y - actual_y) ** 2
            )
            total_distance_error += distance_error

        average_error = total_distance_error / len(predicted)

        # Конвертируем ошибку в точность (меньше ошибка = больше точность)
        max_possible_error = 200  # Максимальная возможная ошибка
        accuracy = max(0.0, 1.0 - (average_error / max_possible_error))

        return accuracy

    def _create_trajectory_pattern_key(self, initial_points: List[Dict]) -> str:
        """Создает ключ для паттерна траектории на основе начальных точек"""
        if not initial_points:
            return "unknown"

        # Используем первые 3 точки для создания паттерна
        pattern_data = []
        for point in initial_points[:3]:
            x = round(point.get("x", 0) / 20)  # Квантуем координаты
            y = round(point.get("y", 0) / 20)
            pattern_data.append(f"{x}_{y}")

        return "_".join(pattern_data)

    def _update_success_factors(self, action_result: Dict[str, Any]):
        """Обновляет факторы успеха"""
        success = action_result.get("success", False)

        # Анализируем различные факторы
        bricks_remaining = action_result.get("remaining_bricks", [])
        if isinstance(bricks_remaining, list):
            bricks_count = len(bricks_remaining)
        else:
            # Если это число, используем как есть
            bricks_count = bricks_remaining if isinstance(bricks_remaining, int) else 0

        factors = {
            "ball_speed": action_result.get("ball_speed", 5),
            "bricks_remaining": bricks_count,
            "paddle_distance": action_result.get("movement_distance", 0),
            "prediction_confidence": action_result.get("confidence", 0.5),
        }

        for factor_name, factor_value in factors.items():
            if factor_name not in self.learning_data["success_factors"]:
                self.learning_data["success_factors"][factor_name] = {
                    "total_cases": 0,
                    "successful_cases": 0,
                    "factor_values": [],
                }

            factor_data = self.learning_data["success_factors"][factor_name]
            factor_data["total_cases"] += 1

            if success:
                factor_data["successful_cases"] += 1

            factor_data["factor_values"].append(factor_value)

            # Ограничиваем размер списка
            if len(factor_data["factor_values"]) > 200:
                factor_data["factor_values"] = factor_data["factor_values"][-100:]

    def _update_learning_stats(self, success: bool):
        """Обновляет статистику обучения"""
        stats = self.learning_data["learning_stats"]
        stats["total_learning_iterations"] += 1

        if success:
            stats["successful_adaptations"] += 1
        else:
            stats["failed_adaptations"] += 1

        # Обновляем среднее улучшение
        total_attempts = stats["successful_adaptations"] + stats["failed_adaptations"]
        if total_attempts > 0:
            improvement_rate = stats["successful_adaptations"] / total_attempts
            stats["average_improvement"] = (
                stats["average_improvement"] * 0.9 + improvement_rate * 0.1
            )

    def get_strategy_recommendation(
        self, current_situation: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Возвращает рекомендации по стратегии для текущей ситуации

        Args:
            current_situation: Текущая ситуация в игре

        Returns:
            Рекомендуемые веса стратегий
        """
        base_weights = self.learning_data["strategy_weights"].copy()

        # Адаптируем веса на основе ситуации
        bricks_count = current_situation.get("bricks_remaining", 25)
        ball_speed = current_situation.get("ball_speed", 5)
        time_pressure = current_situation.get("time_pressure", False)

        # Адаптация в зависимости от количества кубиков
        if bricks_count <= 5:  # Мало кубиков - нужна точность
            base_weights["precision"] *= 1.3
            base_weights["aggressive"] *= 0.8
        elif bricks_count >= 20:  # Много кубиков - можно быть агрессивным
            base_weights["aggressive"] *= 1.2
            base_weights["precision"] *= 0.9

        # Адаптация в зависимости от скорости мяча
        if ball_speed >= 80:  # Высокая скорость - нужна быстрота
            base_weights["speed"] *= 1.3
            base_weights["conservative"] *= 0.8

        # Нормализуем веса
        total_weight = sum(base_weights.values())
        if total_weight > 0:
            base_weights = {k: v / total_weight for k, v in base_weights.items()}

        return base_weights

    def get_optimal_position_preference(self, paddle_x: int) -> float:
        """
        Возвращает предпочтительность позиции на основе исторических данных

        Args:
            paddle_x: X-координата платформы

        Returns:
            Предпочтительность позиции (0.0 - 1.0)
        """
        position_segment = int(paddle_x / 80)

        if position_segment in self.learning_data["position_preferences"]:
            return self.learning_data["position_preferences"][position_segment][
                "success_rate"
            ]

        return 0.5  # Нейтральное значение по умолчанию

    def predict_success_probability(self, action_plan: Dict[str, Any]) -> float:
        """
        Предсказывает вероятность успеха для плана действия

        Args:
            action_plan: План действия

        Returns:
            Предсказанная вероятность успеха (0.0 - 1.0)
        """
        base_probability = 0.5

        # Корректируем на основе факторов успеха
        factors = self.learning_data["success_factors"]

        # Корректировка на основе скорости мяча
        if "ball_speed" in factors:
            factor_data = factors["ball_speed"]
            if factor_data["total_cases"] > 10:
                # Простая корректировка на основе исторических данных
                speed = action_plan.get("ball_speed", 5)
                speed_factor = (
                    1.0 - abs(speed - 50) * 0.01
                )  # Оптимальная скорость около 50
                base_probability *= speed_factor

        # Корректировка на основе расстояния движения
        if "paddle_distance" in factors:
            distance = action_plan.get("movement_distance", 0)
            if distance > 100:  # Большие движения менее надежны
                base_probability *= 0.8
            elif distance < 20:  # Маленькие движения более точны
                base_probability *= 1.1

        return max(0.0, min(1.0, base_probability))

    def save_model(self):
        """Сохраняет модель в файл"""
        try:
            with open(self.model_path, "w", encoding="utf-8") as f:
                json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении модели: {e}")

    def load_model(self):
        """Загружает модель из файла"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)

                # Обновляем данные с проверкой структуры
                for key, value in loaded_data.items():
                    if key in self.learning_data:
                        self.learning_data[key] = value

            except Exception as e:
                print(f"Ошибка при загрузке модели: {e}")

    def reset_learning_data(self):
        """Сбрасывает данные обучения"""
        self.learning_data = {
            "strategy_weights": {
                "aggressive": 0.5,
                "conservative": 0.5,
                "precision": 0.5,
                "speed": 0.5,
            },
            "position_preferences": {},
            "trajectory_patterns": {},
            "success_factors": {},
            "historical_performance": [],
            "learning_stats": {
                "total_learning_iterations": 0,
                "successful_adaptations": 0,
                "failed_adaptations": 0,
                "average_improvement": 0.0,
            },
        }
        self.save_model()

    def get_learning_progress(self) -> Dict[str, Any]:
        """Возвращает прогресс обучения"""
        stats = self.learning_data["learning_stats"]

        if stats["total_learning_iterations"] == 0:
            return {"message": "Обучение еще не начато"}

        success_rate = (
            stats["successful_adaptations"] / stats["total_learning_iterations"]
        )

        return {
            "total_iterations": stats["total_learning_iterations"],
            "success_rate": success_rate,
            "average_improvement": stats["average_improvement"],
            "strategy_weights": self.learning_data["strategy_weights"],
            "learned_positions": len(self.learning_data["position_preferences"]),
            "trajectory_patterns": len(self.learning_data["trajectory_patterns"]),
        }
