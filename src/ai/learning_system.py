"""
Модуль системы обучения для AI с кластеризацией траекторий и обработкой промпта
"""

import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional
import math
from collections import defaultdict
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np


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


class LearningSystem:
    """Система обучения для AI"""

    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)

        # Определяем путь к модели
        if model_path is None:
            ai_dir = get_ai_directory()
            models_dir = os.path.join(ai_dir, "models")
            model_path = os.path.join(models_dir, "ai_model.json")

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
            "success_prediction_model": None,  # Модель для предсказания успеха
            "paddle_speed_factors": {},  # Факторы скорости платформы по скорости мяча
        }

        # Создаем директорию для модели если её нет
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        except (OSError, PermissionError) as e:
            # Если не удается создать каталог, используем текущую директорию
            print(
                f"Предупреждение: не удалось создать каталог модели {os.path.dirname(self.model_path)}: {e}"
            )
            # Fallback: используем текущую директорию
            self.model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "models", "ai_model.json"
            )
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # Загружаем существующую модель если она есть
        self.load_model()

    def update_strategy(self, action_result: Dict[str, Any]):
        """
        Обновляет стратегию на основе результата действия

        Args:
            action_result: Результат последнего действия

        Raises:
            ValueError: Если action_result не является словарем или пуст.
        """
        # Проверка входных данных
        if not isinstance(action_result, dict):
            raise ValueError("action_result должен быть словарем")

        if not action_result:
            raise ValueError("action_result не может быть пустым")

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

        # Периодически обучаем модель предсказания успеха
        if self.learning_data["learning_stats"]["total_learning_iterations"] % 100 == 0:
            self._train_success_prediction_model()

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
            ball_pos = action_result.get("game_state_before", {}).get(
                "ball_position", {}
            )
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

        if not predicted_points:
            return

        # Создаем ключ паттерна для кластеризации
        pattern_key = self._create_trajectory_pattern_key(predicted_points[:3])

        if pattern_key not in self.learning_data["trajectory_patterns"]:
            self.learning_data["trajectory_patterns"][pattern_key] = {
                "accuracy_scores": [],
                "success_rates": [],
                "pattern_frequency": 0,
            }

        pattern = self.learning_data["trajectory_patterns"][pattern_key]
        pattern["pattern_frequency"] += 1

        # Рассчитываем точность только если есть actual_points
        if actual_points:
            accuracy = self._calculate_trajectory_accuracy(
                predicted_points, actual_points
            )
            pattern["accuracy_scores"].append(accuracy)
            pattern["success_rates"].append(1.0 if success else 0.0)

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
            distance_error = math.sqrt(
                (pred_x - actual_x) ** 2 + (pred_y - actual_y) ** 2
            )
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

    def _train_success_prediction_model(self):
        """Обучает модель предсказания успеха на основе исторических данных"""
        factors = self.learning_data["success_factors"]
        if not factors or len(factors) < 2:
            return

        # Собираем данные для обучения
        X = []
        y = []

        for factor_name, factor_data in factors.items():
            if factor_data["total_cases"] < 10:
                continue

            values = factor_data["factor_values"]
            successes = factor_data["successful_cases"]
            total = factor_data["total_cases"]

            # Создаем признаки: фактор, успех/неуспех
            for i, val in enumerate(values):
                # Простой бинарный таргет: успех если фактор привел к успеху
                # Это упрощение; в реальности нужно связывать с конкретными действиями
                success_rate = successes / total
                target = 1 if np.random.random() < success_rate else 0  # Упрощение
                X.append([val])
                y.append(target)

        if len(X) < 10:
            return

        X = np.array(X)
        y = np.array(y)

        # Разделяем на train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Обучаем модель
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)

        # Оцениваем
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        self.logger.info(
            f"Success prediction model trained with accuracy: {accuracy:.2f}"
        )

        self.learning_data["success_prediction_model"] = model

    def cluster_trajectories(self, n_clusters=5):
        """Кластеризует траектории на основе начальных точек"""
        if not self.learning_data["trajectory_patterns"]:
            return []

        pattern_keys = list(self.learning_data["trajectory_patterns"].keys())
        vectors = []
        for key in pattern_keys:
            try:
                coords = [int(x) for x in key.split("_")]
                # Дополняем до 6 элементов нулями или усекаем
                while len(coords) < 6:
                    coords.append(0)
                vectors.append(coords[:6])
            except ValueError:
                # Пропускаем некорректные ключи
                continue

        if len(vectors) < 2:  # Нужно минимум 2 точки для кластеризации
            return []

        if len(vectors) < n_clusters:
            n_clusters = len(vectors)

        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(vectors)
        except Exception as e:
            self.logger.warning(f"Ошибка кластеризации: {e}")
            return []

        return [
            {"pattern": pattern_keys[i], "cluster": clusters[i]}
            for i in range(len(clusters))
        ]

    def _calculate_cluster_diversity(self, trajectory_clusters: List[Dict]) -> float:
        """Рассчитывает разнообразие кластеров траекторий"""
        if not trajectory_clusters:
            return 0.0

        cluster_counts = {}
        for item in trajectory_clusters:
            cluster = item["cluster"]
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

        total_patterns = len(trajectory_clusters)
        entropy = 0.0

        for count in cluster_counts.values():
            probability = count / total_patterns
            if probability > 0:
                entropy -= probability * math.log2(probability)

        # Нормализуем энтропию (максимальная энтропия = log2(число кластеров))
        max_entropy = math.log2(len(cluster_counts)) if cluster_counts else 1.0
        diversity = entropy / max_entropy if max_entropy > 0 else 0.0

        return diversity

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
            return self.learning_data["position_preferences"][position_segment][
                "success_rate"
            ]

        return 0.5

    def predict_success_probability(self, action_plan: Dict[str, Any]) -> float:
        """
        Предсказывает вероятность успеха для плана действия

        Args:
            action_plan: План действия

        Returns:
            Предсказанная вероятность успеха (0.0 - 1.0)
        """
        model = self.learning_data.get("success_prediction_model")
        if model is not None:
            # Используем ML модель
            features = np.array(
                [
                    [
                        action_plan.get("ball_speed", 5),
                        action_plan.get("movement_distance", 0),
                        action_plan.get("confidence", 0.5),
                    ]
                ]
            )
            try:
                proba = model.predict_proba(features)[0][1]  # Вероятность успеха
                return float(proba)
            except Exception as e:
                self.logger.warning(f"Ошибка предсказания модели: {e}")

        # Fallback к простому расчету
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

    def get_adaptive_paddle_speed(
        self, ball_speed: int, distance_to_target: float
    ) -> float:
        """
        Возвращает адаптивную скорость платформы на основе скорости мяча и расстояния до цели

        Args:
            ball_speed: Скорость мяча
            distance_to_target: Расстояние до целевой позиции (пиксели)

        Returns:
            Множитель скорости платформы (1.0 = базовая скорость)
        """
        # Квантуем скорость мяча для группировки
        speed_category = (ball_speed // 5) * 5  # Группируем по 5 единиц

        if speed_category not in self.learning_data["paddle_speed_factors"]:
            self.learning_data["paddle_speed_factors"][speed_category] = {
                "speed_multipliers": [],
                "success_cases": 0,
                "total_cases": 0,
            }

        factors = self.learning_data["paddle_speed_factors"][speed_category]

        # Если есть исторические данные, используем среднее
        if factors["speed_multipliers"]:
            avg_multiplier = sum(factors["speed_multipliers"]) / len(
                factors["speed_multipliers"]
            )
            # Корректируем на основе расстояния (чем больше расстояние, тем выше скорость)
            distance_factor = min(
                3.0, distance_to_target / 200.0
            )  # Макс 3x для расстояния > 600px
            return max(0.5, min(5.0, avg_multiplier * distance_factor))

        # Базовый расчет: скорость платформы пропорциональна скорости мяча
        base_multiplier = max(
            1.0, ball_speed / 10.0
        )  # Минимум 1x, растет с скоростью мяча
        distance_factor = min(3.0, distance_to_target / 200.0)
        return max(0.5, min(5.0, base_multiplier * distance_factor))

    def update_paddle_speed_feedback(
        self, ball_speed: int, speed_multiplier: float, success: bool
    ):
        """
        Обновляет данные о скорости платформы на основе результата

        Args:
            ball_speed: Скорость мяча
            speed_multiplier: Использованный множитель скорости
            success: Успешность движения

        Raises:
            ValueError: Если ball_speed или speed_multiplier некорректны.
        """
        # Проверка входных данных
        if ball_speed < 0:
            raise ValueError("ball_speed не может быть отрицательным")

        if speed_multiplier <= 0:
            raise ValueError("speed_multiplier должен быть положительным")

        speed_category = (ball_speed // 5) * 5

        if speed_category not in self.learning_data["paddle_speed_factors"]:
            self.learning_data["paddle_speed_factors"][speed_category] = {
                "speed_multipliers": [],
                "success_cases": 0,
                "total_cases": 0,
            }

        factors = self.learning_data["paddle_speed_factors"][speed_category]
        factors["total_cases"] += 1

        if success:
            factors["success_cases"] += 1
            factors["speed_multipliers"].append(speed_multiplier)

        # Ограничиваем размер списка
        if len(factors["speed_multipliers"]) > 50:
            # Оставляем только успешные множители
            factors["speed_multipliers"] = factors["speed_multipliers"][-25:]

    def save_model(self):
        """Сохраняет модель в файл"""
        try:
            # Создаем копию данных без ML модели (она не сериализуема в JSON)
            save_data = self.learning_data.copy()
            save_data["success_prediction_model"] = None  # ML модель не сохраняем

            with open(self.model_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            self.logger.info("Модель сохранена успешно")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении модели: {e}")

    def load_model(self):
        """Загружает модель из файла"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)

                for key, value in loaded_data.items():
                    if key in self.learning_data:
                        self.learning_data[key] = value

                self.logger.info("Модель загружена успешно")
            except Exception as e:
                self.logger.error(f"Ошибка при загрузке модели: {e}")

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
            "success_prediction_model": None,
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

        # Анализ кластеров траекторий
        trajectory_clusters = self.cluster_trajectories()
        unique_clusters = (
            len(set(cluster["cluster"] for cluster in trajectory_clusters))
            if trajectory_clusters
            else 0
        )
        cluster_diversity = self._calculate_cluster_diversity(trajectory_clusters)

        return {
            "total_iterations": stats["total_learning_iterations"],
            "success_rate": success_rate,
            "average_improvement": stats["average_improvement"],
            "strategy_weights": self.learning_data["strategy_weights"],
            "learned_positions": len(self.learning_data["position_preferences"]),
            "trajectory_patterns": len(self.learning_data["trajectory_patterns"]),
            "trajectory_clusters_count": unique_clusters,
            "cluster_diversity": cluster_diversity,
        }
