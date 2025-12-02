"""
Основной класс AIPlayer для управления авторежимом игры Арканоид
"""

import pygame
import time
from typing import List, Tuple, Optional, Dict, Any
from .game_state import GameState, Point
from .trajectory_predictor import TrajectoryPredictor
from .position_optimizer import PositionOptimizer
from .learning_system import LearningSystem
from .performance_logger import PerformanceLogger


class AIPlayer:
    """
    Основной класс AIPlayer для управления авторежимом
    
    Координирует работу всех компонентов AI системы:
    - TrajectoryPredictor для предсказания траектории мяча
    - PositionOptimizer для поиска оптимальной позиции платформы
    - LearningSystem для обучения на основе опыта
    - PerformanceLogger для логирования и аналитики
    """
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600, debug_mode: bool = False):
        """
        Инициализация AIPlayer
        
        Args:
            screen_width: Ширина игрового экрана
            screen_height: Высота игрового экрана
            debug_mode: Режим отладки с визуализацией
        """
        # Инициализируем компоненты системы
        self.trajectory_predictor = TrajectoryPredictor(screen_width, screen_height)
        self.position_optimizer = PositionOptimizer(screen_width, screen_height)
        self.learning_system = LearningSystem()
        self.performance_logger = PerformanceLogger()
        
        # Параметры системы
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.debug_mode = debug_mode
        
        # Состояние AI
        self.current_game_state: Optional[GameState] = None
        self.last_paddle_position = None
        self.last_action_time = time.time()
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0
        }
        
        # Статистика текущей игры
        self.current_game_stats = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0
        }
        
        # Флаг активности
        self.is_active = False
        
    def update_game_state(self, ball, paddle, bricks, score: int, start_time: int) -> None:
        """
        Обновляет состояние игры для AI системы
        
        Args:
            ball: Объект мяча из игры
            paddle: Объект платформы из игры
            bricks: Список оставшихся кубиков
            score: Текущий счет игрока
            start_time: Время начала игры (для расчета продолжительности)
        """
        # Создаем новое состояние игры
        self.current_game_state = GameState.create_from_game_objects(
            ball, paddle, bricks, score, start_time
        )
        
        # Инициализируем статистику игры если это новая игра
        if self.current_game_stats["start_time"] is None:
            self.current_game_stats["start_time"] = start_time
            self.performance_logger.log_game_start(self.current_game_state)
        
        # Логируем предсказание траектории если включен режим отладки
        if self.debug_mode and self.is_ball_moving_towards_paddle():
            predicted_trajectory = self.trajectory_predictor.predict_trajectory(
                self.current_game_state
            )
            self.performance_logger.log_trajectory_prediction(
                [{"x": p.x, "y": p.y} for p in predicted_trajectory]
            )
    
    def is_ball_moving_towards_paddle(self) -> bool:
        """Проверяет, движется ли мяч к платформе"""
        if not self.current_game_state:
            return False
        return self.current_game_state.is_ball_falling()
    
    def get_optimal_paddle_position(self) -> int:
        """
        Получает оптимальную позицию для платформы (упрощенная и надежная версия)
        
        Returns:
            X-координата центра платформы
        """
        if not self.current_game_state or not self.is_active:
            return self.screen_width // 2  # Резервная позиция
        
        try:
            # Используем упрощенную логику для надежности
            if self.is_ball_moving_towards_paddle():
                # Для падающего мяча используем прямое предсказание
                optimal_position = self._predict_exact_landing_position()
            else:
                # Для мяча, движущегося вверх, следим за ним
                optimal_position = self._track_ball_position()
            
            return int(optimal_position)
            
        except Exception as e:
            print(f"Ошибка при расчете оптимальной позиции: {e}")
            # Резервная логика - простое следование за мячом
            return int(self.current_game_state.ball_position.x)
    
    def _predict_exact_landing_position(self) -> float:
        """Точное предсказание позиции приземления мяча на платформу"""
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y
        
        # Рассчитываем время до достижения платформы
        time_to_paddle = (paddle_y - ball_y) / vel_y
        
        if time_to_paddle <= 0:
            return ball_x
        
        # Предсказываем траекторию с учетом отскоков от стен
        predicted_x = ball_x + vel_x * time_to_paddle
        screen_width = self.screen_width
        ball_radius = 8
        
        # Моделируем отскоки от стен
        while predicted_x < ball_radius or predicted_x > screen_width - ball_radius:
            if predicted_x < ball_radius:
                predicted_x = 2 * ball_radius - predicted_x
            elif predicted_x > screen_width - ball_radius:
                predicted_x = 2 * (screen_width - ball_radius) - predicted_x
        
        return predicted_x
    
    def _track_ball_position(self) -> float:
        """Следим за текущей позицией мяча с упреждающим движением"""
        ball_x = self.current_game_state.ball_position.x
        vel_x = self.current_game_state.ball_velocity.x
        
        # Добавляем упреждающее движение
        prediction_time = 3  # Упреждение на 3 кадра
        predicted_x = ball_x + vel_x * prediction_time
        
        # Ограничиваем предсказание границами экрана
        screen_width = self.screen_width
        ball_radius = 8
        min_x = ball_radius
        max_x = screen_width - ball_radius
        
        return max(min_x, min(max_x, predicted_x))
    
    def move_paddle_towards(self, current_x: int, paddle_speed: int) -> int:
        """
        Двигает платформу к оптимальной позиции
        
        Args:
            current_x: Текущая X-координата платформы
            paddle_speed: Скорость движения платформы
            
        Returns:
            Смещение платформы (-1, 0, 1)
        """
        if not self.current_game_state or not self.is_active:
            # Резервное движение: просто следует за мячом если AI не инициализирован
            return self._fallback_movement(current_x)
        
        try:
            optimal_x = self.get_optimal_paddle_position()
            
            # Рассчитываем движение
            movement = self.position_optimizer.calculate_paddle_movement(
                current_x, optimal_x, paddle_speed
            )
            
            # Если нет движения, но AI активен, попробуем резервное движение
            if movement == 0 and optimal_x != current_x:
                movement = self._fallback_movement(current_x)
            
            # Логируем движение платформы
            if movement != 0:
                reason = "ball_tracking" if not self.is_ball_moving_towards_paddle() else "trajectory_optimization"
                confidence = self._calculate_decision_confidence(optimal_x)
                self.performance_logger.log_paddle_movement(
                    from_x=current_x,
                    to_x=current_x + movement * paddle_speed,
                    reason=reason,
                    confidence=confidence
                )
                
                # Обновляем статистику текущей игры
                self.current_game_stats["total_moves"] += 1
                if abs(optimal_x - current_x) < 10:  # Точное попадание
                    self.current_game_stats["optimal_moves"] += 1
            
            return movement
            
        except Exception as e:
            print(f"Ошибка при движении платформы: {e}")
            # Резервное движение при ошибках
            return self._fallback_movement(current_x)
    
    def _fallback_movement(self, current_x: int) -> int:
        """
        Резервное движение платформы - улучшенное следование за мячом
        
        Args:
            current_x: Текущая X-координата платформы
            
        Returns:
            Смещение платформы (-1, 0, 1)
        """
        if not self.current_game_state:
            return 0
        
        # Получаем данные о мяче
        ball_x = self.current_game_state.ball_position.x
        ball_y = self.current_game_state.ball_position.y
        vel_x = self.current_game_state.ball_velocity.x
        vel_y = self.current_game_state.ball_velocity.y
        paddle_y = self.current_game_state.paddle_position.y
        
        # Если мяч падает, предсказываем траекторию до платформы
        if vel_y > 0:
            time_to_paddle = (paddle_y - ball_y) / vel_y
            
            if time_to_paddle > 0:
                # Предсказываем точную позицию попадания
                predicted_x = ball_x + vel_x * time_to_paddle
                
                # Учитываем отскоки от стен
                screen_width = self.screen_width
                ball_radius = 8
                
                # Простое моделирование отскоков
                while predicted_x < ball_radius or predicted_x > screen_width - ball_radius:
                    if predicted_x < ball_radius:
                        predicted_x = 2 * ball_radius - predicted_x
                        vel_x = abs(vel_x)
                    elif predicted_x > screen_width - ball_radius:
                        predicted_x = 2 * (screen_width - ball_radius) - predicted_x
                        vel_x = -abs(vel_x)
                
                target_x = predicted_x
            else:
                target_x = ball_x
        else:
            # Мяч движется вверх, следим за ним напрямую
            # Добавляем упреждение на основе скорости
            prediction_factor = abs(vel_x) * 2
            
            if vel_x > 0:
                target_x = ball_x + prediction_factor
            elif vel_x < 0:
                target_x = ball_x - prediction_factor
            else:
                target_x = ball_x
        
        # Рассчитываем движение с высокой чувствительностью
        distance = target_x - current_x
        tolerance = 3  # Очень точный контроль
        
        if abs(distance) <= tolerance:
            return 0
        elif distance > 0:
            return 1
        else:
            return -1
    
    def _is_time_pressure(self) -> bool:
        """Определяет, есть ли временное давление (мало времени/жизней)"""
        if not self.current_game_state:
            return False
        
        # Проверяем время игры (больше 5 минут = давление)
        game_time = self.current_game_state.game_time
        if game_time > 300:  # 5 минут
            return True
        
        # Проверяем количество оставшихся кубиков (меньше 5 = давление)
        if len(self.current_game_state.remaining_bricks) <= 5:
            return True
        
        return False
    
    def _calculate_decision_confidence(self, target_position: int) -> float:
        """
        Рассчитывает уверенность в принятом решении
        
        Args:
            target_position: Целевая позиция
            
        Returns:
            Уровень уверенности (0.0 - 1.0)
        """
        if not self.current_game_state:
            return 0.5
        
        # Базовая уверенность
        confidence = 0.7
        
        # Корректируем на основе количества кубиков
        bricks_count = len(self.current_game_state.remaining_bricks)
        if bricks_count <= 5:  # Мало кубиков = больше важность
            confidence += 0.1
        elif bricks_count >= 20:  # Много кубиков = больше вариантов
            confidence -= 0.1
        
        # Корректируем на основе скорости мяча
        ball_speed = self.current_game_state.ball_speed
        if ball_speed >= 8:  # Высокая скорость = сложнее
            confidence -= 0.1
        elif ball_speed <= 3:  # Низкая скорость = проще
            confidence += 0.1
        
        return max(0.1, min(1.0, confidence))
    
    def learn_from_result(self, action_result: Dict[str, Any]) -> None:
        """
        Обучает AI систему на основе результата действия
        
        Args:
            action_result: Результат последнего действия
        """
        if not self.current_game_state:
            return
        
        # Добавляем контекст к результату
        enhanced_result = action_result.copy()
        enhanced_result.update({
            "game_state_before": {
                "ball_position": {
                    "x": self.current_game_state.ball_position.x,
                    "y": self.current_game_state.ball_position.y
                },
                "paddle_position": {
                    "x": self.current_game_state.paddle_position.x,
                    "y": self.current_game_state.paddle_position.y
                },
                "bricks_remaining": len(self.current_game_state.remaining_bricks),
                "ball_speed": self.current_game_state.ball_speed
            },
            "trajectory_prediction": self._get_current_trajectory_prediction()
        })
        
        # Обновляем систему обучения
        self.learning_system.update_strategy(enhanced_result)
        
        # Логируем результат
        self.performance_logger.log_action(enhanced_result)
        
        # Обновляем метрики производительности
        self._update_performance_metrics(action_result)
    
    def _get_current_trajectory_prediction(self) -> Optional[Dict]:
        """Получает текущее предсказание траектории"""
        if not self.current_game_state or not self.is_ball_moving_towards_paddle():
            return None
        
        try:
            trajectory = self.trajectory_predictor.predict_trajectory(self.current_game_state)
            return {
                "predicted_points": [{"x": p.x, "y": p.y} for p in trajectory],
                "intersection_point": self.trajectory_predictor.predict_paddle_intersection(
                    self.current_game_state, self.current_game_state.paddle_position.y
                )
            }
        except:
            return None
    
    def _update_performance_metrics(self, action_result: Dict[str, Any]) -> None:
        """Обновляет метрики производительности"""
        success = action_result.get("success", False)
        
        if success:
            self.current_game_stats["successful_predictions"] += 1
            if "bricks_destroyed" in action_result:
                self.current_game_stats["bricks_destroyed"] += len(action_result["bricks_destroyed"])
        
        self.current_game_stats["total_predictions"] += 1
        
        # Обновляем общую статистику
        if "final_score" in action_result:
            self.performance_metrics["total_score"] += action_result["final_score"]
    
    def on_game_end(self, success: bool, final_score: int) -> None:
        """
        Обрабатывает окончание игры
        
        Args:
            success: Успешное завершение игры (все кубики сбиты)
            final_score: Итоговый счет
        """
        self.performance_metrics["games_played"] += 1
        
        if success:
            self.performance_metrics["games_won"] += 1
        
        # Обновляем среднюю точность
        if self.current_game_stats["total_predictions"] > 0:
            accuracy = (self.current_game_stats["successful_predictions"] / 
                       self.current_game_stats["total_predictions"])
            self.performance_metrics["average_accuracy"] = (
                (self.performance_metrics["average_accuracy"] * 0.9) + (accuracy * 0.1)
            )
        
        # Получаем прогресс обучения
        learning_progress = self.learning_system.get_learning_progress()
        self.performance_metrics["learning_progress"] = learning_progress.get("success_rate", 0.0)
        
        # Логируем окончание игры
        self.performance_logger.log_game_end(
            self.current_game_state, success, final_score
        )
        
        # Сохраняем метрики
        self.performance_logger.log_performance_metrics(self.performance_metrics)
        
        # Сбрасываем статистику текущей игры
        self.current_game_stats = {
            "start_time": None,
            "bricks_destroyed": 0,
            "successful_predictions": 0,
            "total_predictions": 0,
            "optimal_moves": 0,
            "total_moves": 0
        }
    
    def activate(self) -> None:
        """Активирует AI систему"""
        self.is_active = True
        self.performance_logger.log_action({
            "type": "ai_activated",
            "timestamp": time.time()
        })
    
    def deactivate(self) -> None:
        """Деактивирует AI систему"""
        self.is_active = False
        self.performance_logger.log_action({
            "type": "ai_deactivated",
            "timestamp": time.time()
        })
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Возвращает отчет о производительности AI"""
        return {
            "performance_metrics": self.performance_metrics,
            "learning_progress": self.learning_system.get_learning_progress(),
            "session_report": self.performance_logger.generate_performance_report(),
            "recent_trends": self.performance_logger.analyze_trends()
        }
    
    def visualize_debug_info(self, screen: pygame.Surface) -> None:
        """
        Отображает отладочную информацию на экране
        
        Args:
            screen: Surface для отрисовки
        """
        if not self.debug_mode or not self.current_game_state:
            return
        
        try:
            # Рисуем предсказанную траекторию
            if self.is_ball_moving_towards_paddle():
                trajectory = self.trajectory_predictor.predict_trajectory(self.current_game_state)
                self.trajectory_predictor.visualize_trajectory(screen, trajectory, (255, 255, 0))
            
            # Отображаем оптимальную позицию
            optimal_x = self.get_optimal_paddle_position()
            pygame.draw.line(screen, (0, 255, 0), 
                           (optimal_x, 0), (optimal_x, self.screen_height), 2)
            
            # Показываем информацию об AI
            font = pygame.font.SysFont("arial", 16)
            info_text = f"AI: {len(self.current_game_state.remaining_bricks)} кубиков"
            text_surface = font.render(info_text, True, (255, 255, 0))
            screen.blit(text_surface, (10, 10))
            
        except Exception as e:
            print(f"Ошибка при визуализации: {e}")
    
    def save_learning_data(self) -> None:
        """Сохраняет данные обучения"""
        self.learning_system.save_model()
        self.performance_logger.save_session_log()
    
    def reset_learning(self) -> None:
        """Сбрасывает данные обучения"""
        self.learning_system.reset_learning_data()
        self.performance_logger.clear_session_data()
        
        # Сбрасываем метрики
        self.performance_metrics = {
            "games_played": 0,
            "games_won": 0,
            "total_score": 0,
            "average_accuracy": 0.0,
            "learning_progress": 0.0
        }
